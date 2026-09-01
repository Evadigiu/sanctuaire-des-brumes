-- ============================================================
-- SEED — Le Sanctuaire des Brumes
-- A executer dans Supabase APRES schema_escape_game.sql
-- (SQL Editor > New query > coller > Run)
--
-- Etat au 01/09/2026 : deja execute sur la base de production.
-- Les 12 bornes et les 3 codes de test y sont presents.
-- ============================================================


-- ------------------------------------------------------------
-- Les 12 bornes du parcours, dans l'ordre du sens A (horaire).
--
-- ATTENTION, POINT SENSIBLE : le site retrouve chaque borne par son libelle
-- ecrit EN TOUTES LETTRES (voir logScan() dans assets/js/game.js). Une
-- majuscule ou un accent de travers dans une page d'etape, et le passage du
-- groupe n'est pas enregistre, SANS AUCUN MESSAGE D'ERREUR a l'ecran.
-- Les libelles ci-dessous font foi. Copier-coller, ne pas retaper.
--
-- La colonne "type" n'est utilisee nulle part pour l'instant. Elle contient
-- une incoherence assumee : "Jardin des pivoines" est le briefing de depart
-- mais il est classe 'final', faute d'un type 'depart' dans la liste
-- autorisee par le schema. A corriger avant de baser une stat dessus.
-- ------------------------------------------------------------
insert into qr_points (label, type) values
  ('Jardin des pivoines', 'final'),       -- 1.  Jerry, briefing         (en realite un depart)
  ('Bureau des soignants', 'temoin'),     -- 2.  La collegue soigneuse
  ('Salle de séminaire', 'side_quest'),   -- 3.  Videosurveillance
  ('Enclos des loups', 'side_quest'),     -- 4.  Indice 1 : lettre R
  ('La passante', 'temoin'),              -- 5.  Le cri strident
  ('Enclos des lynx', 'side_quest'),      -- 6.  Sabri & Arez, indice 2 : I
  ('Le vétérinaire', 'temoin'),           -- 7.  Indice 3 : S
  ('Greg', 'temoin'),                     -- 8.  Temoignage evasif
  ('Bill', 'temoin'),                     -- 9.  Les oiseaux, l'alibi
  ('Bureau de Greg', 'side_quest'),       -- 10. L'epouvantail, indice 4 : I
  ('Jardin des Iris', 'side_quest'),      -- 11. Enigme, IRIS = code de la serre
  ('La serre', 'final');                  -- 12. Le botaniste, resolution


-- ------------------------------------------------------------
-- Codes de test, pour essayer le parcours avant l'impression des vrais
-- tickets. Rappel : la limite est de 2 a 6 personnes par groupe, le solo
-- n'est pas autorise.
-- ------------------------------------------------------------
insert into codes (code, max_participants, direction, slot_time, status) values
  ('TEST01', 4, 'horaire', now(), 'unused'),
  ('TEST02', 2, 'antihoraire', now(), 'unused'),
  ('TEST03', 6, 'horaire', now(), 'unused');


-- ============================================================
-- A LANCER JUSTE AVANT LE VRAI LANCEMENT (17 octobre) :
--   delete from codes where code like 'TEST%';
--
-- Note : la suppression est impossible depuis le site (aucune regle de
-- suppression n'existe, c'est volontaire). Cette requete doit donc etre
-- lancee depuis le SQL Editor de Supabase.
-- ============================================================
