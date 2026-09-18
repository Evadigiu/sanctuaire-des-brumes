-- ============================================================
-- SCHEMA BASE DE DONNEES — Le Sanctuaire des Brumes
-- Zoo de Mulhouse, 17 octobre au 2 novembre 2026
-- Format Postgres (compatible Supabase)
--
-- CE FICHIER DECRIT LA BASE REELLEMENT EN PLACE.
-- Derniere verification faite directement sur la base : 1er septembre 2026.
-- Si tu modifies quelque chose dans Supabase, reporte-le ici le jour meme,
-- sinon ce fichier redevient un plan de maison sans les serrures.
-- Pour re-verifier a tout moment : lancer verification_base.sql.
-- ============================================================


-- ============================================================
-- 1. LES TABLES
-- ============================================================

-- Les 12 bornes QR du parcours.
-- NOTE : la colonne "type" n'est utilisee nulle part aujourd'hui (ni par le
-- site, ni par les statistiques). Elle contient d'ailleurs une incoherence :
-- "Jardin des pivoines" est le briefing de depart mais il est classe 'final',
-- faute d'un type 'depart' dans la liste autorisee. Sans consequence tant que
-- personne ne s'en sert. A corriger avant de baser une statistique dessus.
create table qr_points (
  id            uuid primary key default gen_random_uuid(),
  label         text not null,                 -- ex: "Le veterinaire", "La serre"
  type          text not null check (type in ('temoin', 'side_quest', 'final')),
  created_at    timestamptz not null default now()
);

-- Les codes de depart (1 code = 1 groupe).
-- max_participants : 2 a 6 personnes. Le solo n'est pas autorise (decision metier).
create table codes (
  id                uuid primary key default gen_random_uuid(),
  code              text not null unique,        -- code remis a l'accueil du zoo
  max_participants  int not null check (max_participants between 2 and 6),
  direction         text not null check (direction in ('horaire', 'antihoraire')),
  slot_time         timestamptz not null,        -- creneau de depart prevu
  status            text not null default 'unused' check (status in ('unused', 'active', 'expired')),
  activated_at      timestamptz,                 -- pose a la 1ere activation
  expires_at        timestamptz,                 -- = activated_at + 3h
  created_at        timestamptz not null default now()
);

-- Historique de chaque passage a une borne QR.
create table scans (
  id            uuid primary key default gen_random_uuid(),
  code_id       uuid not null references codes(id),
  qr_point_id   uuid not null references qr_points(id),
  scanned_at    timestamptz not null default now()
);

-- Reponses au quiz de l'etape finale. PAS ENCORE UTILISEE (voir section 3).
create table quiz_responses (
  id             uuid primary key default gen_random_uuid(),
  code_id        uuid not null references codes(id),
  question_id    text not null,
  selected       text not null,
  is_correct     boolean not null,
  answered_at    timestamptz not null default now()
);

-- Conclusions libres + verdict IA. PAS ENCORE UTILISEE (voir section 3).
create table conclusions (
  id              uuid primary key default gen_random_uuid(),
  code_id         uuid not null references codes(id),
  submitted_text  text not null,
  ai_verdict      text check (ai_verdict in ('proche', 'partiel', 'eloigne')),
  ai_reply_text   text,
  created_at      timestamptz not null default now()
);


-- ============================================================
-- 2. INDEX
-- ============================================================
create index idx_codes_status on codes(status);
create index idx_codes_slot_time on codes(slot_time);
create index idx_scans_code_id on scans(code_id);
create index idx_scans_qr_point_id on scans(qr_point_id);


-- ============================================================
-- 3. SECURITE (RLS)
--
-- La cle publique du site est visible par tout le monde dans le code source.
-- C'est normal. Ce sont donc UNIQUEMENT les regles ci-dessous qui protegent
-- la base. Elles sont reproduites a l'identique de ce qui tourne en prod.
--
-- >>> AVERTISSEMENT, A LIRE AVANT DE GENERER LES VRAIS CODES <<<
--
-- Ces regles comportent DEUX TROUS CONNUS, sans danger tant que la base ne
-- contient que des codes de test, inacceptables une fois les vrais codes
-- generes :
--
--   TROU 1 — "Lecture publique des codes" autorise n'importe qui a lire la
--   liste complete des codes, y compris ceux non encore vendus. Autrement
--   dit : jouer gratuitement sans passer par la billetterie.
--
--   TROU 2 — "Activation d'un code non utilise" ne verifie que la colonne
--   status. Elle n'empeche ni de modifier plusieurs codes a la fois, ni
--   d'ecrire n'importe quoi dans les autres colonnes. Consequences :
--     a) une seule requete peut passer TOUS les codes non utilises en
--        "active" et expire, rendant tous les tickets imprimes inutilisables ;
--     b) le joueur ecrit lui-meme son expires_at, donc son propre chrono.
--        (Le README ne doit pas pretendre que le chrono est calcule cote
--        serveur : il ne l'est pas.)
--
-- CORRECTION PREVUE : supprimer ces deux regles et faire passer l'activation
-- par une fonction "security definer" (un guichet : le joueur soumet son code,
-- la base verifie et ecrit elle-meme). Voir le point 4 de la feuille de route.
-- ============================================================

alter table qr_points      enable row level security;
alter table codes          enable row level security;
alter table scans          enable row level security;
alter table quiz_responses enable row level security;
alter table conclusions    enable row level security;

-- Les 4 regles reellement en place (verifiees le 01/09/2026).
create policy "Lecture publique des bornes"
  on qr_points for select to public
  using (true);

create policy "Lecture publique des codes"          -- TROU 1, voir ci-dessus
  on codes for select to public
  using (true);

create policy "Activation d'un code non utilise"    -- TROU 2, voir ci-dessus
  on codes for update to public
  using (status = 'unused')
  with check (status = 'active');

create policy "Enregistrement des scans"
  on scans for insert to public
  with check (true);

-- ------------------------------------------------------------
-- CE QUI N'EXISTE PAS, ET QU'IL FAUT SAVOIR :
--
-- * Aucune regle de lecture sur "scans". Les tableaux de bord fonctionnent
--   quand meme, parce qu'une vue Postgres interroge les tables avec les
--   droits de son proprietaire et non ceux du visiteur. Deux consequences :
--     - les vues du backoffice sont lisibles par n'importe qui, le mot de
--       passe "brumes2026" ne cache que le bouton ;
--     - le jour ou quelqu'un activera "security_invoker" sur ces vues, les
--       tableaux de bord tomberont en panne d'un coup.
--
-- * Aucune regle de suppression nulle part. Personne ne peut effacer de
--   donnees depuis le site. C'est voulu, ne pas en ajouter.
--
-- * "Enregistrement des scans" accepte tout, sans verification. N'importe qui
--   peut inventer des passages de bornes et fausser les statistiques.
--
-- * AUCUNE regle sur "quiz_responses" et "conclusions". Ces deux tables sont
--   donc totalement fermees, y compris au site lui-meme. L'etape finale ne
--   pourra RIEN y enregistrer : les reponses des joueurs seront rejetees en
--   silence, sans message d'erreur. A regler en meme temps que le guichet,
--   AVANT de construire l'etape finale.
-- ------------------------------------------------------------


-- ============================================================
-- 4. VUES DE SUIVI (backoffice)
-- ============================================================

-- Groupes actuellement en jeu, avec leur derniere borne scannee.
--
-- Le filtre "and c.expires_at > now()" evite d'afficher indefiniment les
-- groupes des jours precedents : rien ne fait jamais repasser un code de
-- 'active' a 'expired' une fois les 3h ecoulees.
-- Correctif applique sur la base de production le 01/09/2026.
-- Ce fichier est de nouveau aligne avec la prod.
create or replace view live_dashboard as
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
where c.status = 'active'
  and c.expires_at > now();

-- Codes actives par jour, pour recouper avec les ventes SeeTickets.
create or replace view reconciliation_daily as
select
  date(slot_time) as jour,
  count(*) filter (where status != 'unused') as codes_actives,
  sum(max_participants) filter (where status != 'unused') as participants_max_estimes
from codes
group by date(slot_time)
order by jour;
