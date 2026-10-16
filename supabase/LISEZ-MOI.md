# Le juge des conclusions par IA

À la fin de l'enquête, le groupe écrit ce qui est arrivé à Isabelle. La
fonction `juger-conclusions` demande à Claude (modèle **Claude Haiku 5.5**) de
choisir l'un des trois dénouements du cahier, et d'écrire un mot du
commissaire sur le raisonnement du groupe. Le texte du dénouement reste celui
du cahier.

**Le jeu fonctionne sans elle.** Tant que la fonction n'est pas déployée, ou si
elle tombe en panne, ou si l'IA met plus de 9 secondes à répondre, le jeu
applique son juge par mots-clés, sans que le joueur s'en aperçoive.

## Mise en service (environ 20 minutes)

### 1. La clé d'API Anthropic

1. Sur **console.anthropic.com**, créez un compte, ou connectez-vous.
2. Rubrique **Billing** : ajoutez quelques euros de crédit. L'événement
   entier coûte environ 1 € avec Claude Haiku 5.5.
3. Rubrique **Limits** : fixez un plafond de dépense mensuel, par exemple
   10 €. C'est le filet de sécurité.
4. Rubrique **API Keys** : créez une clé (« Create Key »), et copiez-la.
   **Ne la collez nulle part ailleurs que dans Supabase, étape 2** : ni dans
   le dépôt, ni dans un e-mail, ni dans une conversation.

### 2. La clé dans Supabase

Dans votre projet Supabase, ouvrez **Edge Functions**, puis **Secrets**.
Ajoutez un secret :

- nom : `ANTHROPIC_API_KEY`
- valeur : la clé copiée à l'étape 1

### 3. La fonction

1. Toujours dans **Edge Functions**, choisissez de déployer une nouvelle
   fonction **depuis l'éditeur** (« Via Editor »).
2. Nommez-la exactement **`juger-conclusions`**.
3. Effacez le code d'exemple, et collez tout le contenu du fichier
   `supabase/functions/juger-conclusions/index.ts`.
4. Déployez (« Deploy »).

Il n'y a rien à changer dans le site : il appelle déjà cette fonction, et il
s'en passe tant qu'elle n'existe pas.

### 4. L'essai

Jouez une fin de partie avec un code de test, à la borne de la serre. Si le
dénouement s'affiche avec, au-dessus, un mot entre guillemets signé « Le
commissaire Jean », l'IA fonctionne. Sans ce mot, c'est le juge par
mots-clés qui a répondu : regardez les journaux de la fonction (Edge
Functions, puis `juger-conclusions`, puis Logs).

## Relire les conclusions

Dans le SQL Editor de Supabase :

```sql
select created_at, ai_verdict, submitted_text, ai_reply_text
  from conclusions
 order by created_at desc
 limit 50;
```

`ai_reply_text` est vide quand c'est le juge par mots-clés qui a répondu.

## Les garde-fous

- La clé ne quitte jamais Supabase. Le site, public, ne la connaît pas.
- Un seul jugement par billet : recharger la page rend le même verdict, sans
  nouvel appel payant.
- Le billet doit avoir été activé, et le texte est limité à 1 000 signes.
- La réponse de l'IA est contrainte : l'un des trois dénouements, plus un
  commentaire. Un joueur qui écrit « ignore tes consignes » n'obtient rien de
  plus.
- Les conclusions des joueurs sont envoyées à Anthropic pour être jugées. Il
  faut le mentionner dans les mentions légales du jeu.

## Changer l'histoire ou le ton

La vérité de l'enquête, les règles des trois dénouements et le ton du
commissaire se trouvent en haut de `index.ts`, dans `CONSIGNES`. Après une
modification, collez de nouveau le fichier dans l'éditeur de Supabase, et
redéployez.
