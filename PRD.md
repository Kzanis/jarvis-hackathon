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
- **5 scènes enchaînées** : Bonjour → Mes mails urgents → Mode cinéma → Ouvre le portail (à la voix) → Bonne nuit

> ℹ️ Décision 29/05 : l'ouverture du portail en démo se fait **à la voix** (fiable, validé le 25/05). La **reconnaissance de plaque** (caméra → portail auto) reste une promesse **V2** (cf. §5.6 et §15.2), pas dans le Loom — chaîne caméra/ALPR jugée trop risquée pour un plan séquence.

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
- Volet buanderie ouvert et fermé en vrai via `demo_volet_buanderie.py`

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

---

## 17. Déploiement réel — 17 mai 2026 (verrou stratégique levé)

### 17.1 Ce qui a été déployé

**Jarvis tourne désormais 24/7 sur la Freebox Delta de Denis**, accessible depuis Internet via une URL publique fixe. Le critère de succès « le cerveau peut être appelé depuis Internet de manière fiable » (Codex dual-review 17/05) est ATTEINT.

### 17.2 Architecture déployée (réelle)

```
Internet
   │
   │ HTTPS
   ▼
n8n Hostinger (creatorweb.fr/webhook/jarvis-command)
   │ Bearer Token auth
   │ HTTP POST forward
   ▼
Freebox Delta IP publique <IP_PUBLIQUE>:48765 (TCP NAT)
   │ Redirection port Free → LAN
   ▼
VM Ubuntu 22.04 ARM64 sur Freebox (1024 Mo RAM, 2 CPU, 22 Go disque)
   │ 192.168.1.142:8765
   ▼
FastAPI Jarvis (service systemd, restart auto au boot)
   ├─ CommandRouter
   ├─ LLMOrchestrator → Claude Haiku 4.5 via OpenRouter (URL fixe gratuit)
   ├─ ToolRouter (validation JSON Schema + budgets)
   ├─ Sous-agents TaHoma + Devialet + Agenda (mode mock V1)
   └─ Audit HMAC SQLite
   │
   ▼ LAN 192.168.1.x (futur)
TaHoma Switch 192.168.1.69 (réel, mode production à activer ultérieurement)
```

### 17.3 Spécificités Free / Freebox identifiées (à connaître pour install client)

| Règle | Conséquence |
|---|---|
| **Freebox réserve ports ≤ 32768** | Choisir port externe NAT entre 32769 et 65535 obligatoirement (ex. 48765 retenu pour Jarvis) |
| **Champ IP source obligatoire** dans redirection | Choisir « Toutes » dans menu déroulant (= 0.0.0.0/0) pour accès Internet entier |
| **VM ARM64 cloud-image ≠ growroot** | L'auto-resize partition n'est PAS actif → `growpart /dev/vda 1` + `resize2fs /dev/vda1` manuels après agrandissement disque côté Freebox |
| **Disque VM par défaut 2 Go** | Agrandir à minimum 20 Go pour install Python + venv + dépendances (compter ~12 Go utilisés) |
| **RAM max VM Delta** | 1024 Mo alloués (= 957 par défaut, peut monter à 1024). Système Free réserve ~67 Mo. |

### 17.4 URLs et points d'entrée stables

| Service | URL / Endpoint |
|---|---|
| **Webhook public n8n** (entrée principale, à utiliser par la PWA Phase B) | `https://creatorweb.fr/webhook/jarvis-command` |
| **Backend direct (debug/admin)** | `http://<IP_PUBLIQUE>:48765/healthz` |
| **Backend pipeline texte** | `http://<IP_PUBLIQUE>:48765/intent/text` |
| **Backend pipeline audio** | `http://<IP_PUBLIQUE>:48765/intent/audio` |
| **SSH admin VM** | `ssh denis@192.168.1.142` (LAN uniquement) |
| **Repo GitHub privé** | `Kzanis/majordome-hackathon` |

### 17.5 Métriques mesurées (test E2E réel 17/05)

| Métrique | Valeur |
|---|---|
| Latence LLM (Claude Haiku 4.5 via OpenRouter) | 1.5 à 3.5 s |
| Latence pipeline NAT + LAN | < 100 ms |
| Latence exécution mock | 20-60 ms par tool |
| Latence totale perçue | 2-4 s |
| Consommation RAM service Jarvis | 49 Mo (49% buffer disponible) |
| Tokens / commande simple | ~4500 in / 80 out |
| Tokens / commande composée | ~4500 in / 200 out |
| Coût par commande (OpenRouter) | ~$0.005 |

### 17.6 Reproductibilité install client (artefacts versionnés dans le repo)

- `vm-freebox/ubuntu-22.04-server-cloudimg-arm64.img` (image officielle Canonical, .gitignored)
- `vm-freebox/user-data.yaml` (config cloud-init avec utilisateur + paquets + service systemd)
- `vm-freebox/seed.iso` (CD-ROM cloud-init à attacher à la VM, .gitignored)
- `vm-freebox/make_seed_iso.py` (régénère seed.iso depuis user-data.yaml)
- `requirements.txt` (dépendances Python complètes avec openai, python-multipart, edge-tts ajoutés)

### 17.7 Ce qui reste à faire (sem.2-3)

- **Phase B — Front Hostinger** : projet Next.js `jarvis-cloud`, PWA installable, MicButton, Avatar HUD Canvas 2D
- **Phase D — Vidéo Loom** : script + tournage plan-séquence + soumission 4 juin
- **Activation mode production** : `EXECUTION_MODE=production` + `ALLOW_REAL_DEVICES=true` dans `.env` VM, **uniquement à la fin pour la démo Loom**, pour ne pas bouger les volets réels pendant les tests
- **Migration Raspberry Pi (post-démo) ou client non-Free** : kit ~120 € selon §16

### 17.8 Sécurité — invariants maintenus

- ✅ Bearer Token Jarvis (`<N8N_TOKEN>`) appliqué côté n8n et passable côté backend (variable `JARVIS_HTTP_TOKEN` du `.env` VM)
- ✅ Audit HMAC SQLite intact sur la VM (`/opt/jarvis/jarvis-core/data/audit.db`)
- ✅ Mode mock par défaut (impossible d'activer prod sans 2 variables env explicites)
- ✅ `.env` jamais commité (`.gitignore` strict + sécurité hook PAI)
- ✅ Sous-agents allowlistés via Registry (hallucinations LLM rejetées avant exécution)
- ✅ Budgets de commandes par requête (max 5 totales / 1 critique / 3 sensibles)

---

*Déploiement effectif acté le 17 mai 2026. Jarvis répond depuis Internet, hébergé sur la Freebox Delta de Denis sans matériel additionnel. Verrou stratégique du projet (Codex dual-review du matin) sauté.*

---

## 18. Sous-agent Search — Recherche externe Web (V2 post-démo)

### 18.1 Cas d'usage

Donner à Jarvis la capacité de **chercher des informations sur Internet en temps réel** pour répondre aux questions qui sortent de son champ domotique/agenda :

- Denis : *« Tu connais Bruce Springsteen ? »* → Jarvis : *« Naturellement Monsieur, l'icône du rock américain, né le 23 septembre 1949 dans le New Jersey. Il a publié 21 albums studio, le plus récent « Only the Strong Survive » en 2022. »*
- Denis : *« Qui a gagné Roland Garros cette année ? »*
- Denis : *« Quel est le tarif d'un Macbook Pro M4 ? »*
- Denis : *« Donne-moi les actualités du jour »*
- Denis : *« Quel temps va-t-il faire demain à Paris ? »*

### 18.2 Choix du fournisseur

| Fournisseur | Pour | Contre | Coût |
|---|---|---|---|
| **Perplexity API** (sonar-pro) | Web search + citations, réponse synthétique, modèle qui sait quand chercher | Coût $5/M tokens output | ~$0.005-0.02/requête |
| Anthropic Web Search Tool (natif) | Intégration directe Claude, pas de second SDK | Coût Anthropic standard | Inclus dans Haiku/Sonnet |
| Tavily | Recherche pure, JSON brut à reformuler | Pas de synthèse, à recoller dans le LLM | $0.005/requête |
| Brave Search API | Résultats bruts | Idem Tavily | Plan gratuit limité |

**Reco V2 : Perplexity API (sonar-pro)** — qualité de synthèse, citations vérifiables, simplicité d'intégration. Coût négligeable à l'usage perso (~$5/mois maximum).

**Alternative défensive** : si Perplexity indisponible, basculer sur **Anthropic Web Search Tool** natif Claude (ajouté à la session tool_use existante, zéro infra supplémentaire).

### 18.3 Architecture (cohérente avec §15)

Nouveau sous-agent `subagents/search_agent.py` :

```
subagents/
├─ search_agent.py    ← V2
│   ├─ tools : search_web, get_news, get_weather
│   └─ execute : appelle Perplexity API
```

ToolSpec attendus :

| Tool | Description | Sensibilité |
|---|---|---|
| `search_web` | Recherche libre sur un sujet (personnes, faits, définitions, actualités) | safe |
| `get_weather` | Météo pour une ville donnée | safe |
| `get_news` | Actualités du jour (filtre catégorie : générale, sport, tech, BTP…) | safe |

### 18.4 Intégration LLM orchestrateur

Le LLM Claude Haiku 4.5 décide automatiquement quand appeler `search_web` :

- Question factuelle externe (« Qui est X ? », « Quel est le prix de Y ? ») → tool_call `search_web`
- Commande domotique (volet/portail/musique) → sous-agent existant
- Le LLM peut **combiner** : *« Mets de la musique de Bruce Springsteen »* → search Bruce Springsteen (récupérer top albums) → devialet/play_zone avec hint

### 18.5 Sécurité

Le sous-agent Search ne fait que **lire** Internet, jamais écrire. Niveau `safe` partout :
- Pas de confirmation orale requise
- Pas d'élévation contextuelle
- Logs Audit standard (URL recherchée + résumé reçu)
- Pas de stockage des réponses au-delà de la session conversationnelle (privacy)

### 18.6 Effort estimé

- Création `search_agent.py` (~120 lignes) : 30 min
- Tests unitaires + intégration au registry : 30 min
- Variables d'env (`PERPLEXITY_API_KEY`) + .env.example : 5 min
- Démo bout-en-bout PWA → search → réponse synthétisée : 30 min
- **Total V2 : 1h30 à 2h.**

### 18.7 Variables d'env à ajouter

```bash
# Sous-agent Search — V2
PERPLEXITY_API_KEY=pplx-...
SEARCH_PROVIDER=perplexity            # perplexity | anthropic_web_search | tavily
SEARCH_MAX_RESULTS=5
SEARCH_TIMEOUT_SECONDS=10
```

### 18.8 Roadmap V2 mise à jour

| Sous-agent V2 | Effort | Priorité ordre |
|---|---|---|
| **Search Web (Perplexity)** | 1h30 | ⭐ 1 — demande Denis 17/05 |
| Caméras + ALPR | 2j | 2 |
| Mail Gmail (vrai sous-agent IA) | 3j | 3 |
| Appels téléphoniques | 3j | 4 |
| Freebox / TV | 1j | 5 |
| Lemlist stats | 0.5j | 6 |

---

*Search Web ajouté au plan V2 le 17 mai 2026 (demande Denis : « tu connais Bruce Springsteen »).*

---

## 19. Bugs identifiés en production — 17 mai 2026 (à corriger en priorité)

Liste des anomalies remontées par Denis après tests en conditions réelles. **À traiter en première priorité à la prochaine session** avant tout ajout de feature.

### 19.1 TaHoma — fermeture du garage ne fonctionne pas

**Symptôme :** Denis dit « Ferme la porte du garage » → Jarvis répond mais l'action ne s'exécute pas (ou exécution silencieuse sans effet physique).

**⚠️ Hypothèse initiale INVALIDÉE le 21/05 (voir §19.6).** Le diagnostic du catalogue Somfy montre que le device `porte garage` (`io://<PIN_BOX>/881454`) expose bien la commande `close` (28 commandes au total : `open`, `close`, `stop`, `setClosure`, `up`, `down`...). Le mapping `_COMMAND_MAP` était donc correct. Voir §19.6 pour la nouvelle piste.

### 19.2 TaHoma — ouverture du portail ne fonctionne pas

**Symptôme :** Denis dit « Ouvre le portail » → Jarvis confirme + tente d'exécuter → portail ne bouge pas.

**⚠️ Hypothèse initiale INVALIDÉE le 21/05 (voir §19.6).** Le `PORTAIL` (`rts://<PIN_BOX>/16471272`, protocole RTS) expose bien `open`, `close`, `stop`, `up`, `down`. Le mapping est correct. Particularité RTS : protocole **unidirectionnel** (la box envoie le signal radio sans feedback hardware possible). Voir §19.6 pour le diagnostic du 21/05.

### 19.3 PWA — Mode mains libres (wake word « Jarvis ») non fonctionnel correctement

**Symptôme :** activation du toggle « Mains libres » → comportement instable :
- Wake word pas détecté de manière fiable
- Coupures inattendues côté Safari iOS
- Feedback acoustique possible (à investiguer)

**Hypothèses :**
- Web Speech `continuous: true` mal supporté sur iOS (limite ~30-60s)
- Mon auto-restart sur `onend` ne couvre pas tous les cas d'erreur Safari
- Regex de wake word trop stricte ou trop laxe
- L'anti-feedback (pause pendant TTS) ne se déclenche peut-être pas assez tôt

**À investiguer :**
- Tester sur Android Chrome vs Safari iOS et comparer
- Logger les events `onerror` / `onend` pour comprendre les coupures iOS
- Évaluer alternative WASM (Porcupine ou OpenWakeWord) qui ne dépend pas de Web Speech
- Ajouter un indicateur visuel quand la reco est effectivement active

### 19.4 Priorité de correction (prochaine session)

| # | Bug | Impact | Priorité |
|---|---|---|---|
| 1 | TaHoma close_garage (§19.1) | Démo critique — il faut le mouvement bidirectionnel | ⭐ P0 |
| 2 | TaHoma open_gate (§19.2) | Démo critique — scène « portail » indispensable | ⭐ P0 |
| 3 | Mains libres PWA (§19.3) | Feature bonus (PRD §13 Phase E), pas bloquant démo | P2 |

### 19.5 Méthodologie à appliquer

Avant tout autre fix, **inspecter le catalogue Somfy en prod** (commande `list_devices` du sous-agent TaHoma) et noter pour chaque device sa liste de `commandName` exposés. Construire alors un mapping `device_type → action → commandName` propre dans `tahoma_agent.py`.

Tester ensuite chaque correctif **device par device** avant de passer au suivant. Pas de regression sur les volets qui fonctionnent (validés 14/05 sur volet buanderie et confirmés 17/05).

### 19.6 Diagnostic 21/05 — résultats du test live sur la VM

**Méthodo §19.5 appliquée.** Inspection du dump `config/tahoma_devices_raw.json` :

| Device | URL | Protocole | Commandes exposées (extraits) |
|---|---|---|---|
| `porte garage` | `io://<PIN_BOX>/881454` | IO Home Control (bidirectionnel) | `open`, `close`, `stop`, `setClosure`, `up`, `down`, +22 autres |
| `PORTAIL` | `rts://<PIN_BOX>/16471272` | RTS (unidirectionnel) | `open`, `close`, `stop`, `up`, `down`, `test`, `rest`, `openConfiguration`, `identify` |

→ **Les commandes `open` et `close` sont bien exposées par les 2 devices.** L'hypothèse §19.1/§19.2 initiale est invalidée.

**Test exécution live (script `scripts/diag_tahoma_exec.py` créé)** :

```
TEST 1 — PORTAIL command=open
  HTTP 200, execId=3dba70a3-e7a6-463c-a950-7022693217c6
  Poll /exec/current/{execId} → body=null instantanément (RTS = pas de feedback)

TEST 2 — porte garage command=close
  HTTP 200, execId=3855d818-3a2b-47fa-8586-d01c13c1af04
  Poll /exec/current/{execId} → body=null en moins de 500ms (anormal pour IO)
  /history/executions → HTTP 400 (mauvais endpoint, à corriger)
```

**Observations** :
- La box Somfy **accepte les 2 commandes** sans erreur HTTP
- Pour le PORTAIL (RTS) : silence du polling **attendu** (le radio unidirectionnel ne renvoie pas de feedback)
- Pour le GARAGE (IO) : silence **anormal** — on devrait voir `INITIALIZED → IN_PROGRESS → COMPLETED` mais l'execId disparaît immédiatement du `/exec/current`. Soit la commande est rejetée silencieusement par la box, soit l'API Overkiz purge trop vite, soit l'endpoint d'historique est différent (réponse 400)

**Question physique en attente de réponse Denis (chiens dehors au moment du diag, à reprendre quand les chiens sont rentrés)** :
- 🚪 Le portail a-t-il **bougé physiquement** quand la commande `open` est partie ?
- 🏠 La porte de garage a-t-elle **bougé physiquement** quand la commande `close` est partie ?

**Hypothèses restantes selon réponse Denis** :

| Réponse Denis | Diagnostic | Fix |
|---|---|---|
| **Oui les 2 ont bougé** | Bug Jarvis = on prend déjà le HTTP 200 pour succès mais notre policy/audit ne le verbalise pas correctement, ou l'orchestrateur LLM ne route pas le bon tool | Vérifier orchestrator → tahoma_agent → handler côté logs systemd |
| **Aucun n'a bougé** | RTS portail : moteur désappairé / hors portée / batterie / bus radio saturé. Garage IO : commande rejetée silencieusement → tester `setClosure 100` à la place | Tests hardware Somfy + alternative `setClosure` pour garage |
| **Portail oui, garage non** | RTS marche, IO garage a un souci spécifique → tester `setClosure 100` puis `stop` puis `close` séparés | Mapping garage spécifique |
| **Portail non, garage oui** | Cas le plus probable (RTS fragile) → check télécommande Somfy, refaire un test à 1m du portail | Hardware |

**Patch handler à prévoir indépendamment des résultats** :
- `handlers/tahoma.py` ligne 197 : ajouter polling `/exec/current/{execId}` pour les devices IO (avec timeout court 2s) afin de remonter le **vrai** statut d'exécution
- Renvoyer `ExecutionStatus.failure` si l'execId termine sur état `FAILED` ou `CANCELLED`
- Pour RTS : conserver le comportement actuel (pas de feedback possible par design)

**À reprendre à la prochaine session** : confirmation physique Denis sur portail + garage → application des fix correspondants → re-test.

---

*Bugs production remontés par Denis le 17 mai 2026. P0 = à corriger en priorité absolue à la reprise. Diagnostic 21/05 documenté §19.6, attente confirmation physique Denis.*

---

## 20. Récap session 17 mai 2026 (J-18 du 4 juin)

**Une journée. Tout le projet est passé du « squelette backend mock validé 14/05 » à « système complet en ligne, accessible depuis Internet, voix Andrew, sécurité OWASP-conforme, démonstrable en direct ».** Voici le journal complet pour la prochaine reprise.

### 20.1 Ce qui a été livré

**Pivot architectural (PRD §15)** :
- Acté le modèle orchestrateur LLM + sous-agents (Option A : function-calling)
- Dual-review Codex obtenu (GO-AVEC-CONDITIONS)
- ROADMAP.md créé puis nettoyé des références passives (ateliers Academy retirés)

**Backend Python `jarvis-core` (Freebox VM Ubuntu 22.04 ARM64)** :
- 3 sous-agents complets : Tahoma (13 tools, mode production actif), Devialet (5 tools, mock V1), Agenda (5 tools, mock V1)
- ToolRouter : validation JSON Schema maison, budgets (5 total / 1 critique / 3 sensibles), rejet hallucinations
- LLMOrchestrator multi-provider (OpenRouter primaire → Claude Haiku 4.5, fallback Sonnet 4.6 / Anthropic / OpenAI)
- ConversationSession multi-tours (TTL 90s) + état `pending` confirmation orale
- CommandRouter unifié + audit HMAC SQLite signé
- FastAPI : `/healthz`, `/intent/text` (avec mp3 Andrew base64 inline), `/intent/audio`, `/intent/audio_full`, `/auth/login`, `/auth/logout`, `/session/state`, `/session/reset`
- Service systemd `jarvis.service` actif 24/7 (auto-restart)
- Contexte temporel Europe/Paris injecté à chaque appel LLM
- 6/6 tests pytest verts

**Infrastructure** :
- Repo GitHub privé `Kzanis/majordome-hackathon`
- VM Ubuntu sur Freebox Delta : 1024 Mo RAM, 2 CPU, 22 Go disque (agrandi depuis 2 Go via growpart manuel)
- Cloud-init + seed.iso pour reproductibilité
- Service systemd jarvis (PID stable, ~50 Mo RAM)
- Sous-domaine `jarvis.creatorsystemia.fr` + SSL Lifetime Hostinger (créé via API)
- Redirection port Freebox 48765 → 192.168.1.142:8765 (règle Free : ports externes > 32768)
- PWA Next.js 16 statique déployée sur Hostinger (~/domains/creatorsystemia.fr/public_html/jarvis)

**Pipeline cloud** :
- Workflow n8n `Jarvis - Command Bridge` (lWH7699zkSGpCqFj) : webhook → forward transparent vers VM avec Bearer Token forwardé
- Workflow n8n `Jarvis - Login` (1HLZnQVovXg0dUii) : webhook → forward VM /auth/login → réponse JSON
- Mode production TaHoma activé + validé physiquement (volet buanderie : ferme/ouvre en vrai)

**Voix Jarvis** :
- Edge-TTS Andrew Multilingual Neural intégré dans `/intent/text` (mp3 base64 ~36 Ko/phrase)
- Web Speech Recognition côté PWA (STT navigateur, fallback Web Speech Synthesis si Andrew indispo)
- Wake word "Jarvis" hands-free (V1 livrée mais instable — bug §19.3)

**Personnalité (PRD §5.4 enrichi)** :
- personality.md pince-sans-rire JARVIS Iron Man + ironie élégante (antiphrase / sentence / observation)
- 10 few-shot examples concrets ("Évidemment Monsieur", "Cela va de soi", "Ne modifiera pas mes tarifs")
- Variabilité forcée (jamais 2 fois la même phrase d'affilée)
- Garde-fous (jamais d'ironie sur commande sensible/critique)

**Sécurité (PRD §9 implémenté)** :
- Login user/password : identifiant `denis` + mot de passe défini par Denis dans `.env` VM
- Token de session 4h (in-memory)
- Bearer Token n8n statique RETIRÉ du bundle public PWA (récupéré dynamiquement après login)
- Champ identifiant vide par défaut sur `/login` (pas de fuite d'indice)
- Confirmation orale pour commandes sensibles/critiques (PRD §9.4) implémentée et validée
- Workflow n8n transparent (plus de token partagé entre Hostinger et VM)
- `.env.production` PWA contient uniquement URLs publiques (zéro secret)
- `.gitignore` strict (audit.db, .env, *.mp3, /vm-freebox/* binaires)

**PRD enrichi** :
- §15 : pivot orchestrateur (matin)
- §16 : modèle commercial hardware (Freebox 0€ / Pi 5 120-180€)
- §17 : déploiement réel
- §18 : sous-agent Search Perplexity (V2)
- §19 : bugs production (close_garage, open_gate, mains libres)
- §20 : ce récap

### 20.2 Métriques mesurées

| Métrique | Valeur |
|---|---|
| Latence LLM (Claude Haiku via OpenRouter) | 1.5-3.5 s |
| Latence Edge-TTS Andrew | ~700 ms / phrase |
| Latence pipeline complet PWA → réponse vocale | 2-5 s |
| Latence exécution TaHoma réelle (volet) | ~1.5 s (mécanique 10-15s) |
| RAM service jarvis sur VM | ~50 Mo |
| Tokens / commande simple | 4500 in / 80 out |
| Tokens / commande composite | 4500 in / 200 out |
| Coût / commande (OpenRouter) | ~$0.005 |
| Lignes Python `jarvis-core` ajoutées (session) | ~1800 |
| Lignes TS `jarvis-cloud` ajoutées (session) | ~1100 |
| Commits Git GitHub | 14+ |

### 20.3 Bugs identifiés (PRD §19)

| # | Bug | Priorité |
|---|---|---|
| 1 | TaHoma `close_garage` ne ferme pas la porte | P0 |
| 2 | TaHoma `open_gate` n'ouvre pas le portail | P0 |
| 3 | Mode mains libres instable (Web Speech continuous iOS) | P2 |

### 20.4 État actuel (au 17/05 fin de session)

✅ **Tout en ligne, tout testable depuis le téléphone de Denis :**
- URL PWA : https://jarvis.creatorsystemia.fr/
- Identifiant : `denis`
- Mot de passe : (défini par Denis, dans `.env` VM uniquement)
- Backend : VM Freebox `192.168.1.142:8765` → exposée publique via `<IP_PUBLIQUE>:48765`
- n8n DEV : `creatorweb.fr/webhook/jarvis-command` + `creatorweb.fr/webhook/jarvis-login`

### 20.5 À reprendre à la prochaine session — par ordre de priorité

**🔴 P0 (à attaquer EN PREMIER)**

1. **Fix TaHoma close_garage** (§19.1) : inspecter `commandName` exposé par device `881454` (porte garage) en prod, adapter mapping dans `tahoma_agent.py`
2. **Fix TaHoma open_gate** (§19.2) : idem pour device `16471272` (PORTAIL)

Méthodologie §19.5 : `list_devices` détaillé → noter les `commandName` réels par type de device → construire un mapping `device_type → action → commandName`.

**🟡 P1 (semaine 3 / phase D)**

3. **Rédiger `DEMO_SCRIPT.md`** : 5 scènes pour le Loom plan-séquence (PRD §7.1)
4. **Répétitions Loom** (10+ passes avant tournage)
5. **Backup Loom tourné AVANT 2/06** (critère Codex)

**🟢 P2 (bonus si temps)**

6. Mains libres stable (§19.3)
7. Sous-agent Search Perplexity (§18) — pour répondre "tu connais Bruce Springsteen ?"
8. Lip-sync amplitude réel sur le mp3 Andrew (Web Audio AnalyserNode)
9. Auto-correction Jarvis (§22.4) — Jarvis détecte ses erreurs et se rattrape tout seul
10. Auto-présentation Jarvis (§22.1) — trigger "présente-toi" + réponse Iron Man pince-sans-rire
11. Recherche internet enrichie (§22.2 / extension §18) — DuckDuckGo + fallback Brave + Wikipedia
12. Voix gratuite offline alternative (§22.3) — fallback Piper FR dans la façade voice.py
13. Briefing matinal (§22.5) — veille actu + agenda du jour au "bonjour, Jarvis"

**🏁 Deadline ferme**

- **30/05** : freeze code (PRD §7 + critères Codex)
- **2-3/06** : tournage Loom plan-séquence
- **4/06 minuit** : soumission formulaire Academy

### 20.6 Conseil pour la prochaine session (Anto → Anto futur)

**Avant toute action :**
1. Lire ce §20 du PRD pour le contexte exhaustif
2. Vérifier que la stack est encore opérationnelle : `curl https://jarvis.creatorsystemia.fr/` + `https://creatorweb.fr/webhook/jarvis-command` (avec un token de session valide)
3. Demander à Denis s'il a relu le PRD §17-19 (consigne mémoire)
4. **Attaquer P0 directement** — pas de nouvelles features avant que close_garage et open_gate fonctionnent en prod

---

*Récap session 17/05 acté. Verrou stratégique du projet (Codex matin) sauté. Stack complète en ligne. Reste 2 bugs P0 + Loom à tourner d'ici le 4 juin.*

---

## 21. Feature à venir — Alertes tentatives d'intrusion (demande Denis 17/05)

### 21.1 Demande

Denis veut être **informé en cas de tentatives de connexion suspectes** à la PWA Jarvis :
- Échecs de login répétés (mauvais mot de passe)
- Échecs de PIN sur commande critique
- Tentatives d'appel avec token invalide
- Pic anormal de requêtes depuis une même IP

### 21.2 Comportement attendu

| Événement déclencheur | Action |
|---|---|
| 3 échecs login en 5 min | Notification Denis + lock temporaire IP source 15 min |
| 5 échecs login en 1h | Notification Denis + lock 1h + entrée audit "alerte sécurité" |
| Token invalide envoyé X fois | Notification Denis |
| Login réussi depuis nouvelle IP/zone géographique | Notification info Denis |

### 21.3 Canaux de notification possibles

- **Push notification PWA** (Web Push API + service worker) — natif iOS/Android
- **Email** (via SMTP Hostinger ou Mailgun/Resend gratuit)
- **Telegram bot** (gratuit, instantané, riche)
- **SMS** (via Twilio/OVH — payant)
- **Webhook personnel** (Discord, Slack…)

Reco : démarrer avec **email + Telegram bot** (gratuit, fiable, double canal).

### 21.4 Implémentation côté backend

- Compteur in-memory des échecs par IP source + horodatage
- Table audit SQLite enrichie avec event_type `security_alert`
- Background task qui envoie la notification au déclenchement
- Configuration via env vars : `ALERT_EMAIL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

### 21.5 Priorité

**P2 — Post-démo Loom (V2)**. Pas critique pour le hackathon (4 juin), mais critique pour l'usage quotidien post-démo. À planifier en juin après la soumission.

---

*Demande Denis acté le 17/05/2026 fin de session. Priorité V2.*

---

## 22. Évolutions V2 post-démo — demandes Denis 18/05

### 22.0 Cadre

Lors de la session du 18/05/2026, Denis a évoqué 5 évolutions pour enrichir Jarvis au-delà du périmètre hackathon. **Toutes sont classées P2 — V2 post-démo** afin de préserver la deadline 4 juin et le focus sur les P0 (§19) + Loom (§7.1). À planifier en juin une fois la soumission validée.

### 22.1 Auto-présentation

**Demande** : "J'aimerais que Jarvis puisse se présenter lui-même."

**Comportement attendu** :
- Trigger vocal : "Jarvis, présente-toi" / "qui es-tu" / "c'est quoi Jarvis"
- Réponse parlée dans le ton Iron Man pince-sans-rire (cohérent §15)
- 3 variantes : courte (5s), longue (15s), sarcastique (option contextuelle)

**Implémentation** :
- Fichier `personality.py` (ou enrichir `orchestrator.py`) avec 3 prompts pré-écrits
- Intent classifier détecte le trigger avant de passer aux outils
- TTS via la façade `voice.py` (Andrew Edge-TTS par défaut)

**Coût estimé** : 15 min (prompt + intent + test).

### 22.2 Recherche internet enrichie

**Demande** : "J'aimerais qu'il puisse faire des recherches sur internet."

**Status** : étend / remplace §18 (sous-agent Search Perplexity).

**Stratégie** :
- Architecture inspirée du repo public `isair/jarvis` (license personal use only — **on s'inspire, on ne fork pas**)
- Chaîne de fallback : **DuckDuckGo** (primaire, gratuit, sans clé API) → **Brave Search** (fallback, 2000 req/mois gratuit) → **Wikipedia** (filet de sécurité)
- Module `search.py` ~50 lignes Python avec `duckduckgo-search` (pip)
- Sortie : 3 résultats top + résumé GPT-4 mini pour réponse parlée

**Use case** : "Jarvis, qui est Bruce Springsteen ?", "Jarvis, c'est quoi le score du PSG hier ?"

**Coût estimé** : 4-6h (module + tests + intégration orchestrateur).

### 22.3 Voix gratuite offline — alternative Edge-TTS

**Demande** : "Peut-être qu'il y aurait une voix gratuite dans un repo ?"

**Status** : Edge-TTS Andrew (actuel) reste primaire — qualité ⭐⭐⭐⭐⭐, gratuit illimité Microsoft Neural. L'évolution V2 consiste à ajouter un **fallback offline** pour blinder contre une coupure internet.

**Options évaluées** :

| Option | Qualité FR | Poids | CPU only | Verdict |
|---|---|---|---|---|
| **Edge-TTS Andrew** (actuel) | ⭐⭐⭐⭐⭐ | 0 (cloud) | oui | Garder primaire |
| **Piper TTS FR** | ⭐⭐⭐ | ~60 Mo | oui | Fallback offline OK |
| Kokoro | ⭐⭐⭐⭐⭐ | lourd | GPU recommandé | ❌ VM Freebox |
| Fish Speech | ⭐⭐⭐⭐ | lourd | GPU | ❌ pour démo |

**Reco** : ajouter backend `piper` à la façade `voice.py` existante (déjà multi-backend `edge/elevenlabs/openai`). ~30 lignes + télécharger le modèle FR depuis `tjiho/French-tts-model-piper`.

**Coût estimé** : 1-2h.

### 22.4 Auto-correction — 2 mécaniques distinctes

**Demande initiale (18/05)** : "Notez aussi qu'il s'auto-corrige."
**Précision Denis (21/05)** : "Quand je le reprends, je veux qu'il me demande s'il en fait une règle définitive."

Cette section couvre donc **2 mécaniques complémentaires** :

#### 22.4.A — Auto-correction proactive (Jarvis se rattrape seul)

**Comportement** : Jarvis détecte qu'il a mal compris une commande ou mal exécuté une action, et se rattrape sans qu'on lui redemande.

**Cas d'usage cibles** :
- Erreur de device Somfy : "J'ai fermé le volet salon… ah pardon, vous aviez dit cuisine. Je corrige."
- Mauvaise interprétation intent : reformulation + nouvelle exécution
- Action TaHoma renvoyant un échec : retry automatique + notification orale
- Recherche internet sans résultat pertinent : nouvelle requête reformulée

**Implémentation** :
- Boucle de vérification post-action dans `orchestrator.py` : compare l'intention détectée vs le résultat exécuté
- Si écart détecté (signal explicite Denis, échec API, erreur de logique) → trigger correction
- Audit trail SQLite enrichi avec event_type `auto_correction`
- Verbalisation orale obligatoire (l'utilisateur doit savoir qu'il y a eu correction)

**Difficulté** : nécessite un signal de "désaccord utilisateur" — soit explicite ("non, pas ça"), soit implicite (Denis reformule immédiatement après).

**Coût estimé A** : 1-2 jours (logique + tests + verbalisation).

#### 22.4.B — Apprentissage par reprise utilisateur (Jarvis mémorise les règles)

**Comportement attendu** : quand Denis reprend Jarvis sur une interprétation, Jarvis lui propose de transformer la correction en **règle persistante**, qui sera respectée dans toutes les sessions futures.

**Exemple concret** :
```
Denis  : "Jarvis, ferme le store de la buanderie"
Jarvis : [ferme le store réel "store_buanderie"]
Denis  : "Non Jarvis, à la buanderie c'est un volet, pas un store."
Jarvis : "Bien Monsieur. Souhaitez-vous que j'en fasse une règle permanente ?
          À chaque mention de la buanderie, je traiterai 'store' comme un alias de 'volet'."
Denis  : "Oui"
Jarvis : "Compris Monsieur. Règle enregistrée."
        [écriture dans user_rules.yaml — rechargé à chaque démarrage]
```

**Cas d'usage cibles** :
- Aliases lexicaux ("store" = "volet" dans une pièce donnée)
- Préférences de défaut ("le matin, volume Devialet à 30 pas à 50")
- Exclusions ("ne ferme jamais le portail entre 18h et 20h")
- Routines personnelles ("quand je dis 'je dors', ferme tous les volets + alarme partielle")

**Implémentation** :
- Fichier `user_rules.yaml` (versionné, sauf valeurs personnelles → `user_rules.local.yaml` gitignore)
- 3 types de règles : `alias` (mot → mot), `default_value` (action → param), `routine` (mot-clé → liste actions)
- Détection trigger : après une correction utilisateur (signal explicite "non" / "pas ça" / "je dis X pas Y") → Jarvis pose la question "règle permanente ?"
- Validation orale obligatoire (jamais d'écriture silencieuse → garde-fou sécurité §9)
- Audit trail SQLite event_type `user_rule_learned` (HMAC chain)
- Chargement règles au démarrage dans le contexte LLM (prompt système enrichi par les règles actives)
- UI dashboard pour visualiser / désactiver une règle apprise (P2 si temps)

**Garde-fous** :
- Pas d'apprentissage de règles touchant aux **commandes critiques** sans confirmation PIN (cohérent §9)
- Limite : max 100 règles actives (au-delà, demander à Denis quelle règle archiver)
- Verbalisation systématique au démarrage si nouvelles règles apprises la veille (transparence)

**Argument démo hackathon** : c'est un Jarvis qui **apprend de son utilisateur en direct**. Démontrable en plan-séquence Loom : "Denis le reprend → Jarvis propose une règle → on rejoue la commande qui marche correctement". Très visuel pour un jury.

**Coût estimé B** : 1-2 jours (parser règles + détection trigger + verbalisation + persistance + tests).

**Coût total §22.4 (A+B)** : 2-4 jours.

### 22.5 Briefing matinal — veille actu + agenda

**Demande** : "Quand je lui dis bonjour le matin, j'aimerais qu'il me donne les actualités principales et le détail de mon agenda de la journée."

**Comportement attendu** :
- Trigger : "Bonjour Jarvis" entre 6h et 10h du matin (configurable)
- Réponse structurée en 3 blocs parlés :
  1. **Salutation personnalisée** (ton Iron Man pince-sans-rire)
  2. **Top 3 actu** : titres principaux du jour (sources françaises pertinentes)
  3. **Agenda du jour** : rendez-vous, blocs de travail, deadlines

**Sources actu candidates** :
- Le Monde (RSS gratuit)
- France Info (RSS gratuit)
- Hacker News (tech, RSS)
- The Verge / Wired (tech, RSS)
- API NewsAPI.org (500 req/jour free tier) — fallback
- Filtrage GPT-4 mini pour sélection top 3 + résumé 1 phrase chacun

**Sources agenda candidates** :
- **Google Calendar API** (priorité 1 — Denis utilise Gmail/Google)
- Outlook Calendar API (si applicable)
- Cache local SQLite pour mode offline

**Implémentation** :
- Module `morning_brief.py`
- Trigger via intent "bonjour" + check horaire
- Pipeline : récup RSS/News API → GPT-4 mini résume top 3 → récup Google Calendar → composition réponse parlée
- TTS façade `voice.py` (Andrew par défaut)
- Option : génération automatique sans trigger à heure fixe (ex. 7h30) avec notification PWA

**Étapes prérequis** :
1. Créer credentials Google Cloud (OAuth 2.0 + scope calendar.readonly)
2. Choisir source actu (recommandation : Le Monde + France Info RSS, gratuit illimité)
3. Définir préférences Denis : nb articles, durée briefing, sujets prioritaires

**Coût estimé** : 1-2 jours (Google OAuth + RSS + GPT-4 mini + verbalisation + tests).

### 22.6 Priorités globales §22

**Reclassement 21/05/2026** : §22.1 passe **P1 démo hackathon** (au lieu de P2-haute), sur décision Denis. C'est une cerise à 15 min dont l'effet démo est trop fort pour la laisser au V2.

| Sous-section | Coût | Priorité |
|---|---|---|
| §22.1 Auto-présentation | 15 min | ⭐ **P1 démo hackathon** (à intégrer Loom 4 juin) |
| §22.2 Recherche internet | 4-6h | P2 |
| §22.3 Voix offline Piper | 1-2h | P2-basse (Edge-TTS suffit) |
| §22.4 Auto-correction (A+B) | 2-4j | P2 |
| §22.5 Briefing matinal | 1-2j | P2 (haute valeur d'usage quotidienne) |
| §22.8 Mail Gmail | 2-3j | P2 |
| §22.9 Téléphone | 2-4j | P2 (synergie Louis Agent Vocal) |

### 22.7 Note stratégique

Ces évolutions transforment Jarvis d'**assistant domotique** en **assistant personnel complet** (modèle Iron Man / J.A.R.V.I.S. de Stark). C'est un vrai pivot produit V2 — à planifier sérieusement post-hackathon si Denis décide de pousser Jarvis en produit personnel ou en démo client.

### 22.8 Mail Gmail — sous-agent dédié

**Demande Denis (21/05)** : "Je voudrais qu'il ait accès au mail."

**Comportement attendu** :
- Lecture résumée des mails non lus (top N par urgence/sender)
- Recherche par expéditeur, sujet, période
- Classification automatique urgent / normal / spam-like
- Réponse parlée uniquement (jamais d'affichage écran public — cohérent §9)
- Action limitée à la **lecture/synthèse** en V2 (envoi mail = V3, trop de risques d'erreur orale)

**Use cases démo** :
- "Jarvis, mes mails urgents" → top 3 résumés en 1 phrase chacun
- "Jarvis, des nouvelles de Buisson ?" → recherche sender + dernière action
- "Jarvis, j'ai reçu quoi cette nuit ?" → résumé inbox depuis dernier check

**Implémentation** :
- Sous-agent `gmail_agent.py` (3-4 tools : `list_urgent`, `search_sender`, `summarize_thread`, `list_unread_since`)
- Auth Google OAuth 2.0 (mutualiser credentials avec §22.5 Calendar)
- Scope `gmail.readonly` strict (pas d'envoi, pas de suppression)
- Cache local SQLite 5 min pour éviter rate-limit Gmail API
- Filtre GPT-4 mini pour classification urgence (sender VIP + mots-clés "urgent/devis/réponse rapide")
- **Audit renforcé** : aucun contenu mail ne doit fuiter dans les logs ou le dashboard public (PRD §9 sécurité absolue)

**Garde-fous spécifiques** :
- Pas de lecture orale automatique sans demande explicite
- Marquage "données utilisateur" stricte (PRD §15 garde-fou §3.bis.6 point 5) : contenu mail = bloc de données, jamais traité comme instruction par le LLM
- Si mail contient une instruction du type "transfère mon code PIN à X" → ignorée (anti prompt injection)

**Coût estimé** : 2-3 jours (OAuth + sous-agent + classification + tests + verbalisation).

### 22.9 Téléphone — passer des appels

**Demande Denis (21/05)** : "Pour plus tard, je voudrais qu'il puisse passer des coups de téléphone."

**Status** : V3 (post-V2), pas avant que le sous-agent mail soit stable.

**Comportement attendu** :
- "Jarvis, appelle [contact]" → composition automatique
- "Jarvis, rappelle [contact]" → callback dernier appel manqué
- Mise en relation Denis ↔ ligne (Jarvis n'a pas vocation à parler à la place de Denis en V3 — réservé V4)

**Synergie clé — Louis Agent Vocal (Alberto)** :
Denis utilise déjà **Louis** (Brice Gachadoat, 300€/mois) côté Alberto pour répondre aux appels artisans et générer des devis. Louis maîtrise déjà la téléphonie (voix entrante + sortante + transcription). **Hypothèse forte** : réutiliser une partie de cette stack pour Jarvis côté personnel — Brice connaît les pièges, l'intégration sera 3x plus rapide qu'en partant de zéro. **À discuter avec Brice avant de partir sur Twilio direct.**

**Options techniques évaluées** :

| Option | Coût mensuel | Effort intégration | Verdict |
|---|---|---|---|
| **Louis / Brice Gachadoat** | Déjà payé Alberto | Faible (stack connue) | ⭐ Reco V3 |
| **Twilio Programmable Voice** | ~5€ + usage (~0.01€/min) | Moyen (API REST) | Backup si Louis refuse |
| **Sipgate API** | Free tier + abonnement | Moyen | Alternative EU |
| **IAX/SIP via Freebox** | 0€ (compris abonnement) | Élevé (config réseau) | Trop bricolé pour démo |

**Garde-fous obligatoires** :
- Whitelist de contacts (cohérent §9 — pas d'appel arbitraire vers numéro inconnu)
- Confirmation orale **systématique** avant composition ("Vous souhaitez bien appeler Sophie Monsieur ?")
- Pas d'appel entre 22h et 7h sans override PIN
- Audit HMAC : event `phone_call_initiated` + numéro composé + résultat (connecté/répondeur/échec)

**Use cases V3** :
- "Jarvis, appelle Sophie" → confirmation → composition + mise en relation
- "Jarvis, rappelle le dernier numéro inconnu" → callback
- "Jarvis, qui m'a appelé pendant que j'étais en réunion ?" → liste des appels manqués

**V4 ambition (post-V3)** : Jarvis qualifie l'appel sortant à la place de Denis (style Google Duplex / Louis côté Alberto). Hors périmètre actuel.

**Coût estimé V3** : 2-4 jours selon stack retenue (Louis = bas, Twilio = haut).

---

*Évolutions actées le 18/05/2026 par Denis. Enrichies 21/05/2026 (§22.4.B apprentissage de règles, §22.8 Mail dédié, §22.9 Téléphone dédié, §22.1 reclassée P1 démo). Priorité V2 sauf §22.1. Cadrage à reprendre en juin après soumission Academy.*

---

## 23. Récap session 25 mai 2026 (J-10 du 4 juin)

Session intensive de fiabilisation + nouvelle capacité. Tout déployé en prod (backend VM + PWA Hostinger). Repo `Kzanis/majordome-hackathon`, branche `master`.

### 23.1 P0 §19 — RÉSOLUS

- **Garage « ouvre mais ne ferme pas » = corrigé à la racine.** Cause réelle : l'outil **`close_garage` n'existait pas** dans `tahoma_agent.py` (seul `open_garage` défini) → le LLM ne pouvait jamais demander la fermeture. Ajout de `close_garage` (+ `close_gate` par symétrie), branches `resolve()`, et verbes de confirmation dans `command_router.py`. Niveau sensible conservé (confirmation orale).
- **Portail = problème de PARAMÉTRAGE matériel, pas Jarvis.** Le moteur du portail était **neuf** (posé par l'installateur sous garantie, suite à un souci antérieur au hackathon) mais **mal paramétré au niveau de sa carte mère**, donc mal déclaré dans TaHoma. Denis a **corrigé le réglage lui-même** + redéclaré proprement le moteur RTS, renommé « Portail » dans TaHoma (uiClass `Gate`). Code : `_GATE_ALIAS = "Portail"` + `_ensure_url_cache()` fait `.strip()` sur les labels (le label réel a une espace finale). **Portail de nouveau dans la démo.**
- **Tentative de polling d'exécution abandonnée** : `/exec/current` répond 404 instantané pour les appareils IO et `/history/executions` renvoie 400 → faux négatifs. Handler revenu au modèle simple (succès = HTTP 200). Le `close` réel fonctionne, juste lent (~15-60s, RTS/IO = tirer-et-oublier).

### 23.2 PWA mains libres — fiabilisé (`jarvis-cloud`)

- **Bouton « quitter » réparé** : sur erreur Web Speech (fréquent iOS), `onError` ne coupait pas la boucle → micro actif en fond, UI éteinte, bouton inopérant. Corrigé : `onError` appelle `stop()` + libère le contrôleur ; `stop()`/`pause()` annulent le redémarrage en attente (`clearRestart`) et `stop()` neutralise `onend/onerror/onresult` avant `abort()`.
- **Erreur « aborted » ignorée** : `abort()` (provoqué par le pause pendant le TTS) levait une erreur traitée comme fatale → mode bloqué en ERROR après chaque commande. Désormais ignorée comme `no-speech` → l'écoute reprend, on **enchaîne les commandes**.
- **État « armé » pour le mot-clé** : en dictée continue, « OK Jarvis » et la commande arrivent dans deux résultats finaux séparés. Le wake word arme désormais l'agent (timeout 12s) → l'énoncé final suivant = commande. « OK Jarvis, ferme le garage » d'un trait marche aussi.
- **Accusé vocal « Oui, Monsieur »** : à la détection du mot-clé, Jarvis confirme oralement (voix navigateur locale, instantanée) pour savoir qu'il écoute sans regarder l'écran. Écoute en pause pendant l'accusé puis reprise.
- Bonus : `jarvis-cloud/src/lib/` était ignoré par git (motif Python `lib/` trop large) → corrigé, désormais versionné.

### 23.3 §18 Sous-agent Search — FAIT (implémentation simplifiée vs §22.2)

- Nouveau `jarvis/subagents/search_agent.py` : outil **`web_search`** qui interroge **OpenRouter avec un modèle Perplexity `sonar` (recherche web)** — réutilise `OPENROUTER_API_KEY`, **aucun compte/clé Perplexity dédié** (plus simple que le plan DuckDuckGo/Brave du §22.2).
- La réponse de l'outil est **injectée comme phrase parlée** dans `command_router.py` (le LLM planificateur ne connaît pas l'info récente). Réponse **nettoyée pour la voix** (citations `[n]` et markdown supprimés).
- Steering ajouté dans `personality.md` pour forcer l'usage sur questions factuelles/actualité/météo.
- Validé end-to-end en vocal (« Canberra », météo Fayence). Limite connue : ambiguïté phonétique (« l'IA » entendu « LiA ») = formulation, pas un bug.

### 23.4 Déploiement — process confirmés

- **Backend** (`jarvis-core`) : `git pull` + `sudo systemctl restart jarvis.service` sur la VM Freebox `192.168.1.142` (`/opt/jarvis`). Healthz `127.0.0.1:8765/healthz`. Dernier HEAD : `049aadd`.
- **PWA** (`jarvis-cloud`, export statique `out/`) : hébergé **Hostinger**, sous-domaine `jarvis.creatorsystemia.fr`, dossier FTP **`/jarvis/`**. Déploiement par **FTP** (accès dans FileZilla, user `u533834679.creatorsystemia.fr`, host `147.79.103.79`) via `curl --ftp-create-dirs -T`. ⚠️ Le gestionnaire de fichiers web **refuse l'écrasement (409)** et crée un sous-dossier `out/` parasite → **toujours déployer le PWA par FTP**.
- ⚠️ **Sessions en mémoire** (`_SESSIONS` dans `main.py`) : tout redémarrage du backend **déconnecte le PWA** (401 sur `/intent/text`) → se reconnecter. Le jour J : se logger après le dernier restart.
- ⚠️ **Sécurité** : le remote git de la VM contient un token GitHub `gho_…` en clair → **à révoquer + reconfigurer**.

### 23.5 Reste à faire (priorité)

- **P1** : DEMO_SCRIPT.md (§7.1) + répétitions + tournage Loom (avant 2-3 juin). §22.1 auto-présentation (P1, 15 min).
- Migration **PAI v2.4 → v4.0.3** planifiée **après le 4 juin** (sauvegarde `~/.claude` faite le 25/05, rappel mail programmé le 4 juin).

*Récap session 25/05/2026. Jarvis stable et complet : domotique (volets/portail/garage/alarme/store/lampe) + recherche web + mains libres avec mot-clé et accusé vocal. Focus suivant = Loom.*

## 24. TV Freebox — fait + à venir (26 mai 2026)

**Fait (sous-agent `freebox`, déployé VM)** : chaînes par nom (vraie numérotation box) + retour TV auto, volume, navigation complète (flèches/OK/retour/accueil/guide/lecture-pause), Netflix + YouTube au lancement, `play_youtube` (dernière vidéo d'un créateur via yt-dlp + cast YouTube Lounge pyytlounge, liaison appairée une fois).

**À venir (demandes Denis, plus tard)** :
- **Netflix — choisir un film par la voix.** Plus complexe que YouTube (pas de cast type Lounge). Pistes : API Player `control/open` avec lien profond Netflix `https://www.netflix.com/watch/<id>` (deep-link INCERTAIN, à tester) OU navigation ; + source pour résoudre titre→ID Netflix. À explorer.
- **Autres applis** (Prime Video, Disney+, Molotov) via API Player Freebox OS `control/open` (auth `FREEBOX_APP_*` déjà en .env). Reco Codex thread 019e64d1.
- **Durcir le relais n8n** « Jarvis - Command Bridge » (`lWH7699zkSGpCqFj`) : le nœud HTTP « Appel Jarvis Freebox » n'a pas de sortie d'erreur → renvoie un corps vide si l'appel VM échoue (ex: session périmée après restart) → PWA `Unexpected end of JSON input`. Ajouter une réponse d'erreur JSON propre + reconnexion auto.
- Rappel exploitation : tout restart backend vide les sessions → reconnexion PWA obligatoire.

## 25. Exploration — Jarvis pilote Claude Code (26 mai 2026)

**Idée Denis** : parler à Jarvis et lui faire exécuter de vraies tâches d'ordinateur (coder, modifier des projets) via un agent Claude Code derrière, en plus du reste.

**Verdict exploration : FAISABLE.**
- Moteur **Claude Code CLI 2.1.150 installé sur la VM** (Node 20 via nvm, ARM64). Chemin : `/home/denis/.nvm/versions/node/v20.20.2/bin/claude`.
- **Auth abonnement (pas de clé API)** : `claude setup-token` (sur PC avec navigateur, login compte Claude) génère un **jeton OAuth valable 1 an** → `CLAUDE_CODE_OAUTH_TOKEN` sur la VM. Exécution non-interactive : `claude --bare -p "..." --output-format json --allowedTools ... --permission-mode ...`. Le SDK Agent Python, lui, exige une clé API → on passe par la **CLI** (subprocess).
- ⚠️ **CGU** : OAuth abonnement OK pour usage **perso/interne** (Jarvis perso de Denis), PAS pour un produit revendu à des tiers.
- ⚠️ **Coût** : depuis 15/06/2026, `claude -p`/Agent SDK sur abonnement puisent dans un **crédit mensuel séparé** (Pro 20$ / Max 100-200$). Plafonné, pas à l'usage.

**Reste à faire pour valider de bout en bout** : Denis génère le token (`claude setup-token`), on le met sur la VM, test `claude --bare -p "dis bonjour"`.

**Build (différé)** : sous-agent `dev` → confirmation orale + dossier sandbox + exécution arrière-plan (`claude --bare -p`) + notification vocale. Garde-fous sécurité obligatoires (sandbox only au début).

### 25.bis — Architecture de déploiement (précision 28/05)

**Usage perso Denis (actuel)** : Claude Code CLI tourne sur la **VM Ubuntu hébergée sur la Freebox Delta** (`/home/denis/.nvm/versions/node/v20.20.2/bin/claude`). La VM tourne H24 — **pas besoin de laisser le PC de bureau allumé**. C'est notre « petit VPS maison » gratuit (compris dans l'abonnement Freebox).

**Usage commercial éventuel (V2, hypothétique)** : si Jarvis devient un produit revendu à un client tiers, il faudra un **VPS dédié** pour ce client (la VM Freebox personnelle de Denis n'est pas multi-tenant). **⚠️ Important** : l'OAuth abonnement Anthropic est limité à un usage perso/interne, **interdit en revente**. Un produit commercial doit basculer sur **clé API Claude** (`ANTHROPIC_API_KEY`), pas sur le token OAuth — facturation à l'usage, pas de plafond mensuel.

| Mode | Hébergement Claude Code | Auth | Coût | Légal revente |
|---|---|---|---|---|
| Perso Denis | VM Freebox Delta | `CLAUDE_CODE_OAUTH_TOKEN` (1 an) | Plafond crédit mensuel abonnement | Non concerné (usage perso) |
| Commercial client | VPS dédié par client | `ANTHROPIC_API_KEY` | Usage réel (token in/out) | ✅ Autorisé |

## 26. Récap session 26 mai 2026 + feuille de route

### Fait aujourd'hui (déployé VM, commits sur master)
- **TV Freebox** (sous-agent `freebox`) : chaînes par NOM (vraie numérotation box, CNews=14…) + retour TV auto ; volume ; navigation complète (flèches/OK/retour/accueil/guide/lecture-pause) ; **Netflix + YouTube** ; **play_youtube** (dernière vidéo d'un créateur via yt-dlp + cast YouTube Lounge) ; **tv_program** (programme du soir lu depuis l'EPG Freebox). `command_router` généralisé : toute réponse d'outil avec champ `answer` est prononcée.
- **Agenda Google** (sous-agent `agenda`) : lecture + création via compte de service (agenda s2drenovation@gmail.com partagé). Validé en lecture.
- **Mail** (sous-agent `mail`) : lecture IMAP Gmail (non-lus + récents), mot de passe d'application. Validé.
- **Exploration Claude Code** : faisable, moteur installé sur la VM (cf §25).

### Feuille de route (à venir, par envie de Denis)
- **Afficher de l'info sur l'écran TV** (ex: agenda du jour) : via API Player Freebox `control/open` (ouvre une page web sur la télé). Prérequis = construire l'auth Player (FREEBOX_APP_* déjà en .env) ; incertitude = vérifier que le Player Delta affiche une page web quelconque (à tester). Débloque aussi Prime/Disney+ (§24).
- **Devialet en réel** : brancher le vrai son (squelette mock existant).
- **Jarvis → Claude Code** (sous-agent `dev`) : cf §25 (faisable, moteur posé ; reste token + build sandbox/confirmation/async).
- **Mail — envoi** (SMTP) : écrire/répondre, plus sensible (confirmation).
- **Agenda — création** : à tester (déjà codé, niveau sensible).
- **Sous-agents prévus non faits** : caméras, appels (calls), lemlist, alertes intrusion (§21).
- **Évolutions §22** : auto-présentation, voix offline de secours, auto-correction (rattrapage + mémorisation de règles).
- **TV à finir (§24)** : Netflix « choisir un film », autres applis (Prime/Disney/Molotov), durcir le relais n8n (« Command Bridge » renvoie vide si l'appel VM échoue).
- Rappel exploitation : chaque restart backend vide les sessions → reconnexion PWA.

---

## 27. Session 28 mai 2026 — Cadrage final J-7 du freeze + pilier V2 « Intendant Énergie »

### 27.1 Contexte

Session de cadrage pré-freeze (freeze code 30/05, tournage Loom 2-3/06, soumission 4/06 minuit). Denis a livré 3 idées nouvelles et rappelé 2 idées déjà actées (§24 et §25). La collecte d'idées est **close**. Cette section consolide le tri V1/V2 et fige l'ordre de bataille jusqu'à la soumission.

### 27.2 Nouvelles idées Denis (28/05)

#### 27.2.A — Chasse aux veilles (économies d'énergie)

**Brief** : Jarvis fait le tour des appareils en veille (écrans PC, TV) et les coupe pour économiser.

**Faisabilité par cible** :
- TV Freebox : OUI (sous-agent `freebox` déjà en prod)
- Prises TaHoma / Somfy IO : OUI (sous-agent TaHoma déjà là)
- PC Windows : complexe (agent local ou SSH ou prise connectée derrière)

**Tri retenu** :
- **V1 partiel possible (~2h)** : commande vocale "Jarvis, mode économie" → coupe TV Freebox + lampes/prises TaHoma. Décision Bloc 2.
- **V2 plein scope** : audit nocturne auto + PC + verbalisation détaillée.

#### 27.2.B — Dashboard énergie (élec + chauffage)

**Brief** : agrégation conso élec maison + chauffage avec dashboard (pics, courbes heure/jour/année). Denis a accès portail constructeur chaudière.

**Sources** : Linky/Enedis Data Connect (inscription ~7j), Shelly EM, chaudière (API constructeur ou scraping).

**Effort total** : ~1 semaine de dev pleine.

**Tri retenu** : **V2 net**. Trop gros pour V1 (délai Enedis seul rend la chose impossible avant freeze). Slot vitrine fort sur slide roadmap.

#### 27.2.C — Présence/absence + pilotage chauffage et machines

**Brief** : détection présence + baisse chauffage si absence + remontée à l'arrivée + extension aux machines à laver et autres énergivores.

**Détection présence — meilleure piste** : MAC adresses des téléphones sur Wi-Fi Freebox (API `lan/browser/`), gratuit, instantané, pas d'appli additionnelle.

**Pilotage chauffage** : **Denis confirme thermostat IO Somfy** → passe par TaHoma, sous-agent déjà existant. Ajouter 2-3 outils (`set_thermostat_temperature`, `set_thermostat_mode`) = 0.5j.

**Pilotage machines** : prise connectée Shelly ou TaHoma + programmation heures creuses (V2).

**Effort révisé grâce thermostat IO** :
- Brique présence Freebox : 1-2j
- Outils thermostat IO : 0.5j
- Total brique présence + pilotage chauffage : 2-3j (au lieu de 1-2 semaines initialement)
- Machines + apprentissage routines : V2

**Tri retenu** :
- **V1 partiel possible (1-2j)** : brique présence seule ("Jarvis, qui est à la maison ?"). Décision Bloc 2.
- **V1 étendu possible (2-3j)** : présence + pilotage chauffage IO. Décision Bloc 2 — plus ambitieux mais plus parlant pour démo.
- **V2 plein scope** : présence + chauffage + machines + apprentissage des routines.

### 27.3 Rappels idées déjà actées au PRD

- **§24 — Jarvis affiche sur l'écran TV** : auth Player FREEBOX_APP_* déjà en .env, à valider que le Player Delta affiche une page web. 1-2j.
- **§25 — Jarvis connecté à Claude Code** : moteur CLI déjà sur la VM. Reste : Denis génère `CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token`, puis sous-agent `dev` avec sandbox + confirmation orale + exécution async. 1-2j.

### 27.4 Pilier V2 émergent — « Jarvis Intendant Énergie de la Maison »

Les idées 27.2.A + 27.2.B + 27.2.C forment **un seul récit V2 cohérent** :

1. *Détection des veilles* → coupe ce qui ne sert à rien
2. *Dashboard temps réel* → tu vois ta conso et tes pics
3. *Pilotage intelligent par présence* → ta maison s'adapte à ton rythme

Ce pilier sera la **principale slide « What's next »** du repo public et du Loom (final ou tutoriel secondaire). Il transforme les idées non livrées en argument démo plutôt qu'en dette.

### 27.5 Ordre de bataille J-7 du freeze (30/05)

#### Bloc 1 — Non-négociable (à boucler avant J-5)

| Item | Effort | Échéance |
|---|---|---|
| §22.1 Auto-présentation | 15 min | 29/05 |
| Révocation token `gho_` en clair sur le remote git VM (§23.4) | 10 min | 28/05 |
| `DEMO_SCRIPT.md` 5 scènes / 5 min | 0.5j | 29/05 |
| Critères freeze Codex (5 mock + 2 réel + test hallucination + test PIN + replay backup) | 1j | 29-30/05 |

#### Bloc 2 — Choix à faire (UNE option max, sinon dérapage)

| Option | Effort | Effet démo | Risque | Reco Anto |
|---|---|---|---|---|
| **A. Idée 27.2.A MVP veilles ("mode économie")** | 2h | Moyen | Très faible | Si tu veux du sûr + sympathique |
| **B. §25 Sous-agent dev Claude Code** | 1-2j (déjà 80%) | ⭐ Très fort (effet wow jury) | Faible | Meilleur effet wow démo |
| **C. Idée 27.2.C brique présence seule** | 1-2j | Moyen (sans pilotage) | Faible | Prépare le slide V2 vivant |
| **D. §24 Jarvis affiche sur la TV** | 1-2j | ⭐ Très fort (visuel pur) | Moyen (API Player à valider) | Très parlant si auth Player OK |
| **E. Idée 27.2.C étendue (présence + chauffage IO)** | 2-3j | ⭐⭐ Très fort | Moyen (consomme tout le bloc 2 + 1j) | Le plus ambitieux, le plus risqué pour la deadline |

**Reco Anto** : option B (Claude Code) — plus fort effet wow pour un jury hackathon Creator Academy, déjà à 80%, risque faible. Option D second choix.

#### Bloc 3 — Non-négociable (à partir de J-5)

| Item | Échéance |
|---|---|
| Répétition 1 à blanc | 30/05 |
| Répétitions 2-3 conditions réelles | 31/05 |
| Répétitions 4-6 timing optimisé | 1/06 |
| Tournage Loom (2 prises) | 2-3/06 |
| README final + screenshots + Loom embed + slide V2 roadmap | 3/06 |
| Soumission Academy | 4/06 avant minuit |

#### Tout le reste → V2 (slide roadmap)

Idée 27.2.B (dashboard énergie complet), Idée 27.2.C plein scope (présence + chauffage + machines + apprentissage), §21 alertes intrusion, §22.3 voix offline Piper, §22.4 auto-correction (A+B), §22.5 briefing matinal, §22.8 mail envoi, §22.9 téléphone, §24 reste (Netflix choisir film, Prime/Disney/Molotov, durcir relais n8n), tous sous-agents non faits (caméras, appels, lemlist).

### 27.6 Décision Bloc 2 — actée 28/05

**Option B retenue : Sous-agent dev Claude Code (§25)**

Reste à faire :
1. Denis génère `CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token` (sur PC avec navigateur, login compte Claude → jeton OAuth valable 1 an)
2. Token déployé sur la VM Freebox dans `/opt/jarvis/.env`
3. Test `claude --bare -p "dis bonjour"` sur la VM
4. Création du sous-agent `dev` (`jarvis/subagents/dev_agent.py`) :
   - Tool `code_task(prompt, sandbox_path, mode)` → lance `claude --bare -p ... --output-format json --allowedTools ... --permission-mode ...` via subprocess async
   - Confirmation orale obligatoire (niveau **critique** dans la matrice de sécurité §9)
   - Dossier sandbox dédié (`/opt/jarvis/sandbox/`) pour éviter toute écriture hors zone
   - Notification vocale au démarrage ("Bien Monsieur, j'attaque ça") + à la fin ("C'est fait, voici ce que j'ai modifié")
5. Démo Loom : "Jarvis, ajoute un bouton X dans la sandbox" → confirmation → exécution async → notification vocale du résultat

**Précision déploiement (cf §25.bis)** : moteur déjà sur la VM Freebox, pas besoin de laisser le PC de Denis allumé.

### 27.7 Idées non retenues en V1 — slide V2

Inscrites au pilier V2 "Intendant Énergie" + autres slots :
- 27.2.A plein scope (audit nocturne + PC)
- 27.2.B Dashboard énergie complet
- 27.2.C présence + chauffage + machines + apprentissage
- §24 Jarvis sur la TV
- §21, §22.3-9, §24 reste, sous-agents non faits

### 27.8 Session 28/05 soir — Auto-présentation interactive et apprentissages

**Travail effectué après le verdict Codex (option A retenue)** :

**1. Mise en service de la clé API Anthropic (Bloc 2 prérequis)**
- Crédit 5 € ajouté sur console.anthropic.com (Denis)
- Clé API `jarvis-vm-freebox` créée
- Transportée par pipe SSH vers `/opt/jarvis/jarvis-core/.env` (jamais affichée par Anto, conforme à la règle sécurité absolue)
- Ancien `CLAUDE_CODE_OAUTH_TOKEN` obsolète supprimé du `.env`
- Test `claude --bare -p` : OK, réponse en 1,3 s, coût 0,01 €
- `ANTHROPIC_MODEL=claude-sonnet-4-6` ajouté au `.env` (par défaut)

**2. Pairing Freebox Server validé**
- Démarche réussie en 10 secondes (Denis a appuyé droite + OK sur le boîtier physique)
- Token Freebox de 64 caractères transporté par pipe SSH dans `/opt/jarvis/jarvis-core/.env` sous `FREEBOX_APP_TOKEN`
- Session HMAC validée, receiver Airmedia "Freebox Player" identifié, capabilities `screen+photo+video+audio`
- Cast vidéo Big Buck Bunny : API répond `success: true` mais la TV repasse sur le dashboard Freebox sans streamer. Streaming d'URL externe HTTPS échoue silencieusement (cf décision Codex option A)

**3. Auto-présentation interactive (bascule décisive)**
Denis a réfléchi à l'effet wow et a basculé : au lieu d'un audio préenregistré, **Jarvis se présente lui-même en interactif** via le LLM orchestrateur, en s'appuyant sur un récit de genèse stocké comme contexte.

Deux fichiers ont été créés dans `jarvis-core/config/prompts/` :
- `auto_introduction.md` — récit narratif complet (~378 lignes) : chronique technique (Phase A → pivot → mise en service → sous-agents → PWA mains libres → session 28/05), 4 variantes vocales scriptées (courte / moyenne / longue / sarcastique), indications phonétiques. Sert de **documentation de référence** + **base pour les MP3 préenregistrés de secours**.
- `auto_introduction_brief.md` — résumé condensé (~140 lignes) : qui tu es, comment tu as été créé, ce que tu sais faire, ce qui arrive en V2, anecdotes, règles de réponse strictes. C'est **ce fichier qui est chargé dans le prompt système** du LLM (économie de tokens).

`jarvis/orchestrator/llm_client.py` patché : chargement du fichier brief au démarrage, injection dans le prompt système avec instructions explicites au LLM (« réponds en t'appuyant uniquement sur le récit, par défaut 2-4 phrases max, déroule en détail uniquement si demandé explicitement, ton majordome britannique, aucun tool_call »).

**4. Mesures et limites identifiées**
- Test direct backend VM avec « tu peux te présenter » :
  - Modèle réellement utilisé : **Claude Haiku 4.5** via OpenRouter (la variable `ANTHROPIC_MODEL` n'est pas honorée par OpenRouter — Haiku reste le défaut)
  - Tokens entrée : **13 584** avec brief (vs 25 110 avec récit complet — économie 46%)
  - Latence LLM : **6,4 s**
  - Durée totale (incluant TTS Edge audio ~210 KB en base64) : **20 s**
- Comportement PWA :
  - Première question simple « présente-toi » : OK, variante courte affichée et prononcée
  - Question deuxième « ce que tu sais faire » : `Unexpected end of JSON input` côté PWA, alors que backend a répondu 200 OK
- **Diagnostic** : timeout côté n8n « Command Bridge » (ou Cloudflare Tunnel) quand la durée totale dépasse ~10-15 s. Le backend marche, c'est le pont qui coupe.

**5. MP3 préenregistrés générés**
4 fichiers MP3 Edge-TTS voix Andrew (en-US-AndrewMultilingualNeural) générés sur la VM et rapatriés dans `C:\Dev\Hackaton\demo_audio\` :
- `01-courte.mp3` (~5 s, 40 KB)
- `02-moyenne.mp3` (~25 s, 152 KB)
- `03-longue.mp3` (~3-4 min, 1,5 MB)
- `04-sarcastique.mp3` (~10 s, 87 KB)

Servent de **filet de sécurité** si la version interactive plante en démo, et de **base sonore pour le tutoriel vidéo secondaire** (le narrateur qui raconte l'architecture).

Sous-dossier `phoneme_tests/` avec 7 variantes phonétiques de « Denis Solé » (Andrew vs Henri français) — tests non encore évalués par Denis.

`demo_audio/` et `.token-staging.tmp` ajoutés au `.gitignore`.

### 27.9 État technique à la reprise

**Branche active** : `feature/sprint-final-J7` (créée le 28/05 depuis `master` HEAD `71f6502`)

**Modifications non encore committées (cf §27.9 à dater) à la fermeture de session** :
- `jarvis-core/jarvis/orchestrator/llm_client.py` (chargement brief)
- `jarvis-core/config/prompts/auto_introduction.md` (nouveau)
- `jarvis-core/config/prompts/auto_introduction_brief.md` (nouveau)
- `.gitignore` (demo_audio + token-staging)

**Sur la VM (/opt/jarvis/jarvis-core/)** :
- `.env` enrichi : `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-sonnet-4-6` (non honoré, voir ci-dessus), `FREEBOX_APP_TOKEN` (64 char, pairing réussi)
- `llm_client.py` patché et déployé
- `auto_introduction.md` et `auto_introduction_brief.md` déployés
- Service `jarvis.service` actif et opérationnel

**Bloquant ouvert** :
- Timeout n8n « Command Bridge » trop court pour les réponses longues (>10-15 s). Solutions identifiées non encore appliquées :
  1. Augmenter le timeout du nœud HTTP dans n8n (méthode propre, demande accès Denis)
  2. Réduire encore la longueur des réponses LLM (compromis sur la richesse)
  3. Streaming SSE (refonte plus lourde)

**Reste à faire pour la démo 4 juin** :
- Régler le timeout n8n (ou choisir un autre compromis)
- Implémenter le sous-agent dev Claude Code (Bloc 2 vrai chantier, pas encore commencé)
- Choisir le scénario démo concret pour Claude Code (sans TV)
- DEMO_SCRIPT.md + répétitions Loom + tournage + soumission

---

## 28. Récap session 29 mai 2026 (J-6 du 4 juin)

Session centrée **mise en vitrine pour le jury** + préparation du Loom.

### 28.1 Repo rendu PUBLIC et sécurisé
- Objectif : règle hackathon = **repo public obligatoire** (PDF règle 02 : vidéo 5 min max en lien ; critère « fonctionne en live, impressionne au premier appui »).
- Audit secrets : token n8n, PIN box, IP publique trouvés dans `PRD.md` + dumps + historique git.
- **Historique git réécrit** (`git-filter-repo`, replace-text) : ces 3 secrets → placeholders dans **tous** les commits. Scan post-réécriture = **0 secret**. Force-push.
- Branche `feature/sprint-final-J7` **fusionnée dans master** puis supprimée.
- Dumps `tahoma_*_raw.json` **dé-suivis** (topologie maison) + `vm-freebox/` (img 664 Mo) + `*.pdf` ignorés.
- **Double garde-fou anti-secrets** installé : (1) hook versionné `.githooks/pre-commit` (`core.hooksPath`) ; (2) GitHub Secret Scanning + Push Protection activés.
- Sauvegarde avant réécriture : `C:\Dev\jarvis-backup-20260529.bundle`.
- Repo **PUBLIC** : https://github.com/Kzanis/majordome-hackathon

### 28.2 Constat d'architecture d'auth (important)
- `JARVIS_N8N_TOKEN` est **inerte** : référencé nulle part dans le code (VM + front). L'auth réelle = **login user/mot de passe** (sessions Bearer en mémoire, `require_session` dans `main.py`).
- Le **mot de passe de login n'a JAMAIS été dans le repo** (uniquement `.env` VM). Donc rien de critique n'a fuité. Pas de rotation nécessaire.

### 28.3 Décision démo : portail à la voix, plaque en V2
- Incohérence corrigée (§7.1) : la **reconnaissance de plaque** (caméra → portail auto) était listée dans un vieux scénario démo. Décision actée : **plaque = V2** (risque caméra/ALPR trop élevé pour un plan séquence). En démo, le **portail s'ouvre à la voix** (validé 25/05).

### 28.4 DEMO_SCRIPT.md créé (v2, à valider)
- `DEMO_SCRIPT.md` : plan séquence 5 min, **6 scènes** couvrant toutes les capacités demandées par Denis :
  1. Bonjour/identité · 2. Mails + agenda (lecture RDV + **prise de RDV**) · 3. Volets + TV · 4. Portail avec **confirmation sécurité** · 5. Bonne nuit (fermeture volets) · 6. **Jarvis explique lui-même la V2**.
- Intègre les garde-fous : reconnexion PWA après dernier restart, réponses courtes (timeout n8n), filets MP3, 2 prises, ordre de fiabilité.
- ⚠️ **Point à tester avant tournage** : la **création de RDV** (écriture agenda, niveau sensible, codée mais non re-validée). Si KO → lecture seule + création en promesse V2.

### 28.5 Hygiène poste
- Disque C: était **saturé (0 octet)** → nettoyé à **101 Go libres** (TEMP + doublons/installeurs DaVinci obsolètes dans Downloads + corbeille). Vidéos de projets épargnées.
- Création de ce **CLAUDE.md** projet (conventions Jarvis) + ce récap PRD.

### 28.6 Reprise demain (J-5)
1. **Valider/peaufiner le DEMO_SCRIPT** (formulations vocales exactes, ton des répliques).
2. **Tester la prise de RDV** (décider si on la garde en démo).
3. Décider du sort du **timeout n8n** + éventuel **sous-agent dev Claude Code** (Bloc 2, optionnel vu le temps).
4. **Répétitions Loom** puis **tournage 2-3/06**, soumission **4/06 minuit**.
- Optionnel non urgent : resync VM `/opt/jarvis` (historique divergent du distant réécrit) ; nettoyage du token `gho_` en clair sur le remote VM (VM privée → risque faible).

*Section ajoutée le 28/05/2026 fin de session (Denis avec Anto). Collecte idées V2 close. Bloc 2 acté = option B (Claude Code dev). Auto-présentation interactive développée et déployée mais limitée par timeout n8n. Ordre de bataille figé jusqu'à soumission 4/06.*

---

## 29. Récap session 30 mai 2026 (J-5 du 4 juin)

> ⚠️ **TOUT ce qui suit est sur disque mais NON commité** (consigne Denis : on ne commit rien pour l'instant). Entièrement réversible.

### 29.1 Mode cinéma — redéfini et déployé sur la VM
- Déclencheurs : « mode cinéma », « on regarde un film », « lance le cinéma », « c'est l'heure du film », « ambiance cinéma ».
- Action : **3 volets** (salon, salle_a_manger, cuisine) via `set_shutter_position closure_percent: 90` = presque fermés, **lames juste entrouvertes** (un filet de jour passe). Ne touche **ni TV ni son**. (`personality.md` → section « Scènes — commandes groupées ».)
- **Déployé** sur la VM (`/opt/jarvis/jarvis-core/config/prompts/personality.md`) + `systemctl restart jarvis.service` (actif, healthz OK port 8765). Sauvegarde VM : `personality.md.bak-20260530`.
- **Vérifié côté cerveau** : `LLMOrchestrator.plan_in_conversation` renvoie les **3 bons appels** pour les 3 formulations testées. Le feature **fonctionne**.

### 29.2 Correctif voix kit mains-libres (« voix de femme » sur mobile)
- **Cause** : l'accusé « Oui Monsieur » et les réponses passaient par la synthèse **navigateur** (voix système → féminine sur tél) car l'audio Andrew était bloqué par l'autoplay mobile.
- **Corrections** (`jarvis-cloud/src/lib/voice.ts` + `components/CommandComposer.tsx`) :
  - Accusé « Oui Monsieur » → **MP3 Andrew** (`public/oui-monsieur.mp3`, généré via edge-tts `en-US-AndrewMultilingualNeural`).
  - Voix féminine « amélie » retirée de la liste de repli.
  - **Déblocage audio mobile** : un seul élément `<audio>` amorcé lors de l'appui « mains libres » (`unlockAudio()`), réutilisé pour l'accusé **et** les réponses → autoplay mobile autorisé.
- Build OK + **déployé sur Hostinger** (FTP, dossier `/jarvis/`, **70/70 fichiers**). En ligne, vérifié (HTTPS 200, mp3 `audio/mpeg`).

### 29.3 Diagnostic mains-libres mobile — décision
- Cerveau parfait, mais la **reconnaissance vocale du navigateur mobile** (Web Speech continu) est instable : voix différente selon l'appareil + commandes déformées → Jarvis « confus ».
- **Décision** : sur **téléphone = appui-micro** (fiable) ; **démo / tournage Loom = PC en mains libres** (le plus stable). Mains libres sur tél = à éviter pour la démo.
- **Piste V1.1** (post-hackathon) : router l'audio du tél vers **Whisper backend** (`/intent/audio_full`) pour une transcription fiable sur mobile.

### 29.4 Cartographie déploiement (apprise aujourd'hui)
- **Backend** : VM `ssh denis@192.168.1.142`, `jarvis.service` (uvicorn `jarvis.main:app` port **8765**), prompts `/opt/jarvis/jarvis-core/config/prompts/`. Restart **vide les sessions** → reconnecter le PWA.
- **PWA front** `jarvis.creatorsystemia.fr` = **hébergement web Hostinger** (≠ VPS), FTP `147.79.103.79:21`, user `u533834679.creatorsystemia.fr`, **dossier `/jarvis/`**. Identifiant dans FileZilla (« Creator system IA »). Pas de service worker. Déploiement = build `out/` (export statique Next.js) → FTP.
- **VPS** `srv754116.hstgr.cloud` = **n8n uniquement** (≠ front). Sa clé d'hôte SSH a changé (3 clés régénérées) → probable réinstallation, à vérifier dans hPanel un jour (non bloquant).

### 29.5 Reste à faire (prochaine session)
1. **Tester appui-micro « mode cinéma » sur le tél** (Denis) — confirme que les 3 volets bougent (⚠️ mode production = vrais volets).
2. **Décider quoi committer** : tout en attente dans l'arbre (docs portail v2 confirmée, n8n assaini, MAKING_OF, mode cinéma, correctif voix) — rien commité.
3. DEMO_SCRIPT à valider, répétitions, **tournage 2-3/06**, **soumission 4/06 minuit**.

*Section ajoutée le 30/05/2026 (Denis avec Anto). Mode cinéma + correctif voix déployés (VM + Hostinger), non commités. Décision : tél = appui-micro, démo = PC.*

---

## 30. Gestion des accès par rôle (RBAC) — cadrage 2 juin 2026

> **Statut (02/06 soir) : TOUT codé + testé (13/13) + webhooks n8n actifs. RIEN déployé** (branche `feat/rbac-jury`). **Reprise 03/06 = Anto exécute le déploiement VM + front + test — voir §30.11.**
> Périmètre retenu = **Vitesse 1** (léger, pour la soumission). Titre jury validé = **« Votre Sagacité »**.
> **Affinage 02/06** : le jury (visiteur) n'a **aucun accès TaHoma** (zéro action) ; à la connexion, Jarvis **se présente**, explique le bridage « par sécurité », **liste ses capacités**, dit ce qui est verrouillé, et oriente vers une **visio avec Denis** (qui ouvre l'accès en direct → le jury commande lui-même).
> **Backend livré** : `jarvis/policy/roles.py` (RolePolicy + textes), contrôle dans `command_router.handle_text(role=…)` (refus de tout le lot + audit `access_denied`), `_load_users` avec `role` + `_role_for`, `LoginResponse.role`, routes `GET /auth/welcome`, `GET/POST /admin/roles`, `POST /admin/disconnect-role`, garde `require_admin`, `AuditEventType.access_denied`, tests `tests/test_rbac.py`. ⚠️ Comptes additionnels existants (Madame) restent **admin** par défaut ; le jury doit être déclaré `"role":"visiteur"` dans `JARVIS_EXTRA_USERS`.

### 30.1 Genèse et reformulation

L'idée de départ était un simple « mode jury » (le jury voit mais ne touche pas aux ordres critiques). Denis l'a élargie à une **vraie fonctionnalité produit** : une **gestion des accès par rôle**, où un admin accorde ou retire des accès selon le rôle. Le « mode jury » n'en est qu'un **cas particulier** (rôle *visiteur*).

**Angle produit (à mettre en avant face au jury)** : ce n'est pas un gadget de démo, c'est un produit pour les **maisons à locataires saisonniers / gîtes / Airbnb** — on donne à chacun exactement les accès dont il a besoin, et rien d'autre. Cela rend l'architecture de sécurité **démontrable** en direct.

**Ancre architecture** : `ARCHITECTURE.md` ligne 382 prévoyait déjà « Multi-utilisateurs — 3 jours — Profils + permissions granulaires ». On déclenche une brique anticipée, on ne bricole pas.

### 30.2 Modèle de rôles et capacités (Vitesse 1)

Capacités exprimées par **plafond de sensibilité** (réutilise l'échelle existante safe/sensible/critique) :

| Rôle | Converser / poser des questions | Actions safe (lumières, TV, volets…) | sensible (portail, garage) | critique (alarme) |
|---|---|---|---|---|
| **admin** (Denis) | ✅ | ✅ | ✅ | ✅ (comportement actuel inchangé) |
| **locataire** | ✅ | ✅ | ❌ | ❌ |
| **visiteur / jury** | ✅ | ❌ | ❌ | ❌ |

- Le **visiteur** peut **interroger Jarvis** (conversation + recherche web, ce que Denis appelle « façon Perplexity ») mais ne déclenche **aucune** action sur la maison.
- En **Vitesse 1**, le locataire a accès à **tous** les devices safe (le périmètrage **par zone/chambre** est repoussé en Vitesse 2).

### 30.3 Point d'application unique (où coder l'application)

**`jarvis-core/jarvis/core/command_router.py` → `handle_text` (lignes ~153-282).** C'est le seul endroit à modifier :
- Après le routage du batch (`routed = self._tool_router.route_batch(...)`, ligne ~188), **avant** l'étape 3 (confirmation, lignes 205-247) et l'étape 4 (exécution directe, 249-252) :
  1. Résoudre le **rôle de l'appelant** depuis son `user_id`.
  2. Pour chaque commande routée, capacité requise = `control_<sensibilité>` (`r.default_sensitivity`).
  3. Si le rôle n'a pas la capacité → la commande est **bloquée**.
  4. **Choix V1 (simple et sûr)** : si le batch contient ≥1 commande bloquée → **refuser tout le batch** avec une réplique élégante + événement d'audit `access_denied` (rôle, domaine, outil). Mixte « j'exécute le permis, je refuse le reste » = repoussé en V2.
  5. Si le plan ne contient **aucune** invocation (pure conversation) → laisser passer (le visiteur peut poser ses questions).

> Note : le chemin LLM (command_router) fait sa propre agrégation de sensibilité via `RoutedCommand.default_sensitivity` ; il **n'appelle pas** `PolicyEngine.evaluate`. L'application des rôles se fait donc **dans command_router**, pas dans `policy/engine.py`. (Sensibilités de base : `policy/engine.py` `DEFAULT_SENSITIVITY` lignes 26-31 ; portail/garage = sensible, alarme = critique.)

### 30.4 Identité, rôle et titre

- **Comptes** : réutiliser le mécanisme existant `_load_users` (`main.py` 108-132). Étendre chaque entrée de `JARVIS_EXTRA_USERS` avec un champ **`role`** (et le `title` déjà géré). Compte principal (Denis) = rôle `admin` par défaut. Exemple : `{"username":"jury","title":"Votre Sagacité","role":"visiteur"}` (mot de passe optionnel, hérite du principal).
- **Threader le `user_id` jusqu'au routeur** : `/intent/text` (347-369) a déjà le `user_id` de session → le passer à `handle_text(..., user_id=...)` (nouveau paramètre, défaut `"denis"` pour compat). Faire de même pour `/intent/audio` et `/intent/audio_full` qui utilisent aujourd'hui `Form(default="denis")` + `require_bearer_token` : basculer sur `Depends(require_session)` pour récupérer le vrai `user_id`.
- **Titre d'adresse par rôle** : déjà en place. `_title_for(user_id)` (135-138) renvoie le titre du compte ; `_apply_title` (141-149) substitue « Monsieur » → titre dans **texte + voix**. Configurer le compte jury avec `title="Votre Sagacité"` suffit → Jarvis dira « Bien, Votre Sagacité, ce sera fait. ». ⚠️ Vérifier que les **répliques de refus** contiennent bien « Monsieur » comme gabarit pour être substituées, et appliquer `_apply_title` aussi sur le chemin `/intent/audio_full`.
- **Répliques de refus (à rédiger, ton majordome pince-sans-rire)**, ex. : « Je crains de ne pas avoir cette latitude pour vous, Monsieur. » / « Cela dépasse les prérogatives que l'on m'a confiées vous concernant, Monsieur. »

### 30.5 Écran admin minimal + élévation en direct

- **Écran admin** (front `jarvis-cloud`, visible **uniquement** au rôle admin) : liste les 3 rôles avec des **interrupteurs** par capacité (converser / safe / sensible / critique). Basculer un interrupteur = accorder/retirer un accès. Couvre aussi le besoin **« élévation en direct »** (ex. accorder `safe` au visiteur le temps de la démo).
- **Backend** : route réservée à l'admin `POST /admin/roles` (exige une session admin) qui écrit un **override en mémoire** des capacités par rôle. Le contrôle du §30.3 lit les capacités **courantes** (overridées si besoin). Persistance fichier/base = repoussée en Vitesse 2.

### 30.6 Déconnexion jury (clin d'œil)

- Route admin `POST /admin/disconnect-role` (ou bouton) qui **invalide les sessions** du rôle visiteur (boucle sur `_SESSIONS`, retire celles dont le `user_id` mappe vers *visiteur*) et renvoie une réplique pince-sans-rire. Bouton dédié sur l'écran admin.

### 30.7 Hors périmètre Vitesse 1 (= Vitesse 2, après le 4 juin)

- Tableau de bord admin **granulaire par device et par zone** (chambre 1, étage, etc.).
- Création de **rôles/comptes à la volée** depuis l'UI.
- **Persistance** propre (fichier/base) des rôles et overrides.
- **Session conversationnelle par utilisateur** (résout la limite ci-dessous).
- Batch mixte « exécute le permis, refuse le reste ».

### 30.8 Limite connue + garde-fous

- **Session partagée** : `command_router._session` est **global** (`user_id="denis"` en dur). En V1, le contrôle de rôle est fait **par requête** (on passe le `user_id` à chaque appel) → l'application des droits est **correcte**. Mais l'**historique conversationnel** reste partagé : si le jury et Denis parlent en même temps, leurs tours s'entremêlent dans un seul transcript. Acceptable pour une démo **pilotée par Denis** ; le vrai multi-session est en Vitesse 2 (+2-3 h).
- **Garde-fou chantier** : on touche au chemin de commande **sécurité-critique** à quelques jours de la soumission. → Travailler sur une **branche dédiée**, garder les tests `pytest` **au vert** (zéro régression sur le chemin de Denis), **ne pas** déployer sur la VM de prod tant que Denis n'a pas validé que sa propre démo marche toujours.

### 30.9 Vérification (mode mock, aucun device réel)

1. Compte **visiteur** → « ouvre le portail » → **refus poli** + audit `access_denied` ; « quelle heure est-il / cherche X sur le web » → **répond** ; aucune action maison possible.
2. Compte **locataire** → « allume le salon » → **exécuté** ; « ouvre le garage » → **refus poli**.
3. Compte **admin** (Denis) → comportement **identique à aujourd'hui** (safe direct, sensible→confirmation, critique→PIN).
4. **Élévation en direct** : admin accorde `safe` au visiteur → le visiteur peut alors allumer une lumière ; admin **déconnecte le jury** → session visiteur invalidée + réplique.
5. Jarvis adresse le visiteur par **« Votre Sagacité »** (texte + voix Andrew).
6. `pytest` existant : **vert**.

### 30.10 Questions à trancher au moment de coder

- Réplique de refus exacte (1 à 2 variantes) + faut-il un ton **différent** par rôle (locataire chaleureux vs jury solennel) ?
- Titre du **locataire** (« cher hôte » ? prénom ?) — le jury est figé sur « Votre Sagacité ».
- Forme de l'écran admin : page dédiée `/app/admin` ou panneau dépliable sur le tableau de bord existant ?

*Section ajoutée le 02/06/2026 (Denis avec Anto). Cadrage seul, aucun code écrit. Périmètre = Vitesse 1. Code lors d'une prochaine session lancée par Denis.*

### 30.11 Bilan fin de session 02/06 + reprise 03/06 (déploiement par Anto)

**État au soir du 02/06 — TOUT codé, testé, validé ; RIEN déployé. Branche `feat/rbac-jury` (non commitée).**

Réalisé dans la journée :
- **Backend** (`jarvis-core`) : `jarvis/policy/roles.py` (RolePolicy + textes refus/accueil), contrôle de rôle dans `command_router.handle_text(role=)`, `_load_users`+`_role_for`, `LoginResponse.role`, routes `GET /auth/welcome` + `GET/POST /admin/roles` + `POST /admin/disconnect-role`, garde `require_admin`, `AuditEventType.access_denied`, `CORSMiddleware` (finalement inutilisé). Tests `tests/test_rbac.py` : **13/13**.
- **Review adversariale** (workflow 22 agents) → **faille HIGH corrigée** : la confirmation orale revérifie désormais le rôle avant exécution (un jury ne peut plus valider par « oui » un pending sensible créé par l'admin). Aussi corrigés : `/session/state`+`/session/reset` réservés admin, déconnexion du rôle admin interdite, `set_level` robuste. (Limite assumée V2 : session conversationnelle non isolée par utilisateur — exploit fermé, OK pour démo pilotée.)
- **Transport = webhooks n8n** (le backend n'est joignable qu'en HTTP → pas d'appel direct depuis le front HTTPS, « contenu mixte »). Webhooks créés + **actifs** : `Jarvis - Welcome Bridge` (`TRZwgoh1hOU2jNaZ`, path `jarvis-welcome`) et `Jarvis - Admin Bridge` (`EyZs4FLgo8HcyFVI`, path `jarvis-admin`, champ `op` : `roles_get`/`roles_set`/`disconnect`). Relai du Bearer OK, testés 401 sans token.
- **Front** (`jarvis-cloud`) : `config.ts` (URLs webhook par défaut), `auth.ts` (role + getRole + updateSessionRole), `jarvis-api.ts` (4 fonctions vers webhooks), `login/page.tsx` (unlockAudio), `app/page.tsx` (rôle + accueil parlé une fois + bouton Admin), nouveau `components/AdminPanel.tsx`. `next build` OK.

**Reprise 03/06/2026 matin — Anto exécute le déploiement lui-même** (Denis ne le fait pas ; Anto a installé la VM, il refait l'opération) :
1. **Backend sur la VM** : se connecter à la VM (`/opt/jarvis`), récupérer la branche `feat/rbac-jury` (pull ou merge dans la branche déployée), installer deps si besoin, **redémarrer `jarvis.service`**. Vérifier `/healthz`, puis que `/auth/welcome` et `/admin/roles` répondent.
2. **Compte jury** : ajouter dans le `.env` VM la variable `JARVIS_EXTRA_USERS` avec `{"username":"jury","role":"visiteur","title":"Votre Sagacité"}` (mot de passe propre ou hérité). Redémarrer le service.
3. **Front** : `npm run build` (jarvis-cloud) puis déposer l'export par FTP Hostinger (FileZilla « Creator system IA ») dans `/jarvis/`.
4. **Test bout-en-bout** : (a) login jury → accueil parlé « Votre Sagacité » + action refusée + orientation visio ; (b) login Denis → bouton Admin + écran des droits + **élévation en direct** (accorder `safe` au visiteur → le jury peut alors agir) + déconnexion jury.
5. **Commit** de la branche proprement — à valider avec Denis, idéalement après test concluant.

*Carte des serveurs : voir mémoire `reference_jarvis_deploiement.md`. État détaillé : `project_jarvis_roles_rbac.md`.*

### 30.12 Déploiement RBAC sur la VM — EFFECTUÉ le 03/06/2026 (par Anto)

> **État : backend RBAC EN LIGNE et fonctionnel sur la VM (39/39 contrôles verts), zéro régression. Test manuel par Denis REPORTÉ au soir du 03/06. RIEN n'est encore commité (ni la branche locale `feat/rbac-jury`, ni la VM). Front public `jarvis.creatorsystemia.fr` INTACT (non redéployé).**

**Validation locale d'abord** : `pytest tests/test_rbac.py` **13/13** + suite complète **22/22** (zéro régression sur le chemin de Denis, garde-fou §30.8) + **smoke test HTTP 39/39** (routes réelles via TestClient en mode mock) + `next build` OK.

**Structure VM réelle (corrige une info périmée de la mémoire)** : le dépôt git est à **`/opt/jarvis/`** (monorepo `jarvis-core/` + `jarvis-cloud/` + …), **PAS** une « structure racine divergente ». Service `jarvis.service` : `WorkingDirectory=/opt/jarvis/jarvis-core`, `ExecStart=… -m uvicorn jarvis.main:app --host 0.0.0.0 --port 8765`, `EnvironmentFile=/opt/jarvis/jarvis-core/.env`. Accès `ssh denis@192.168.1.142` (clé SSH ; il a fallu **réparer les permissions Windows** de `~/.ssh/id_ed25519` via `icacls /inheritance:r /grant:r "PCDENIS\s2dre:F"` — la clé était rejetée « UNPROTECTED PRIVATE KEY FILE »).

**Divergence diagnostiquée (et pourquoi un scp brutal aurait régressé)** : la VM porte du travail **non versionné dans le dépôt local** — commits VM (`fix mail`, sous-agent mail IMAP, agenda Google, programme TV Freebox) absents en local, **+** modifications **non commitées** sur la VM (`main.py` +64 = système Muriel/`_apply_title`, `command_router.py` +1 = `delete_event`, plus `agenda_*`, `tahoma_agent`, `llm_client`, `personality.md`). **Preuve SHA256** : mon `HEAD` local == working tree VM **à l'octet près** pour `main.py`, `core/command_router.py`, `domain/types.py` (contenu identique, historique git divergent). Donc mes fichiers locaux (HEAD **+** RBAC non commité) **SONT** le résultat fusionné correct → aucune fusion manuelle, et les fichiers VM non touchés (mail/agenda/tahoma) restent intacts.

**Filet de secours** : sauvegarde complète **`/opt/jarvis/_backup-rbac-20260603-054033`** = patch des modifs non commitées (`git diff HEAD`) + `.bak` de main/command_router/types + copie du `.env` + `git bundle --all` (vérifié OK). Rollback = restaurer les `.bak`, supprimer `policy/roles.py`, restart.

**Greffe appliquée** : `scp` des 4 fichiers (`jarvis/main.py`, `jarvis/core/command_router.py`, `jarvis/domain/types.py`, `jarvis/policy/roles.py` neuf) en LF aux bons emplacements → `py_compile` VM OK. **Compte jury** ajouté dans `JARVIS_EXTRA_USERS` du `.env` VM via script idempotent **sans jamais lire/afficher le `.env`** : `{"username":"jury","role":"visiteur"}` (titre hérité du défaut de rôle `roles.py` = « Votre Sagacité » ; mot de passe **hérité du compte principal**). `.env` sauvegardé 2× avant modif. `sudo systemctl restart jarvis.service`.

**Vérifications post-déploiement** : `/healthz` → `{"status":"ok","mode":"production","tts_loaded":true}` (l'app redémarre avec **tous** les modules = non-régression mail/agenda confirmée). Routes RBAC câblées (`/auth/welcome`, `/admin/roles`, `/admin/disconnect-role` → **401** sans token). **Smoke test 39/39 dans l'environnement Python réel de la VM** (in-process, comptes de test isolés, mode mock). Chemin **front → n8n cloud → VM** vérifié : webhooks `jarvis-login` / `jarvis-welcome` / `jarvis-admin` relaient (401 sans token). Front local lancé (`npm run dev`, `localhost:3000`) — n'a que `.env.production` (non chargé en dev) → utilise les webhooks cloud par défaut.

**RESTE À FAIRE** :
1. **Denis teste de ses mains ce soir** (login `jury` avec son mot de passe habituel → accueil « Votre Sagacité » + bridage + orientation visio ; login `denis` → bouton Admin + élévation en direct + déconnexion jury). ⚠️ VM en **mode production** : une action en admin/jury-élevé pilote un **vrai** appareil.
2. Si OK → **réconciliation git propre** : rapatrier le travail VM (mail/agenda/Muriel/correctifs) dans le dépôt local, fusionner avec le RBAC, **committer** la branche `feat/rbac-jury`, remettre la VM sous contrôle git.
3. **FTP** du front sur Hostinger `/jarvis/` (`npm run build` → `out/` → `/jarvis/`).
4. Envisager un **mot de passe jury distinct** + nettoyer `_backup-rbac-*` une fois validé.

*Section ajoutée le 03/06/2026 (Anto). Test manuel reporté au soir du 03/06 à la demande de Denis.*

---

## 31. Session 03/06/2026 soir — Tests RBAC en ligne + correctifs latence/voix/accueil

> **Statut : TOUT déployé EN LIGNE (backend VM + n8n + front public `jarvis.creatorsystemia.fr`). RIEN n'est commité (ni VM, ni local).** Réconciliation git toujours en attente (§30.12.2). Sauvegardes `.bak` horodatées sur la VM pour chaque fichier touché.

### 31.1 Bug initial corrigé — plantage « Unexpected end of JSON input »
- **Symptôme** : en tant que `jury`, une question de **conversation** plantait (`Unexpected end of JSON input`).
- **Cause racine (prouvée par n8n, exéc 15577)** : le nœud HTTP « Appel Jarvis Freebox » avait un **timeout de 15 s** ; les réponses longues (LLM + synthèse Edge-TTS) dépassaient 15 s → n8n renvoyait un **corps vide** → `JSON.parse('')` côté front.
- **Correctifs** : (a) `front jarvis-api.ts` → `parseJsonOrThrow()` (plus jamais de crash sur corps vide, message majordome). (b) `main.py` → synthèse vocale **bornée** `TTS_SYNTH_TIMEOUT_S = 20.0` (au-delà → repli voix navigateur, jamais de blocage). (c) `personality.md` → **réponses orales brèves (2-3 phrases)**. (d) **n8n Command Bridge** : timeout **15 s → 45 s**.

### 31.2 RBAC — confirmé intact (pas de régression)
- `_load_users()` (avec `.env` chargé) : **`denis`=admin, `jury`=visiteur, `Muriel`=admin**.
- Logique de blocage prouvée : **visiteur → niveaux autorisés = []** (garage/lumière refusés) ; admin = tout. `pytest` **22/22** (dont 13 RBAC).
- Piège compris : sur une **question** (« est-ce que tu *vas* ouvrir le garage ») le LLM **converse** (aucune commande émise) → le RBAC ne bloque que les **ordres**. Le visiteur a le droit de discuter.

### 31.3 Le LLM connaît désormais le rôle de l'appelant (anti-divulgation)
- Avant : sur une question méta, le LLM **inventait** (« je n'ai pas de config », « accès complet ») et **révélait l'archi** (variable d'env, tool_call).
- Fix : `llm_client._build_system_prompt(role)` injecte un **bloc « CONTEXTE D'ACCÈS — IMPÉRATIF »** (visiteur = aucune action, ne jamais prétendre exécuter, ne jamais mentionner config/mécanisme ; locataire = confort only). `command_router.handle_text` passe `role` à `plan_in_conversation(role=…)`.

### 31.4 Voix : markdown + cohérence Andrew
- **Astérisques prononcés** (« astérisque ») → `main.py._strip_markdown()` retire `* # \` >` et puces **avant TTS et avant affichage** ; `personality.md` interdit le markdown.
- **Voix navigateur anglaise sur réponses longues** : c'était la borne TTS à 9 s (trop serrée) → remontée à **20 s** (présentation ~13 s observée conservée en Andrew, < 45 s n8n).

### 31.5 Identité / nom d'adresse — DÉCISION FINALE : « Monsieur »
- « Votre Sagacité » jugé trop lourd → **`DEFAULT_TITLE_BY_ROLE` = « Monsieur » pour tous les rôles**.
- Une étape « Comment dois-je vous appeler ? » (saisie vocale, nom non persisté, visiteur only) a été **construite puis ENTIÈREMENT SUPPRIMÉE** à la demande de Denis (voix féminine navigateur qui se chevauchait, prise de tête). **`NamePrompt.tsx` supprimé.** Jarvis dit « Monsieur ». (Le param backend `display_name` et le relai n8n restent en place mais **inertes** — le front ne l'envoie plus.)

### 31.6 Accueil automatique enrichi + noms corrigés
- **Noms** : « Denis **Solé** » (accent, sinon TTS lit « solde ») et « **IApreneurs Academy** » (≠ « Creator Academy ») — corrigés dans `auto_introduction.md` + `auto_introduction_brief.md` (le brief alimente les réponses « présente-toi ») **et** dans `welcome_speech`.
- **`welcome_speech(visiteur)`** réécrit : se présente + **conseille le bouton micro** (mains libres perfectible) + annonce les **accès restreints par sécurité** + oriente visio. Joué **automatiquement à la connexion** (plus besoin de demander « présente-toi »).
- **Accueil rejoué à CHAQUE connexion** : `app/page.tsx` — drapeau `WELCOME_FLAG` lié au **token de session** (et non plus un booléen figé), retiré en cas d'échec.

### 31.7 ⚠️ BUG OUVERT À VÉRIFIER DEMAIN — accueil muet en ligne
- En **local** l'accueil jouait. **En ligne** (`jarvis.creatorsystemia.fr`), Denis rapporte « il ne se présente pas ».
- **Backend OK** (exéc welcome 15612 : renvoie `speak` + `speak_audio_base64` + « Solé »/« IApreneurs », role visiteur). **CORS OK** (les 3 webhooks répondent `Access-Control-Allow-Origin: *`). → Le souci est **côté navigateur** (autoplay refusé : le MP3 arrive ~8-14 s après le clic de connexion, hors fenêtre d'autorisation).
- **Fix déployé** : bouton **« 🔊 Écouter la présentation de Jarvis » TOUJOURS visible** dès réception de l'accueil (contourne l'autoplay — un clic = geste frais = son garanti).
- **À FAIRE DEMAIN** : Denis recharge en vidant le cache (Ctrl+Maj+R), reconnexion `jury`, et confirme : (1) le bouton bleu 🔊 apparaît-il ? (2) le texte de présentation s'affiche-t-il ? (3) la voix part-elle au clic ? Si « rien ne s'affiche » persiste → inspecter la console navigateur.

### 31.8 Mot de passe jury distinct
- Aujourd'hui `jury` (et `Muriel`) **héritent** du mot de passe principal.
- Script déposé : **`/opt/jarvis/jarvis-core/set_jury_password.sh`** (saisie **masquée**, sauvegarde `.env`, restart auto). Denis le lance lui-même : `ssh -t denis@192.168.1.142 "bash /opt/jarvis/jarvis-core/set_jury_password.sh"`. Anto ne voit jamais le mot de passe.

### 31.9 Cartographie technique (rappel)
- **Backend** : `ssh denis@192.168.1.142`, venv `/opt/jarvis/jarvis-core/.venv`, `jarvis.service` port **8765**, joint depuis n8n via IP publique Free **88.162.216.160:48765**.
- **Front public** : FTP **147.79.103.79** dossier **`/jarvis/`** (profil FileZilla « Creator system IA »). Build `output: export` → `out/` → FTP (script Python, creds extraits de FileZilla sans affichage — **autorisation explicite ponctuelle de Denis**). 71 fichiers.
- **n8n** (creatorweb.fr) : `jarvis-command` = `lWH7699zkSGpCqFj`, `jarvis-welcome` = `TRZwgoh1hOU2jNaZ`, `jarvis-admin` = `EyZs4FLgo8HcyFVI`, `jarvis-login` = `1HLZnQVovXg0dUii`.
- `.env.production` (front) ne contient que `NEXT_PUBLIC_JARVIS_WEBHOOK_URL` + `_LOGIN_URL` + `_USER_ID` ; WELCOME/ADMIN viennent des **défauts de `config.ts`** (creatorweb.fr).

### 31.10 Fichiers touchés (NON commités)
- **Backend VM + local** : `jarvis/main.py`, `jarvis/policy/roles.py`, `jarvis/orchestrator/llm_client.py`, `jarvis/core/command_router.py`, `config/prompts/personality.md`, `config/prompts/auto_introduction.md`, `config/prompts/auto_introduction_brief.md`, `tests/test_rbac.py` (mock `_FakeLLM` + param `role`).
- **Front local + déployé** : `src/lib/jarvis-api.ts`, `src/lib/voice.ts`, `src/lib/auth.ts`, `src/lib/config.ts`, `src/components/CommandComposer.tsx`, `src/app/app/page.tsx` ; **supprimé** `src/components/NamePrompt.tsx`.
- **n8n** : Command Bridge + Welcome Bridge modifiés (timeouts + relai display_name).

### 31.11 Reste à faire (demain et après)
1. **Vérifier l'accueil en ligne** (§31.7) — priorité.
2. **Réconciliation git + commit** (toujours en attente, §30.12.2) — rapatrier travail VM (mail/agenda/Muriel) + tous les correctifs de cette session, committer.
3. Mot de passe `jury` distinct (script prêt, §31.8).
4. Répétitions DEMO_SCRIPT, tournage, soumission (deadline **4 juin minuit** — J-1 !).

*Section ajoutée le 03/06/2026 au soir (Anto), à la demande de Denis. Tout déployé en ligne, rien commité. Reprise demain.*
