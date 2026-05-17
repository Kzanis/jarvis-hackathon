# Workflows n8n — Jarvis

Ce dossier contient les workflows n8n exportés en JSON, prêts à être importés dans n'importe quelle instance n8n.

## Liste des workflows

### `jarvis-command-bridge.json`

**Rôle :** pont sécurisé entre la PWA mobile et le backend Jarvis local (à la maison).

**Trigger :** webhook `POST /webhook/jarvis-command`

**Auth :** header `Authorization: Bearer <token>`

**Architecture :**

```
PWA mobile (HTTPS)
   │
   │ POST /webhook/jarvis-command
   │ Authorization: Bearer <token>
   │ X-Jarvis-User: denis
   │ {"text": "Jarvis, ferme le volet de la buanderie"}
   ▼
n8n Webhook
   ▼
Valider Token (JS) ── token invalide ──► Respond 401
   │
   │ token OK
   ▼
Respond 200 (mock pour l'instant — à remplacer par forward HTTP vers backend local via Cloudflare Tunnel)
```

## Import dans n8n

1. Ouvrir n8n
2. Workflows → bouton **+** → **Import from File**
3. Sélectionner `jarvis-command-bridge.json`
4. **AVANT D'ACTIVER** : remplacer dans le node "Valider Token" la constante `expectedToken` par votre propre token (32 octets aléatoires base64url, généré avec `openssl rand -base64 32` par exemple)
5. Sauvegarder
6. Activer le workflow

## Test après import

```bash
# Test sans token (doit retourner unauthorized)
curl -X POST https://<votre-n8n>/webhook/jarvis-command \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'

# Test avec token valide
curl -X POST https://<votre-n8n>/webhook/jarvis-command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer VOTRE_TOKEN_ICI" \
  -H "X-Jarvis-User: denis" \
  -d '{"text":"Jarvis, ferme le volet de la buanderie"}'
```

Réponse attendue (mode mock) :
```json
{
  "status": "ok",
  "user_id": "denis",
  "received": {"text": "Jarvis, ferme le volet de la buanderie"},
  "jarvis_says": "Bien Monsieur. Ce sera fait.",
  "note": "Mock — forward vers backend Jarvis local à ajouter quand Cloudflare Tunnel sera prêt.",
  "timestamp": "2026-05-14T..."
}
```

## Sécurité — Pourquoi Bearer Token et pas HMAC ?

L'implémentation initiale visait HMAC-SHA256 pour signer chaque requête, mais la version actuelle de n8n bloque `require('crypto')` dans les Code nodes (`Module 'crypto' is disallowed`).

Le Bearer Token sur HTTPS reste sûr :
- Transmission chiffrée TLS
- Token long (32 octets = 256 bits d'entropie)
- Rotation facile (changer le token dans le workflow + dans le `.env` client)

**Migration future HMAC :** quand n8n autorisera `crypto`, ou via le node natif `n8n-nodes-base.crypto`, on basculera sur HMAC pour la non-replay.

## Variables d'environnement côté n8n

Aucune nécessaire dans la version Bearer Token actuelle (le token est hardcodé dans le code, à modifier avant import).

Pour une production réelle :
- Stocker le token dans un secret manager côté n8n (credentials)
- Ou activer `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` puis utiliser `$env.JARVIS_TOKEN`
