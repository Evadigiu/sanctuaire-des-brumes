-- ============================================================
-- SEED — Le Sanctuaire des Brumes
-- À exécuter dans Supabase, APRÈS schema_escape_game.sql
-- (SQL Editor > New query > coller > Run)
-- ============================================================

-- Les 12 bornes du parcours (sens A)
insert into qr_points (label, type) values
  ('Jardin des pivoines', 'final'),
  ('Bureau des soignants', 'temoin'),
  ('Salle de séminaire', 'side_quest'),
  ('Enclos des loups', 'side_quest'),
  ('La passante', 'temoin'),
  ('Enclos des lynx', 'side_quest'),
  ('Le vétérinaire', 'temoin'),
  ('Greg', 'temoin'),
  ('Bill', 'temoin'),
  ('Bureau de Greg', 'side_quest'),
  ('Jardin des Iris', 'side_quest'),
  ('La serre', 'final');

-- Quelques codes de test pour essayer le parcours avant l'impression des vrais tickets
-- (à supprimer avant le lancement réel, cf. requête de nettoyage tout en bas)
insert into codes (code, max_participants, direction, slot_time, status) values
  ('TEST01', 4, 'horaire', now(), 'unused'),
  ('TEST02', 2, 'antihoraire', now(), 'unused'),
  ('TEST03', 6, 'horaire', now(), 'unused');

-- ============================================================
-- Nettoyage à lancer juste avant le vrai lancement (17 octobre) :
-- delete from codes where code like 'TEST%';
-- ============================================================
