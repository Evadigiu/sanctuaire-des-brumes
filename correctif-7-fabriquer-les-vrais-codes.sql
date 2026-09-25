-- ============================================================
-- CORRECTIF 7 — FABRIQUER LES VRAIS CODES
-- Le Sanctuaire des Brumes — a lancer APRES le correctif 6.
--
-- A QUOI CA SERT
--
-- Le correctif 6 a ferme la liste des codes. Il reste a s'assurer qu'on ne
-- puisse pas les deviner. C'est la vraie protection : un compteur d'essais
-- ralentit un curieux, la longueur du code le decourage definitivement.
--
-- LE PIEGE A EVITER
--
-- La tentation naturelle est de numeroter : SDB-001, SDB-002, SDB-003. Ne
-- le fais jamais. Un visiteur qui voit le billet de son voisin devine tous
-- les autres en trois secondes, et le correctif 6 n'y peut rien.
--
-- LE FORMAT RETENU : 8 caracteres tires au hasard, dans un alphabet de 32
-- signes ou l'on a retire tout ce qui se confond a la lecture (pas de O ni
-- de 0, pas de I ni de 1). Cela fait mille milliards de combinaisons, et
-- personne au guichet ne lit un zero pour un O.
--
--   Exemple de code produit : K7NPX4RT
-- ============================================================


-- ------------------------------------------------------------
-- 1. LE TIRAGE AU SORT
--
-- gen_random_uuid() fournit du hasard de qualite cryptographique. Un
-- identifiant de ce type contient 16 octets, dont deux ne sont PAS
-- aleatoires : ce sont ceux qui disent "je suis un identifiant de type 4".
-- Les utiliser reduirait le choix a 16 lettres au lieu de 32 sur une des
-- positions du code. On prend donc les six premiers octets d'un premier
-- tirage et les deux premiers d'un second, tous parfaitement aleatoires.
--
-- L'alphabet fait 32 signes et 256 se divise par 32 : aucune lettre n'a
-- plus de chances qu'une autre.
-- ------------------------------------------------------------
create or replace function nouveau_code_lisible()
returns text
language plpgsql
as $$
declare
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';  -- ni I, ni O, ni 0, ni 1
  premier  bytea := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
  second   bytea := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
  resultat text := '';
  i        int;
begin
  for i in 0..5 loop
    resultat := resultat || substr(alphabet, 1 + (get_byte(premier, i) % 32), 1);
  end loop;
  for i in 0..1 loop
    resultat := resultat || substr(alphabet, 1 + (get_byte(second, i) % 32), 1);
  end loop;
  return resultat;
end;
$$;


-- ------------------------------------------------------------
-- 2. LA FABRIQUE
--
-- p_jour   : la date des billets (les codes ne se perimant qu'a l'usage,
--            cette date sert surtout au recoupement avec la billetterie)
-- p_taille : le nombre de personnes que le billet couvre, de 1 a 6
-- p_nombre : combien de codes fabriquer
-- p_sens   : 'horaire', 'antihoraire', ou rien du tout pour moitie-moitie
--            (c'est ce qui evite que tout le monde parte du meme cote)
--
-- Si le tirage tombe par malchance sur un code deja pris, il recommence.
-- ------------------------------------------------------------
create or replace function fabriquer_codes(
  p_jour   date,
  p_taille int,
  p_nombre int,
  p_sens   text default null
)
returns setof text
language plpgsql
as $$
declare
  v_code text;
  v_sens text;
  i      int;
begin
  if p_taille < 1 or p_taille > 6 then
    raise exception 'Un billet couvre de 1 a 6 personnes, pas %.', p_taille;
  end if;
  if p_sens is not null and p_sens not in ('horaire', 'antihoraire') then
    raise exception 'Le sens vaut horaire, antihoraire, ou rien.';
  end if;

  for i in 1..p_nombre loop
    v_sens := coalesce(p_sens,
      case when i % 2 = 1 then 'horaire' else 'antihoraire' end);

    loop
      v_code := nouveau_code_lisible();
      begin
        insert into codes (code, max_participants, direction, slot_time)
        values (v_code, p_taille, v_sens, p_jour + time '09:00');
        exit;
      exception when unique_violation then
        null;   -- deja pris, on retire
      end;
    end loop;

    return next v_code;
  end loop;
end;
$$;


-- ------------------------------------------------------------
-- 3. ON REFERME DERRIERE SOI
--
-- Postgres autorise par defaut TOUT LE MONDE a executer une fonction
-- nouvellement creee, et Supabase les expose au site. Sans ces deux
-- lignes, n'importe quel visiteur pourrait se fabriquer ses propres codes
-- depuis son telephone : on aurait ferme la porte et laisse l'imprimante
-- allumee dans le couloir.
--
-- Ces deux fonctions ne doivent servir qu'ici, dans le SQL Editor.
-- ------------------------------------------------------------
revoke execute on function nouveau_code_lisible()             from public, anon, authenticated;
revoke execute on function fabriquer_codes(date, int, int, text) from public, anon, authenticated;


-- ============================================================
-- 4. MODE D'EMPLOI
--
-- Rien au-dessus de cette ligne ne cree de code : ce sont des outils.
-- La fabrication, c'est ci-dessous, et c'est a toi de la lancer quand tu
-- connais tes volumes.
--
-- EXEMPLE — 40 billets de 2 personnes et 25 billets de 4 personnes pour
-- le 17 octobre 2026, repartis moitie dans chaque sens :
--
--   select fabriquer_codes('2026-10-17', 2, 40);
--   select fabriquer_codes('2026-10-17', 4, 25);
--
-- Chaque ligne renvoie la liste des codes fabriques.
--
-- AVANT LE PREMIER VRAI LOT, effacer les codes de test :
--
--   delete from scans where code_id in (select id from codes where code like 'TEST%');
--   delete from codes where code like 'TEST%';
--
-- POUR RECUPERER LA LISTE A IMPRIMER (codes jamais utilises) :
--
--   select code, max_participants as personnes, direction, date(slot_time) as jour
--     from codes
--    where status = 'unused'
--    order by jour, personnes, code;
--
-- Le bouton "Download CSV" sous les resultats de Supabase te sort le
-- fichier a donner a l'imprimeur.
--
-- COMBIEN EN FABRIQUER : au moins autant que de billets vendus, et une
-- reserve. Un code non distribue ne coute rien et ne s'use pas ; un code
-- manquant un samedi matin a la caisse coute une file d'attente.
-- ============================================================
