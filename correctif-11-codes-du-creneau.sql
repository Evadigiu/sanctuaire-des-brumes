-- ============================================================
-- CORRECTIF 11 — Les codes des groupes partis, au tableau de bord
--
-- Le bloc « Créneau en cours » du suivi en direct comptait les départs
-- sans dire QUI était parti. On ajoute à sa vue la fin du code (4
-- derniers caractères), comme la liste des groupes actifs et les
-- signalements le font déjà.
--
-- Pourquoi pas le code entier : cette vue est lisible avec la clé
-- publique du site, et le mot de passe du tableau de bord ne protège que
-- l'affichage. Un code entier lu ici permettrait à n'importe qui de
-- rejoindre la partie d'un groupe en cours. Quatre caractères suffisent
-- à reconnaître un groupe, pas à jouer à sa place.
--
-- A coller dans le SQL Editor de Supabase, puis « Run ». Sans risque :
-- la vue garde ses colonnes, on en ajoute une à la fin.
-- ============================================================

create or replace view departs_recents as
select activated_at, participants_reels, max_participants, direction,
       right(code, 4) as code
from codes
where activated_at is not null;

grant select on table departs_recents to anon, authenticated;

-- Controle : doit afficher les derniers departs, avec leurs 4 caracteres.
select activated_at, code, participants_reels, direction
from departs_recents
order by activated_at desc
limit 5;
