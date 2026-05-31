# Workflows n8n — Jarvis

Ce dossier contient les workflows n8n du projet, exportés en JSON et **nettoyés de tout secret** (l'adresse réelle du backend est remplacée par un placeholder). Ils sont prêts à être importés dans n'importe quelle instance n8n.

> 🔒 **Aucun mot de passe ni token n'est stocké dans ces workflows.** L'authentification réelle est gérée par le backend `jarvis-core` (login + jeton de session). n8n ne fait que **transmettre** le jeton fourni par la PWA.

## Rôle des deux workflows

Jarvis n'utilise n8n que comme **pont sécurisé** entre la PWA mobile (publique, sur Hostinger) et le backend `jarvis-core` (privé, sur la VM Freebox à la maison). Toute la logique métier et tous les garde-fous sont dans le backend, pas dans n8n.

### 1. `jarvis-login.json` — la connexion

**Trigger :** webhook `POST /webhook/jarvis-login`

```
PWA  ──{username, password}──►  n8n  ──►  backend /auth/login  ──►  {jeton de session}
```

La PWA envoie les identifiants, n8n les transmet au backend, le backend renvoie un jeton de session valable 4 h. n8n ne stocke rien.

### 2. `jarvis-command-bridge.json` — les commandes vocales

**Trigger :** webhook `POST /webhook/jarvis-command`
**Auth :** header `Authorization: Bearer <jeton de session>`

```
PWA ──{text, Bearer jeton}──► n8n ──► [Valider Token] ──► [Si autorisé ?]
                                                             │
                                       non ──► Respond 401/400
                                       oui ──► backend /intent/text (avec le Bearer) ──► Respond 200
```

Le nœud **Valider Token** vérifie seulement qu'un `Authorization: Bearer` et un champ `text` sont présents — la **validité** du jeton, elle, est vérifiée côté backend (source de vérité unique). Si tout est bon, la commande est transmise au backend, qui l'exécute via l'orchestrateur et les sous-agents (TaHoma, Freebox, etc.).

## ⚙️ Avant d'importer : remplacer le placeholder

Les deux workflows pointent vers `http://VOTRE_BACKEND_JARVIS:PORT`. Remplacez cette valeur par l'adresse de **votre** backend `jarvis-core` (dans les nœuds *Forward Login Freebox* et *Appel Jarvis Freebox*).

## Import dans n8n

1. Ouvrir n8n → **Workflows** → **+** → **Import from File**
2. Sélectionner `jarvis-login.json` (puis recommencer pour `jarvis-command-bridge.json`)
3. Dans chaque nœud HTTP, remplacer `http://VOTRE_BACKEND_JARVIS:PORT` par votre adresse réelle
4. Sauvegarder, puis activer

## Sécurité — pourquoi Bearer Token et pas HMAC ?

L'implémentation initiale visait HMAC-SHA256, mais la version de n8n bloque `require('crypto')` dans les nœuds Code (`Module 'crypto' is disallowed`). Le Bearer Token sur HTTPS reste sûr (TLS + jeton long + rotation facile). Migration HMAC prévue quand n8n autorisera `crypto`, ou via le nœud natif `n8n-nodes-base.crypto`.

> Voir [`../MAKING_OF.md`](../MAKING_OF.md) §3.5 pour le détail de ce choix.
