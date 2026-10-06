-- ============================================================
-- CORRECTIF 8 — REPRENDRE UNE PARTIE DEPUIS UNE BORNE
-- Le Sanctuaire des Brumes — a lancer APRES le correctif 6.
--
-- A QUOI CA SERT
--
-- La partie en cours est rangee dans la memoire du navigateur. Or un QR
-- code n'ouvre pas toujours la page dans le meme navigateur que celui ou
-- l'on a demarre : le lecteur de codes du centre de controle de l'iPhone,
-- Google Lens, l'appareil photo de certains Android, un onglet de
-- navigation privee ouvrent chacun leur propre memoire, vide. La borne ne
-- trouvait alors aucune partie et renvoyait le groupe a l'accueil avec
-- "Merci de demarrer l'enquete depuis cette page avec votre code."
--
-- Desormais la borne propose de ressaisir le code et reste sur place. Ce
-- guichet rend la partie en cours, et SEULEMENT elle : il n'ouvre jamais
-- une partie neuve. Sans cela, un groupe tombant sur une borne avant
-- d'etre passe par l'accueil lancerait son chrono sans avoir donne son
-- nombre de joueurs ni accepte les consignes.
--
-- Les phrases du champ "message" s'affichent telles quelles a l'ecran :
-- elles portent leurs accents et vouvoient, comme dans le correctif 6.
-- ============================================================

create or replace function reprendre_partie(p_code text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_code       text := upper(trim(coalesce(p_code, '')));
  v_origine    text;
  v_tentatives int;
  v_row        codes%rowtype;
begin
  if v_code = '' then
    return json_build_object('ok', false,
      'message', 'Saisissez le code inscrit sur votre billet.');
  end if;

  -- Meme garde-fou que l'activation, et meme compteur : on ne doit pas
  -- pouvoir deviner les codes par cette porte plutot que par l'autre.
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

  v_row := (select c from codes c where c.code = v_code);

  if v_row.id is null then
    delete from tentatives_activation where tente_le < now() - interval '1 day';
    insert into tentatives_activation (origine) values (v_origine);
    return json_build_object('ok', false,
      'message', 'Ce code n''existe pas. Vérifiez la saisie, ou demandez de l''aide à l''accueil.');
  end if;

  if v_row.status = 'expired'
     or (v_row.expires_at is not null and v_row.expires_at <= now()) then
    return json_build_object('ok', false,
      'message', 'Ce code a déjà servi et sa partie est terminée. Adressez-vous à l''accueil du zoo.');
  end if;

  if v_row.status <> 'active' then
    return json_build_object('ok', false, 'pas_commencee', true,
      'message', 'Cette enquête n''a pas encore commencé. Démarrez-la depuis la page d''accueil.');
  end if;

  return json_build_object('ok', true,
    'code_id',    v_row.id,
    'code',       v_row.code,
    'direction',  v_row.direction,
    'expires_at', v_row.expires_at);
end;
$$;

grant execute on function reprendre_partie(text) to anon, authenticated;


-- ------------------------------------------------------------
-- CONTROLE : doit renvoyer une ligne a "OUI".
-- ------------------------------------------------------------
select 'Guichet de reprise en place' as quoi,
       case when exists (select 1 from pg_proc where proname = 'reprendre_partie')
            then 'OUI' else 'NON' end as etat;
