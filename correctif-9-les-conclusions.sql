-- ============================================================
-- LE GUICHET DES CONCLUSIONS
--
-- A coller dans Supabase : SQL Editor > NOUVEL ONGLET > Run.
--
-- >>> Supabase proposera peut-etre « Run and enable RLS » (bouton vert).
-- >>> REPONDEZ « RUN WITHOUT RLS » (bouton orange). C'est une fausse alerte :
-- >>> l'outil prend un bout de la fonction pour une creation de table et
-- >>> casse la requete. Ca nous est deja arrive.
--
-- CE QUE FAIT CE FICHIER
-- La table conclusions n'avait AUCUNE regle d'acces. Les reponses des
-- joueurs y etaient donc rejetees en silence : le jeu affichait sa fin,
-- et rien n'arrivait jamais dans la base.
--
-- On ne donne pas pour autant le droit d'ecrire au telephone du joueur.
-- Il passe par un guichet, comme pour les passages de bornes : une
-- fonction qui verifie la partie, range le texte, et ne rend que « c'est
-- enregistre ». Personne ne peut lire les conclusions des autres, ni en
-- inventer pour une partie qui ne lui appartient pas.
-- ============================================================

alter table conclusions enable row level security;
revoke all on conclusions from anon, authenticated;

-- Le verdict est desormais un rang de denouement, pas un avis d'IA.
alter table conclusions drop constraint if exists conclusions_ai_verdict_check;

create or replace function enregistrer_conclusions(
  p_code_id uuid,
  p_texte text,
  p_denouement text
) returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_ok boolean;
  v_texte text;
begin
  -- 1. La partie existe-t-elle, et a-t-elle ete activee ?
  select true into v_ok
    from codes
   where id = p_code_id and status in ('active', 'expired')
   limit 1;
  if v_ok is not true then
    return json_build_object('ok', false, 'message', 'Partie inconnue.');
  end if;

  -- 2. On borne le texte. Un champ libre sur un site public finit
  --    toujours par recevoir autre chose que des conclusions d'enquete.
  v_texte := left(coalesce(p_texte, ''), 2000);
  if length(btrim(v_texte)) = 0 then
    return json_build_object('ok', false, 'message', 'Conclusions vides.');
  end if;

  -- 3. Une seule reddition par partie. Le groupe qui recharge sa page ne
  --    doit pas remplir la table de doublons.
  if exists (select 1 from conclusions where code_id = p_code_id) then
    return json_build_object('ok', true, 'deja_rendu', true);
  end if;

  insert into conclusions (code_id, submitted_text, ai_verdict)
  values (p_code_id, v_texte, left(coalesce(p_denouement, ''), 20));

  return json_build_object('ok', true);
end;
$$;

revoke all on function enregistrer_conclusions(uuid, text, text) from public;
grant execute on function enregistrer_conclusions(uuid, text, text)
  to anon, authenticated;

-- ============================================================
-- POUR LIRE LES CONCLUSIONS APRES COUP
--
-- A lancer depuis l'editeur SQL quand vous voudrez les relire. Le code
-- est masque : seuls ses quatre derniers signes apparaissent, de quoi
-- retrouver un groupe sans etaler la billetterie a l'ecran.
-- ============================================================
create or replace view conclusions_rendues as
select c.created_at,
       right(co.code, 4) as code,
       c.ai_verdict      as denouement,
       c.submitted_text  as conclusions
  from conclusions c
  join codes co on co.id = c.code_id
 order by c.created_at desc;

-- Controle : doit s'afficher sans erreur (vide tant que personne n'a joue).
select * from conclusions_rendues limit 5;
