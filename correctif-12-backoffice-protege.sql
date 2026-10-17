-- ============================================================
-- CORRECTIF 12 — Le backoffice protégé, et l'historique des parties
--
-- A LANCER EN DERNIER, dans cet ordre :
--   1. Supabase, Authentication : inscriptions FERMEES, et un compte
--      créé pour l'équipe (voir la notice dans la PR) ;
--   2. la PR du backoffice fusionnée (connexion par e-mail) ;
--   3. ce fichier, collé dans le SQL Editor, puis « Run ».
-- Lancé avant l'étape 2, le tableau de bord en ligne deviendrait vide
-- jusqu'à la fusion. Le JEU, lui, n'est touché à aucun moment.
--
-- CE QU'IL FAIT
--   A. Le nom d'équipe saisi au départ est enfin gardé en base (il ne
--      vivait que dans le téléphone du groupe).
--   B. Une vue « historique_parties » : une ligne par partie, avec tout ce
--      que le jeu sait d'elle. Rien n'est jamais effacé : les données
--      restent tant qu'on ne les supprime pas à la main.
--   C. Les vues du backoffice ne répondent plus qu'à un compte connecté.
--      Jusqu'ici, la clé publique du site suffisait à les lire, et l'une
--      d'elles (code_progress) donnait les codes ENTIERS des parties
--      commencées : de quoi rejoindre la partie d'un groupe en cours.
--   D. Le bouton « Traité » des signalements, réservé lui aussi.
--
-- On peut le relancer sans danger.
-- ============================================================


-- ------------------------------------------------------------
-- A. LE NOM DU GROUPE
-- ------------------------------------------------------------
alter table codes add column if not exists nom_groupe text;

-- Un guichet à part, appelé juste après l'activation, plutôt qu'un
-- paramètre de plus à activer_code : si ce correctif n'est pas encore
-- lancé, l'appel échoue en silence et la partie démarre quand même.
create or replace function nommer_groupe(p_code_id uuid, p_nom text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_nom text := left(btrim(coalesce(p_nom, '')), 60);
begin
  if v_nom = '' then return false; end if;
  -- Seulement une partie commencée, et une seule fois : on ne rebaptise
  -- pas le groupe d'un autre.
  update codes set nom_groupe = v_nom
   where id = p_code_id
     and status in ('active', 'expired')
     and nom_groupe is null;
  return found;
end;
$$;

revoke all on function nommer_groupe(uuid, text) from public;
grant execute on function nommer_groupe(uuid, text) to anon, authenticated;


-- ------------------------------------------------------------
-- B. L'HISTORIQUE DE TOUTES LES PARTIES
-- ------------------------------------------------------------
create or replace view historique_parties as
select
  c.activated_at,
  c.code,
  c.nom_groupe,
  c.participants_reels,
  c.max_participants,
  c.direction,
  c.slot_time,
  c.expires_at,
  c.status,
  count(distinct s.qr_point_id)                    as nb_bornes,
  count(s.id)                                      as nb_scans,
  min(s.scanned_at)                                as premier_scan,
  max(s.scanned_at)                                as dernier_scan,
  coalesce(bool_or(qp.label = 'La serre'), false)  as a_atteint_la_serre,
  (select qp2.label from scans s2
     join qr_points qp2 on qp2.id = s2.qr_point_id
    where s2.code_id = c.id
    order by s2.scanned_at desc limit 1)           as derniere_borne,
  string_agg(qp.label || ' ' || to_char(s.scanned_at at time zone 'Europe/Paris', 'HH24:MI'),
             ' → ' order by s.scanned_at)          as parcours,
  (select co.submitted_text from conclusions co
    where co.code_id = c.id order by co.created_at limit 1) as conclusion,
  (select co.ai_verdict from conclusions co
    where co.code_id = c.id order by co.created_at limit 1) as denouement,
  (select count(*) from signalements sg where sg.code_id = c.id) as nb_signalements
from codes c
left join scans s      on s.code_id = c.id
left join qr_points qp on qp.id = s.qr_point_id
where c.activated_at is not null
group by c.id
order by c.activated_at desc;


-- ------------------------------------------------------------
-- Les codes ENTIERS au tableau de bord, maintenant qu'il est protégé.
-- On ajoute une colonne en fin de vue (« code » reste les 4 derniers
-- caractères), ce qui laisse le correctif 11 valable, lancé ou non.
-- ------------------------------------------------------------
create or replace view departs_recents as
select activated_at, participants_reels, max_participants, direction,
       right(code, 4) as code, code as code_complet, nom_groupe
from codes
where activated_at is not null;

create or replace view live_dashboard as
select
  right(c.code, 4) as code,
  c.max_participants,
  c.direction,
  c.slot_time,
  c.activated_at,
  c.expires_at,
  qp.label as last_point,
  s.scanned_at as last_scan_at,
  now() - s.scanned_at as time_since_last_scan,
  c.code as code_complet,
  c.nom_groupe,
  c.participants_reels
from codes c
left join lateral (
  select qr_point_id, scanned_at
  from scans
  where scans.code_id = c.id
  order by scanned_at desc
  limit 1
) s on true
left join qr_points qp on qp.id = s.qr_point_id
where c.status = 'active'
  and c.expires_at > now();


-- ------------------------------------------------------------
-- C. LES VUES DU BACKOFFICE, RESERVEES A UN COMPTE CONNECTE
--
-- Ces vues lisent les tables avec les droits de leur propriétaire : c'est
-- donc le droit de LIRE LA VUE qui fait la porte. On le retire au public
-- (anon) et on le donne aux comptes connectés (authenticated). Les
-- inscriptions étant fermées, « connecté » veut dire : l'équipe.
-- Une vue absente de la base est simplement passée.
-- ------------------------------------------------------------
do $$
declare
  v text;
begin
  foreach v in array array[
    'live_dashboard', 'departs_recents', 'signalements_recents',
    'reconciliation_daily', 'historique_parties', 'conclusions_rendues',
    'code_progress', 'scan_durations', 'avg_duration_by_point',
    'abandon_points', 'completion_summary'
  ] loop
    if to_regclass('public.' || v) is not null then
      execute format('revoke all on table public.%I from anon, public', v);
      execute format('grant select on table public.%I to authenticated', v);
    end if;
  end loop;
end $$;


-- ------------------------------------------------------------
-- D. LE BOUTON « TRAITE » DES SIGNALEMENTS
-- ------------------------------------------------------------
revoke all on function marquer_signalement_traite(uuid) from anon, public;
grant execute on function marquer_signalement_traite(uuid) to authenticated;


-- ------------------------------------------------------------
-- CONTROLE : chaque ligne doit dire « fermee au public ».
-- ------------------------------------------------------------
select v as vue,
       case when to_regclass('public.' || v) is null then 'absente (rien a faire)'
            when has_table_privilege('anon', 'public.' || v, 'select') then 'ENCORE OUVERTE'
            else 'fermee au public' end as etat
from unnest(array[
  'live_dashboard', 'departs_recents', 'signalements_recents',
  'reconciliation_daily', 'historique_parties', 'conclusions_rendues',
  'code_progress', 'scan_durations', 'avg_duration_by_point',
  'abandon_points', 'completion_summary'
]) as v;
