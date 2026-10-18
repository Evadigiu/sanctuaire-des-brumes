-- ============================================================
-- CORRECTIF 13 — Plus de chrono de 3 h ; le code s'eteint a la fin
--
-- Les groupes visitent le zoo en meme temps qu'ils jouent, et beaucoup
-- depassaient les 3 h : ils etaient coupes avant la fin. Desormais :
--   - une partie vaut jusqu'a MINUIT (heure de Paris) le jour de son
--     activation : personne n'est coupe pendant sa visite, et un code ne
--     peut pas resservir un autre jour ;
--   - elle s'eteint 30 MINUTES APRES LA REPONSE FINALE a la serre : un
--     code fini ne rouvre plus rien, ni pour ce groupe ni pour un autre.
--
-- A SAVOIR : un code active n'est pas lie a un seul telephone. Tant que la
-- partie est ouverte, le meme code la rouvre sur un autre telephone (c'est
-- voulu : telephone vide, parent qui prend le relais, QR ouvert dans une
-- autre fenetre). C'est la fin de partie qui le grille.
--
-- On peut le relancer sans danger. Les fonctions sont reprises a
-- l'identique des correctifs 6 et 9, seules les lignes commentees changent.
-- ============================================================


-- 1. L'ACTIVATION : fin a minuit au lieu de 3 h.
create or replace function activer_code(p_code text, p_nb_joueurs int default null)
returns json
language plpgsql
security definer                 -- s'execute avec les droits du proprietaire
set search_path = public
as $$
declare
  v_code       text := upper(trim(coalesce(p_code, '')));
  v_origine    text;
  v_tentatives int;
  v_row        codes%rowtype;
  v_fin        timestamptz;
begin
  if v_code = '' then
    return json_build_object('ok', false,
      'message', 'Saisissez le code inscrit sur votre billet.');
  end if;

  -- D'ou vient la demande. Si l'information manque, on ne compte pas :
  -- mieux vaut un garde-fou en moins qu'un joueur bloque a la caisse.
  begin
    v_origine := split_part(
      current_setting('request.headers', true)::json ->> 'x-forwarded-for', ',', 1);
  exception when others then
    v_origine := null;
  end;

  if v_origine is not null and v_origine <> '' then
    v_tentatives := (select count(*) from tentatives_activation
                      where origine = v_origine
                        and tente_le > now() - interval '1 hour');

    if v_tentatives >= 100 then
      return json_build_object('ok', false,
        'message', 'Trop d''essais depuis cet appareil. Patientez une heure, ou adressez-vous à l''accueil du zoo.');
    end if;
  end if;

  -- "for update" met la ligne de cote le temps de la decision : deux
  -- telephones ne peuvent pas activer le meme code au meme instant.
  --
  -- On met de cote, PUIS on lit, en deux temps. Ecrit d'un seul trait,
  -- "select ... into v_row", cela voudrait dire "range le resultat dans
  -- v_row" ici, mais "cree une table nommee v_row" en SQL ordinaire.
  -- L'assistant de Supabase lit la seconde version, croit voir une table
  -- sans protection et va inserer un "alter table" au milieu de la
  -- fonction, ce qui la casse. Ces deux lignes evitent le malentendu.
  perform 1 from codes where code = v_code for update;

  if not found then
    delete from tentatives_activation where tente_le < now() - interval '1 day';
    insert into tentatives_activation (origine) values (v_origine);
    return json_build_object('ok', false,
      'message', 'Ce code n''existe pas. Vérifiez la saisie, ou demandez de l''aide à l''accueil.');
  end if;

  v_row := (select c from codes c where c.code = v_code);

  -- Code deja consomme : marque expire, ou sa fin est passee (minuit le jour
  -- de l'activation, ou 30 minutes apres la reponse finale).
  if v_row.status = 'expired'
     or (v_row.expires_at is not null and v_row.expires_at <= now()) then
    return json_build_object('ok', false,
      'message', 'Ce code a déjà servi et sa partie est terminée. Adressez-vous à l''accueil du zoo.');
  end if;

  -- Partie en cours : on la rend plutot que de refuser. Utile quand le
  -- telephone se recharge, se vide, ou change de mains dans le groupe.
  if v_row.status = 'active' then
    return json_build_object('ok', true,
      'code_id',    v_row.id,
      'code',       v_row.code,
      'direction',  v_row.direction,
      'expires_at', v_row.expires_at);
  end if;

  -- Reste le cas 'unused' : premiere activation.
  if p_nb_joueurs is not null and p_nb_joueurs < 1 then
    return json_build_object('ok', false,
      'message', 'Indiquez le nombre de joueurs de votre équipe.');
  end if;

  if p_nb_joueurs is not null and p_nb_joueurs > v_row.max_participants then
    return json_build_object('ok', false,
      'message', case when v_row.max_participants = 1
                      then 'Ce billet ne couvre qu''une seule personne.'
                      else 'Ce billet couvre ' || v_row.max_participants ||
                           ' personnes au maximum.' end ||
                 ' Corrigez le nombre, ou demandez un second code à l''accueil.');
  end if;

  -- Plus de chrono de 3 h : la partie vaut jusqu'a minuit (heure de
  -- Paris) le jour de l'activation. Elle s'eteint plus tot, 30 minutes
  -- apres la reponse finale (voir enregistrer_conclusions).
  v_fin := ((now() at time zone 'Europe/Paris')::date + 1)::timestamp
           at time zone 'Europe/Paris';

  update codes
     set status             = 'active',
         activated_at       = now(),
         expires_at         = v_fin,
         participants_reels = coalesce(p_nb_joueurs, participants_reels)
   where id = v_row.id;

  return json_build_object('ok', true,
    'code_id',    v_row.id,
    'code',       v_row.code,
    'direction',  v_row.direction,
    'expires_at', v_fin);
end;
$$;

grant execute on function activer_code(text, int) to anon, authenticated;


-- 2. LA REPONSE FINALE : le code s'eteint 30 minutes apres.
create or replace function enregistrer_conclusions(
  p_code_id uuid,
  p_texte text,
  p_denouement text
) returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_ok boolean;
  v_texte text;
begin
  -- 1. La partie existe-t-elle, et a-t-elle ete activee ?
  select true into v_ok
    from codes
   where id = p_code_id and status in ('active', 'expired')
   limit 1;
  if v_ok is not true then
    return json_build_object('ok', false, 'message', 'Partie inconnue.');
  end if;

  -- 2. On borne le texte. Un champ libre sur un site public finit
  --    toujours par recevoir autre chose que des conclusions d'enquete.
  v_texte := left(coalesce(p_texte, ''), 2000);
  if length(btrim(v_texte)) = 0 then
    return json_build_object('ok', false, 'message', 'Conclusions vides.');
  end if;

  -- 3. Une seule reddition par partie. Le groupe qui recharge sa page ne
  --    doit pas remplir la table de doublons.
  if exists (select 1 from conclusions where code_id = p_code_id) then
    return json_build_object('ok', true, 'deja_rendu', true);
  end if;

  insert into conclusions (code_id, submitted_text, ai_verdict)
  values (p_code_id, v_texte, left(coalesce(p_denouement, ''), 20));

  -- L'enquete est finie : le code s'eteint 30 minutes plus tard, le temps
  -- de lire le denouement, de passer au photocall, de revoir un temoignage.
  -- Apres, il ne rouvre plus rien, ni pour ce groupe ni pour un autre.
  update codes
     set expires_at = least(coalesce(expires_at, now() + interval '30 minutes'),
                            now() + interval '30 minutes')
   where id = p_code_id;

  return json_build_object('ok', true);
end;
$$;

revoke all on function enregistrer_conclusions(uuid, text, text) from public;
grant execute on function enregistrer_conclusions(uuid, text, text)
  to anon, authenticated;


-- 3. LES PARTIES DEJA COMMENCEES AUJOURD'HUI
-- Celles encore ouvertes, et celles coupees par les 3 h sans avoir rendu
-- leurs conclusions, valent jusqu'a ce soir minuit. Les telephones le
-- verront a leur prochaine borne (le site redemande l'heure de fin a la
-- base a chaque borne).
update codes c
   set expires_at = ((now() at time zone 'Europe/Paris')::date + 1)::timestamp
                    at time zone 'Europe/Paris',
       status = 'active'
 where c.activated_at is not null
   and (c.activated_at at time zone 'Europe/Paris')::date
       = (now() at time zone 'Europe/Paris')::date
   and not exists (select 1 from conclusions co where co.code_id = c.id);


-- CONTROLE : les parties du jour et leur nouvelle fin (heure de Paris).
select right(code, 4) as code,
       to_char(activated_at at time zone 'Europe/Paris', 'HH24:MI') as depart,
       to_char(expires_at   at time zone 'Europe/Paris', 'DD/MM HH24:MI') as fin
  from codes
 where activated_at is not null
   and (activated_at at time zone 'Europe/Paris')::date
       = (now() at time zone 'Europe/Paris')::date
 order by activated_at desc;
