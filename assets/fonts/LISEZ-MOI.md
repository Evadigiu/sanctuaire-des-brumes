# Les polices du jeu

## DCC — Ash (titres)

`dcc-ash.otf` est le fichier d'origine, tel que fourni. `dcc-ash.woff2` est la
version servie aux joueurs : convertie au format web, et allégée.

**Elle ne contient que les CAPITALES**, les chiffres et la ponctuation, parce
que les titres du site sont affichés en majuscules et qu'aucune minuscule n'est
donc jamais dessinée. Cela divise son poids par presque cinq : 638 Ko au départ,
136 Ko à l'arrivée. Sur un réseau que douze groupes se partagent à l'accueil du
zoo, ça se sent.

**Si un jour un titre doit s'afficher en casse normale**, il faudra refabriquer
ce fichier en gardant les minuscules :

```python
from fontTools import subset
opt = subset.Options(); opt.layout_features = ["*"]; opt.flavor = "woff2"
f = subset.load_font("assets/fonts/dcc-ash.otf", opt)
s = subset.Subsetter(options=opt)
s.populate(text="ABC...abc...0123 .,;:!?")   # ajouter les minuscules
s.subset(f)
subset.save_font(f, "assets/fonts/dcc-ash.woff2", opt)
```

### Ce que cette police ne sait pas écrire

Elle vise l'Europe centrale, pas le français. Vingt caractères français lui
manquent, dont des courants :

```
à ç è ê ï ù û ÿ œ æ   À Ç È Ê Ï Ù Û Ÿ Œ Æ
```

Elle possède en revanche l'accent aigu et le tréma : `é ë î ô ü É Ë Î Ô Ü`.

Dans les titres actuels, deux mots sont touchés : **LA COLLÈGUE SOIGNEUSE** et
**VOTRE ENQUÊTE COMMENCE**. Le navigateur dessine alors ces lettres-là avec la
police de repli, ce qui se voit.

Trois façons de s'en sortir, par ordre de préférence :
1. fabriquer les lettres manquantes dans la police (faisable : les accents
   isolés `grave`, `acute`, `dieresis` et `cedilla` existent, il n'y a qu'à les
   composer avec les lettres de base) ;
2. reformuler les titres concernés ;
3. ne rien faire et accepter le mélange de polices sur ces deux mots.

### Licence

Le fichier ne déclare aucune licence. Son autorisation d'intégration technique
est « editable embedding », qui permet l'usage web et la modification. Cela ne
dit rien de la licence juridique : beaucoup de polices gratuites sont réservées
à un usage personnel, ce que n'est pas un jeu à billets payants. **À vérifier
auprès de la fonderie avant le lancement.**

## Avenir (sous-titres et corps)

Avenir n'est pas installée dans la police du site : c'est une police
commerciale, présente d'origine sur iPhone et Mac, absente d'Android et de
Windows. Environ la moitié des joueurs ne la verront donc pas.

Le site la demande en premier, puis se rabat sur **Mulish**, dessinée sur le
même principe et très proche à l'œil. Mulish est chargée depuis Google Fonts.
