# PRD — Jarvis : Assistant Personnel IA Domotique
## Hackathon Creator Academy — Thème 1 : Assistant Personnel

**Date de rédaction :** 12 mai 2026
**Dernière mise à jour :** 17 mai 2026 (pivot architecture orchestrateur multi-agents — voir §15)
**Deadline soumission :** 4 juin 2026 à minuit
**Porteur :** Denis Sole
**Partenaire :** Hostinger (éligibilité couverte : site + dashboard + n8n hébergés sur Hostinger)

---

## 1. Vision

Construire **Jarvis**, un majordome personnel IA accessible depuis une **PWA mobile**, qui :
- Contrôle physiquement la maison de Denis (volets, portail, garage, alarme, store, TV, son)
- Gère son environnement digital (mails, agenda, prospection)
- Parle comme un majordome britannique (style Alfred / J.A.R.V.I.S. Iron Man)
- Apparaît visuellement sous forme d'**avatar HUD cyan** qui bouge les lèvres en synchronisation avec sa voix

**Différenciation concurrentielle :**
Là où 90% des participants vont créer un Jarvis qui lit des emails sur un terminal, Denis présente :
- Un Jarvis **mobile** (PWA installable sur téléphone)
- Avec une **identité visuelle** (avatar HUD style Iron Man qui parle à l'écran)
- Avec une **personnalité éditoriale** (majordome britannique, voix grave)
- Qui **ouvre physiquement son portail**, **descend ses volets**, **change de chaîne sur sa TV**
- **En live, devant le jury**, depuis son téléphone, en plan séquence

---

## 2. Objectifs

| Objectif | Critère de succès |
|---|---|
| Démo live 5 minutes sans plantage | 5 scènes enchaînées sans erreur |
| Contrôle domotique vocal complet | TaHoma + Freebox + Devialet répondent |
| Brief vocal du matin | Mails urgents + agenda énoncés à l'oral |
| Vision bonus | Plaque reconnue → portail s'ouvre |
| Éligibilité Hostinger | Site + dashboard + n8n hébergés Hostinger |
| Expérience cinématographique | Avatar HUD + voix majordome + démo plan séquence |
| Revendabilité | Produit présentable comme une vraie app SaaS |

---

## 3. Architecture Globale

### 3.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                     COUCHE PUBLIQUE — HOSTINGER                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Site vitrine │  │  Dashboard   │  │  PWA Jarvis Mobile   │ │
│  │  (Next.js)   │  │  temps réel  │  │  (manifest + SW)     │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  n8n VPS Hostinger — Orchestrateur cloud                   │ │
│  │  • Webhooks publics  • Cron brief matinal  • Bridge maison│ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                    Cloudflare Tunnel (sécurisé)
                                │
┌─────────────────────────────────────────────────────────────────┐
│                  COUCHE LOCALE — MAISON DENIS                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Jarvis Core (FastAPI Python)                              │ │
│  │  • Whisper STT  • Claude intent  • ElevenLabs TTS         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  TaHoma  │  │ Freebox  │  │ Devialet │  │ Vision (cam) │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Flux d'une commande vocale depuis le téléphone

```
1. Denis ouvre la PWA Jarvis sur son téléphone
2. Avatar HUD en mode "idle" (ondes cyan respirant)
3. Tape le bouton micro → avatar passe en "listening" (pulsation rapide)
4. Dit "Jarvis, ouvre le portail"
5. Audio envoyé HTTPS → site Hostinger → webhook n8n
6. n8n forward via Cloudflare Tunnel → FastAPI maison
7. Whisper transcrit (~2s)
8. Claude route l'intent + applique le ton majordome (~1.5s)
9. Avatar passe en "thinking" (rotation)
10. Handler TaHoma ouvre le portail physiquement
11. Réponse "Bien Monsieur. Le portail est ouvert." → ElevenLabs TTS
12. Audio retourne PWA → avatar passe en "speaking" (lip-sync amplitude)
13. Dashboard public log la commande en temps réel
14. Total : ~5-6 secondes
```

---

## 4. Stack Technique

### 4.1 Couche publique (Hostinger)

| Composant | Tech | Hébergement |
|---|---|---|
| Site vitrine + dashboard + PWA | Next.js 16 (App Router) | Hostinger (site/VPS) |
| API publique | Routes Next.js + n8n webhooks | Hostinger VPS |
| Orchestration cloud | n8n (déjà déployé) | Hostinger VPS |
| Tunnel sécurisé | Cloudflare Tunnel | Cloudflare (gratuit) |
| Domaine | `jarvis.creatorsystemia.fr` (ou dédié) | À configurer |

### 4.2 Couche locale (maison Denis)

| Composant | Tech | Rôle |
|---|---|---|
| Jarvis Core | FastAPI + uvicorn | Réception webhooks + orchestration |
| Voice IN | Whisper (local) | STT |
| Intent | Anthropic Claude API | Routage + ton majordome |
| Voice OUT | ElevenLabs TTS | Voix grave britannique |
| Vision daemon | OpenCV + YOLOv8 + fast-alpr | Reconnaissance plaque |

### 4.3 APIs locales (réseau maison)

| Système | Protocole | Auth | Accès |
|---|---|---|---|
| Somfy TaHoma | REST HTTPS local | Bearer token | `https://[IP_tahoma]:8443` |
| Freebox Player | REST HTTPS local | Session HMAC-SHA1 | `https://mafreebox.freebox.fr` |
| Devialet | HTTP REST local | Aucune | `http://[IP_devialet]:80` |
| Caméra (option A) | FTP push sur PIR | — | Dossier FTP local |
| Caméra (option B) | RTSP (Android) | — | `rtsp://[IP]:8080/video` |

### 4.4 APIs cloud

| Service | Usage | Coût |
|---|---|---|
| Claude API (Anthropic) | Intent routing + ton majordome | ~$0.01/interaction |
| ElevenLabs | Voix sortante (grave britannique) | Free tier ou ~$0.001/phrase |
| Google Calendar API | Lecture + écriture RDV | Gratuit |
| Gmail API | Lecture mails urgents | Gratuit |
| Lemlist API | Stats prospection | Déjà abonné |
| n8n Hostinger | Orchestration cloud | Déjà payé |

### 4.5 Dépendances Python (côté maison)

```
whisper              # Voice input (STT)
anthropic            # Claude API
elevenlabs           # Voice output (TTS)
fastapi + uvicorn    # Core HTTP server
requests             # HTTP calls vers TaHoma / Freebox
devialet             # Client Devialet (PyPI v1.5.7)
freebox-api          # Client Freebox (hacf-fr)
google-api-python-client  # Calendar + Gmail
opencv-python        # Vision — capture caméra
ultralytics          # YOLOv8 — détection voiture
fast-alpr            # Lecture plaque (local, gratuit)
watchdog             # Surveillance dossier FTP
python-dotenv        # Secrets
```

### 4.6 Dépendances Web (côté PWA Hostinger)

```
next                 # Framework
react                # UI
tailwindcss          # Style
framer-motion        # Animations avatar
zustand              # State management
socket.io-client     # Dashboard temps réel (ou Server-Sent Events)
workbox              # PWA service worker
```

---

## 5. Features

### 5.1 Commandes vocales — Scènes domotiques

| Commande | Actions déclenchées |
|---|---|
| `"Jarvis, bonjour"` | Ouvre tous les volets + désactive alarme + brief vocal (mails + agenda) + Devialet joue |
| `"Jarvis, je pars"` | Ferme volets + active alarme + ouvre portail 30s + Devialet s'éteint |
| `"Jarvis, mode cinéma"` | Ferme volets salon + Freebox lance contenu + Devialet volume max |
| `"Jarvis, bonne nuit"` | Ferme tous les volets + ferme store + active alarme + Devialet s'éteint |
| `"Jarvis, ouvre/ferme [volet X]"` | Commande unitaire volet spécifique |
| `"Jarvis, ouvre le portail"` | TaHoma → portail ouvert 30s |
| `"Jarvis, ouvre le garage"` | TaHoma → porte garage |
| `"Jarvis, active/désactive l'alarme"` | TaHoma → alarme on/off |
| `"Jarvis, mets la télé sur [chaîne]"` | Freebox → change de chaîne |
| `"Jarvis, coupe le son"` | Devialet → volume 0 |
| `"Jarvis, monte/baisse le son"` | Devialet → +/- 10 |

### 5.2 Commandes vocales — Digital

| Commande | Actions |
|---|---|
| `"Jarvis, mes mails urgents"` | Gmail → résume les 3 plus importants à l'oral |
| `"Jarvis, mon agenda demain"` | Google Calendar → énonce les RDV |
| `"Jarvis, note un RDV [X] [date] [heure]"` | Google Calendar → crée l'événement |
| `"Jarvis, mes leads qui traînent"` | Lemlist → stats prospects sans réponse |

### 5.3 Avatar visuel — HUD Iron Man

**Concept :** un visage abstrait géométrique cyan/bleu inspiré du HUD J.A.R.V.I.S. d'Iron Man. Pas d'avatar humain (évite l'uncanny valley), uniquement une **identité visuelle** qui réagit à l'état du système.

**Stack technique :**
- **Canvas 2D** (MVP) dans la PWA — bibliothèque `framer-motion` pour les animations
- **Stretch goal S3** : passage à **Three.js** (3D) si temps disponible
- **Web Audio API** (`AnalyserNode`) : lit l'amplitude du flux audio TTS en temps réel
- **Lip-sync simplifié** : la "bouche" varie en hauteur selon l'amplitude (pas de viseme analysis complexe — l'amplitude suffit pour l'effet)

**États visuels :**
| État | Animation |
|---|---|
| **Idle** | Ondes concentriques lentes, respiration cyan |
| **Listening** | Pulsation rapide bleu cyan (Whisper actif) |
| **Thinking** | Rotation des cercles concentriques (Claude réfléchit) |
| **Speaking** | "Bouche" anime en hauteur selon amplitude audio TTS |
| **Action OK** | Flash vert bref quand commande exécutée |
| **Error** | Flash orange + ondulation perturbée |

**Référence visuelle :** Le HUD Tony Stark / J.A.R.V.I.S. — cercles concentriques bleu cyan, lignes géométriques, ondes audio qui pulsent.

### 5.4 Personnalité — Majordome britannique

**Concept :** Jarvis s'inspire d'Alfred Pennyworth (Batman) et de J.A.R.V.I.S. (Iron Man). Langage soutenu, vouvoiement strict, ton calme et déférent avec une pointe d'humour pince-sans-rire.

**Fichier :** `config/prompts/personality.md`

**Règles éditoriales :**
- Vouvoiement strict, jamais de tutoiement
- Adresse "Monsieur" en début ou fin de réponse
- Phrases courtes, élégantes, légèrement britanniques
- Ton calme, déférent, avec une pointe d'humour pince-sans-rire
- Ne jamais expliquer son fonctionnement interne

**Confirmations standard :**
- "Bien Monsieur."
- "À votre service."
- "Ce sera fait."
- "Comme il vous plaira."
- "Avec plaisir, Monsieur."

**En cas d'échec :**
- "Je crains que cela ne soit pas possible, Monsieur."
- "Permettez-moi de vous signaler que…"
- "Je dois vous prier de m'excuser, Monsieur."

**Brief matinal :**
```
"Bonjour Monsieur. Permettez-moi de vous présenter votre journée.
Vous avez X messages prioritaires, et trois rendez-vous en perspective.
Le premier à dix heures avec…"
```

**Exemples de répliques cibles :**

| Commande Denis | Réponse Jarvis |
|---|---|
| "Jarvis, bonjour" | "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. Voici votre matinée…" |
| "Ouvre le portail" | "Bien Monsieur. Le portail est ouvert." |
| "Mes mails urgents" | "Trois messages méritent votre attention, Monsieur. Le premier…" |
| "Bonne nuit" | "Excellente nuit Monsieur. Je veille." |
| Erreur device | "Je crains que la connexion au volet du salon ne réponde pas, Monsieur. Souhaitez-vous que je réessaie ?" |

### 5.5 Voix TTS — Timbre majordome

**Reco principale :** ElevenLabs voix **Adam** ou **Antoni** (grave, posée, légèrement britannique)
- Possibilité de créer une voix custom "British Butler" via voice cloning ElevenLabs

**Fallback :** OpenAI TTS `onyx` (grave, sérieuse, gratuit dans tier API)

**À éviter :**
- Voix féminines aigües (casse l'effet majordome)
- Voix synthétiques robotiques vieille école

### 5.6 Vision — Reconnaissance voiture (bonus)

**Stratégie en cascade (par ordre de priorité) :**

```
Option A (test d'abord) :
  Caméra Ctronics → PIR détecte → snapshot FTP → fast-alpr → plaque Denis → portail

Option B (si Option A insuffisante) :
  Vieux Android + app "IP Webcam" → RTSP → OpenCV → YOLOv8 → fast-alpr → portail

Option C (fallback démo) :
  Webcam laptop → même pipeline → portail
```

**Logique de décision :**
```python
if plaque in whitelist and cooldown_ok():
    tahoma.open_portail()
    tts.say("Bonjour Monsieur, portail ouvert.")
    set_cooldown(60)  # Anti-rebond 60 secondes
elif heure in range(22, 7) and mouvement:
    tts.say("Véhicule non reconnu devant le portail, Monsieur.")
```

---

## 6. Architecture Détaillée

### 6.1 Structure fichiers

```
C:\Dev\Hackaton\
├── PRD.md                        ← ce fichier
├── ARCHITECTURE.md
├── DEMO_SCRIPT.md                ← script démo 5 min (à créer S3)
│
├── jarvis-cloud/                 ← SITE + PWA (déployé Hostinger)
│   ├── package.json
│   ├── next.config.js
│   ├── public/
│   │   ├── manifest.json         ← PWA manifest
│   │   └── icons/                ← icônes PWA
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          ← Landing vitrine
│   │   │   ├── dashboard/        ← Dashboard temps réel public
│   │   │   └── app/              ← PWA Jarvis (interface vocale)
│   │   ├── components/
│   │   │   ├── Avatar/           ← HUD Iron Man Canvas 2D
│   │   │   │   ├── HUDCanvas.tsx
│   │   │   │   ├── audioAnalyser.ts  ← Web Audio API
│   │   │   │   └── states.ts     ← idle/listening/thinking/speaking
│   │   │   ├── MicButton.tsx
│   │   │   └── LogStream.tsx     ← Dashboard live
│   │   ├── lib/
│   │   │   ├── webhook.ts        ← Appels n8n
│   │   │   └── sw.ts             ← Service worker PWA
│   │   └── styles/
│   └── tests/
│
├── jarvis-core/                  ← BACKEND PYTHON (maison Denis)
│   ├── pyproject.toml
│   ├── .env                      ← secrets (JAMAIS commité)
│   ├── .env.example
│   ├── config/
│   │   ├── settings.yaml         # IP devices, seuils
│   │   ├── whitelist_plates.yaml # plaques autorisées
│   │   └── prompts/
│   │       ├── intent_router.md  # system prompt Claude
│   │       └── personality.md    # ← personnalité majordome
│   ├── jarvis/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── core/
│   │   │   ├── intent_engine.py  # Claude → intent + params
│   │   │   ├── action_router.py  # dispatch vers handlers
│   │   │   ├── context.py        # état conversation
│   │   │   └── voice.py          # Whisper + ElevenLabs pipeline
│   │   ├── handlers/
│   │   │   ├── base.py
│   │   │   ├── tahoma.py
│   │   │   ├── freebox.py
│   │   │   ├── devialet.py
│   │   │   ├── calendar.py
│   │   │   ├── gmail.py
│   │   │   └── lemlist.py
│   │   ├── vision/
│   │   │   ├── daemon.py
│   │   │   ├── camera.py
│   │   │   ├── alpr.py
│   │   │   └── decisions.py
│   │   ├── mocks/                ← MOCK MODE pour le jury
│   │   │   ├── tahoma_mock.py
│   │   │   ├── freebox_mock.py
│   │   │   └── devialet_mock.py
│   │   └── cloud_bridge/
│   │       ├── webhook_receiver.py
│   │       └── tunnel.py         # Cloudflare Tunnel
│   ├── scripts/
│   │   ├── start_jarvis.bat
│   │   └── test_devices.py
│   └── tests/
│       └── fixtures/
│           └── demo_arrival.mp4
│
└── n8n-workflows/                ← Workflows n8n exportés (versioning)
    ├── brief_matinal.json
    ├── webhook_bridge.json
    └── vision_alert.json
```

### 6.2 Modes d'exécution du repo (pour le jury)

| Mode | Usage | Activation |
|---|---|---|
| `production` | Chez Denis, devices réels | `JARVIS_MODE=production` |
| `mock` | Jury, simulateur de devices | `JARVIS_MODE=mock` |
| `replay` | Rejoue une session enregistrée | `JARVIS_MODE=replay` |

**MOCK MODE :** les handlers physiques sont remplacés par des simulateurs qui loggent l'action. Le pipeline complet (Whisper → Claude → action → TTS → avatar) reste fonctionnel. Le jury peut cloner le repo, lancer `docker-compose up`, parler au micro, et voir le système réagir sans avoir de TaHoma/Freebox/Devialet.

---

## 7. Stratégie de Livraison

Contrainte : tout le matériel physique est chez Denis. Le jury doit pouvoir vérifier sans s'y déplacer.

**4 piliers de preuve combinés :**

### 7.1 Vidéo Loom — Preuve principale (plan séquence)

**Règles de production :**
- **Une seule prise**, pas de cut, 5 minutes
- **Split-screen** : téléphone Denis (PWA + avatar HUD) à gauche, caméra maison à droite
- **Preuve d'authenticité** : horloge live à l'écran + élément aléatoire (météo du jour, dernier message)
- **Voix off Denis** explique l'architecture pendant l'action
- **5 scènes enchaînées** : Bonjour → Mes mails urgents → Mode cinéma → Ouvre le portail (vision plaque) → Bonne nuit

➫ Impossible à faker en plan séquence : la maison qui obéit en direct.

### 7.2 Site + Dashboard public Hostinger

URL publique : `jarvis.creatorsystemia.fr` (ou domaine dédié)
- **Landing** : présentation produit, captures, vidéo démo embed
- **Dashboard** : logs commandes temps réel, historique 100 dernières interactions, état devices
- **PWA installable** depuis le site
- **Bonus éligibilité Hostinger** : VPS = service public actif, pas juste case à cocher

### 7.3 MOCK MODE dans le repo GitHub

Le jury clone, lance `docker-compose up`, parle au micro → voit Jarvis réagir end-to-end **sans devices**. Différence majeure avec les autres participants.

### 7.4 Documentation chirurgicale

- `README.md` clair : 3 modes d'exécution expliqués
- `ARCHITECTURE.md` avec schémas réseau
- Vidéos secondaires `/docs/clips/` : 30s par scène
- Tests unitaires en CI GitHub Actions → preuve que le code est testé

---

## 8. Planning 3 Semaines

### Semaine 1 — 12 au 18 mai : Core fonctionnel + setup site
**Objectif :** "Ferme les volets" fonctionne de bout en bout depuis un micro local.

| Jour | Tâche |
|---|---|
| 12-13 mai | Setup `jarvis-core` Python (pyproject.toml, .env, settings.yaml) |
| 14 mai | Handler TaHoma : lister devices, open/close volets, portail |
| 14-15 mai | Whisper voice input + ElevenLabs TTS output (voix Adam) |
| 15-16 mai | Claude intent engine + prompt majordome v1 (`personality.md`) |
| 16-17 mai | FastAPI core, 2-3 scènes complètes (bonjour, je pars, bonne nuit) |
| 17-18 mai | Setup `jarvis-cloud` Next.js + déploiement Hostinger (skeleton) |
| **Lun 18 mai** | **Atelier Jarvis + hardware avec Tom (Academy) — CRITIQUE** |

**Livrable S1 :** Commande vocale locale (laptop micro) → volets bougent physiquement, voix majordome répond.

---

### Semaine 2 — 19 au 25 mai : PWA + avatar + handlers complets
**Objectif :** Pipeline complet PWA mobile → maison + avatar HUD fonctionnel.

| Jour | Tâche |
|---|---|
| 19 mai | Handler Freebox Player (TV, chaînes, volume) |
| 20 mai | Handler Devialet (son, volume, source) |
| 20-21 mai | Google Calendar (lecture + écriture RDV) |
| 21-22 mai | Gmail (mails urgents) + Lemlist (leads) |
| 22-23 mai | PWA frontend : MicButton + envoi audio HTTPS + retour TTS |
| 22-23 mai | Avatar HUD Canvas 2D : 5 états (idle/listening/thinking/speaking/action) |
| 23-24 mai | Lip-sync Web Audio API : bouche réagit à l'amplitude TTS |
| 24-25 mai | Cloudflare Tunnel + n8n webhook bridge (PWA → maison) |
| 24-25 mai | Vision : tester Option A (FTP Ctronics) ou B (Android RTSP) |
| 25 mai | Dashboard temps réel (logs live + état devices) |
| **Lun 25 mai** | **Atelier Networking Academy** |

**Livrable S2 :** Essai en direct #1 — Denis sort son téléphone, ouvre PWA, parle, voit l'avatar bouger les lèvres, la maison réagit.

---

### Semaine 3 — 26 mai au 4 juin : Polish + Démo
**Objectif :** 5 minutes de démo plan séquence irréprochables.

| Jour | Tâche |
|---|---|
| 26-27 mai | MOCK MODE complet (mocks devices + simulateur visuel HTML) |
| 27-28 mai | Caches Claude pour commandes de démo (latence minimale) |
| 28 mai | DevWithMe #2 avec Tylian (Academy) |
| 28-29 mai | Fallbacks : mode replay vision, mode manuel bouton |
| 29-30 mai | Rédiger `DEMO_SCRIPT.md` (script précis 5 min) |
| 30 mai | **Freeze code** — plus aucune nouvelle feature |
| 31 mai - 1er juin | Répétitions générales (10 passes minimum) |
| **Lun 1er juin** | **Q&R dernière ligne droite avec Tom (Academy)** |
| 2-3 juin | Tournage vidéo Loom plan séquence (plusieurs prises possibles) |
| 4 juin | Soumission formulaire avant minuit |

**Stretch goal S3 si temps :** passer avatar 2D Canvas → 3D Three.js (tête robot stylée).

---

## 9. Sécurité — Règle absolue du projet

**Principe directeur :** Jarvis pilote physiquement la maison de Denis (portail, alarme, garage) et lit ses données personnelles. Une faille = quelqu'un peut ouvrir le portail à distance et lire ses mails. **Au moindre doute, choisir l'option la plus restrictive.**

### 9.1 Architecture sécurité — 5 couches

| Couche | Mesures |
|---|---|
| **1. Identité** | Auth obligatoire PWA (Magic Link email + Passkey). Liste blanche = Denis uniquement. Session 4h + refresh signé. |
| **2. Transport** | HTTPS partout. Webhooks n8n signés HMAC SHA-256 (secret rotatif). Cloudflare Access devant le tunnel (auth Google). |
| **3. Garde-fous métier** | Commandes sensibles → confirmation vocale ou PIN. Heures restreintes. Rate limiting. Kill switch. |
| **4. Secrets & données** | `.env` strict (`.gitignore` OK). Variables Hostinger Vault côté cloud. Logs scrubés (pas de PII, pas de tokens). |
| **5. Audit & révocation** | Audit log signé de toute commande. Notification push si commande sensible. Révocation immédiate token compromis. |

### 9.2 Les 8 garde-fous obligatoires

| # | Garde-fou | Déclenchement |
|---|---|---|
| 1 | **Auth obligatoire** | Toute commande PWA → token Denis valide ou rejet |
| 2 | **Confirmation vocale** | Portail / alarme / garage → "Confirmez Monsieur ?" |
| 3 | **PIN vocal sensible** | Désactivation alarme à distance → 4 chiffres oraux |
| 4 | **Heures restreintes** | Portail / garage entre 22h-7h → bloqué sauf override volontaire |
| 5 | **Rate limiting** | Max 10 commandes/min, max 500/jour, par utilisateur |
| 6 | **Kill switch** | "Jarvis, désactive tout" → freeze 1h, demande re-auth |
| 7 | **Audit log** | Chaque commande → ligne signée + notif push si critique |
| 8 | **MOCK obligatoire pour jury** | Le repo public exécute uniquement `mock`. Mode `production` joignable QUE depuis LAN Denis ou Cloudflare Tunnel auth |

### 9.3 Données personnelles — règles de manipulation

- **Mails Gmail** : résumé à l'oral uniquement, jamais loggés en clair, jamais dans le dashboard public
- **Calendar** : titres d'événements anonymisés dans les logs (ex : "RDV 14h" pas "RDV avec Sarah Saint-Dizier")
- **Lemlist** : stats agrégées uniquement, pas de nom de prospect dans le dashboard public
- **Plaques voiture** (vision) : whitelist en local, jamais loggée, hash si stockage longue durée
- **Logs Whisper** : transcripts effacés après 24h, sauf opt-in explicite Denis

### 9.4 Catégorisation des commandes & confirmation vocale

Chaque commande porte un niveau de sensibilité qui détermine si Jarvis exécute directement ou demande confirmation à l'oral. Objectif : empêcher toute action physique non voulue (mauvaise transcription, bruit, commande mal interprétée).

#### 9.4.1 Les 3 niveaux

| Niveau | Confirmation | Caractéristique | Exemples |
|---|---|---|---|
| 🟢 **SAFE** | Aucune (action immédiate + feedback vocal) | Réversible, à faible conséquence | Volume +/-, chaîne TV, mes mails, mon agenda, mode cinéma, brief matinal, mets/coupe le son |
| 🟡 **SENSIBLE** | Une confirmation orale | Action physique extérieure ou impactante | Ouvrir portail (jour), ouvrir garage (jour), "je pars", ouvrir tous les volets, fermer tous les volets |
| 🔴 **CRITIQUE** | Confirmation + PIN vocal 4 chiffres | Sécurité maison, hors plage horaire | Désactiver alarme, ouvrir portail/garage nuit (22h-7h), "désactive tout" |

#### 9.4.2 Sensibilité contextuelle (auto-élévation)

Le niveau de base peut être **élevé automatiquement** selon le contexte :

| Condition | Effet |
|---|---|
| Heure entre 22h-7h | Toute commande SAFE → SENSIBLE, toute SENSIBLE → CRITIQUE |
| Même commande répétée 2× en 1 min | Re-confirmation obligatoire avec "Vous êtes sûr Monsieur ?" |
| Commande non précédée d'un contexte cohérent (ex : "ouvre le portail" sans "je rentre" préalable la nuit) | Élévation +1 niveau |
| Confiance Claude < 0.7 sur l'intent | Élévation +1 niveau systématique |

#### 9.4.3 Mécanisme de confirmation vocale — état `PendingConfirmation`

```
Flux d'une commande SENSIBLE :

1. Denis  : "Jarvis, ouvre le portail"
2. Whisper transcrit → Claude classe intent : open_gate, sensitivity: sensible
3. Action Router → policy.check() → "confirmation requise"
4. Contexte conversationnel passe en état PendingConfirmation:
   {
     intent: "open_gate",
     params: {},
     expires_at: now + 15s,
     attempts: 0
   }
5. Jarvis (TTS) : "Vous souhaitez bien ouvrir le portail Monsieur ?"
6. Denis : "Oui" (ou "Non" / "Confirmé" / "Annule")
7. Whisper transcrit → Claude détecte yes/no/cancel
8. Si YES dans 15s → execute + audit log
   Si NO → annule + "Bien Monsieur, j'annule."
   Si timeout → annule + "Pas de confirmation, j'annule la demande Monsieur."
   Si AMBIGU → "Je n'ai pas bien compris Monsieur, est-ce un oui ?"
```

#### 9.4.4 Dialogues majordome — phrases de confirmation

**Niveau SENSIBLE — confirmation simple :**
- "Vous souhaitez bien ouvrir le portail Monsieur ?"
- "Je dois confirmer : ouverture du portail, c'est bien cela ?"
- "Permettez-moi de m'assurer : je dois ouvrir le portail ?"

**Niveau CRITIQUE — demande de PIN :**
- "Je dois confirmer votre identité Monsieur. Veuillez me donner votre code."
- "Cette action requiert votre code de sécurité Monsieur."
- "Pour des raisons évidentes, votre code est nécessaire Monsieur."

**Confirmation reçue :**
- "Bien Monsieur. Le portail s'ouvre."
- "Ce sera fait Monsieur."
- "À votre service. Le portail est en mouvement."

**Refus / annulation :**
- "Bien Monsieur, j'annule la demande."
- "Comme il vous plaira Monsieur."

**Timeout :**
- "Pas de confirmation reçue Monsieur, j'annule la demande."

**Ambigu :**
- "Je n'ai pas bien compris Monsieur, dois-je l'ouvrir ?"

**Code erroné :**
- "Le code n'est pas correct Monsieur. Souhaitez-vous réessayer ?"
- *Après 3 échecs* : "Trois tentatives infructueuses Monsieur. Je dois désactiver les commandes sensibles pour une heure et vous notifier."

### 9.5 Mode d'exécution & exposition

| Mode | Auth | Devices réels | Exposition publique |
|---|---|---|---|
| `production` | Magic Link + Passkey | Oui | LAN Denis ou Cloudflare Tunnel + Access |
| `mock` | Optionnelle | Non (simulateurs) | Repo GitHub clone OK |
| `replay` | Optionnelle | Non (replay enregistré) | Repo GitHub clone OK |

### 9.6 Checklist sécurité par session

À chaque session de dev, vérifier :
- [ ] `.env` non commité (pré-commit hook)
- [ ] Aucune log avec secrets en clair
- [ ] Tests passent en mode `mock` (validation pour le jury)
- [ ] Aucune nouvelle URL/webhook sans auth ajouté
- [ ] Commandes nouvelles classées : critique / sensible / safe → garde-fous appliqués

---

## 10. Risques et Mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Latence pipeline vocal mobile > 7s | Moyenne | Cache Claude pour scènes démo + streaming TTS + Cloudflare Tunnel direct sans n8n en fallback |
| Caméra vision non fonctionnelle | Haute | Webcam laptop en fallback (garanti) |
| TaHoma IP change sur le réseau | Faible | Réserver IP fixe dans la box |
| ElevenLabs quota dépassé | Faible | OpenAI TTS `onyx` en fallback |
| Cloudflare Tunnel instable démo | Faible | Si plantage cloud, fallback démo locale (micro laptop) |
| Avatar 3D trop complexe S3 | Moyenne | Garder Canvas 2D MVP, 3D en stretch goal uniquement |
| Voix majordome pas crédible | Moyenne | Test précoce S1 avec 5 voix candidates, valider auditivement |
| Personnalité Claude dérive du ton | Moyenne | Few-shot examples dans le prompt + cache des réponses canoniques |

---

## 11. Critères de Victoire

Le jury veut être "impressionné". Indicateurs concrets :

1. **Contrôle physique en live** : volets qui bougent pendant la démo
2. **Multi-domaines** : domotique + digital dans la même session
3. **Identité produit** : avatar HUD + voix majordome = expérience cinématographique
4. **Fluidité** : pas de délai ressenti, voix naturelle
5. **Mobilité** : commande depuis le téléphone, pas un laptop fixe
6. **Cas d'usage réel** : démontrer une journée type (matin → départ → retour)
7. **Revendabilité** : "ce Jarvis, je pourrais le vendre" → stack pro Hostinger + PWA + n8n
8. **Vérifiabilité** : MOCK MODE → le jury peut exécuter le code

---

## 12. Soumission

- **Formulaire :** lien communauté Academy (canal hackathon)
- **Vidéo Loom :** 5 minutes plan séquence, présenter en live les scènes
- **Livrables :** repo GitHub `jarvis-cloud` + `jarvis-core` + instructions installation
- **Site public :** lien `jarvis.creatorsystemia.fr` (vitrine + dashboard + PWA)
- **Hébergement Hostinger :** site + dashboard + n8n VPS = éligibilité 200% ✅

---

## 13. Plan B — Meetup 19 juin

Si présélectionné pour le meetup du 19 juin :
- **Option 1** : Laptop + routeur 4G + mini TaHoma de démo apportable (1 volet de bureau) → démo physique sur scène
- **Option 2** : Démo Cloudflare Tunnel depuis la scène → ouvrir SES volets à distance depuis Paris
- **Option 3** : Lecture vidéo Loom + Q&R sur l'architecture

---

*PRD rédigé le 12 mai 2026 — Mis à jour le 14 mai 2026 avec architecture cloud Hostinger + PWA + avatar HUD + personnalité majordome — avec Anto (PAI)*

---

## 14. État de session — 14 mai 2026 (fin de journée)

### ✅ Ce qui est livré

**Backend Python `jarvis-core` (intégralement fonctionnel) :**
- Architecture hexagonale `domain / policy / core / handlers / mocks / audit`
- 24 types métier dans `domain/types.py` + 3 Protocols dans `domain/protocols.py`
- `policy/engine.py` avec 3 niveaux + élévation contextuelle (nuit, répétition, confiance)
- `core/orchestrator.py` : pipeline complet `Intent → Policy → Confirmation → Execute → Audit`
- `audit/store.py` : SQLite WAL + chaîne HMAC SHA-256 vérifiable
- `mocks/tahoma_mock.py` : 13 devices simulés
- `handlers/tahoma.py` : handler réel avec garde-fou `ALLOW_REAL_DEVICES` (refuse instanciation sans 2 variables explicites)
- `core/intent_engine_local.py` : NLU fuzzy matching, 0 API, latence < 5 ms
- `core/voice.py` : façade TTS multi-backend (Edge-TTS / ElevenLabs / OpenAI), voix Andrew par défaut
- `core/stt.py` : Whisper local (modèle small chargé)

**Sécurité :**
- `.env` strict, `.gitignore` exclut secrets
- Mode mock par défaut (impossible d'activer production sans `EXECUTION_MODE=production` + `ALLOW_REAL_DEVICES=true`)
- 8 garde-fous codifiés (auth, confirmation, PIN, heures restreintes, rate limit, kill switch, audit log, MOCK obligatoire jury)

**Tests qui passent :**
- Pipeline mock complet : 5/5 scénarios (safe / sensible / confirmation / critique / élévation nuit)
- Intent local synonymes : 10/10 phrases (rideau↔volet, barrière↔portail, Joris↔Jarvis)
- Handler TaHoma réel : 5/5 (garde-fou + connexion + 17 devices + commande)
- Audit chain HMAC : 16 événements signés vérifiés intègres
- Latence E2E mock : 3 ms moyenne après optimisations (×340 plus rapide qu'initial 1017 ms)

**Validation physique :**
- Volet buanderie ouvert et fermé en vrai via `demo_volet_buanderie.py` (testé devant Brice en visio)

**Workflow n8n :**
- `Jarvis - Command Bridge` ID `lWH7699zkSGpCqFj` actif sur creatorweb.fr DEV
- Auth Bearer Token (HMAC reporté car `require('crypto')` bloqué par sandbox n8n)
- 3 tests OK : sans token → 401, avec bon token → 200, token invalide → 401
- Token : `<N8N_TOKEN>` (dans `.env` Jarvis sous `JARVIS_N8N_TOKEN`)
- Exporté dans `n8n-workflows/jarvis-command-bridge.json` + README d'import

**Documentation :**
- `README.md` principal (273 lignes) : démo, quick start mock, architecture, sécurité, stack, exemples, tests, planning
- `ARCHITECTURE.md` (290 lignes) : technique complet, schémas, flux, hexagonal, sécurité 5 couches, machine à état, audit HMAC, perfs
- `n8n-workflows/README.md` : doc d'import + curl examples

**Devices identifiés :**
- TaHoma Switch IP `192.168.1.69`, PIN box `<PIN_BOX>`, 17 devices (8 volets, portail, garage, store, 2 zones alarme, 1 lampe RTS)
- Freebox Delta IP `192.168.1.254` (audio Devialet 6 HP intégré, pas de Phantom séparé)
- Micro PC : casque G535 utilisable, mais Whisper capte faiblement → gain logiciel ×100 nécessaire

**Voix Jarvis :**
- Backend par défaut : Edge-TTS (gratuit illimité)
- Voice ID : `en-US-AndrewMultilingualNeural` (US Multilingual qui parle français correctement)
- Validé par Denis le 14 mai

### 🚧 Ce qui reste

**Phase B — Front Hostinger (à faire en S2)**
- B1. Squelette Next.js `jarvis-cloud` + déploiement Hostinger
- B2. Landing page produit
- B3. PWA mobile installable (micro + interface)
- B4. Dashboard temps réel (lit audit SQLite via API)
- B5. Avatar HUD Iron Man Canvas + lip-sync

**Phase C — Pont cloud (S2)**
- C1. Cloudflare Tunnel sur PC Denis
- C2. Workflow n8n forward vers tunnel (au lieu du mock)

**Phase D — Vidéo + soumission (S3, 26 mai - 4 juin)**
- D1. Script vidéo Loom 5 min
- D2. Tournage plan séquence
- D3. Tutoriel vidéo explicatif
- D4. Soumission formulaire 4 juin avant minuit

**Phase E — Bonus si temps**
- Wake word "Jarvis" + conversation 2 tours ("Oui Monsieur" + commande)
- Vision ALPR caméra
- Migration éventuelle Raspberry Pi pour 24/7

### 🎯 Atelier critique à ne pas rater
- **Lundi 18 mai** : Atelier Jarvis + hardware avec Tom (Creator Academy)

### À la prochaine session
**Anto demandera à Denis de vérifier `README.md` et `ARCHITECTURE.md` avant d'attaquer la Phase B.**

> ⚠️ **Mise à jour 17 mai 2026** : avant d'attaquer la Phase B, l'architecture a pivoté vers un modèle **orchestrateur LLM + sous-agents**. Voir §15 pour le cadrage V1/V2, les décisions techniques actées et l'impact sur la suite des travaux.

---

## 15. Pivot architectural — 17 mai 2026 : Orchestrateur multi-agents

### 15.1 Décision

Jarvis devient un **agent IA orchestrateur** qui délègue à des **sous-agents spécialisés** (un par domaine fonctionnel). Le moteur monolithique `core/orchestrator.py` actuel (Intent Engine fuzzy → Handlers Python) est conservé comme **fast-path local**, et une **couche orchestrateur LLM** s'ajoute au-dessus pour gérer les commandes ambiguës, composites ou hors table.

**Argument structurant (Denis) :** extensibilité. Ajouter un nouveau domaine (caméras, mail, appels…) = créer un sous-agent + le déclarer dans le registre orchestrateur. Aucune modification du cœur.

### 15.2 Cadrage V1 vs V2

| Périmètre | Sous-agents | Quand |
|---|---|---|
| **V1 (hackathon — avant Loom 4 juin)** | TaHoma + Devialet + Agenda | Cette session + Phase B |
| **V2 (post-démo)** | Caméras + Appels téléphoniques + Mail + reste | Après soumission 4 juin |

### 15.3 Modèle de sous-agent retenu

**Option A — Tools function-calling** (validée 17/05) :
- Un seul LLM orchestrateur (Claude) avec des **outils typés** par sous-agent
- Chaque sous-agent expose ses tools dans un registre : `tahoma.close_shutter`, `devialet.play_zone`, `agenda.create_event`…
- L'orchestrateur compose les appels en function-calling (1 appel LLM par commande, multi-tool calls possibles)
- Pas de sous-agents IA autonomes pour la V1 (réservé V2 si un domaine en bénéficie vraiment — ex. tri d'un fil mail long)

**Pourquoi pas vrais sous-agents IA autonomes en V1 :**
- Coût : 2+ appels LLM par commande au lieu de 1
- Complexité : loop tool-use imbriquée, debugging plus lourd
- Bénéfice marginal pour TaHoma/Devialet (déterministes)

### 15.4 Stack technique — décisions actées

| Composant | Choix | Raison |
|---|---|---|
| **LLM orchestrateur** | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Latence ~500 ms, coût ~$0.001/commande, suffisant pour routage + composition. Fallback Sonnet 4.6 si Haiku se trompe sur du multi-tool complexe. |
| **Sous-agent Agenda** | Google Calendar API (OAuth déjà existant — réutilisé du projet Creation Devis) | Zéro friction, OAuth Service Account déjà fonctionnel |
| **Intent Engine local** | **Conservé** en fast-path | Match fuzzy en < 5 ms sur les ~10 commandes ultra-fréquentes (volet buanderie, etc.) → zéro appel LLM, zéro coût. Bypass orchestrateur si match confiance > 0.85. |
| **Policy Engine + Audit HMAC** | **Frontière dure inchangée** | Le LLM orchestrateur ne peut PAS franchir la barrière sécurité. Il propose une `DeviceCommand`, le Policy Engine valide, l'Audit log avant/après. Le LLM n'est jamais une preuve d'identité ni un PIN. |
| **Mode mock jury** | Sous-agents mockés (tools mockés) | Au lieu de mocker les handlers, on mocke les sous-agents : même Protocol, comportement identique pour le jury. |

### 15.5 Structure cible `jarvis-core` (V1)

```
jarvis-core/
├─ domain/                      (inchangé : types, protocols)
├─ policy/                      (inchangé : 3 niveaux + élévation contextuelle)
├─ audit/                       (inchangé : HMAC SQLite)
├─ core/
│   ├─ orchestrator.py          (refactoré : route fast-path local OU LLM orchestrateur)
│   ├─ intent_engine_local.py   (inchangé : fast-path fuzzy)
│   └─ voice.py                 (inchangé)
├─ orchestrator/                ← NOUVEAU
│   ├─ llm_client.py            (client Claude Haiku 4.5 + prompts système majordome)
│   ├─ registry.py              (déclare les sous-agents disponibles et leurs tools)
│   └─ tool_router.py           (function-calling → DeviceCommand typée → policy.check → execute)
├─ subagents/                   ← NOUVEAU
│   ├─ base.py                  (Protocol SubAgent : metadata, tools exposés, niveau policy par défaut)
│   ├─ tahoma_agent.py          (tools : list_devices, open_shutter, close_shutter, set_position, open_gate, open_garage, set_alarm…)
│   ├─ devialet_agent.py        (tools : play_zone, set_volume, stop, set_source, mute…)
│   └─ agenda_agent.py          (tools : list_events_today, list_events_tomorrow, create_event, find_slot, delete_event…)
├─ handlers/                    (compat : code TaHoma réel préservé, appelé par tahoma_agent.py)
├─ mocks/                       (mocks par sous-agent désormais)
└─ tests/                       (10/10 actuels gardés + tests par sous-agent)
```

### 15.6 Flux d'une commande V1 (avec orchestrateur)

```
1. Audio PWA → Hostinger → n8n → Cloudflare Tunnel → FastAPI local
2. Whisper STT → texte
3. core/orchestrator.py évalue :
   ├─ FAST-PATH : intent_engine_local.match(text, threshold=0.85)
   │   └─ Match → DeviceCommand directe → goto 5
   └─ SLOW-PATH : LLM orchestrateur (Claude Haiku 4.5)
       ├─ Prompt système : personnalité majordome + registre des tools
       ├─ Claude génère 1+ tool_calls (ex : tahoma.close_shutter + devialet.play_zone)
       └─ Pour chaque tool_call : tool_router résout → DeviceCommand typée
4. Pour chaque DeviceCommand :
   a. policy.check() → safe/sensible/critique + élévation contextuelle
   b. Si confirmation requise → état PendingConfirmation (inchangé)
   c. audit.log("command_requested" + "policy_evaluated")
5. SubAgent.execute(DeviceCommand) → handler réel ou mock
6. audit.log("command_dispatched" + "command_succeeded")
7. Réponse vocale "speak-first" (Edge-TTS Andrew) → PWA
```

### 15.7 Impact sur le planning

| Phase | Avant pivot | Après pivot |
|---|---|---|
| **Phase B (front Hostinger)** | Inchangée | Inchangée — on peut paralléliser |
| **Phase C (Cloudflare Tunnel)** | Inchangée | Inchangée |
| **Phase D (Loom + soumission)** | 5 scènes domotiques | 5 scènes domotiques **+** démonstration de la composition (ex. "Mode cinéma" = 1 commande → ferme volets salon + lance Freebox + Devialet volume max, orchestré par 1 seul appel LLM multi-tool) |
| **Sprint orchestrateur** | — | **2-3 jours de dev** (registry + llm_client + tool_router + 3 sous-agents) en parallèle de la Phase B |

### 15.8 Bénéfices revendiqués face au jury

1. **Extensibilité native** : démontrable en live (ajout d'un sous-agent dummy en 30 secondes pendant la démo)
2. **Composition langage naturel** : "Jarvis, mode cinéma" → 3 actions orchestrées sans hard-coding de la scène
3. **Architecture industrialisable** : pattern réutilisable pour n'importe quel domaine (vraie revendabilité produit)
4. **Sécurité préservée** : Policy + Audit restent au-dessus du LLM — démontrable (un prompt injection ne peut pas faire ouvrir le portail la nuit)

### 15.9 Sécurité — invariants maintenus

La règle absolue du projet (§9) reste intégralement valide :
- Auth obligatoire PWA ✅ inchangé
- 3 niveaux + élévation contextuelle ✅ inchangé (Policy Engine au-dessus du LLM)
- PIN vocal critique ✅ inchangé
- Heures restreintes ✅ inchangé
- Rate limiting ✅ inchangé (à appliquer au niveau orchestrateur ET au niveau LLM API)
- Kill switch ✅ inchangé
- Audit log HMAC ✅ inchangé (audit chaque tool_call individuellement)
- MOCK obligatoire jury ✅ inchangé (sous-agents mockés)

**Nouveau garde-fou ajouté :** validation stricte des outputs LLM. L'orchestrateur ne fait JAMAIS confiance à un `device_id` ou `action` retourné par le LLM sans le vérifier contre le registre des sous-agents. Toute hallucination → rejet + audit log + réponse majordome "Je crains de ne pas pouvoir interpréter cette demande, Monsieur."

### 15.10 V2 — Roadmap post-Loom

| Sous-agent V2 | Modèle pressenti | Effort estimé |
|---|---|---|
| **Caméras + ALPR** | Tool function-calling (déterministe) | 2 jours |
| **Mail (Gmail)** | Vrai sous-agent IA (tri + résumé fil long → besoin raisonnement) | 3 jours |
| **Appels téléphoniques** | Vrai sous-agent IA (transcription + classification) | 3 jours |
| **Freebox / TV** | Tool function-calling | 1 jour |
| **Lemlist (stats prospection)** | Tool function-calling | 0.5 jour |

---

*Pivot architectural acté le 17 mai 2026 — avec Anto (PAI). Decision Denis : orchestrateur LLM + sous-agents, modèle Option A (function-calling), V1 = TaHoma + Devialet + Agenda, V2 post-démo = caméras + appels + mail + reste.*

---

## 16. Modèle commercial — Hardware par client (17 mai 2026)

### 16.1 Position d'hébergement du backend

Le backend Python `jarvis-core` doit physiquement tourner **sur le LAN du client** pour atteindre ses devices domotiques (TaHoma `192.168.1.x`, Freebox, Devialet). C'est une contrainte réseau dure, pas un choix logiciel.

### 16.2 Hébergement selon la box Internet du client

| Profil client | Hébergement recommandé | Coût matériel | Tunnel sortant |
|---|---|---|---|
| **Client Free Delta** (comme Denis) | VM intégrée à la Freebox | **0 €** (déjà chez lui) | Non requis (Freebox a une IP publique + redirection de port intégrée) |
| **Client Free Ultra** | VM intégrée | 0 € | Non requis |
| **Client Free Pop** | VM intégrée si activée + disque | 0-50 € (disque éventuel) | Non requis |
| **Client Free Révolution** | Pas de VM | Pi 5 dédié | ~120-180 € kit complet |
| **Client Orange / Bouygues / SFR / Sosh** | Box sans VM hôte | Pi 5 dédié | Tailscale Funnel ou autre tunnel |
| **Client autre opérateur** | Pi 5 dédié | ~120-180 € kit complet | Tailscale Funnel |

### 16.3 Argument commercial

**Offre Jarvis Premium** :
- Setup Freebox Delta/Ultra (clients Free haut de gamme) : **inclus dans le forfait** (0 € hardware additionnel)
- Setup autre box : **+120 à 180 €** de Pi 5 + accessoires (carte microSD/SSD, alimentation, boîtier) facturés en supplément
- Service d'installation et de configuration : facturé séparément (forfait setup)

### 16.4 Pourquoi ce modèle est défendable

- **Pas de surcoût caché** : si le client a déjà une Freebox compatible, il n'achète rien
- **Solution pérenne** : un Pi 5 dure 5+ ans, consomme 5 W, coût électrique négligeable (~3 €/an)
- **Marge sur le hardware** : le Pi 5 peut être revendu avec une marge raisonnable + l'installation
- **Pas de dépendance fournisseur** : pas besoin de tunnel cloud payant (Cloudflare Enterprise, etc.)

### 16.5 Implication produit

L'image VM/Pi qu'on prépare doit être **identique** dans les deux cas. Le client final ne voit pas la différence — il a juste une box (Freebox ou Pi) qui héberge Jarvis sur son LAN, accessible depuis Internet par la PWA mobile.

---

*Modèle commercial hardware acté le 17 mai 2026.*
