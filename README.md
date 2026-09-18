# Le Sanctuaire des Brumes

Escape game en plein air, Zoo de Mulhouse, 17 octobre au 2 novembre 2026.
Pomelo Événementiel.

Le document de référence du projet est **`CONTEXTE_PROJET.md`** : concept,
personnages, parcours, décisions prises. Ce README ne parle que du code.

Site en ligne : https://evadigiu.github.io/sanctuaire-des-brumes/

---

## Comment ça marche, en deux phrases

Un site statique (les pages que voient les joueurs) hébergé sur GitHub Pages,
et une base Supabase qui sert de mémoire (codes, chrono, passages de bornes).
Le site ne retient rien tout seul, tout ce qui doit survivre passe par Supabase.

Les deux sont déjà installés et fonctionnels. Il n'y a rien à mettre en route.

---

## Les fichiers

| Fichier | À quoi il sert |
|---|---|
| `index.html` | Page d'accueil, saisie du code, démarrage de la partie |
| `etapes/` | Les 16 pages du parcours. **Fabriquées automatiquement, ne jamais les corriger à la main.** |
| `assets/js/etape.js` | L'enchaînement des écrans d'une borne, et le tri selon le sens du groupe |
| `contenu/` | Le cahier de contenu, les outils qui fabriquent et vérifient. Voir `contenu/LISEZ-MOI.md` |
| `assets/css/style.css` | Le style visuel de tout le site |
| `assets/js/game.js` | La logique du jeu : activation, chrono, enregistrement des passages |
| `assets/js/supabase-client.js` | Le branchement à la base (adresse + clé publique) |
| `backoffice/dashboard.html` | Suivi en direct des groupes en jeu |
| `backoffice/statistiques.html` | Durées par étape, abandons, taux de complétion |
| `schema_escape_game.sql` | Description de la base telle qu'elle est réellement. **Contient les avertissements de sécurité.** |
| `seed.sql` | Le contenu de départ : les 12 bornes et les codes de test |
| `stats.sql` | Les calculs statistiques |
| `correctifs.sql` | Journal des corrections appliquées à la base. Rien en attente. |
| `verification_base.sql` | Outil de contrôle : vérifie que la base correspond bien aux fichiers |

## Modifier le site

Tout se fait depuis l'interface web de GitHub, sans rien installer. Après
enregistrement, comptez une à deux minutes avant que le changement soit visible
en ligne.

**Un piège à connaître :** le site est servi depuis un sous-dossier
(`/sanctuaire-des-brumes/`). Tout chemin qui commence par `/` casse le site.
Les chemins doivent toujours être relatifs (`../assets/...`).

**Tester en local** ne fonctionne pas bien : en ouvrant les fichiers par
double-clic, le navigateur bloque les échanges avec Supabase. Le plus fiable
reste de publier et de tester en ligne.

---

## Où on en est

**Fait :**
- Base Supabase installée, 12 bornes et 3 codes de test enregistrés
- Page d'accueil et activation d'un code, testées de bout en bout
- Chrono de 3h et enregistrement des passages de bornes
- Les 12 pages d'étape, enchaînées de la borne 1 à la borne 12. La mécanique
  fonctionne partout (chrono, enregistrement du passage, passage à la suite).
  **Les textes restent à écrire**, les emplacements sont marqués `A REMPLIR`
  dans chaque fichier.
- Tableaux de bord de suivi et de statistiques
- Site en ligne sur GitHub Pages

**Où en est le jeu au 18 septembre 2026**

Les 16 pages du parcours sont fabriquées et les deux sens tournent de bout en
bout, 15 étapes chacun, du commissaire Jean jusqu'à la serre. Chaque borne
enchaîne ses écrans un par un : accueil, média, texte ou épreuve, puis la
direction à prendre.

Une borne physique ne porte qu'un seul QR code, donc **une seule page sert les
deux sens** : elle lit le sens du groupe et n'affiche que ce qui le concerne.
Un groupe qui tomberait par hasard sur la borne de l'autre parcours est
prévenu au lieu de rester bloqué.

**À faire, dans l'ordre :**
1. Remplacer les vidéos et l'audio (9 médias vides, dépend du tournage)
**Ce qui n'est pas encore construit :**
- L'épreuve qui convertit les 4 lettres en chiffres (étape du botaniste).
- Le champ de conclusions jugé par une IA, et les trois fins (étape de la serre).
  Il ne peut pas fonctionner tant que les tables `quiz_responses` et
  `conclusions` n'ont aucune règle d'accès : les réponses seraient rejetées en
  silence.
- Le quiz animalier, à écrire pendant le tournage.
- Les photos qui montrent le chemin à prendre. Les emplacements sont prêts dans
  chaque écran d'orientation, en commentaire.

**Deux décisions en attente :**
- **Le déséquilibre des lettres.** En sens B, le joueur les ramasse dans
  l'ordre I, R, I, S : le mot est déjà écrit et il ne lui reste qu'à convertir.
  En sens A il ramasse R, I, S, I et doit d'abord reconstituer. Signalé trois
  fois, jamais tranché. À régler avant le tournage et la fabrication des décors.
- **Cinq lieux trop vagues** pour savoir où poser une affichette : « Forêt »,
  « Statues », « Accueil », « La serre », et surtout « au milieu » pour Greg
  version B, qui n'est pas un lieu.

## Sécurité : ce qu'il faut savoir

La clé du site est publique, visible par tout le monde dans le code source.
C'est normal pour ce type de projet. Ce sont uniquement les règles configurées
dans Supabase qui protègent la base.

Ces règles ont aujourd'hui **quatre défauts connus**, vérifiés directement sur
la base le 1er septembre 2026 :

1. **N'importe qui peut lire la liste complète des codes**, y compris ceux non
   encore vendus. C'est-à-dire jouer sans passer par la billetterie.
2. **Une seule requête peut griller tous les codes non utilisés d'un coup**, ce
   qui rendrait tous les tickets imprimés inutilisables du jour au lendemain.
   La même faiblesse permet à un joueur de s'accorder plus de 3 heures.
3. **N'importe qui peut inventer des passages de bornes**, ce qui fausserait les
   statistiques sans qu'on puisse faire le tri.
4. **Les tables du quiz et des conclusions sont totalement fermées**, y compris
   au site lui-même. L'étape finale ne pourra rien y enregistrer : les réponses
   des joueurs seront rejetées en silence.

Rien ne brûle aujourd'hui : la base ne contient que 3 codes de test, il n'y a
donc rien à voler ni à détruire. **Le point de bascule, c'est le jour où les
vrais codes seront générés.** Les quatre défauts se réparent ensemble, par le
même chantier : faire en sorte que le téléphone du joueur n'écrive plus jamais
directement dans la base.

Le détail technique complet est dans `schema_escape_game.sql`, section 3.

**À noter aussi :** le chrono n'est pas calculé côté serveur. C'est le
téléphone du joueur qui écrit lui-même son heure de fin. Le chantier de
sécurité ci-dessus corrige aussi ce point.

Enfin, le mot de passe du backoffice (`brumes2026`) est écrit en clair dans le
code des pages. Il cache le bouton, il ne protège pas les données.
