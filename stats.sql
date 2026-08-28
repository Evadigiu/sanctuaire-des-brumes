-- ============================================================
-- STATISTIQUES — Le Sanctuaire des Brumes
-- À exécuter dans Supabase, APRÈS schema_escape_game.sql et seed.sql
-- N'ajoute que des vues (aucune table), s'appuie sur les données
-- déjà présentes dans "codes" et "scans".
-- ============================================================

-- Temps passé à chaque borne avant de passer à la suivante,
-- calculé pour chaque groupe individuellement.
create or replace view scan_durations as
select
  s.code_id,
  s.qr_point_id,
  qp.label,
  s.scanned_at,
  lead(s.scanned_at) over (partition by s.code_id order by s.scanned_at) - s.scanned_at as duration_to_next,
  lead(s.scanned_at) over (partition by s.code_id order by s.scanned_at) is null as is_last_scan
from scans s
join qr_points qp on qp.id = s.qr_point_id;

-- Durée moyenne ET médiane par borne, tous groupes confondus.
-- Regarder la médiane en priorité : la moyenne est facilement faussée
-- par un groupe qui a fait une pause devant les animaux.
create or replace view avg_duration_by_point as
select
  label,
  count(*) as nb_passages,
  avg(duration_to_next) as duree_moyenne,
  percentile_cont(0.5) within group (order by duration_to_next) as duree_mediane
from scan_durations
where duration_to_next is not null
group by label
order by duree_mediane desc;

-- Pour chaque code, sa progression : a-t-il atteint la dernière borne
-- (La serre), et si non, où s'est-il arrêté.
create or replace view code_progress as
select
  c.id as code_id,
  c.code,
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

-- À quelle borne les groupes abandonnent le plus souvent
-- (code expiré ou temps écoulé, sans avoir atteint la Serre).
create or replace view abandon_points as
select
  coalesce(last_point_reached, 'Jamais scanné') as derniere_borne,
  count(*) as nb_abandons
from code_progress
where reached_final = false
  and (status = 'expired' or (expires_at is not null and expires_at < now()))
group by derniere_borne
order by nb_abandons desc;

-- Vue d'ensemble : combien de groupes ont fini, abandonné, ou sont
-- encore en train de jouer en ce moment.
create or replace view completion_summary as
select
  count(*) filter (where reached_final) as termines,
  count(*) filter (where not reached_final and (status = 'expired' or expires_at < now())) as abandonnes,
  count(*) filter (where not reached_final and status = 'active' and expires_at >= now()) as en_cours
from code_progress;
