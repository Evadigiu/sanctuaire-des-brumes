# Le Sanctuaire des Brumes — Contexte du projet

Document de passation à l'attention de Claude Code. Contient tout ce qui a été décidé jusqu'ici sur ce projet : concept, contenu, architecture technique, état d'avancement, et points encore ouverts. Dépôt GitHub : `Evadigiu/sanctuaire-des-brumes`.

---

## 1. Le projet en une phrase

Escape game / enquête immersive en plein air, au Zoo de Mulhouse, du 17 octobre au 2 novembre 2026 (vacances de la Toussaint), organisé par Pomelo Événementiel en partenariat avec le zoo. Cible principale 18-35 ans, mais ouvert à tous les publics (tout public, adressé prioritairement 15-35). Ton : humoristique et volontairement dark, ambiance Halloween élégante plutôt que kitsch.

## 2. Le concept, tel que raconté aux joueurs (synopsis)

Le joueur incarne un·e enquêteur·rice envoyé·e sur la disparition d'Isabelle, soigneuse animalière du zoo, la veille au soir près de l'enclos des loups. Le parcours se fait en autonomie via des bornes QR code disséminées dans le parc, chacune déclenchant une vidéo, un témoignage ou une épreuve. Durée de jeu : jusqu'à 3h maximum (pas une durée fixe, certains groupes bouclent en 1h, d'autres prennent tout leur temps ; le système bloque seulement après 3h).

## 3. La vérité (spoiler, réservé à l'équipe, utile pour la cohérence narrative)

Grégoire (Greg), l'agent technique, a voulu faire une farce d'Halloween à Isabelle : épouvantail dans l'enclos des loups, appel au talkie-walkie avec une voix d'outre-tombe pour l'attirer, planque pour la filmer. Après 15 minutes sans qu'elle arrive, il abandonne et repart en laissant l'épouvantail. En réalité, Isabelle s'est sentie mal en chemin, s'est arrêtée aux toilettes et s'est endormie profondément (le botaniste s'était trompé de plante pour sa tisane du soir, lui servant un puissant somnifère au lieu de la mélisse habituelle) ; elle ne se réveille que le lendemain midi. Le cri strident entendu par la passante est un renard, pas un loup : les loups, effrayés par l'épouvantail, se sont repliés au fond de l'enclos, laissant le renard traverser librement le parc. Le matin venu, Grégoire retire discrètement l'épouvantail avant l'ouverture.

## 4. Les personnages

Noms fixés dans le cahier de contenu du 18/09/2026. **Jerry n'existe plus**, il est remplacé par le commissaire Jean, qui intervient deux fois : au briefing, puis par un appel téléphonique en cours de partie.

| Personnage | Rôle dans l'enquête |
|---|---|
| **Commissaire Jean** | Briefe le joueur au départ, puis le rappelle en cours de route |
| **Isabelle** | La disparue, apparition muette à la toute fin |
| **Mathilde** | Collègue soigneuse, premier témoin en sens A |
| **Sophie** | Cheffe de la sécurité, montre les caméras de surveillance |
| **Marina** | La passante, a entendu le cri |
| **Sabri & Arez** | Animent le quiz animalier |
| **Sandra** | Vétérinaire |
| **Greg** | Agent technique, auteur involontaire du canular. **Seul personnage dédoublé** : une version pour chaque sens |
| **Bill** | Collègue de Greg, spécialiste oiseaux, fausse piste et alibi |
| **Le botaniste** | Découvre la scène finale. **Nom encore à choisir.** |

## 5. Le parcours (cahier de contenu du 18/09/2026)

17 étapes. Les deux sens partagent le départ (commissaire Jean) et la fin (le botaniste, puis la serre), et permutent deux blocs au milieu.

| Code | Étape | Lieu | Lettre | Sens A | Sens B |
|---|---|---|---|---|---|
| E00 | Départ de l'enquête | Accueil (ticket papier, pas de QR) | | 0 | 0 |
| E01 | Le commissaire Jean | Jardin des pivoines | | 1 | 1 |
| E02 | Mathilde, collègue soigneuse | Bureau des soignants | | 2 | 8 |
| E03 | Sophie, les caméras de surveillance | Salle de séminaire | | 3 | 7 |
| E04 | Les jumelles, la carcasse | Enclos des loups | **R** | 4 | 9 |
| E05 | Marina, la passante | Au-dessus de l'enclos des loups | | 5 | 10 |
| E06 | Quiz animalier, Sabri & Arez | Panthère de l'Amour | **I** | 6 | 11 |
| E07 | Sandra, vétérinaire | Forêt | | 7 | 12 |
| E08 | Le panneau d'empreintes | Après le vétérinaire | **S** | 8 | 13 |
| E09 | Greg, version sens A | Sentier des plantes sauvages | | 9 | — |
| E16 | Greg, version sens B | *lieu à préciser* | | — | 2 |
| E10 | Bill | Grande volière | | 10 | 3 |
| E11 | Le sac du botaniste | Jardin des tulipes | | 11 | 4 |
| E12 | L'appel du commissaire | Statues | | 12 | 5 |
| E13 | Le bureau de Greg | Zone de pique-nique | **I** | 13 | 6 |
| E14 | Le botaniste | Jardin des Iris | | 14 | 14 |
| E15 | La serre, résolution finale | La serre | | 15 | 15 |

### Les mécaniques demandées, pas encore construites

- **Écran de départ** : saisie du nom d'enquêteur **et du nombre de personnes** (donnée neuve, utile pour recouper avec la billetterie).
- **E08, panneau d'empreintes** : champ de saisie libre, la bonne réponse est `11`, et elle seule débloque la lettre S.
- **E12, appel du commissaire** : une sonnerie, puis un bouton « décrocher » qui lance l'audio.
- **E14** : convertir les 4 lettres en chiffres pour obtenir le code de la serre.
- **E15** : champ libre de conclusions jugé par une IA, une vidéo de résolution, puis trois fins possibles (parfait, presque, dommage). Correspond aux valeurs `proche` / `partiel` / `eloigne` déjà prévues en base.
- **E06, quiz animalier** : contenu à écrire pendant le tournage.

### ⚠️ Le déséquilibre des lettres n'est toujours pas tranché

- **Sens A** : R, I, S, I. Le joueur doit reconstituer le mot avant de le convertir en chiffres.
- **Sens B** : I, R, I, S. **Le mot est déjà écrit dans l'ordre.** L'étape de reconstitution disparaît.

Signalé le 5 septembre, toujours ouvert. Se corrige en permutant deux lettres entre les bornes, décision à prendre avant le tournage et la fabrication des décors.

## 6. Architecture technique

**Principe général :** site statique (vitrine) + Supabase (arrière-boutique/mémoire). Le site ne peut rien retenir seul ; toute donnée qui doit survivre (codes, chrono, scans, réponses) passe par Supabase.

**Hébergement du site :** GitHub Pages, dépôt `Evadigiu/sanctuaire-des-brumes`, branche `main`, à la racine. URL de prod : `https://evadigiu.github.io/sanctuaire-des-brumes/`.

**Piège déjà rencontré et corrigé :** GitHub Pages sert ce site depuis un sous-dossier (`/sanctuaire-des-brumes/`), pas depuis la racine du domaine. Tout chemin absolu commençant par `/` (`/assets/...`, `/index.html`) casse. Tous les chemins doivent être relatifs. Dans `game.js`, une constante `BASE_PATH` calcule dynamiquement `"../"` ou `""` selon que le script tourne depuis `/etapes/` ou depuis la racine, pour que les redirections marchent des deux côtés.

**Base de données :** Supabase (projet "Le sanctuaire des brumes", org "Pomelo"). URL et clé anon déjà configurées dans `assets/js/supabase-client.js`.

**Structure actuelle du dépôt :**
```
sanctuaire-des-brumes/
├── index.html              — page de départ, activation du code
├── README.md                — guide de mise en route (Supabase + GitHub Pages)
├── schema_escape_game.sql   — description fidèle de la base réelle, policies RLS incluses, + avertissements de sécurité
├── seed.sql                 — peuple les 12 bornes + 3 codes de test (TEST01, TEST02, TEST03)
├── stats.sql                 — vues ajoutées : scan_durations, avg_duration_by_point, code_progress, abandon_points, completion_summary
├── correctifs.sql           — journal des corrections appliquées à la base (rien en attente)
├── verification_base.sql    — outil de contrôle : compare la base réelle à ce que disent ces fichiers
├── assets/
│   ├── css/style.css        — thème visuel partagé
│   └── js/
│       ├── supabase-client.js  — config (URL + clé anon)
│       └── game.js             — logique : activateCode(), requireActiveSession(), logScan(), startCountdown()
├── etapes/
│   ├── jardin-des-pivoines.html — étape 1, briefing de Jerry (texte provisoire, à valider)
│   └── bureau-soignants.html    — étape 2, modèle de référence à dupliquer pour les 10 autres
└── backoffice/
    ├── dashboard.html        — suivi en direct des groupes actifs (protégé par mot de passe FAIBLE, voir section 9)
    └── statistiques.html     — durées par étape, taux d'abandon, taux de complétion
```

## 7. Schéma de base de données

**Table `codes`** : id, code (unique), max_participants (int, contrainte **entre 2 et 6**, PAS 1-5, un bug corrigé en cours de route), direction ('horaire'/'antihoraire'), slot_time, status ('unused'/'active'/'expired'), activated_at, expires_at (= activated_at + **3h**, pas 2h).

**Table `qr_points`** : id, label, type ('temoin'/'side_quest'/'final'). 12 lignes correspondant au parcours sens A.

**Table `scans`** : id, code_id, qr_point_id, scanned_at. Journal de chaque passage de borne, jamais purgé (c'est l'historique).

**Table `quiz_responses`** et **`conclusions`** : prévues pour l'étape finale uniquement (quiz + texte libre + verdict IA), **pas encore implémentées côté frontend**.

**Vues** : `live_dashboard` (groupes actifs en ce moment), `reconciliation_daily` (codes activés par jour, pour vérifier la cohérence avec les ventes SeeTickets), `scan_durations`, `avg_duration_by_point`, `code_progress`, `abandon_points`, `completion_summary` (statistiques historiques).

**RLS (Row Level Security) activé** sur les 5 tables. Vérifié directement sur la base le 01/09/2026 : il y a **quatre** policies, et non cinq. Celle qui était listée ici pour la lecture des scans n'existe pas.

```sql
create policy "Lecture publique des bornes" on qr_points for select to public using (true);
create policy "Lecture publique des codes" on codes for select to public using (true);
create policy "Activation d'un code non utilise" on codes for update to public
  using (status = 'unused') with check (status = 'active');
create policy "Enregistrement des scans" on scans for insert to public with check (true);
```

Ce qui n'existe pas, et qu'il faut savoir :
- **Aucune policy sur `quiz_responses` ni `conclusions`.** Ces deux tables sont donc entièrement fermées, y compris au site. L'étape finale ne pourra rien y écrire, et les insertions échoueront **en silence**. À régler avant de la construire.
- **Aucune policy de lecture sur `scans`.** Les tableaux de bord fonctionnent quand même parce qu'une vue Postgres interroge les tables avec les droits de son propriétaire, pas ceux du visiteur. Conséquence : ces vues sont lisibles par n'importe qui, et elles tomberaient en panne si `security_invoker` était activé dessus un jour.
- **Aucune policy de suppression.** Personne ne peut effacer de données depuis le site. C'est volontaire, ne pas en ajouter.

La vérification est rejouable à tout moment : coller `verification_base.sql` dans le SQL Editor de Supabase.

### ⚠️ Supabase, changement du 30 octobre 2026

À partir du 30 octobre, Supabase n'accorde plus automatiquement l'accès API aux **nouvelles** tables du schéma `public`. Les tables du jeu sont antérieures et gardent leurs droits : **le jeu n'est pas affecté**.

Deux conséquences, et la date tombe en plein pendant l'événement :

- **Ne créer aucune table entre le 17 octobre et le 2 novembre.** Rien ne l'exige de toute façon : l'étape finale utilise `quiz_responses` et `conclusions`, qui existent déjà.
- **Toute nouvelle table ou vue doit être accompagnée de son `grant`**, dans la même requête. Le correctif 4 le fait désormais pour la table des signalements, de sorte qu'il fonctionne qu'il soit lancé avant ou après la date.

Sans ce `grant`, la table est bien créée mais reste muette : le site reçoit un refus, et rien dans le code ne laisse deviner pourquoi.

## 8. Règles métier importantes

- **Groupes** : **1 à 6 personnes** par code. Le jeu en solo est autorisé depuis le 20/09/2026, ce qui revient sur la décision précédente qui l'interdisait.
  *Effet de bord à surveiller* : la capacité du parcours se compte en **groupes**, pas en personnes (12 groupes toutes les 30 minutes). Beaucoup de joueurs solo, c'est autant de groupes en plus sur le tracé pour le même nombre de visiteurs, donc un parcours plus chargé à recette égale.
- **Chrono** : jusqu'à 3h maximum, pas une durée fixe. Le code ne bloque qu'après 3h révolues.
- **Billetterie** : entièrement externe, via SeeTickets (système du zoo). La LP de prévente/vente est sur Wix (`pomelolab.fr` ou un nom dédié, pas encore tranché), qui redirige vers SeeTickets. **Pomelo n'a aucune visibilité directe sur les réservations SeeTickets** tant qu'un code n'a pas été activé sur le terrain — c'est une limite connue et acceptée, pas un bug.
- **Remise du code** : à l'accueil du zoo, après vérification du billet SeeTickets, sous forme de ticket physique imprimé avec QR code.
- **Flux visé** : 12 groupes toutes les 30 minutes (donc 24 groupes/heure), sens horaire et antihoraire simultanés. Ce chiffre double la capacité initialement calculée (12/heure) et **n'a pas été revalidé sur le terrain** pour les deux zones de convergence physique identifiées sur le tracé (corridor vers Greg, zone finale Bureau des soigneurs/Passante).
- **Prix** : billet combiné zoo + jeu, tarif jeu autour de 4-10€/personne (à confirmer selon la politique tarifaire du zoo). 1€ par participant est reversé à la conservation animale.
- **Sens de rotation** : attribué au moment de la génération du code (colonne `direction`), pas calculé dynamiquement à l'activation.

## 9. État d'avancement (ce qui marche, testé de bout en bout)

✅ Schéma Supabase posé et peuplé (12 bornes, 3 codes de test)
⚠️ RLS activé sur les 5 tables, mais **4 défauts confirmés** (voir section 10), et 2 tables sans aucune policy
✅ Page de départ (`index.html`) : consignes, saisie du code, activation réelle
✅ **Les 12 pages d'étape existent et s'enchaînent**, de la borne 1 à la borne 12. Mécanique fonctionnelle partout : chrono, enregistrement du passage, lien vers la suite. Seule `bureau-soignants.html` (étape 2) a été testée en conditions réelles. Les textes sont vides, sauf l'étape 1 dont le texte est provisoire.
✅ Site en ligne sur GitHub Pages, chemins relatifs corrigés
✅ Dashboard de suivi en direct et page de statistiques, fonctionnels
✅ Palette de couleurs finalisée (voir section 10)

⬜ **Les textes des 12 étapes** — la structure est posée, les emplacements sont marqués `A REMPLIR` dans chaque fichier. Décision préalable nécessaire sur les indices et sur le code IRIS (voir section 12).
⬜ Étape finale (quiz noté + champ "vos conclusions" + appel à une IA qui juge la réponse + écran "photo finish" récapitulatif) — non commencée
⬜ Vraies vidéos (actuellement des balises `<video>` vides dans le modèle) — dépend du tournage
⬜ Génération en masse des vrais codes de production (environ 2000+, actuellement seulement 3 codes de test)
⬜ Sécurisation renforcée de l'activation des codes (voir section 10)
⬜ Vraie authentification pour le backoffice (voir section 10)
⬜ Application des nouvelles couleurs (section 10) au CSS existant, encore sur l'ancienne palette navy/or/rose

## 10. Points de sécurité connus, à corriger avant le lancement du 17 octobre

*Section corrigée le 01/09/2026 après vérification directe sur la base. Les deux premiers points étaient sous-estimés, les deux derniers n'avaient pas été identifiés.*

1. **N'importe qui peut lire la liste complète des codes.** La policy `Lecture publique des codes` autorise le `select` sans aucune condition. Avec la clé anon, qui est publique par construction, il suffit d'une requête pour récupérer les ~2000 codes de production, dont ceux non encore vendus. Il n'y a rien à « exploiter » : c'est l'usage prévu de l'API. C'est le trou au coût économique le plus direct, puisqu'il court-circuite la billetterie.

2. **Une seule requête peut griller tous les codes non utilisés.** Le `with check` de la policy d'activation ne contraint que la colonne `status`. Il ne limite ni le nombre de lignes touchées, ni le contenu des autres colonnes. Donc `update codes set status='active', expires_at=now() where status='unused'` passe les deux conditions et rend **tous les tickets imprimés inutilisables**. La même faiblesse permet au joueur d'écrire son propre `expires_at` : le chrono de 3h n'est pas contraignable tant que le client écrit cette colonne.

3. **N'importe qui peut inventer des passages de bornes.** La policy d'insertion sur `scans` accepte tout sans vérification. Les statistiques sur lesquelles repose l'ajustement du parcours sont donc falsifiables, sans possibilité de faire le tri après coup.

4. **L'étape finale ne pourra rien enregistrer.** `quiz_responses` et `conclusions` sont protégées mais n'ont aucune policy. Les réponses des joueurs seront rejetées sans message d'erreur.

**Rien de tout cela n'est urgent aujourd'hui** : la base contient 3 codes de test. Le point de bascule n'est pas une date, c'est la génération des vrais codes (étape 6 de la section 12). La réparation doit être terminée avant.

**Correction retenue : une fonction `security definer` appelée en RPC, pas une Edge Function.** Le principe est le même (le joueur soumet son code, la base vérifie et écrit elle-même, le client ne touche plus jamais aux tables) mais elle se pose en collant du SQL dans le SQL Editor, sans outillage Deno ni CLI à installer. On supprime alors les deux policies sur `codes`, ce qui referme les points 1 et 2 d'un coup, et le chrono devient réellement calculé côté serveur.
2. **Le backoffice (`dashboard.html`, `statistiques.html`) est protégé par un mot de passe codé en dur dans le HTML** (`brumes2026`), visible par quiconque regarde le code source. Ce n'est qu'un frein visuel, pas une vraie sécurité — les données sous-jacentes restent lisibles via la clé anon publique de toute façon (RLS ouvert en lecture sur codes/scans/qr_points). À remplacer par une vraie authentification (Supabase Auth) avant le lancement.

## 11. Palette de couleurs (nouvelle version, validée, à appliquer au CSS existant)

Dérivée par extraction des couleurs réelles du visuel clé et du logo (pas une palette générique). Explicitement choisie pour éviter toute connotation "outil IA" (pas de rose/violet saturé, contrairement à la première version du CSS actuel qui utilisait un rose `#EE3F81`).

| Rôle | Couleur |
|---|---|
| Fond | `#141A1F` |
| Panneaux/cartes | `#232B33` |
| Texte principal | `#E4D3BC` |
| Accent titre | `#B4855C` |
| Accent secondaire (hover/actif) | `#C9A96E` |
| Vert nature | `#7C9A57` |
| Alerte/erreur | `#A85A3E` |

Typographie choisie séparément : **Cinzel** pour les titres, **Times New Roman gras** pour le corps de texte (à noter : le CSS actuel de `style.css` utilise encore `Georgia, 'Times New Roman', serif` pour le corps, pas Times New Roman seul en gras — à harmoniser).

## 12. Prochaines étapes, dans l'ordre suggéré

1. Écrire les textes des 12 étapes (chercher `A REMPLIR` dans les fichiers de `etapes/`).

   **Trois décisions préalables, elles conditionnent la structure des pages :**
   - *Les 4 indices (R, I, S, I) s'affichent-ils à l'écran, ou le joueur les trouve-t-il dans le décor ?* La section 5 dit qu'ils sont physiques (chapeau de l'épouvantail, etc.). Un encadré `.indice` est prévu sur les 4 bornes concernées, à supprimer s'il fait doublon avec le décor.
   - *Le code IRIS se tape-t-il sur le site, ou sur un cadenas physique à la serre ?* Aucune saisie n'a été construite dans le doute. Si elle doit exister, c'est une mécanique à ajouter.
   - *Que se passe-t-il après la borne 12 ?* Le bouton de `la-serre.html` est inactif tant que l'étape finale n'est pas construite.
2. Appliquer la nouvelle palette de couleurs (section 11) à `assets/css/style.css`.
   *Point ouvert : la palette validée ne définit aucune couleur de texte secondaire, or `.muted` est utilisé partout dans le site. Il en faut une, sinon du gris bleuté de l'ancienne palette subsistera.*
3. **Sécuriser la base** (fonction `security definer`, voir section 10). Referme les 4 défauts d'un coup, dont celui qui bloque l'étape finale. **Doit être terminé avant l'étape 5.**
4. Construire l'étape finale (quiz + conclusions + verdict IA + écran de résolution).
5. Générer les vrais codes de production une fois le volume final confirmé.
6. Mettre une vraie authentification sur le backoffice.
7. Intégrer les vraies vidéos une fois tournées.
8. Repérage terrain pour confirmer (ou infirmer) le sens B et la capacité réelle de flux à 24 groupes/heure.

**Dettes techniques mineures, notées pour ne pas les oublier :**
- Le site retrouve chaque borne par son **libellé écrit en toutes lettres** (`logScan()` dans `game.js`). Une faute de frappe ou d'accent dans une page et le passage n'est pas enregistré, sans aucun message d'erreur. Sur 10 pages à écrire, ça arrivera. Les libellés de référence sont dans `seed.sql`, à copier-coller.
- Un joueur qui recharge une page crée un **passage en double**, ce qui fausse les durées avec des valeurs à zéro.
- La colonne `type` de `qr_points` n'est utilisée nulle part, et « Jardin des pivoines » y est classé `final` alors que c'est le départ. Sans conséquence tant que personne ne s'en sert.
- Le champ « nom d'enquêteur » de l'accueil est saisi mais **jamais envoyé en base**. Volontaire pour l'écran final, ou oubli ?
