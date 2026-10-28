# Silver Fever, le site des 30 ans

Samedi 30 janvier 2027, 19h30, Expérience Park, Wittenheim.

Ce dossier n'a rien à voir avec l'escape game : il est rangé ici
provisoirement et doit partir dans son propre dépôt GitHub.

## Les fichiers

| Fichier | À quoi il sert |
|---|---|
| `index.html` | Tout le site, en un seul fichier (style et script compris) |
| `silver-fever.sql` | Crée les tables du sondage et de la playlist dans Supabase |

## Mise en ligne, dans l'ordre

1. **La base.** Dans Supabase > SQL Editor, colle tout `silver-fever.sql`
   et clique sur Run. Sans cette étape, le site s'affiche mais le sondage
   et la playlist renvoient « Impossible d'enregistrer ».
2. **Le dépôt.** Sur GitHub, crée un nouveau dépôt public (par exemple
   `silver-fever`) et dépose-y `index.html` (bouton « Add file > Upload files »).
3. **La publication.** Dans le dépôt : Settings > Pages > Source
   « Deploy from a branch », branche `main`, dossier `/ (root)`, Save.
   Le site est en ligne une à deux minutes plus tard à l'adresse
   `https://<ton-compte>.github.io/silver-fever/`.
4. **Le test.** Réponds une fois au sondage et ajoute un son, puis
   vérifie dans Supabase > Table Editor que les lignes apparaissent.
   Efface-les ensuite si tu veux repartir de zéro.

## Lire les réponses

Les invités ne voient jamais qui a répondu, seulement le nombre de « oui ».
La liste complète se lit dans Supabase : les requêtes toutes prêtes sont
en bas de `silver-fever.sql`. Si quelqu'un répond deux fois avec le même
prénom, c'est sa dernière réponse qui compte.

## Deux points à surveiller

- **La base est celle de l'escape game.** Les tables sont préfixées `sf_`
  pour ne rien mélanger, mais si tu préfères séparer, crée un projet
  Supabase gratuit dédié, lance le SQL dedans, et remplace les deux
  lignes `SUPABASE_URL` et `SUPABASE_ANON_KEY` en haut du script
  d'`index.html`.
- **Supabase gratuit se met en pause après 7 jours sans activité.** Si
  les invitations partent longtemps avant la soirée, il peut y avoir des
  semaines creuses. Le site affichera alors une erreur au moment
  d'enregistrer. Les données ne sont pas perdues : un clic sur
  « Restore project » dans Supabase suffit. Pense à y jeter un œil
  quand tu envoies l'invitation et dans la semaine qui précède la soirée.

## Ce qui se règle facilement

En haut du script d'`index.html` :
- `FIN_AGENDA` : l'heure de fin mise dans les agendas (2h du matin par défaut,
  c'est une estimation).
- `DEBUT` : la date et l'heure, utilisées par le compte à rebours.
