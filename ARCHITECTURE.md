# Architecture détaillée — Jarvis

> Document technique destiné aux développeurs et au jury Creator Academy.

## 1. Vue d'ensemble

Jarvis est un système distribué à **3 couches indépendantes** qui communiquent via des contrats stricts (HTTPS + auth Bearer).

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COUCHE 1 — CLOUD PUBLIC                          │
│                          (Hostinger VPS)                             │
│                                                                      │
│   PWA mobile ◄──► Site vitrine ◄──► Dashboard ◄──► n8n workflow     │
│   (Next.js)      (Next.js)         (Next.js)      (Webhook + auth)  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                            Cloudflare Tunnel
                            (HTTPS sortant depuis maison)
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                  COUCHE 2 — BACKEND LOCAL                            │
│                       (PC Denis, à la maison)                        │
│                                                                      │
│   FastAPI Python (jarvis-core)                                       │
│   ├─ Orchestrator       (pipeline d'une commande)                    │
│   ├─ Policy Engine      (3 niveaux, élévation contextuelle)          │
│   ├─ Intent Engine      (fuzzy matching local)                       │
│   ├─ Voice (Whisper STT + Edge-TTS)                                  │
│   ├─ Handlers           (TaHoma, Freebox)                            │
│   ├─ Mocks              (substituts pour tests + jury)               │
│   └─ Audit Store        (SQLite signé HMAC)                          │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ LAN privé 192.168.1.x
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│              COUCHE 3 — DEVICES PHYSIQUES                            │
│                                                                      │
│   TaHoma Switch    Freebox Delta    (futur : caméra ALPR)            │
│   (Local API)      (audio Devialet)                                  │
│   192.168.1.69     192.168.1.254                                     │
│   17 devices       Player + Server                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Principe directeur :** *edge computing*. Le code qui parle aux devices physiques DOIT être sur le LAN — un VPS cloud ne peut pas atteindre `192.168.1.69`.

---

## 2. Flux d'une commande vocale (mode production)

```
1. Denis sort son téléphone, ouvre la PWA Jarvis (icône d'app installée)
2. Tape le bouton micro → avatar HUD passe en "listening"
3. Dit : "Jarvis, ferme le rideau de la buanderie"
   │
   ▼ enregistrement audio
4. PWA envoie l'audio HTTPS au site Hostinger
   │  (signé Bearer Token + identifiant utilisateur)
   ▼
5. Site Hostinger forward au workflow n8n
   │
   ▼ webhook /jarvis-command
6. n8n valide le token + l'identité
   │  (sinon → 401, log audit côté cloud)
   ▼
7. n8n forward (via Cloudflare Tunnel) au backend Python local
   │  POST https://jarvis-tunnel.../intent
   ▼
8. Backend Python local :
   a. Whisper transcrit l'audio → "Jarvis, ferme le rideau de la buanderie"
   b. Intent Engine local matche "rideau" → device `volet_buanderie`, action `close`
   c. Policy Engine évalue :
      - heure = 14h → safe
      - device = volet → safe
      - confidence Whisper = 0.95 → safe
      - décision : ALLOW exécution directe (volet = safe, pas portail)
   d. Audit log : event "command_requested" + "policy_evaluated"
9. Réponse vocale immédiate (pattern "speak first") :
   - Jarvis génère : "Bien Monsieur. Ce sera fait."
   - Edge-TTS synthétise → MP3
   - Retour HTTP à n8n → PWA → haut-parleur téléphone Denis
10. EN PARALLÈLE : exécution physique
    - TahomaHandler.execute(volet_buanderie, close)
    - HTTP POST vers https://192.168.1.69:8443/...
    - TaHoma déclenche le moteur du volet (mouvement ~15s)
11. Audit log : event "command_dispatched" puis "command_succeeded"
12. Dashboard temps réel met à jour la liste des actions

Total latence ressentie côté Denis : ~600ms (Whisper + Claude + TTS)
Latence pipeline software : <300ms grâce au "speak first"
Latence physique du volet : 10-15s (mécanique Somfy, incompressible)
```

---

## 3. Couches logicielles `jarvis-core` (backend Python)

> **⚠️ Mise à jour 17 mai 2026 — pivot orchestrateur multi-agents (PRD §15).**
> L'architecture hexagonale ci-dessous reste **le socle**. Une nouvelle couche orchestrateur LLM s'ajoute **au-dessus** sans remplacer l'existant. Voir §3.bis pour le pivot.

Architecture inspirée du **Hexagonal / Ports & Adapters**.

```
┌─────────────────────────────────────────────────────────────┐
│  domain/                                                     │
│  Types métier purs, aucune dépendance externe                │
│  ├─ types.py        : Intent, DeviceCommand, ExecutionResult │
│  │                    PolicyDecision, AuditEvent...          │
│  └─ protocols.py    : DeviceHandler, AuditStore, ContextStore│
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ utilisé par tous les autres modules
                       │
       ┌───────────────┼───────────────┬────────────┐
       ▼               ▼               ▼            ▼
   ┌────────┐    ┌─────────┐    ┌──────────┐   ┌────────┐
   │ policy │    │  core   │    │ handlers │   │ mocks  │
   │        │    │         │    │          │   │        │
   │ engine │    │ orches- │    │ tahoma   │   │ tahoma │
   │ rules  │    │ trator  │    │ freebox  │   │ ...    │
   │        │    │ voice   │    │ ...      │   │        │
   │        │    │ intent  │    │          │   │        │
   └────────┘    └─────────┘    └──────────┘   └────────┘
                                       ▲
                                       │ Protocol DeviceHandler
                                       │ (handler réel et mock interchangeables)
                                       │
                       ┌───────────────┴────────────┐
                       │                            │
                  production                    mock/test
                  (Denis chez lui)               (jury, CI)
```

**Bénéfice clé :** le **mock** et le **handler réel** implémentent le même Protocol. L'orchestrator ne sait pas (et ne doit pas savoir) lequel il utilise. C'est ça qui permet au jury d'exécuter le code sans matériel.

---

## 3.bis Couche orchestrateur multi-agents (pivot 17 mai 2026)

### 3.bis.1 Position dans l'architecture

```
┌────────────────────────────────────────────────────────────────┐
│  COUCHE ORCHESTRATEUR LLM  (nouvelle, additive)                │
│  ────────────────────────────────                              │
│  orchestrator/                                                 │
│  ├─ llm_client.py    : Claude Haiku 4.5 + prompt majordome     │
│  ├─ registry.py      : registre allowlisté des sous-agents     │
│  └─ tool_router.py   : tool_call LLM → DeviceCommand typée     │
│                                                                │
│  subagents/                                                    │
│  ├─ base.py          : Protocol SubAgent + Pydantic strict     │
│  ├─ tahoma_agent.py  : 10 tools (volets, portail, garage…)     │
│  ├─ devialet_agent.py: 5 tools (volume, source, zone…)         │
│  └─ agenda_agent.py  : 5 tools (events, slots, create…)        │
└──────────────────────────┬─────────────────────────────────────┘
                           │ DeviceCommand validée
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  COUCHE EXISTANTE  (inchangée, source de vérité)               │
│  ────────────────────────────────                              │
│  core/orchestrator.py → policy/ → handlers/ ou mocks/ → audit/ │
└────────────────────────────────────────────────────────────────┘
```

**Principe directeur :** la couche orchestrateur LLM **propose** des `DeviceCommand`. Le Policy Engine + l'Audit HMAC restent en frontière dure entre la proposition et l'exécution. Le LLM ne peut PAS bypasser la sécurité.

### 3.bis.2 Pipeline complet d'une commande (post-pivot)

```
1. Audio PWA → Whisper STT → texte
2. core/orchestrator.py :
   ├─ FAST-PATH : intent_engine_local.match(text, threshold=0.85)
   │   └─ Match → DeviceCommand directe → goto étape 4
   └─ SLOW-PATH : llm_client.plan(text)
       ├─ Prompt système : personnalité majordome + registre tools
       ├─ Claude génère 1+ tool_calls (composition multi-action OK)
       └─ tool_router.resolve(tool_call) → DeviceCommand validée Pydantic
3. Validation stricte :
   ├─ device_id ∈ registry ? sinon REJECT + audit "hallucination"
   ├─ action ∈ enum Literal ? sinon REJECT
   ├─ params extra="forbid" ? sinon REJECT
   └─ budget commandes/requête OK ? sinon REJECT
4. policy.check(DeviceCommand) → safe/sensible/critique + élévation
5. Confirmation si requise (état PendingConfirmation inchangé)
6. audit.log("command_requested" + "policy_evaluated")
7. SubAgent.execute(DeviceCommand) → handler réel ou mock
8. audit.log("command_dispatched" + "command_succeeded"/"failed")
9. Réponse "speak-first" Edge-TTS Andrew → PWA
```

### 3.bis.3 Contrat sous-agent (`subagents/base.py`)

```python
from pydantic import BaseModel, ConfigDict
from typing import Protocol, Literal

class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str                        # ex: "close_shutter"
    description: str                 # pour le prompt LLM
    params_schema: dict              # JSON Schema strict
    default_sensitivity: Literal["safe", "sensible", "critique"]

class SubAgent(Protocol):
    domain: str                      # ex: "tahoma"
    tools: list[ToolSpec]
    def execute(self, command: DeviceCommand) -> ExecutionResult: ...
```

### 3.bis.4 Cadrage V1 vs V2

| Périmètre | Sous-agents | Quand |
|---|---|---|
| **V1 hackathon** | tahoma + devialet + agenda | Avant Loom 4 juin |
| **V2 post-démo** | caméras + mail + appels + freebox + lemlist | Après 4 juin |

### 3.bis.5 Modèle LLM retenu (verdict Codex)

| Choix | Modèle | Raison |
|---|---|---|
| Primaire | **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) | Latence ~500ms, coût ~$0.001/commande, tool-use solide |
| Fallback | Claude Sonnet 4.6 | Si Haiku se trompe sur composition multi-tool |
| **Exclu V1** | Llama 3.x via Ollama local | Variance trop forte pour démo mobile < 1.5s |

### 3.bis.6 Garde-fous additionnels (post-Codex)

1. **Pydantic strict partout** : `extra="forbid"` + enums fermées
2. **Registry allowlisté** : LLM ne nomme jamais un handler Python directement
3. **Budgets par requête** : max 5 commandes/requête, max 1 critique/requête
4. **Anti-replay** : nonce + TTL côté n8n et backend
5. **Marquage données/instructions** : contenus mail/agenda/caméra = blocs délimités jamais traités comme instructions
6. **Audit log enrichi** : transcript STT + tool-call brut LLM + DeviceCommand normalisée + décision Policy + résultat

### 3.bis.7 Bénéfices revendiqués face au jury

- **Extensibilité native** : ajouter un domaine = 1 fichier + 1 ligne registry, sans toucher le cœur
- **Composition langage naturel** : « Mode cinéma » = 3 actions orchestrées sans hard-coding
- **Architecture industrialisable** : pattern réutilisable n'importe quel domaine (revendabilité)
- **Sécurité préservée** : Policy + Audit restent au-dessus du LLM, démontrable (prompt injection ne peut pas ouvrir le portail la nuit)

---

## 4. Sécurité — Architecture en 5 couches

| Couche | Mesures | État |
|---|---|---|
| **1. Identité** | Auth obligatoire PWA (Magic Link + Passkey). Whitelist = Denis. Session 4h. | À implémenter (PWA en S2) |
| **2. Transport** | HTTPS partout. Bearer Token sur webhook n8n. Cloudflare Access devant le tunnel. | Bearer ✅, Access à activer |
| **3. Garde-fous métier** | 3 niveaux (safe/sensible/critique) + élévation contextuelle. Rate limiting. Kill switch. | ✅ Implémenté |
| **4. Secrets & données** | `.env` strict (`.gitignore` OK). Variables sensibles jamais dans le repo. | ✅ |
| **5. Audit & révocation** | Audit signé HMAC. Notification push si critique. Révocation token immédiate. | ✅ SQLite + chaîne HMAC |

### Les 3 niveaux de sensibilité

| Niveau | Confirmation | Exemples |
|---|---|---|
| 🟢 **safe** | Aucune, exécution directe | Volume, chaîne TV, mails, agenda, mode cinéma |
| 🟡 **sensible** | Une confirmation orale | Portail, garage (jour), "je pars", store banne |
| 🔴 **critique** | Confirmation + PIN vocal 4 chiffres | Désactivation alarme, portail/garage la nuit |

### Élévation contextuelle (auto)

Le niveau de base peut être **élevé automatiquement** :

| Condition | Effet |
|---|---|
| Heure entre 22h-7h | +1 niveau (safe→sensible, sensible→critique) |
| Même commande répétée 2× en 1 min | +1 niveau ("vous êtes sûr ?") |
| Confiance Whisper/intent < 0.7 | +1 niveau |

### Garde-fou anti-accident production

Le `TahomaHandler` réel **refuse de s'instancier** si :
- `EXECUTION_MODE != production`
- **OU** `ALLOW_REAL_DEVICES != true`

→ Les 2 variables doivent être explicitement positionnées dans le `.env` local. Impossible d'activer le matériel réel par accident depuis un repo cloné.

---

## 5. État conversationnel — Machine à état `PendingConfirmation`

```
                  ┌────────┐
                  │  IDLE  │
                  └───┬────┘
                      │
                      │ intent classé sensible
                      ▼
            ┌──────────────────────┐
            │ PENDING_SENSIBLE     │
            │ (expire dans 15s)    │
            └─────┬───────────┬────┘
                  │           │
            user dit "oui"   user dit "non"
            ou timeout vers  ou ambiguïté
            execute          → IDLE (annulé)
                  │           │
                  ▼           │
            ┌─────────┐       │
            │ EXECUTE │       │
            └─────────┘       │
                              │
                              ▼
                          ┌────────┐
                          │ IDLE   │
                          └────────┘
```

Pour les commandes critiques, l'état est `PENDING_CRITIQUE` qui demande un PIN (4 chiffres oraux). 3 échecs → état `LOCKED` (freeze 1h + notification push).

---

## 6. Audit log — Chaîne HMAC

Chaque commande génère **plusieurs événements** signés en chaîne. Toute altération d'un événement passé invalide tous les événements suivants (intégrité vérifiable).

### Événements possibles

| Event | Quand |
|---|---|
| `command_requested` | À chaque commande reçue |
| `policy_evaluated` | Après évaluation du policy engine |
| `confirmation_requested` | Si sensible ou critique |
| `confirmation_accepted` | Si l'utilisateur confirme |
| `confirmation_refused` | Si l'utilisateur dit non |
| `confirmation_timeout` | Si pas de réponse dans 15s |
| `pin_attempted` | Si critique, sur saisie PIN |
| `pin_succeeded` / `pin_failed` | Résultat PIN |
| `command_dispatched` | Avant d'envoyer la commande au handler |
| `command_succeeded` / `command_failed` | Résultat exécution |
| `system_locked` | Après 3 échecs PIN |
| `rate_limited` | Si rate limit atteint |

### Signature

```python
signature_N = HMAC_SHA256(secret, signature_{N-1} || canonical_payload_N)
```

Le premier événement utilise `"GENESIS"` comme `signature_0`. Pour vérifier l'intégrité, on recalcule toute la chaîne et on compare. Si un seul événement a été modifié, sa signature ne correspond plus.

---

## 7. Modes d'exécution

| Mode | Effet | Activation |
|---|---|---|
| `mock` | Handlers = simulateurs, aucun appel réseau aux devices, latence simulée 50ms | Défaut (sans config explicite) |
| `replay` | Rejoue une session audit pré-enregistrée (utile démo, debug) | `JARVIS_MODE=replay` + fichier replay |
| `production` | Handlers réels, appels API TaHoma/Freebox, devices physiques bougent | `EXECUTION_MODE=production` + `ALLOW_REAL_DEVICES=true` |

**Tests :** chaque handler réel passe les mêmes contract tests que son mock (sauf tests réseau marqués `integration`).

---

## 8. Performances mesurées

| Métrique | Valeur | Conditions |
|---|---|---|
| Latence pipeline mock | 3 ms moyenne | 3 commandes successives |
| Latence pipeline réel | ~1 s | API TaHoma locale (avant optim) |
| Latence pipeline réel optimisé | 300 ms | Client HTTP persistant + speak-first |
| Latence perçue utilisateur | ~5 ms | Jarvis répond immédiatement, exécution en arrière-plan |
| Latence physique volet TaHoma | 10-15 s | Mécanique Somfy, incompressible |
| Latence Whisper STT (small, FR) | ~2 s | 5 s d'audio → texte |
| Latence Edge-TTS (Andrew, ~50 chars) | ~700 ms | 1ère phrase, ensuite plus rapide |

---

## 9. Évolutions futures (post-hackathon)

| Item | Effort | Bénéfice |
|---|---|---|
| Migration Python sur Raspberry Pi | 1 jour | 24/7 stable, 5W |
| HMAC remplaçant Bearer Token | 2h | Anti-replay |
| Wake word "Jarvis" (porcupine/openwakeword) | 4h | Activation mains libres |
| Vision ALPR (reconnaissance plaque voiture) | 2 jours | Portail s'ouvre sur arrivée Denis |
| Apprentissage adaptatif (historique commandes) | 1 semaine | Suggestions proactives |
| Multi-utilisateurs (femme, enfants) | 3 jours | Profils + permissions granulaires |

---

*Architecture validée le 14 mai 2026, après revue Codex (GPT-5.2). Voir le PRD pour le cadrage produit complet.*
