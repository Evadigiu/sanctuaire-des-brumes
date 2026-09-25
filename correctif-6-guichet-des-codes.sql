-- ============================================================
-- CORRECTIF 6 — LE GUICHET DES CODES
-- Le Sanctuaire des Brumes — a lancer AVANT de generer les vrais codes.
--
-- COMMENT LE LANCER
--   Supabase > SQL Editor > New query > coller ce fichier entier > Run.
--   Il peut etre relance sans risque : chaque morceau verifie d'abord si
--   le travail est deja fait.
--
--   >>> UN AVERTISSEMENT VA S'AFFICHER : "Potential issue detected, this
--   query creates tables without enabling Row Level Security". REPONDRE
--   "RUN WITHOUT RLS", le bouton orange. <<<
--
--   C'est un faux positif. Le detecteur de Supabase lit le nom des
--   variables internes des fonctions (v_row, v_tentatives) et croit y voir
--   des tables a proteger. S'il a l'autorisation, il ajoute deux lignes
--   "ALTER TABLE ... ENABLE ROW LEVEL SECURITY" AU MILIEU d'une fonction,
--   ce qui la casse : la requete entiere est refusee (erreur a "as $$") et
--   rien n'est applique.
--
--   La seule table creee ici est verrouillee par le fichier lui-meme, a la
--   section 1 : "enable row level security" puis "revoke all". Le
--   garde-fou reclame est deja en place.
--
-- ATTENTION : ce correctif et la mise a jour du site vont ENSEMBLE.
-- Lance-le le jour ou tu fusionnes la branche, pas avant : entre les deux,
-- l'activation des codes ne marche plus.
--
--
-- CE QU'IL CORRIGE
--
--   TROU 1 — N'importe qui pouvait lire la liste complete des codes depuis
--   son telephone, y compris ceux pas encore vendus. Donc jouer gratuitement.
--
--   TROU 2 — N'importe qui pouvait ecrire dans la table des codes. Une seule
--   requete suffisait a passer TOUS les codes en "utilise et expire" :
--   l'integralite des billets imprimes devenait inutilisable, un matin, d'un
--   coup. Et chaque joueur ecrivait lui-meme la fin de son chrono.
--
--   TROU 3 — non documente jusqu'ici. La table des passages acceptait
--   n'importe quelle ecriture, sans verification. Un joueur pouvait donc
--   inscrire d'un coup ses seize passages de bornes et deverrouiller tout
--   le parcours sans marcher, ou simplement fausser les statistiques.
--
--
-- LE PRINCIPE : LE GUICHET
--
-- Aujourd'hui le joueur entre lui-meme dans le bureau et se sert dans les
-- dossiers. Apres ce correctif, le bureau est ferme : il y a un guichet.
-- Le joueur glisse sa demande ("voici mon code, nous sommes quatre"), la
-- base verifie et ecrit elle-meme. Il ne touche plus jamais aux dossiers.
--
-- C'est exactement le mecanisme du correctif 5 (le bouton "traite" des
-- signalements), en plus gros. Il a servi de banc d'essai.
-- ============================================================


-- ------------------------------------------------------------
-- 1. LE REGISTRE DES ESSAIS RATES
--
-- Sans la liste des codes sous les yeux, il reste a les deviner. On compte
-- donc les echecs, et au-dela de 100 en une heure depuis la meme connexion,
-- le guichet se ferme a cette connexion.
--
-- POURQUOI 100 ET PAS 5 : au zoo, tout le monde passe par le meme wifi, et
-- les reseaux mobiles font partager une meme adresse a des milliers de
-- clients. Une limite serre bloquerait des joueurs qui ont paye, a cause des
-- fautes de frappe des autres. Le vrai rempart n'est pas ce compteur, c'est
-- la longueur des codes (correctif 7) : 100 essais a l'heure contre mille
-- milliards de combinaisons, c'est perdu d'avance pour le curieux.
--
-- Cette table n'est ouverte a personne : ni lecture, ni ecriture, ni droit
-- d'acces. Seul le guichet y touche, parce qu'il travaille avec les droits
-- du proprietaire de la base.
-- ------------------------------------------------------------
create table if not exists tentatives_activation (
  id        uuid primary key default gen_random_uuid(),
  origine   text,
  tente_le  timestamptz not null default now()
);

alter table tentatives_activation enable row level security;

create index if not exists idx_tentatives_origine
  on tentatives_activation (origine, tente_le desc);

-- Ceinture et bretelles : la regle RLS ci-dessus suffit a cacher les lignes,
-- mais on retire aussi le droit d'acces. Une table dont personne n'a besoin
-- ne doit figurer dans aucune liste.
revoke all on table tentatives_activation from anon, authenticated;


-- ------------------------------------------------------------
-- 2. LE GUICHET D'ACTIVATION
--
-- Le site ne dit plus "donne-moi la ligne du code TEST01" mais "voici un
-- code, ouvre-moi une partie si tu peux". La base repond par un oui ou un
-- non accompagne d'une phrase affichable telle quelle a l'ecran.
--
-- Trois choses changent au passage, en plus de la securite :
--   * le chrono de 3h est desormais calcule par la base, plus par le
--     telephone du joueur. Changer l'heure de son portable ne donne plus
--     de rallonge ;
--   * un groupe qui annonce plus de personnes que son billet n'en couvre
--     est refuse, avec le nombre prevu dans le message ;
--   * deux telephones qui activent le meme code en meme temps ne se
--     marchent plus dessus : le second recoit la partie ouverte par le
--     premier au lieu d'un message d'erreur.
-- ------------------------------------------------------------
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
      'message', 'Entre le code inscrit sur ton billet.');
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
    select count(*) into v_tentatives
      from tentatives_activation
     where origine = v_origine
       and tente_le > now() - interval '1 hour';

    if v_tentatives >= 100 then
      return json_build_object('ok', false,
        'message', 'Trop d''essais depuis cet appareil. Attends une heure ou adresse-toi a l''accueil du zoo.');
    end if;
  end if;

  -- "for update" met la ligne de cote le temps de la decision : deux
  -- telephones ne peuvent pas activer le meme code au meme instant.
  select * into v_row from codes where code = v_code for update;

  if not found then
    delete from tentatives_activation where tente_le < now() - interval '1 day';
    insert into tentatives_activation (origine) values (v_origine);
    return json_build_object('ok', false,
      'message', 'Ce code n''existe pas. Verifie la saisie ou demande a l''accueil.');
  end if;

  -- Code deja consomme : soit marque expire, soit active il y a plus de 3h.
  if v_row.status = 'expired'
     or (v_row.expires_at is not null and v_row.expires_at <= now()) then
    return json_build_object('ok', false,
      'message', 'Ce code a deja servi et sa partie est terminee. Adresse-toi a l''accueil du zoo.');
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
  if p_nb_joueurs is not null
     and (p_nb_joueurs < 1 or p_nb_joueurs > v_row.max_participants) then
    return json_build_object('ok', false,
      'message', 'Ce billet couvre ' || v_row.max_participants ||
                 ' personne(s) au maximum. Corrige le nombre, ou demande un second code a l''accueil.');
  end if;

  v_fin := now() + interval '3 hours';

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


-- ------------------------------------------------------------
-- 3. LE GUICHET DES PASSAGES
--
-- Meme principe pour l'enregistrement d'une borne : le site demande, la
-- base verifie que la partie est bien ouverte et ecrit elle-meme.
--
-- Effet secondaire utile : le point sensible signale dans seed.sql
-- disparait. Jusqu'ici, un accent de travers dans le libelle d'une borne
-- faisait perdre le passage SANS aucun message. Desormais le guichet
-- repond "borne inconnue", et le message apparait dans la console du
-- navigateur pendant les tests.
-- ------------------------------------------------------------
create or replace function enregistrer_passage(p_code_id uuid, p_borne text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_point uuid;
begin
  perform 1 from codes
   where id = p_code_id
     and status = 'active'
     and expires_at > now();

  if not found then
    return json_build_object('ok', false, 'message', 'Aucune partie en cours pour ce code.');
  end if;

  select id into v_point from qr_points where label = p_borne;

  if not found then
    return json_build_object('ok', false,
      'message', 'Borne inconnue en base : ' || coalesce(p_borne, '(vide)'));
  end if;

  insert into scans (code_id, qr_point_id) values (p_code_id, v_point);
  return json_build_object('ok', true);
end;
$$;

grant execute on function enregistrer_passage(uuid, text) to anon, authenticated;


-- ------------------------------------------------------------
-- 4. ON FERME LES PORTES
--
-- C'est ici que les trous se bouchent. A ne lancer qu'avec les guichets
-- ci-dessus en place, sinon le jeu ne demarre plus du tout.
-- ------------------------------------------------------------
drop policy if exists "Lecture publique des codes"       on codes;   -- TROU 1
drop policy if exists "Activation d'un code non utilise" on codes;   -- TROU 2
drop policy if exists "Enregistrement des scans"         on scans;   -- TROU 3

-- La lecture des passages reste ouverte : c'est elle qui permet au jeu de
-- verifier la progression d'un groupe, et elle ne contient ni nom, ni code,
-- rien qu'un identifiant technique. Ne pas la retirer, le verrouillage du
-- parcours tomberait avec.


-- ------------------------------------------------------------
-- 5. LES VUES QUI LAISSAIENT ENCORE PASSER LES CODES
--
-- Une vue travaille avec les droits de son proprietaire : fermer la table
-- ne la ferme pas. Trois vues du backoffice affichaient le code en entier,
-- et le backoffice n'est protege que par un mot de passe ecrit dans la page.
-- Le trou 1 serait donc reste ouvert par cette porte-la.
--
-- On n'affiche plus que les 4 derniers caracteres : assez pour reconnaitre
-- un groupe sur le terrain, pas assez pour deviner son code.
--
-- "create or replace" et non "drop" : les statistiques d'abandon sont
-- construites par-dessus, un drop les emporterait avec.
-- ------------------------------------------------------------
create or replace view live_dashboard as
select
  right(c.code, 4) as code,
  c.max_participants,
  c.direction,
  c.slot_time,
  c.activated_at,
  c.expires_at,
  qp.label as last_point,
  s.scanned_at as last_scan_at,
  now() - s.scanned_at as time_since_last_scan
from codes c
left join lateral (
  select qr_point_id, scanned_at
  from scans
  where scans.code_id = c.id
  order by scanned_at desc
  limit 1
) s on true
left join qr_points qp on qp.id = s.qr_point_id
where c.status = 'active'
  and c.expires_at > now();

create or replace view code_progress as
select
  c.id as code_id,
  right(c.code, 4) as code,
  c.status,
  c.activated_at,
  c.expires_at,
  max(s.scanned_at) as last_scan_at,
  bool_or(qp.label = 'La serre') as reached_final,
  (
    select qp2.label
    from scans s2
    join qr_points qp2 on qp2.id = s2.qr_point_id
    where s2.code_id = c.id
    order by s2.scanned_at desc
    limit 1
  ) as last_point_reached
from codes c
left join scans s on s.code_id = c.id
left join qr_points qp on qp.id = s.qr_point_id
where c.status in ('active', 'expired')
group by c.id, c.code, c.status, c.activated_at, c.expires_at;

create or replace view signalements_recents as
select s.id, s.signale_le, s.categorie, s.borne, s.message, s.traite_le,
       right(c.code, 4) as code
from signalements s
left join codes c on c.id = s.code_id
order by s.signale_le desc;


-- ------------------------------------------------------------
-- 6. LE COMPTEUR DE DEPARTS DU BACKOFFICE
--
-- Le tableau de bord lisait la table des codes pour compter les departs
-- de la demi-heure (le plafond de 72 personnes). Cette table est fermee
-- maintenant : on lui ouvre une fenetre qui ne montre que les nombres,
-- aucun code.
-- ------------------------------------------------------------
create or replace view departs_recents as
select activated_at, participants_reels, max_participants, direction
from codes
where activated_at is not null;

grant select on table departs_recents to anon, authenticated;


-- ------------------------------------------------------------
-- 7. CONTROLE
--
-- Doit renvoyer trois lignes a "OUI" et une liste de politiques ou ne
-- figurent plus ni "Lecture publique des codes", ni "Activation d'un
-- code non utilise", ni "Enregistrement des scans".
-- ------------------------------------------------------------
select 'Guichet d''activation en place'
       as quoi,
       case when exists (select 1 from pg_proc where proname = 'activer_code')
            then 'OUI' else 'NON' end as etat
union all
select 'Guichet des passages en place',
       case when exists (select 1 from pg_proc where proname = 'enregistrer_passage')
            then 'OUI' else 'NON' end
union all
select 'Table des codes fermee au public',
       case when not exists (
              select 1 from pg_policies
               where tablename = 'codes' and 'public' = any(roles))
            then 'OUI' else 'NON' end;
