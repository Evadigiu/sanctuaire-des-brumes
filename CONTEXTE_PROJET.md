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

| Personnage | Interprète | Fonction |
|---|---|---|
| Jerry | Acteur | Briefe le joueur au démarrage, pose le synopsis et les consignes |
| Isabelle | Cameo | La disparue, apparition muette et endormie à la toute fin |
| Collègue soigneuse | Un·e vrai·e membre du personnel du zoo (pas un acteur classique) | Premier témoin, raconte le départ d'Isabelle la veille |
| Vétérinaire | Acteur | Démystifie la piste des loups, guide vers l'indice empreinte |
| Greg (Grégoire) | Acteur | Agent technique, auteur involontaire du canular, témoignage évasif |
| Bill | Acteur | Collègue de Greg, spécialisé oiseaux (pas reptiles), fausse piste, donne un alibi |
| La passante | Acteur | Témoin extérieur, a entendu le cri strident |
| Sabri & Arez | Acteurs | Animent le quiz sonore, 3 vidéos du facile au difficile |
| Le Botaniste | Acteur | Découvre la scène finale, panique, déclenche la révélation |

## 5. Le parcours, sens A (12 bornes, confirmé)

1. Jardin des pivoines — Jerry (briefing) — consignes + synopsis
2. Bureau des soignants — Collègue soigneuse — Facetime, dernier échange avec Isabelle
3. Salle de séminaire — (vidéosurveillance) — Isabelle part tout droit au lieu d'aller aux loups
4. Enclos des loups — (observation) — Indice 1 : lettre R (chapeau de l'épouvantail)
5. La passante — Passante — témoignage du cri strident
6. Enclos des lynx — Sabri & Arez — quiz sonore, Indice 2 : lettre I
7. Le vétérinaire — Vétérinaire — démystifie la piste des loups, Indice 3 : S
8. Greg — Greg — témoignage évasif, renvoie vers Bill (fausse piste)
9. Bill — Bill — digresse sur les oiseaux, donne un alibi
10. Bureau de Greg — (observation) — découverte de l'épouvantail, Indice 4 : lettre I
11. Jardin des Iris — (énigme) — alphabet à valeur numérique, IRIS devient le code de la serre
12. La serre — Le Botaniste — panique, bascule vers l'étape de résolution finale

Les 4 indices (R, I, S, I) forment un anagramme d'IRIS, le nom du jardin où se trouve le code final (probablement volontaire).

**Sens B (antihoraire) : NON CONFIRMÉ.** Une hypothèse de structure a été discutée (inverser l'ordre au sein des paires géographiques : Bureau des soigneurs/Passante au sud, Greg/Vétérinaire à l'est) mais jamais validée sur le terrain. Ne pas construire le contenu du sens B sans repérage physique préalable du zoo (largeur des chemins, embranchements réels au départ).

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
├── schema_escape_game.sql   — tables : codes, qr_points, scans, quiz_responses, conclusions + vues live_dashboard, reconciliation_daily
├── seed.sql                 — peuple les 12 bornes + 3 codes de test (TEST01, TEST02, TEST03)
├── stats.sql                 — vues ajoutées : scan_durations, avg_duration_by_point, code_progress, abandon_points, completion_summary
├── assets/
│   ├── css/style.css        — thème visuel partagé
│   └── js/
│       ├── supabase-client.js  — config (URL + clé anon)
│       └── game.js             — logique : activateCode(), requireActiveSession(), logScan(), startCountdown()
├── etapes/
│   └── bureau-soignants.html — SEULE page d'étape construite à ce jour (modèle à dupliquer pour les 11 autres)
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

**RLS (Row Level Security) activé**, avec ces policies déjà en place :
```sql
create policy "Lecture publique des codes" on codes for select using (true);
create policy "Activation d'un code non utilise" on codes for update using (status = 'unused') with check (status = 'active');
create policy "Lecture publique des bornes" on qr_points for select using (true);
create policy "Enregistrement des scans" on scans for insert with check (true);
create policy "Lecture publique des scans" on scans for select using (true);
```

## 8. Règles métier importantes

- **Groupes** : 2 à 6 personnes par code (pas de solo autorisé, décision explicite).
- **Chrono** : jusqu'à 3h maximum, pas une durée fixe. Le code ne bloque qu'après 3h révolues.
- **Billetterie** : entièrement externe, via SeeTickets (système du zoo). La LP de prévente/vente est sur Wix (`pomelolab.fr` ou un nom dédié, pas encore tranché), qui redirige vers SeeTickets. **Pomelo n'a aucune visibilité directe sur les réservations SeeTickets** tant qu'un code n'a pas été activé sur le terrain — c'est une limite connue et acceptée, pas un bug.
- **Remise du code** : à l'accueil du zoo, après vérification du billet SeeTickets, sous forme de ticket physique imprimé avec QR code.
- **Flux visé** : 12 groupes toutes les 30 minutes (donc 24 groupes/heure), sens horaire et antihoraire simultanés. Ce chiffre double la capacité initialement calculée (12/heure) et **n'a pas été revalidé sur le terrain** pour les deux zones de convergence physique identifiées sur le tracé (corridor vers Greg, zone finale Bureau des soigneurs/Passante).
- **Prix** : billet combiné zoo + jeu, tarif jeu autour de 4-10€/personne (à confirmer selon la politique tarifaire du zoo). 1€ par participant est reversé à la conservation animale.
- **Sens de rotation** : attribué au moment de la génération du code (colonne `direction`), pas calculé dynamiquement à l'activation.

## 9. État d'avancement (ce qui marche, testé de bout en bout)

✅ Schéma Supabase posé et peuplé (12 bornes, 3 codes de test)
✅ RLS configuré et fonctionnel
✅ Page de départ (`index.html`) : consignes, saisie du code, activation réelle
✅ Une page d'étape modèle (`etapes/bureau-soignants.html`), testée avec succès (scan enregistré, chrono fonctionnel, redirection)
✅ Site en ligne sur GitHub Pages, chemins relatifs corrigés
✅ Dashboard de suivi en direct et page de statistiques, fonctionnels
✅ Palette de couleurs finalisée (voir section 10)

⬜ **11 pages d'étape restantes** à créer sur le modèle de `bureau-soignants.html` (Salle de séminaire, Enclos des loups, La passante, Enclos des lynx, Le vétérinaire, Greg, Bill, Bureau de Greg, Jardin des Iris, La serre) — prochaine tâche demandée
⬜ Étape finale (quiz noté + champ "vos conclusions" + appel à une IA qui juge la réponse + écran "photo finish" récapitulatif) — non commencée
⬜ Vraies vidéos (actuellement des balises `<video>` vides dans le modèle) — dépend du tournage
⬜ Génération en masse des vrais codes de production (environ 2000+, actuellement seulement 3 codes de test)
⬜ Sécurisation renforcée de l'activation des codes (voir section 10)
⬜ Vraie authentification pour le backoffice (voir section 10)
⬜ Application des nouvelles couleurs (section 10) au CSS existant, encore sur l'ancienne palette navy/or/rose

## 10. Points de sécurité connus, à corriger avant le lancement du 17 octobre

1. **L'activation d'un code se fait directement depuis le navigateur du joueur**, via une requête `update` sur la table `codes` protégée seulement par une policy RLS (`status = 'unused'`). C'est fonctionnel mais quelqu'un de curieux qui inspecte le code JS pourrait comprendre la mécanique et potentiellement l'exploiter. La correction prévue (pas encore faite) : déplacer cette logique dans une Supabase Edge Function, invisible et non modifiable côté client.
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

1. Dupliquer `etapes/bureau-soignants.html` pour créer les 11 pages restantes.
2. Appliquer la nouvelle palette de couleurs (section 11) à `assets/css/style.css`.
3. Construire l'étape finale (quiz + conclusions + verdict IA + écran de résolution).
4. Sécuriser l'activation des codes via une Edge Function.
5. Mettre une vraie authentification sur le backoffice.
6. Générer les vrais codes de production une fois le volume final confirmé.
7. Intégrer les vraies vidéos une fois tournées.
8. Repérage terrain pour confirmer (ou infirmer) le sens B et la capacité réelle de flux à 24 groupes/heure.
