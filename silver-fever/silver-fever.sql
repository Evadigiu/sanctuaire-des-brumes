-- ============================================================
-- SILVER FEVER : les deux tables du site d'anniversaire
-- ============================================================
-- À lancer UNE FOIS dans Supabase > SQL Editor > New query > Run.
-- Le script peut être relancé sans danger (il ne supprime rien).
--
-- Ce qu'il crée :
--   sf_reponses : les réponses au sondage (oui / non). Les invités
--                 peuvent répondre, mais PERSONNE ne peut lire la liste
--                 depuis le site. Toi seule la lis dans Supabase.
--   sf_sons     : la playlist. Les invités ajoutent et voient la liste.
--   sf_compte_venues() : renvoie seulement le nombre de « oui »,
--                 pour afficher « 12 personnes ont déjà dit oui ».
--
-- Préfixe « sf_ » : pour ne jamais se mélanger aux tables de
-- l'escape game si la même base sert aux deux projets.
-- ============================================================

create table if not exists public.sf_reponses (
  id            bigint generated always as identity primary key,
  prenom        text    not null check (char_length(prenom) between 1 and 80),
  venue         boolean not null,
  nb_personnes  smallint not null default 1 check (nb_personnes between 0 and 4),
  mot           text    check (mot is null or char_length(mot) <= 500),
  cree_le       timestamptz not null default now()
);

create table if not exists public.sf_sons (
  id           bigint generated always as identity primary key,
  titre        text not null check (char_length(titre) between 1 and 120),
  artiste      text check (artiste is null or char_length(artiste) <= 120),
  propose_par  text check (propose_par is null or char_length(propose_par) <= 80),
  cree_le      timestamptz not null default now()
);

-- Verrouillage : sans règle explicite, rien n'est permis
alter table public.sf_reponses enable row level security;
alter table public.sf_sons     enable row level security;

-- Les invités (rôle anon) peuvent répondre, sans pouvoir lire, modifier ni effacer
drop policy if exists "invites repondent" on public.sf_reponses;
create policy "invites repondent" on public.sf_reponses
  for insert to anon with check (true);

-- Les invités peuvent ajouter un son et lire la playlist
drop policy if exists "invites ajoutent un son" on public.sf_sons;
create policy "invites ajoutent un son" on public.sf_sons
  for insert to anon with check (true);

drop policy if exists "invites lisent la playlist" on public.sf_sons;
create policy "invites lisent la playlist" on public.sf_sons
  for select to anon using (true);

grant insert on public.sf_reponses to anon;
grant insert, select on public.sf_sons to anon;

-- Le compteur affiché sur le site : seulement des totaux, jamais de prénom.
-- Si quelqu'un répond deux fois avec le même prénom, seule sa dernière réponse compte.
create or replace function public.sf_compte_venues()
returns json
language sql
security definer
set search_path = public
as $$
  with derniere as (
    select distinct on (lower(trim(prenom))) venue, nb_personnes
    from sf_reponses
    order by lower(trim(prenom)), cree_le desc
  )
  select json_build_object(
    'personnes', coalesce(sum(nb_personnes) filter (where venue), 0),
    'reponses',  count(*)
  )
  from derniere;
$$;

revoke all on function public.sf_compte_venues() from public;
grant execute on function public.sf_compte_venues() to anon;


-- ============================================================
-- POUR CONSULTER (à copier dans SQL Editor quand tu veux)
-- ============================================================
--
-- La liste des invités, une ligne par personne (sa dernière réponse) :
--
--   select distinct on (lower(trim(prenom)))
--          prenom, case when venue then 'oui' else 'non' end as reponse,
--          nb_personnes, mot, cree_le
--   from sf_reponses
--   order by lower(trim(prenom)), cree_le desc;
--
-- Le total de personnes attendues :
--
--   select public.sf_compte_venues();
--
-- La playlist dans l'ordre des propositions :
--
--   select titre, artiste, propose_par from sf_sons order by cree_le;
--
-- Retirer un son indésirable (remplace 12 par son id) :
--
--   delete from sf_sons where id = 12;
