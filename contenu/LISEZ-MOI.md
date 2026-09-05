# Le cahier de contenu

`sanctuaire-cahier-de-contenu.xlsx` contient **tous les textes du jeu**.

## Le principe

Les textes s'écrivent dans ce tableur, et les pages du site sont ensuite
fabriquées automatiquement à partir de lui.

Conséquence à retenir : **le tableur fait foi.** Si un texte doit changer, il
change ici, puis les pages sont refabriquées. Ne jamais corriger un texte
directement dans une page de `etapes/`, il serait écrasé à la fabrication
suivante.

## Pourquoi passer par un tableur plutôt qu'écrire dans les pages

Deux raisons, dont une qui compte vraiment.

La première est le volume : 86 blocs de texte répartis sur 17 étapes, avec des
variantes selon le sens du parcours. Page après page, on perd le fil de ce qui
est fait.

La seconde est plus importante. Le site retrouve chaque borne par son libellé
écrit en toutes lettres : une majuscule ou un accent de travers, et le passage
du groupe n'est pas enregistré, **sans aucun message d'erreur**. En fabriquant
les pages depuis le tableur, ces libellés ne sont jamais retapés à la main, et
cette classe d'erreur disparaît.

## Les trois onglets

- **Lisez-moi** : le mode d'emploi, et les questions en attente de réponse.
- **Parcours** : la structure du jeu, l'ordre des étapes dans chaque sens, les
  lieux. C'est là que se décide le nombre de QR codes à fabriquer.
- **Textes** : les 86 textes à écrire, un par ligne.

Les cases sur fond crème sont à remplir, celles sur fond gris sont fixées,
celles sur fond rose sont des questions ouvertes.

## Regénérer le tableur

`generer-le-cahier.py` reconstruit le fichier à vide. **Il écrase tout ce qui a
été écrit dedans.** Il ne sert qu'à faire évoluer la structure du cahier (une
colonne en plus, une étape ajoutée), jamais après le début de la rédaction,
sauf à récupérer d'abord le contenu déjà saisi.
