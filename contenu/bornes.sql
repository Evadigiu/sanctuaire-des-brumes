-- ============================================================
-- LES BORNES DU PARCOURS
-- Fabrique automatiquement depuis le cahier de contenu.
-- Les libelles sont RIGOUREUSEMENT identiques a ceux que les pages
-- envoient a logScan() : les deux sortent du meme fichier.
--
-- A coller dans Supabase : SQL Editor > New query > Run.
-- ============================================================
--
--  /!\  CETTE REQUETE EFFACE TOUT L'HISTORIQUE DES PASSAGES  /!\
--
--  Sans danger aujourd'hui : la base ne contient que des passages de
--  test. Apres le lancement du 17 octobre, ce serait la perte de toutes
--  les donnees du jeu, sans retour possible.
--
--  Avant de lancer, verifier ce qu'on s'apprete a perdre :
--      select count(*) from scans;
--  Si le chiffre n'est pas proche de zero, NE PAS CONTINUER.
-- ============================================================

delete from scans;              -- les passages, d'abord
delete from qr_points;          -- puis les anciennes bornes

insert into qr_points (label, type) values
  ('LE COMMISSAIRE JEAN', 'temoin')                     ,  -- E01, Jardin des pivoines
  ('LA COLLÈGUE SOIGNEUSE', 'temoin')                   ,  -- E02, Bureau des soignants
  ('Greg, version sens B', 'temoin')                    ,  -- E16, au milieu
  ('Indice : les cameras de surveillance', 'side_quest'),  -- E03, Salle de seminaire
  ('Indice : les jumelles, la carcasse', 'side_quest')  ,  -- E04, Enclos des loups
  ('LA PASSANTE', 'temoin')                             ,  -- E05, Au dessus de l'enclos des loups
  ('QUIZ ANIMALIER', 'side_quest')                      ,  -- E06, Panthère de l'amour
  ('VÉTÉRINAIRE', 'temoin')                             ,  -- E07, Forêt
  ('Indice : le panneau d''empreinte', 'side_quest')    ,  -- E08, Après le vétérinaire
  ('Greg, version sens A', 'temoin')                    ,  -- E09, Sentier des plantes sauvages d'alsace
  ('Bill', 'temoin')                                    ,  -- E10, Grande volière
  ('Indice : Le sac du botaniste', 'side_quest')        ,  -- E11, Jardin des tulipes
  ('Appel du commissaire', 'side_quest')                ,  -- E12, Statues
  ('Bureau de Greg', 'side_quest')                      ,  -- E13, Zone de picnic
  ('LE BOTANISTE', 'temoin')                            ,  -- E14, Jardin des Iris
  ('La serre', 'final')                                 ;  -- E15, La serre

-- Controle : doit renvoyer 16.
select count(*) as bornes_enregistrees from qr_points;
