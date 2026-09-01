-- ============================================================
-- VERIFICATION DE LA BASE — Le Sanctuaire des Brumes
--
-- Cette requete NE MODIFIE RIEN. Elle se contente de regarder
-- comment la base est configuree et de le raconter.
--
-- Mode d'emploi :
--   Supabase > SQL Editor > New query > coller ceci > Run
--   Puis copier le tableau de resultats et le renvoyer a Claude.
-- ============================================================

select 'A. PROTECTION' as bloc,
       c.relname || '  ->  ' ||
       case when c.relrowsecurity then 'protegee' else '*** NON PROTEGEE ***' end as detail
from pg_class c
where c.relnamespace = 'public'::regnamespace
  and c.relkind = 'r'

union all

select 'B. REGLE',
       p.tablename || '  |  action: ' || p.cmd ||
       '  |  pour: ' || array_to_string(p.roles, ',') ||
       '  |  nom: ' || p.policyname ||
       '  |  condition d''acces: ' || coalesce(p.qual, 'aucune') ||
       '  |  condition d''ecriture: ' || coalesce(p.with_check, 'aucune')
from pg_policies p
where p.schemaname = 'public'

union all

select 'C. LIMITE',
       con.conrelid::regclass::text || '  |  ' || pg_get_constraintdef(con.oid)
from pg_constraint con
where con.connamespace = 'public'::regnamespace
  and con.contype in ('c','u','p','f')

union all

select 'D. CONTENU', 'codes enregistres : ' || count(*)::text from codes
union all
select 'D. CONTENU', 'bornes enregistrees : ' || count(*)::text from qr_points
union all
select 'D. CONTENU', 'passages enregistres : ' || count(*)::text from scans

order by 1, 2;
