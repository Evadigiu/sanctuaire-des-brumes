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

Ces règles avaient **quatre défauts connus**. Trois sont réparés depuis le
25 septembre 2026 par `correctif-6-guichet-des-codes.sql` :

1. ~~N'importe qui pouvait lire la liste complète des codes~~ → la table est
   fermée. L'activation passe par un guichet (`activer_code`) : le site soumet
   un code, la base vérifie et ouvre elle-même la partie.
2. ~~Une seule requête pouvait griller tous les codes d'un coup~~ → plus aucune
   écriture directe n'est possible. Le chrono de 3 h est désormais calculé par
   la base, plus par le téléphone du joueur.
3. ~~N'importe qui pouvait inventer des passages de bornes~~ → même guichet
   (`enregistrer_passage`), qui vérifie que la partie est bien ouverte.
4. **Les tables du quiz et des conclusions sont toujours fermées**, y compris au
   site lui-même. L'étape finale ne pourra rien y enregistrer : les réponses des
   joueurs seront rejetées en silence. À régler en construisant l'étape finale,
   par un guichet et non par une règle ouverte.

Deux points restent ouverts, à traiter avant l'ouverture au public :

- **Le backoffice n'est pas protégé.** Voir ci-dessous.
- **Le format des vrais codes.** Un code numéroté (SDB-001, SDB-002…) se devine
  en trois secondes et annule tout ce qui précède.
  `correctif-7-fabriquer-les-vrais-codes.sql` fabrique des codes de 8 signes
  tirés au hasard, sans caractères qui se confondent à la lecture.

Le détail technique complet est dans `schema_escape_game.sql`, section 3.

Enfin, le mot de passe du backoffice (`brumes2026`) est écrit en clair dans le
code des pages. Il cache le bouton, il ne protège pas les données.
