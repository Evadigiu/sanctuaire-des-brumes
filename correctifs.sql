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
--            ETAT : TOUT EST APPLIQUE, RIEN A FAIRE
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
