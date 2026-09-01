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
| `etapes/` | Une page par borne du parcours. **2 créées sur 12.** |
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
- 2 pages d'étape sur 12 : Jardin des pivoines (Jerry) et Bureau des soignants
- Tableaux de bord de suivi et de statistiques
- Site en ligne sur GitHub Pages

**À faire, dans l'ordre :**
1. Les 10 pages d'étape restantes, sur le modèle de `bureau-soignants.html`
2. Appliquer la nouvelle palette de couleurs (voir `CONTEXTE_PROJET.md`, section 11)
3. **Refermer les trous de sécurité** (voir plus bas). Impérativement avant l'étape 5.
4. Construire l'étape finale : quiz, conclusions, verdict IA
5. Générer les vrais codes de production
6. Intégrer les vraies vidéos une fois tournées
7. Repérage terrain : confirmer le sens B et la capacité réelle de flux

---

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
