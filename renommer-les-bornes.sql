-- ============================================================
-- RENOMMAGE DE DEUX BORNES
-- A lancer APRES avoir merge la mise a jour du site.
--
-- Le jeu retrouve chaque borne par son libelle ecrit en toutes lettres.
-- Si la page dit "L'ENCLOS DES LOUPS" et que la base connait encore
-- "Indice : les jumelles, la carcasse", le passage du groupe n'est PAS
-- enregistre : le guichet repond "borne inconnue", et le verrouillage
-- bloque ensuite le groupe a la borne suivante.
--
-- On RENOMME les lignes existantes, on n'en cree pas de nouvelles : les
-- passages deja enregistres restent rattaches a la bonne borne.
-- ============================================================

update qr_points
   set label = 'SOPHIE, CHEFFE DE LA SÉCURITÉ'
 where label = 'Indice : les cameras de surveillance';

update qr_points
   set label = 'L''ENCLOS DES LOUPS'
 where label = 'Indice : les jumelles, la carcasse';

-- Controle : les deux nouveaux libelles doivent apparaitre, et aucun
-- ancien ne doit subsister.
select label from qr_points
 where label in ('SOPHIE, CHEFFE DE LA SÉCURITÉ', 'L''ENCLOS DES LOUPS',
                 'Indice : les cameras de surveillance',
                 'Indice : les jumelles, la carcasse')
 order by label;
