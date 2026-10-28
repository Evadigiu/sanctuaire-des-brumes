-- ============================================================
-- SILVER FEVER : la playlist partagée du site d'anniversaire
-- ============================================================
-- À lancer UNE FOIS dans Supabase > SQL Editor > New query > Run.
-- Le script peut être relancé sans danger (il ne supprime rien).
--
-- Seule la playlist vit ici. Les réponses au sondage partent par
-- mail via Formspree et ne passent pas par Supabase.
--
-- Préfixe « sf_ » : pour ne jamais se mélanger aux tables de
-- l'escape game, qui utilisent la même base.
-- ============================================================

create table if not exists public.sf_sons (
  id           bigint generated always as identity primary key,
  titre        text not null check (char_length(titre) between 1 and 120),
  artiste      text check (artiste is null or char_length(artiste) <= 120),
  propose_par  text check (propose_par is null or char_length(propose_par) <= 80),
  cree_le      timestamptz not null default now()
);

-- Verrouillage : sans règle explicite, rien n'est permis
alter table public.sf_sons enable row level security;

-- Les invités (rôle anon) peuvent ajouter un son et lire la liste,
-- mais ni modifier ni effacer ceux des autres.
drop policy if exists "invites ajoutent un son" on public.sf_sons;
create policy "invites ajoutent un son" on public.sf_sons
  for insert to anon with check (true);

drop policy if exists "invites lisent la playlist" on public.sf_sons;
create policy "invites lisent la playlist" on public.sf_sons
  for select to anon using (true);

revoke all on public.sf_sons from anon;
grant insert, select on public.sf_sons to anon;


-- ============================================================
-- POUR GÉRER LA PLAYLIST (à copier dans SQL Editor quand tu veux)
-- ============================================================
--
-- La playlist dans l'ordre des propositions, avec les numéros :
--
--   select id, titre, artiste, propose_par from sf_sons order by cree_le;
--
-- Retirer un son (remplace 12 par son numéro) :
--
--   delete from sf_sons where id = 12;
--
-- On peut aussi tout faire à la souris dans Table Editor > sf_sons.
