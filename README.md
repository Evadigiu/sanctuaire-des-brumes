# Le Sanctuaire des Brumes, code du jeu

Site statique (aucune installation locale nécessaire) + Supabase comme
arrière-boutique (codes, chrono, suivi des scans).

## Où en est ce premier jet

Ce qui fonctionne déjà dans ce dossier :
- La page de départ (`index.html`) : consignes, saisie du code, activation.
- Une page d'étape modèle (`etapes/bureau-soignants.html`), à dupliquer
  pour les 11 autres bornes.
- Le chrono de 3h, calculé côté serveur (Supabase), pas côté téléphone.
- L'enregistrement de chaque passage de borne (table `scans`).

Ce qu'il reste à faire, dans l'ordre logique :
1. Créer le projet Supabase et y coller le schéma (étapes ci-dessous).
2. Dupliquer `etapes/bureau-soignants.html` pour créer les 11 autres pages,
   en changeant le titre, le témoin, le contenu, et le lien "étape suivante".
3. Ajouter les vraies vidéos une fois tournées (remplacer les balises `<source>` vides).
4. Construire l'étape finale (quiz + conclusions + verdict IA), pas encore incluse ici.
5. Construire le dashboard de suivi en direct (page séparée, protégée).
6. Générer les vrais codes en masse (script à faire, pas le `seed.sql` de test).
7. Brancher le sens B une fois confirmé sur le terrain (voir note dans `index.html`).

## Étape 1, créer le projet Supabase

1. Va sur [supabase.com](https://supabase.com), crée un compte gratuit.
2. Crée un nouveau projet (choisis une région Europe pour la vitesse).
3. Note le mot de passe de base de données que tu choisis à la création,
   garde le de côté.
4. Une fois le projet créé, va dans l'onglet **SQL Editor** (menu de gauche).
5. Ouvre `schema_escape_game.sql` de ce dossier, copie tout le contenu,
   colle le dans une nouvelle requête, clique **Run**.
6. Fais la même chose avec `seed.sql`, pour peupler les 12 bornes et
   créer 3 codes de test (`TEST01`, `TEST02`, `TEST03`).
7. Va dans **Project Settings > API**. Tu y trouveras deux informations :
   - `Project URL`
   - la clé `anon public`
8. Ouvre `assets/js/supabase-client.js` dans ce dossier, colle ces deux
   valeurs à la place de `VOTRE-PROJET` et `VOTRE_CLE_ANON_PUBLIC`.

## Étape 2, mettre le site en ligne (GitHub Pages)

1. Crée un nouveau dépôt GitHub (public ou privé, les deux fonctionnent
   avec GitHub Pages sur un compte gratuit si le dépôt est public ;
   privé demande un compte payant).
2. Ajoute tous les fichiers de ce dossier dans le dépôt (glisser-déposer
   possible depuis l'interface web de GitHub, comme pour TBA).
3. Dans le dépôt, va dans **Settings > Pages**, choisis la branche
   principale comme source, sauvegarde.
4. Après une à deux minutes, le site est accessible à une adresse du
   type `https://tonpseudo.github.io/nom-du-depot/`.
5. Une fois un nom de domaine choisi, il pourra être branché à cette
   étape (comme pour pomelolab.fr).

## Tester en local avant de mettre en ligne

Comme c'est un site statique, tu peux l'ouvrir directement en double-cliquant
sur `index.html`, mais certains navigateurs bloquent les requêtes vers
Supabase depuis un fichier ouvert en local (`file://`). Le plus fiable est
de tester directement une fois mis en ligne sur GitHub Pages (gratuit,
quelques minutes de délai à chaque modification).

## Une fois les deux comptes prêts

Reviens vers moi avec les valeurs de l'étape 1 (Project URL et clé anon,
ou juste dis moi que c'est fait) et je peux continuer à construire la
suite : les 11 autres pages d'étape, l'étape finale avec l'IA, et le
dashboard de suivi.
