-- ============================================================
-- REFERMER LES CONCLUSIONS
--
-- A coller dans Supabase : SQL Editor > NOUVEL ONGLET > Run.
--
-- CE QUI S'EST PASSE
-- La vue conclusions_rendues a ete creee pour que VOUS relisiez les
-- enquetes depuis l'editeur SQL. Elle s'est retrouvee lisible par
-- n'importe quel visiteur du site.
--
-- Pourquoi : une vue appartient a son createur et s'execute avec SES
-- droits. Elle traverse donc le verrou pose sur la table qu'elle lit. Le
-- verrou sur conclusions etait bien en place ; la vue passait au-dessus.
--
-- Ce qui etait expose : le texte libre ecrit par les joueurs a la fin de
-- leur enquete. Personne n'a a le lire a part vous.
--
-- Rien ne la lit depuis le site : le tableau de bord ne s'en sert pas.
-- On la referme donc, et vous continuez a la lire depuis l'editeur SQL,
-- ou vous etes proprietaire de la base.
-- ============================================================

revoke all on conclusions_rendues from anon, authenticated;

-- ============================================================
-- CE QU'UN VISITEUR PEUT REELLEMENT LIRE
--
-- Deux verrous protegent une table : le DROIT de la lire, et le verrou
-- RLS qui filtre les lignes. Regarder le premier seul ne dit rien — et
-- une VUE echappe aux deux, puisqu'elle s'execute avec les droits de son
-- createur. D'ou la derniere colonne, qui fait la synthese.
-- ============================================================
select c.relname                                   as objet,
       case c.relkind when 'v' then 'vue' else 'table' end as genre,
       has_table_privilege('anon', c.oid, 'SELECT') as droit_de_lire,
       c.relrowsecurity                             as verrou_pose,
       (select count(*) from pg_policies p
         where p.schemaname = 'public' and p.tablename = c.relname) as regles,
       case
         when c.relkind = 'v' and has_table_privilege('anon', c.oid, 'SELECT')
              then 'OUI'
         when c.relkind = 'v' then 'non'
         when not has_table_privilege('anon', c.oid, 'SELECT') then 'non'
         when not c.relrowsecurity then 'OUI'
         when (select count(*) from pg_policies p
                where p.schemaname='public' and p.tablename=c.relname) = 0 then 'non'
         else 'selon les regles'
       end                                          as un_visiteur_lit
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind in ('r','v')
 order by un_visiteur_lit desc, 1;
