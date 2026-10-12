-- ============================================================
-- EFFACER LES CODES DE TEST
--
-- A lancer UNE SEULE FOIS, le matin de l'ouverture, avant le premier
-- visiteur. PAS AVANT : ce sont ces codes-la qui permettent de repeter le
-- parcours sans courir dans le parc.
--
-- L'ordre des quatre effacements compte. Un code laisse derriere lui ses
-- passages de bornes, ses reponses de quiz et ses conclusions : la base
-- refuse de l'effacer tant que ces trois traces existent. La version qui
-- figurait dans le mode d'emploi n'en retirait qu'une, et echouait donc
-- avec un message incomprehensible, le matin meme, avec du monde a
-- l'accueil. Essaye sur une base ou un code de test avait tout laisse.
--
-- "begin / commit" : les quatre effacements passent ensemble ou pas du
-- tout. Pas de demi-menage.
--
-- Relancer ce fichier une seconde fois ne provoque rien.
-- ============================================================
begin;

delete from scans
 where code_id in (select id from codes where code like 'TEST%');

delete from quiz_responses
 where code_id in (select id from codes where code like 'TEST%');

delete from conclusions
 where code_id in (select id from codes where code like 'TEST%');

delete from codes where code like 'TEST%';

commit;

-- Controle : codes_de_test doit valoir 0, et vrais_codes 600.
select count(*) filter (where code like 'TEST%')     as codes_de_test,
       count(*) filter (where code not like 'TEST%') as vrais_codes
  from codes;
