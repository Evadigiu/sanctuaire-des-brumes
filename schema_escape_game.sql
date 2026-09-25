-- ============================================================
-- SCHEMA BASE DE DONNEES — Le Sanctuaire des Brumes
-- Zoo de Mulhouse, 17 octobre au 2 novembre 2026
-- Format Postgres (compatible Supabase)
--
-- CE FICHIER DECRIT LA BASE REELLEMENT EN PLACE.
-- Derniere verification faite directement sur la base : 1er septembre 2026,
-- mise a jour le 25 septembre 2026 (correctifs 4, 5, 6).
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
-- max_participants : 1 a 6 personnes. Le jeu en solo est autorise (decision du 20/09/2026,
-- qui revient sur la regle precedente interdisant le solo).
create table codes (
  id                uuid primary key default gen_random_uuid(),
  code              text not null unique,        -- code remis a l'accueil du zoo
  max_participants  int not null check (max_participants between 1 and 6),
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
-- 2 bis. DROITS D'ACCES A L'API (a partir du 30 octobre 2026)
--
-- Supabase a cesse, le 30 octobre 2026, d'accorder automatiquement
-- l'acces API aux nouvelles tables du schema public. Les cinq tables
-- ci-dessus sont anterieures : elles gardent leurs droits, rien a faire.
--
-- MAIS toute table creee APRES cette date reste muette tant qu'un GRANT
-- explicite ne lui a pas ete accorde. Le site recoit alors un refus, et
-- rien dans le code ne laisse deviner pourquoi.
--
-- REGLE POUR LA SUITE : toute nouvelle table ou vue s'accompagne de son
-- GRANT, dans la meme requete. Les correctifs 4 et 6 le font deja pour la
-- table des signalements et pour la vue des departs.
--
-- A ne pas confondre avec la securite : un GRANT ouvre la porte du
-- couloir, les regles RLS de la section 3 ouvrent celle de la piece.
-- Accorder un GRANT n'expose rien tant que les regles tiennent.
-- ============================================================


-- ============================================================
-- 3. SECURITE (RLS)
--
-- La cle publique du site est visible par tout le monde dans le code source.
-- C'est normal. Ce sont donc UNIQUEMENT les regles ci-dessous, et les
-- guichets de la section 3 bis, qui protegent la base.
--
-- Les trois trous signales ici jusqu'au 25/09/2026 sont boucher : voir
-- correctif-6-guichet-des-codes.sql. Pour memoire, ils permettaient
-- respectivement de lire tous les codes (donc de jouer sans payer), de
-- griller tous les billets imprimes en une requete, et de s'inscrire les
-- seize passages de bornes sans marcher.
-- ============================================================

alter table qr_points      enable row level security;
alter table codes          enable row level security;
alter table scans          enable row level security;
alter table quiz_responses enable row level security;
alter table conclusions    enable row level security;

-- Les regles reellement en place apres le correctif 6.
create policy "Lecture publique des bornes"
  on qr_points for select to public
  using (true);

-- La table "codes" n'a plus AUCUNE regle publique : ni lecture, ni
-- ecriture. Tout passe par activer_code(), section 3 bis.

-- Lecture des passages : c'est elle qui permet au jeu de verifier la
-- progression d'un groupe. Elle ne contient ni nom ni code, seulement des
-- identifiants techniques. Ne pas la retirer : le verrouillage du parcours
-- tomberait avec.
create policy "Lecture publique des scans"
  on scans for select to public
  using (true);

-- L'ecriture des passages, elle, passe par enregistrer_passage().

create policy "Signalement depuis le terrain"
  on signalements for insert to public
  with check (true);


-- ------------------------------------------------------------
-- 3 bis. LES GUICHETS (fonctions security definer)
--
-- Une fonction "security definer" travaille avec les droits du
-- proprietaire de la base, pas ceux du visiteur. Le site lui soumet une
-- demande, elle verifie et ecrit elle-meme. C'est ce qui permet de fermer
-- completement les tables sans empecher le jeu de fonctionner.
--
--   activer_code(code, nb_joueurs)     ouvre une partie, calcule le chrono
--                                      de 3h cote serveur, limite les
--                                      essais en rafale
--   enregistrer_passage(code_id, borne) inscrit un passage si la partie est
--                                      ouverte, et signale un libelle de
--                                      borne inconnu au lieu de le perdre
--   marquer_signalement_traite(id)     clot un signalement (correctif 5)
--
-- REGLE A NE PAS OUBLIER : Postgres autorise par defaut TOUT LE MONDE a
-- executer une fonction nouvellement creee, et Supabase les expose au site.
-- Toute fonction d'administration (fabriquer_codes, par exemple) doit donc
-- s'accompagner de son "revoke execute ... from public". Voir le
-- correctif 7.
-- ------------------------------------------------------------


-- ------------------------------------------------------------
-- CE QUI N'EXISTE PAS, ET QU'IL FAUT SAVOIR :
--
-- * Aucune regle de suppression nulle part. Personne ne peut effacer de
--   donnees depuis le site. C'est voulu, ne pas en ajouter.
--
-- * AUCUNE regle sur "quiz_responses" et "conclusions". Ces deux tables sont
--   donc totalement fermees, y compris au site lui-meme. L'etape finale ne
--   pourra RIEN y enregistrer : les reponses des joueurs seront rejetees en
--   silence, sans message d'erreur. A regler AVANT de construire l'etape
--   finale, et par un guichet plutot que par une regle ouverte.
--
-- * LE BACKOFFICE N'EST PAS PROTEGE. Le mot de passe "brumes2026" est ecrit
--   en clair dans dashboard.html : il ne cache qu'un bouton. Les vues de
--   suivi sont lisibles par n'importe qui. Depuis le correctif 6 elles ne
--   montrent plus que les 4 derniers caracteres d'un code, ce qui evite le
--   pire, mais l'activite du jeu reste consultable par un inconnu. Correctif
--   a prevoir : un vrai compte Supabase Auth pour l'equipe, et les vues
--   fermees a "anon".
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
  right(c.code, 4) as code,   -- code partiel : voir correctif 6
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
