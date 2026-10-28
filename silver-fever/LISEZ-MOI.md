# Silver Fever, le site des 30 ans

Samedi 30 janvier 2027, 19h30, Expérience Park, Wittenheim.
Apéro dînatoire sur place. Réponses attendues avant le 15 janvier.

Ce dossier n'a rien à voir avec l'escape game : il est rangé ici
provisoirement et doit partir dans son propre dépôt GitHub.

| Fichier | À quoi il sert |
|---|---|
| `index.html` | Tout le site, en un seul fichier (style et script compris) |
| `silver-fever.sql` | Crée la table de la playlist dans Supabase |

Deux circuits :
- **Le sondage** (oui / non) part **par mail** grâce à Formspree.
  Ton amie reçoit chaque réponse, les invités ne voient pas qui vient.
- **La playlist** est rangée dans **Supabase** (la base de l'escape game,
  table `sf_sons`) : tout le monde voit la liste des sons proposés.
  Si Supabase ne répond pas, le son part par mail à la place, pour ne
  pas être perdu.

## Mise en ligne, dans l'ordre

1. **Formspree.** Fait : le formulaire `https://formspree.io/f/xwllberr`
   est branché (`FORMSPREE_ID` en haut du script d'`index.html`). Les
   mails arrivent à l'adresse du compte Formspree qui a créé ce formulaire.
2. **(rien à faire)**
3. **La playlist.** Dans Supabase > SQL Editor, coller tout
   `silver-fever.sql` et cliquer sur Run. Sans cette étape, la playlist
   ne s'affiche pas et chaque son part par mail (plan B).
4. **Le dépôt.** Sur GitHub, créer un nouveau dépôt public (par exemple
   `silver-fever`) et y déposer `index.html` (bouton « Add file > Upload files »).
5. **La publication.** Dans le dépôt : Settings > Pages > Source
   « Deploy from a branch », branche `main`, dossier `/ (root)`, Save.
   Le site est en ligne une à deux minutes plus tard à l'adresse
   `https://<ton-compte>.github.io/silver-fever/`.
6. **Le test.** Depuis le site en ligne, répondre une fois au sondage
   (le mail doit arriver, vérifier les spams ; le tout premier envoi
   peut demander une confirmation dans Formspree), puis proposer un son
   (il doit apparaître dans la liste). Effacer ensuite le son de test
   dans Supabase > Table Editor > sf_sons.

## Ce que reçoit ton amie

Un mail par envoi, avec un objet lisible d'un coup d'œil :

- `✅ OUI · Julie M (2 personnes) · Silver Fever`
- `❌ NON · Thomas · Silver Fever`
- `🎵 Dancing Queen · ABBA · Silver Fever` (seulement si la liste partagée
  était indisponible au moment de l'envoi)

Toutes les réponses restent aussi consultables dans le tableau de bord
Formspree, et peuvent s'y exporter en tableau.

## À surveiller

- **Le quota gratuit de Formspree** est limité (de l'ordre de 50 envois
  par mois, à vérifier sur leur page de tarifs). Seules les réponses au
  sondage le consomment en temps normal.
- **Supabase gratuit se met en pause après 7 jours sans activité.** La
  playlist cesse alors de s'afficher et les sons partent par mail. Rien
  n'est perdu : un clic sur « Restore project » dans Supabase relance
  tout. Y penser en envoyant l'invitation et la semaine avant la soirée.
- **Retirer un son** (doublon, blague) : Supabase > Table Editor > sf_sons,
  ou la requête en bas de `silver-fever.sql`.
- **Une personne qui change d'avis** envoie une nouvelle réponse : c'est
  le mail le plus récent qui compte.

## Ce qui se règle facilement

En haut du script d'`index.html` :
- `DEBUT` : la date et l'heure, utilisées par le compte à rebours et l'agenda.
- `DATE_LIMITE` : après cette date, le sondage reste ouvert mais signale
  que la date est passée.
