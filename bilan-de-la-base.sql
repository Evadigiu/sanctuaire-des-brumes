-- ============================================================
-- OU EN EST LA BASE ? — Le Sanctuaire des Brumes
--
-- Cette requete NE MODIFIE RIEN. Elle regarde la base et repond a une
-- seule question : qu'est-ce qui a deja ete lance, et qu'est-ce qui
-- reste a faire.
--
-- Mode d'emploi :
--   Supabase > SQL Editor > New query > coller ceci > Run
--
-- A relancer chaque fois qu'un doute survient. C'est fait pour ca.
-- ============================================================

with etat as (
  select
    -- Correctif 1 : la vue du suivi ignore-t-elle les parties terminees ?
    coalesce((select pg_get_viewdef('live_dashboard'::regclass) like '%expires_at > now()%'), false)
      as c1_fantomes,

    -- Correctif 2 : la colonne du nombre reel de joueurs existe-t-elle ?
    exists (select 1 from information_schema.columns
             where table_name = 'codes' and column_name = 'participants_reels')
      as c2_nb_joueurs,

    -- Correctif 3 : le jeu en solo est-il autorise ?
    exists (select 1 from pg_constraint
             where conrelid = 'codes'::regclass
               and pg_get_constraintdef(oid) like '%max_participants >= 1%')
      as c3_solo,

    -- Correctif 4 : le jeu peut-il relire la progression, et signaler un probleme ?
    exists (select 1 from pg_policies
             where tablename = 'scans' and cmd = 'SELECT')
      as c4_lecture_scans,
    (to_regclass('public.signalements') is not null)
      as c4_signalements,

    -- Correctif 5 : peut-on clore un signalement ?
    exists (select 1 from information_schema.columns
             where table_name = 'signalements' and column_name = 'traite_le')
      as c5_cloture,
    exists (select 1 from pg_proc
             where proname = 'marquer_signalement_traite')
      as c5_guichet,

    -- Les bornes du parcours
    (select count(*) from qr_points) as nb_bornes,
    (select count(*) from codes)     as nb_codes,
    (select count(*) from scans)     as nb_passages
)
select * from (
  select 1 as ordre, 'Correctif 1' as quoi,
         'Le suivi en direct n''affiche plus les groupes des jours passes' as a_quoi_ca_sert,
         case when c1_fantomes then 'FAIT' else 'A LANCER' end as etat from etat
  union all
  select 2, 'Correctif 2',
         'Le nombre reel de joueurs est enregistre',
         case when c2_nb_joueurs then 'FAIT' else 'A LANCER' end from etat
  union all
  select 3, 'Correctif 3',
         'Le jeu en solo est autorise (1 a 6 personnes)',
         case when c3_solo then 'FAIT' else 'A LANCER' end from etat
  union all
  select 4, 'Correctif 4a',
         'Le parcours est verrouille : impossible de sauter des bornes',
         case when c4_lecture_scans then 'FAIT' else 'A LANCER' end from etat
  union all
  select 5, 'Correctif 4b',
         'Le bouton « j''ai un probleme » enregistre les signalements',
         case when c4_signalements then 'FAIT' else 'A LANCER' end from etat
  union all
  select 6, 'Correctif 5',
         'L''equipe peut clore un signalement traite',
         case when c5_cloture and c5_guichet then 'FAIT' else 'A LANCER' end from etat
  union all
  select 7, 'Les bornes',
         'Le parcours compte ' || nb_bornes || ' bornes (il en faut 16)',
         case when nb_bornes = 16 then 'FAIT' else 'A REVOIR' end from etat
  union all
  select 8, 'Le contenu',
         nb_codes || ' code(s), ' || nb_passages || ' passage(s) enregistre(s)',
         'pour information' from etat
) bilan
order by ordre;
