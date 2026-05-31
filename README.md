# 🤖 Jarvis — Assistant personnel IA domotique

> *« Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. »*

**Hackathon Creator Academy 2026 — Thème 1 : Assistant Personnel**

Jarvis est un majordome IA qui :
- 🪟 **Contrôle physiquement** la maison (volets, portail, garage, alarme, store) via la box Somfy TaHoma
- 📺 **Pilote** la Freebox (TV, chaînes, volume, audio Devialet intégré à la Delta)
- 📱 **Accessible mobile** via une PWA installable (téléphone = télécommande Jarvis)
- 🎩 **Parle en majordome** britannique (voix Andrew, ton Alfred Pennyworth / J.A.R.V.I.S. Iron Man)
- 🛡️ **Sécurisé** : auth obligatoire, 3 niveaux de sensibilité, confirmation vocale pour les actions critiques
- 🆓 **0€ de coût récurrent** (Edge-TTS gratuit, intent NLU local, n8n self-hosted)

---

## 🎬 Démo

**🎥 Présentation du projet (< 5 min)** → https://youtu.be/OB42MOhmvXk

**🎬 Démo complète — Jarvis pilote la vraie maison, en direct** → https://youtu.be/QZAmOG7IwMk

![architecture](docs/architecture.png)

---

## ⚡ Quick start — Mode jury (Mock)

Le repo public est conçu pour être **exécutable sans aucun matériel physique** grâce au MOCK MODE.

```bash
git clone https://github.com/Kzanis/majordome-hackathon
cd majordome-hackathon/jarvis-core

# 1. Installer les dépendances Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# 2. Lancer la démo du pipeline sécurisé (5 scénarios, zéro device réel)
python scripts/demo_pipeline.py
```

**Ce que tu verras :**
- Une commande "safe" (volume) → exécution directe
- Une commande "sensible" (portail) → Jarvis demande confirmation orale
- Tu réponds "oui" → exécution
- Une commande "critique" (alarme) → demande de code PIN
- Une commande à 23h → élévation automatique du niveau de sensibilité
- Vérification HMAC de la chaîne d'audit (16 événements signés)

Pas besoin de TaHoma, pas besoin de Freebox, pas besoin du PC de Denis. Tout tourne sur ta machine en simulation.

---

## 🏗️ Architecture

3 couches indépendantes :

```
☁️ COUCHE CLOUD (Hostinger)
   ├─ Site vitrine + Dashboard temps réel (Next.js)
   ├─ PWA mobile installable (téléphone Denis)
   └─ n8n workflow "Command Bridge" (auth Bearer + routage)
                    │
              Cloudflare Tunnel
                    │
🏠 COUCHE LOCALE (PC Denis)
   ├─ Python FastAPI Jarvis Core
   │  ├─ Orchestrator (pipeline commande)
   │  ├─ Policy Engine (3 niveaux, élévation contextuelle)
   │  ├─ Intent Engine local (fuzzy matching, 0 API)
   │  ├─ Audit Store SQLite (chaîne HMAC)
   │  ├─ Handlers réels (TaHoma, Freebox)
   │  └─ Mocks équivalents (pour tests + jury)
                    │
🔌 COUCHE PHYSIQUE (LAN maison)
   ├─ Somfy TaHoma Switch (IP 192.168.1.69, Local API)
   └─ Freebox Delta (audio Devialet intégré)
```

Voir [`ARCHITECTURE.md`](ARCHITECTURE.md) pour le détail complet.

---

## 🛡️ Sécurité (règle absolue du projet)

Jarvis pilote un portail et une alarme. **Au moindre doute → option la plus restrictive.**

### 8 garde-fous obligatoires

| # | Garde-fou | Quand il s'active |
|---|---|---|
| 1 | Auth obligatoire | Toute commande PWA → token valide ou rejet |
| 2 | Confirmation vocale | Portail / alarme / garage → "Confirmez Monsieur ?" |
| 3 | PIN vocal sensible | Désactivation alarme à distance → 4 chiffres oraux |
| 4 | Heures restreintes | Portail / garage entre 22h-7h → bloqué sauf override |
| 5 | Rate limiting | Max 10 commandes/min, max 500/jour, par utilisateur |
| 6 | Kill switch | "Jarvis, désactive tout" → freeze 1h, demande re-auth |
| 7 | Audit log signé HMAC | Chaque commande → ligne signée + notif push si critique |
| 8 | MOCK obligatoire pour jury | Le repo public exécute **uniquement** en mock par défaut |

### 3 modes d'exécution

| Mode | Auth | Devices réels | Activation |
|---|---|---|---|
| `mock` | Optionnelle | Non (simulateurs) | Défaut, marche partout |
| `replay` | Optionnelle | Non (rejoue) | Pour tester scénarios |
| `production` | Magic Link + Passkey | **Oui** | `EXECUTION_MODE=production` **+** `ALLOW_REAL_DEVICES=true` |

→ **Impossible d'activer la production par accident** : 2 variables d'environnement explicites obligatoires, et `.env` exclu de Git.

---

## 🧩 Stack technique

| Couche | Tech | Choix |
|---|---|---|
| Voice IN (STT) | Whisper local | 100% offline, français |
| Voice OUT (TTS) | Microsoft Edge-TTS | Gratuit illimité, voix Andrew Multilingual |
| NLU (Intent) | Fuzzy matching local (`rapidfuzz`) | 0 API, <5ms, déterministe |
| Orchestration cloud | n8n self-hosted (Hostinger VPS) | Webhook + auth + routage |
| Pont cloud↔maison | Cloudflare Tunnel | Gratuit, pas d'IP publique fixe nécessaire |
| Backend local | FastAPI Python | Async, contracts Protocol |
| Audit | SQLite WAL + HMAC chain | Append-only, intégrité vérifiable |
| Frontend | Next.js + PWA + Canvas avatar | Site + dashboard + interface vocale mobile |

---

## 📂 Structure du repo

```
majordome-hackathon/
├── README.md                    ← tu es ici
├── ARCHITECTURE.md              ← architecture détaillée
├── PRD.md                       ← cahier des charges produit
│
├── jarvis-core/                 ← Backend Python (tourne sur PC Denis)
│   ├── requirements.txt
│   ├── .env.example             ← copier en .env et remplir
│   ├── config/
│   │   └── settings.yaml        ← mapping vocal → devices
│   ├── jarvis/
│   │   ├── domain/              ← types (Intent, Command, PolicyDecision...)
│   │   ├── policy/              ← engine de sécurité métier
│   │   ├── core/                ← orchestrator, voice, intent
│   │   ├── handlers/            ← TaHoma réel
│   │   ├── mocks/               ← simulateurs (pour jury + tests)
│   │   └── audit/               ← SQLite signé HMAC
│   └── scripts/
│       ├── demo_pipeline.py     ← démo pipeline en mock
│       ├── test_devices.py      ← validation devices physiques
│       └── ...
│
├── jarvis-cloud/                ← Front Next.js (déployé Hostinger)
│   ├── (à venir S2)
│
├── n8n-workflows/               ← Workflows exportés
│   ├── jarvis-command-bridge.json
│   └── README.md
│
└── docs/
    ├── architecture.png         ← diagramme système
    └── pipeline.png             ← flux d'une commande
```

---

## 🎯 Exemples d'interactions

### Commande safe (volume) — exécution directe
```
Denis  : "Jarvis, monte le son"
Jarvis : "Bien Monsieur. Ce sera fait."
        [volume Freebox +10, instantané]
```

### Commande sensible (portail) — confirmation
```
Denis  : "Jarvis, ouvre le portail"
Jarvis : "Vous souhaitez bien ouvrir le portail Monsieur ?"
Denis  : "Oui"
Jarvis : "Bien Monsieur. Le portail s'ouvre."
        [TaHoma → portail bouge physiquement]
```

### Erreur de transcription Whisper → annulée
```
Denis  : "Jarvis, ouvre la fenêtre du salon"
        [Whisper transcrit par erreur : "ouvre le portail"]
Jarvis : "Vous souhaitez bien ouvrir le portail Monsieur ?"
Denis  : "Non, j'ai dit la fenêtre"
Jarvis : "Bien Monsieur, j'annule."
```
→ **L'erreur ne devient jamais une action physique.** C'est exactement le risque qu'on a éliminé.

### Commande critique la nuit — élévation auto
```
Denis  : "Jarvis, ouvre le portail" (à 23h30)
        [Sensibilité base=sensible → élevée=critique par heure nocturne]
Jarvis : "Cette action requiert votre code de sécurité Monsieur."
Denis  : "Sept-deux-quatre-neuf"
Jarvis : "Bien Monsieur. Le portail s'ouvre."
```

---

## 🧪 Tests

| Suite | Statut | Coverage |
|---|---|---|
| Pipeline complet (mock) | ✅ 5/5 scénarios | Safe / Sensible / PIN / Confirmation / Élévation |
| Intent local (synonymes) | ✅ 10/10 phrases | Rideau↔Volet, Barrière↔Portail, Joris↔Jarvis |
| Handler TaHoma réel | ✅ 5/5 tests | Garde-fou + connexion + 17 devices + commande |
| Audit chain HMAC | ✅ Intègre | 16 événements signés vérifiés |
| Latence E2E (mock) | ✅ 3ms perçu | Pattern "speak first, execute after" |

---

## 📅 Planning hackathon (3 semaines)

| Semaine | Objectif |
|---|---|
| **S1** (12-18 mai) | ✅ Core Python + handlers + voix + intent local + workflow n8n |
| **S2** (19-25 mai) | Front Hostinger + PWA + dashboard + Cloudflare Tunnel + vision |
| **S3** (26 mai - 4 juin) | Polish + scènes + script + tournage vidéo Loom + soumission |

---

## 🤝 Soumission

- Vidéo Loom 5 min — plan séquence
- Repo GitHub (ce repo)
- Site public : `jarvis.creatorsystemia.fr` *(à déployer)*
- Workflow n8n exportable dans [`n8n-workflows/`](n8n-workflows/)

---

## 📜 Licence et crédits

- Développé par Denis Solé avec l'assistance IA d'**Anto** (PAI — Personal AI Infrastructure)
- Code sous licence MIT *(à confirmer)*
- Hackathon partenaire : Creator Academy × Hostinger

---

*« Excellente journée Monsieur. Je veille. »*
