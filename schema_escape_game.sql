-- ============================================================
-- SCHÉMA BASE DE DONNÉES — Escape game Zoo de Mulhouse
-- Format Postgres (compatible Supabase)
-- ============================================================

-- Les 12 bornes QR du parcours (4 témoins + leurs quêtes + l'étape finale)
create table qr_points (
  id            uuid primary key default gen_random_uuid(),
  label         text not null,                 -- ex: "Vétérinaire", "Greg", "Serre - conclusion"
  type          text not null check (type in ('temoin', 'side_quest', 'final')),
  created_at    timestamptz not null default now()
);

-- Les codes de départ (1 code = 1 groupe = 1 à 5 personnes)
create table codes (
  id                uuid primary key default gen_random_uuid(),
  code              text not null unique,        -- code remis à l'accueil
  max_participants  int not null check (max_participants between 1 and 5),
  direction         text not null check (direction in ('horaire', 'antihoraire')),
  slot_time         timestamptz not null,         -- créneau de départ prévu (grille des 1224 slots)
  status            text not null default 'unused' check (status in ('unused', 'active', 'expired')),
  activated_at      timestamptz,                  -- posé au 1er scan, jamais modifié ensuite
  expires_at        timestamptz,                  -- = activated_at + 3h, calculé côté serveur
  created_at        timestamptz not null default now()
);

-- Historique de chaque passage à une borne QR (suivi de progression + reconstitution)
create table scans (
  id            uuid primary key default gen_random_uuid(),
  code_id       uuid not null references codes(id),
  qr_point_id   uuid not null references qr_points(id),
  scanned_at    timestamptz not null default now()
);

-- Réponses au quiz de l'étape finale
create table quiz_responses (
  id             uuid primary key default gen_random_uuid(),
  code_id        uuid not null references codes(id),
  question_id    text not null,
  selected       text not null,
  is_correct     boolean not null,
  answered_at    timestamptz not null default now()
);

-- Conclusions libres + verdict IA (étape finale uniquement)
create table conclusions (
  id              uuid primary key default gen_random_uuid(),
  code_id         uuid not null references codes(id),
  submitted_text  text not null,
  ai_verdict      text check (ai_verdict in ('proche', 'partiel', 'eloigne')),
  ai_reply_text   text,               -- réponse "en personnage" affichée au joueur, jamais du texte libre non contrôlé
  created_at      timestamptz not null default now()
);

-- ============================================================
-- Index utiles
-- ============================================================
create index idx_codes_status on codes(status);
create index idx_codes_slot_time on codes(slot_time);
create index idx_scans_code_id on scans(code_id);
create index idx_scans_qr_point_id on scans(qr_point_id);

-- ============================================================
-- Vue de suivi live (dashboard équipe Pomelo)
-- Donne, pour chaque code actif, le dernier point scanné et l'heure
-- ============================================================
create view live_dashboard as
select
  c.code,
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
where c.status = 'active';

-- ============================================================
-- Vue de réconciliation (comparaison avec la billetterie)
-- Nombre de codes activés vs capacité théorique par jour
-- ============================================================
create view reconciliation_daily as
select
  date(slot_time) as jour,
  count(*) filter (where status != 'unused') as codes_actives,
  sum(max_participants) filter (where status != 'unused') as participants_max_estimes
from codes
group by date(slot_time)
order by jour;
