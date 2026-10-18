-- ============================================================
-- CORRECTIF 14 — « Alors, cette enquete vous a plu ? »
--
-- A la fin de l'enquete, le groupe note le jeu (1 a 5 etoiles) et peut
-- laisser un mot. Ce fichier cree :
--   - la table des avis, fermee au public : on n'y entre que par le
--     guichet donner_avis(), un avis par partie (renvoyer le corrige) ;
--   - la vue avis_joueurs, lisible par le seul compte de l'equipe ;
--   - deux colonnes « note » et « avis » a la fin de historique_parties.
--
-- A coller dans le SQL Editor, puis « Run ». On peut le relancer.
-- Tant qu'il n'est pas lance, l'ecran des etoiles s'affiche, mais l'envoi
-- echoue poliment (« Ce n'est pas grave, merci quand meme »).
-- ============================================================

create table if not exists avis (
  id       uuid primary key default gen_random_uuid(),
  code_id  uuid not null references codes(id),
  note     int  not null check (note between 1 and 5),
  texte    text,
  cree_le  timestamptz not null default now()
);
create unique index if not exists avis_un_par_partie on avis(code_id);

alter table avis enable row level security;
revoke all on table avis from anon, authenticated, public;

create or replace function donner_avis(p_code_id uuid, p_note int, p_texte text)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_ok boolean;
begin
  if p_note is null or p_note < 1 or p_note > 5 then
    return json_build_object('ok', false, 'message', 'Note invalide.');
  end if;
  -- Une vraie partie, commencee : pas d'avis anonymes venus d'ailleurs.
  select true into v_ok from codes
   where id = p_code_id and status in ('active', 'expired') limit 1;
  if v_ok is not true then
    return json_build_object('ok', false, 'message', 'Partie inconnue.');
  end if;

  insert into avis (code_id, note, texte)
  values (p_code_id, p_note, nullif(left(btrim(coalesce(p_texte, '')), 1000), ''))
  on conflict (code_id) do update
    set note = excluded.note, texte = excluded.texte, cree_le = now();

  return json_build_object('ok', true);
end;
$$;

revoke all on function donner_avis(uuid, int, text) from public;
grant execute on function donner_avis(uuid, int, text) to anon, authenticated;

-- Les avis, pour le tableau de bord (compte de l'equipe seulement).
create or replace view avis_joueurs as
select a.cree_le, a.note, a.texte,
       c.code, c.nom_groupe, c.participants_reels, c.direction,
       (select co.ai_verdict from conclusions co
         where co.code_id = c.id order by co.created_at limit 1) as denouement
  from avis a
  join codes c on c.id = a.code_id
 order by a.cree_le desc;

revoke all on table avis_joueurs from anon, public;
grant select on table avis_joueurs to authenticated;

-- L'historique, avec la note et l'avis en fin de ligne.
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
  (select count(*) from signalements sg where sg.code_id = c.id) as nb_signalements,
  (select av.note  from avis av where av.code_id = c.id) as note,
  (select av.texte from avis av where av.code_id = c.id) as avis
from codes c
left join scans s      on s.code_id = c.id
left join qr_points qp on qp.id = s.qr_point_id
where c.activated_at is not null
group by c.id
order by c.activated_at desc;

revoke all on table historique_parties from anon, public;
grant select on table historique_parties to authenticated;

-- CONTROLE : doit afficher « fermee au public » deux fois, et le guichet.
select 'avis_joueurs' as objet,
       case when has_table_privilege('anon', 'public.avis_joueurs', 'select')
            then 'ENCORE OUVERTE' else 'fermee au public' end as etat
union all
select 'avis (table)',
       case when has_table_privilege('anon', 'public.avis', 'select')
            then 'ENCORE OUVERTE' else 'fermee au public' end
union all
select 'guichet donner_avis',
       case when has_function_privilege('anon', 'donner_avis(uuid,int,text)', 'execute')
            then 'ouvert aux joueurs' else 'FERME' end;
