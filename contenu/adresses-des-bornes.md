# Adresses des bornes a encoder dans les QR codes

Domaine utilise : `https://enquete.pomelolab.fr`

> **A verifier avant toute impression.** Un QR code encode une adresse en dur.
> Si le site passe un jour sur un nom de domaine personnalise, toutes les
> affichettes deja posees dans le parc cessent de fonctionner. Ce choix doit
> etre arrete avant la fabrication, pas apres.

Le depart (E00) n'a pas de QR dans le parc : le code est remis sur un ticket
papier a la caisse, et le joueur arrive sur la page d'accueil du site.

Chaque affichette porte le QR code ET le nombre a 4 chiffres, a saisir dans
le jeu si le QR refuse de se lire.

| Code | Borne | Lieu | Sens A | Sens B | Secours | Adresse a encoder |
|---|---|---|---|---|---|---|
| E01 | LE COMMISSAIRE JEAN | Jardin des pivoines | 1 | 1 | **8055** | `https://enquete.pomelolab.fr/8055/` |
| E02 | LA COLLÈGUE SOIGNEUSE | Bureau des soignants | 2 | 8 | **1965** | `https://enquete.pomelolab.fr/1965/` |
| E16 | Greg, version sens B | au milieu | — | 2 | **8017** | `https://enquete.pomelolab.fr/8017/` |
| E03 | Indice : les cameras de surveillance | Salle de seminaire | 3 | 7 | **3215** | `https://enquete.pomelolab.fr/3215/` |
| E04 | Indice : les jumelles, la carcasse | Enclos des loups | 4 | 9 | **3208** | `https://enquete.pomelolab.fr/3208/` |
| E05 | LA PASSANTE | Au dessus de l'enclos des loups | 5 | 10 | **6120** | `https://enquete.pomelolab.fr/6120/` |
| E06 | QUIZ ANIMALIER | Panthère de l'amour | 6 | 11 | **8048** | `https://enquete.pomelolab.fr/8048/` |
| E07 | VÉTÉRINAIRE | Forêt | 7 | 12 | **7157** | `https://enquete.pomelolab.fr/7157/` |
| E08 | Indice : le panneau d'empreinte | Après le vétérinaire | 8 | 13 | **1959** | `https://enquete.pomelolab.fr/1959/` |
| E09 | Greg, version sens A | Sentier des plantes sauvages d'alsace | 9 | — | **6116** | `https://enquete.pomelolab.fr/6116/` |
| E10 | Bill | Grande volière | 10 | 3 | **8023** | `https://enquete.pomelolab.fr/8023/` |
| E11 | Indice : Le sac du botaniste | Jardin des tulipes | 11 | 4 | **1871** | `https://enquete.pomelolab.fr/1871/` |
| E12 | Appel du commissaire | Statues | 12 | 5 | **1868** | `https://enquete.pomelolab.fr/1868/` |
| E13 | Bureau de Greg | Zone de picnic | 13 | 6 | **3182** | `https://enquete.pomelolab.fr/3182/` |
| E14 | LE BOTANISTE | Jardin des Iris | 14 | 14 | **3177** | `https://enquete.pomelolab.fr/3177/` |
| E15 | La serre | La serre | 15 | 15 | **6025** | `https://enquete.pomelolab.fr/6025/` |

## Page d'accueil (remise du ticket)

`https://enquete.pomelolab.fr/` — le joueur y arrive avec le code imprime sur son ticket.

## Pourquoi des adresses en chiffres

L'adresse s'affiche dans la barre du navigateur avant meme que la
page se charge. `/etapes/e04-indice-les-jumelles-la-carcasse.html`
annoncait l'enigme et le nombre d'etapes ; `/3208/` ne dit rien.

Le nombre est aussi celui a saisir si le QR refuse de se lire : une
seule reference a imprimer sur l'affichette, pour les deux usages.

