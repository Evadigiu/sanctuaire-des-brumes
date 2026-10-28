# Silver Fever, le site des 30 ans

Samedi 30 janvier 2027, 19h30, Expérience Park, Wittenheim.
Apéro dînatoire sur place. Réponses attendues avant le 15 janvier.

Ce dossier n'a rien à voir avec l'escape game : il est rangé ici
provisoirement et doit partir dans son propre dépôt GitHub.

Tout le site tient dans `index.html` (style et script compris). Les
réponses au sondage et les suggestions de chansons partent par mail
grâce à Formspree, aucune base de données n'est nécessaire.

## Mise en ligne, dans l'ordre

1. **Formspree (à faire par la personne qui doit recevoir les mails).**
   Créer un compte sur formspree.io avec son adresse mail, confirmer
   l'adresse, puis « New form ». Formspree donne une adresse du type
   `https://formspree.io/f/xbjnqwer` : l'identifiant, ce sont les
   caractères après `/f/`.
2. **Brancher le site.** Dans `index.html`, en haut du script, remplacer
   `A_REMPLACER` par cet identifiant :
   `const FORMSPREE_ID = "xbjnqwer";`
   Tant que ce n'est pas fait, les formulaires affichent « Le formulaire
   n'est pas encore branché ».
3. **Le dépôt.** Sur GitHub, créer un nouveau dépôt public (par exemple
   `silver-fever`) et y déposer `index.html` (bouton « Add file > Upload files »).
4. **La publication.** Dans le dépôt : Settings > Pages > Source
   « Deploy from a branch », branche `main`, dossier `/ (root)`, Save.
   Le site est en ligne une à deux minutes plus tard à l'adresse
   `https://<ton-compte>.github.io/silver-fever/`.
5. **Le test.** Répondre une fois au sondage et proposer un son depuis le
   site en ligne. Le tout premier envoi peut demander une confirmation
   dans Formspree. Vérifier ensuite que les deux mails arrivent (et pas
   dans les spams).

## Ce que reçoit ton amie

Un mail par envoi, avec un objet lisible d'un coup d'œil :

- `✅ OUI · Julie M (2 personnes) · Silver Fever`
- `❌ NON · Thomas · Silver Fever`
- `🎵 Dancing Queen · ABBA · Silver Fever`

Toutes les réponses restent aussi consultables dans le tableau de bord
Formspree, et peuvent s'y exporter en tableau.

## À surveiller

- **Le quota gratuit de Formspree** est limité (de l'ordre de 50 envois
  par mois, à vérifier sur leur page de tarifs). Les réponses ET les
  chansons comptent dans ce quota. Avec beaucoup d'invités qui répondent
  le même mois et proposent plusieurs sons, on peut l'atteindre : les
  envois suivants seraient alors refusés et le site afficherait une
  erreur. Formspree prévient par mail quand on s'en approche.
- **Les invités ne voient plus la playlist des autres**, seulement leurs
  propres propositions (gardées dans leur navigateur). Il n'y a plus non
  plus de compteur « X personnes ont dit oui ».
- **Une personne qui change d'avis** envoie une nouvelle réponse : c'est
  le mail le plus récent qui compte.

## Ce qui se règle facilement

En haut du script d'`index.html` :
- `DEBUT` : la date et l'heure, utilisées par le compte à rebours et l'agenda.
- `DATE_LIMITE` : après cette date, le sondage reste ouvert mais signale
  que la date est passée.
