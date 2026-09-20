-- ============================================================
-- CORRECTIFS BASE DE DONNEES — Le Sanctuaire des Brumes
--
-- Journal des correctifs appliques a la base de production.
-- Chaque correctif reste ici une fois applique, pour garder la trace de ce
-- qui a ete change et quand.
--
-- Mode d'emploi pour un nouveau correctif :
--   Supabase > SQL Editor > New query > coller > Run
--   Message attendu : "Success. No rows returned"
--
-- ============================================================
--   ETAT : tout est applique. Voir la remise a zero des codes de test,
--          tout en bas, a relancer avant chaque essai.
-- ============================================================


-- ------------------------------------------------------------
-- CORRECTIF 1 — Le tableau de bord affichait des groupes fantomes
-- >>> APPLIQUE EN PRODUCTION LE 01/09/2026 <<<
--
-- Le probleme : le suivi en direct liste les groupes dont le code est
-- "active". Or rien, nulle part, ne fait jamais repasser un code de "active"
-- a "expired" une fois les 3 heures ecoulees. Au troisieme jour du jeu, ton
-- equipe verrait donc encore tous les groupes du jour 1 et du jour 2 affiches
-- comme etant en train de jouer.
--
-- La correction : n'afficher que les groupes dont le temps n'est pas ecoule.
-- Une seule ligne ajoutee, aucune donnee modifiee.
-- ------------------------------------------------------------

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


-- ============================================================
-- CE QUI N'EST VOLONTAIREMENT PAS DANS CE FICHIER
--
-- Les vrais trous de securite (lecture publique des codes, activation trop
-- permissive, tables du quiz totalement fermees) ne se reparent PAS par un
-- petit correctif. Ils demandent de changer la facon dont le site parle a la
-- base : le joueur ne doit plus ecrire dans la base lui-meme.
--
-- C'est un chantier a part, a mener imperativement AVANT de generer les vrais
-- codes de production. Voir la section SECURITE de schema_escape_game.sql.
-- ============================================================


-- ------------------------------------------------------------
-- CORRECTIF 2 — Enregistrer le nombre reel de joueurs
-- >>> APPLIQUE EN PRODUCTION LE 20/09/2026 <<<
--
-- L'ecran de depart demande desormais le nombre de joueurs. Aujourd'hui
-- cette reponse ne quitte pas le telephone : la colonne n'existe pas.
--
-- La table connait deja max_participants, mais c'est la capacite prevue a la
-- generation du code, pas le nombre de personnes reellement venues. Les deux
-- ensemble permettent de recouper avec la billetterie SeeTickets, ce qui
-- n'etait possible d'aucune autre facon jusqu'ici.
--
-- Le site n'a plus besoin d'etre prevenu : si la colonne venait a manquer,
-- il reessaie sans elle plutot que de bloquer l'activation. Un groupe qui
-- attend a la caisse ne doit jamais rester coince pour un champ de confort.
-- ------------------------------------------------------------

alter table codes
  add column if not exists participants_reels int
  check (participants_reels between 2 and 6);
-- NOTE : ce minimum de 2 a ete ramene a 1 par le correctif 3, plus bas.
-- La ligne ci-dessus est conservee telle qu'elle a ete lancee, c'est un journal.


-- ------------------------------------------------------------
-- CORRECTIF 3 — Autoriser le jeu en solo (1 a 6 personnes)
-- >>> PAS ENCORE APPLIQUE <<<
--
-- Decision du 20/09/2026, qui revient sur la regle precedente interdisant
-- le solo. Les deux colonnes qui comptent des personnes plafonnaient a un
-- minimum de 2 : un code prevu pour une seule personne serait refuse par la
-- base, et un joueur seul ne pourrait pas declarer qu'il est seul.
--
-- Ne touche a aucune donnee : on remplace deux regles de controle.
-- ------------------------------------------------------------

alter table codes drop constraint if exists codes_max_participants_check;
alter table codes add  constraint codes_max_participants_check
  check (max_participants between 1 and 6);

alter table codes drop constraint if exists codes_participants_reels_check;
alter table codes add  constraint codes_participants_reels_check
  check (participants_reels between 1 and 6);

-- Controle : les deux lignes doivent afficher "between 1 and 6".
select conname as regle, pg_get_constraintdef(oid) as definition
from pg_constraint
where conrelid = 'codes'::regclass
  and conname in ('codes_max_participants_check', 'codes_participants_reels_check');


-- ------------------------------------------------------------
-- REMISE A ZERO DES CODES DE TEST
-- A relancer avant chaque nouvelle session d'essai.
--
-- Un code deja active garde sa date de fin : le rejouer ouvrirait une
-- partie deja terminee. Cette requete leur rend leur etat neuf.
--
-- Ne touche QUE les codes commencant par TEST. Sans effet sur les vrais.
-- ------------------------------------------------------------

update codes
   set status = 'unused',
       activated_at = null,
       expires_at = null,
       participants_reels = null
 where code like 'TEST%';

-- Controle : les trois codes de test doivent etre a 'unused'.
select code, status, expires_at from codes where code like 'TEST%' order by code;
