# ROADMAP — Jarvis Hackathon Creator Academy

**Source de vérité unique** pour le pilotage Jarvis jusqu'à la soumission.

- **Aujourd'hui :** 17 mai 2026
- **Deadline soumission :** 4 juin 2026 à minuit (**J-18, compte à rebours**)
- **Note calendrier externe (pas un livrable) :** atelier Tom (Academy) lundi 18 mai
- **Stratégie :** 4 axes parallélisables, chemin critique = Loom plan séquence
- **Dual-review Codex (17/05) :** GO-AVEC-CONDITIONS sur pivot — voir §Recommandations Codex en bas

---

## Vue d'ensemble — état J-18

| Phase | Statut | Détail |
|---|---|---|
| **A. Backend Python `jarvis-core`** | ✅ **Bouclée 14/05** | 10/10 tests, voix Andrew, intent local, audit HMAC, garde-fous, volet buanderie validé |
| **A.bis Pivot orchestrateur** | 🟡 **Acté 17/05** | PRD §15 à jour, ARCHITECTURE à mettre à jour, code à produire |
| **B. Front Hostinger (PWA + avatar)** | ⬜ À démarrer | Squelette Next.js, landing, PWA mobile, avatar HUD, dashboard |
| **C. Pont cloud (Cloudflare Tunnel)** | ⬜ À démarrer | Tunnel sur PC, n8n forward vers tunnel |
| **D. Vidéo Loom + soumission** | ⬜ À démarrer | Script, tournage, upload, soumission |

---

## Stratégie de parallélisation

```
Sem. 2 (19-25 mai)               Sem. 3 (26 mai - 4 juin)
┌─────────────────────────┐      ┌──────────────────────────────┐
│ ORCHESTRATEUR (2-3j)    │──┐   │                              │
│ TaHoma+Devialet+Agenda  │  │   │                              │
└─────────────────────────┘  │   │                              │
                             │   │                              │
┌─────────────────────────┐  ├──►│ INTÉGRATION end-to-end        │
│ FRONT HOSTINGER (5j)    │──┤   │ Polish + Mocks + Caches      │
│ Next.js + PWA + Avatar  │  │   │ Répétitions (10 passes)      │
└─────────────────────────┘  │   │                              │
                             │   │                              │
┌─────────────────────────┐  │   │ FREEZE 30/05                  │
│ CLOUD PONT (1-2j)       │──┘   │                              │
│ Cloudflare Tunnel + n8n │      │ Tournage Loom 2-3/06         │
└─────────────────────────┘      │ Soumission 4/06              │
                                  └──────────────────────────────┘
```

---

## Chemin critique (= ne PEUT PAS prendre du retard)

Toute slip sur ces items repousse mécaniquement la démo Loom :

1. **Cloudflare Tunnel fonctionnel** (J-10 max = 25/05) — sans tunnel, pas de démo mobile, le téléphone ne peut pas atteindre le PC
2. **PWA mobile installable** (J-8 max = 27/05) — vidéo Loom = téléphone, donc PWA = obligatoire
3. **Orchestrateur LLM en mode mock** (J-10 max = 25/05) — pour répéter sans dépendre des devices
4. **Avatar HUD 5 états (sans lip-sync bloquant)** (J-8 max = 27/05) — identité visuelle = critère de victoire jury, lip-sync en fallback
5. **MOCK MODE complet sous-agents** (J-5 max = 30/05) — repo public reproductible
6. **Script Loom validé** (J-4 max = 31/05) — répéter avant de tourner
7. **Replay Loom complet tourné AVANT 2/06** (Codex) — backup au cas où le tournage final foire

**Tout le reste = polish, peut glisser de 1-2 jours sans casser la démo.**

---

## Détail jour par jour

### Sem. 2 — 18 au 25 mai : Sprint orchestrateur + Front démarrage

| Date | Jour | Axe | Tâche | Livrable |
|---|---|---|---|---|
| Lun 18/05 (PM) | J-17 | DOC | Mettre à jour `ARCHITECTURE.md` (§3 + §4) pour refléter pivot orchestrateur | ARCHITECTURE.md à jour |
| Mar 19/05 | J-16 | ORCHESTRATEUR | Créer `orchestrator/llm_client.py` (Claude Haiku 4.5 + prompt système majordome) | LLM répond en français majordome |
| Mar 19/05 | J-16 | ORCHESTRATEUR | Créer `subagents/base.py` (Protocol SubAgent + metadata, Pydantic `extra="forbid"`) | Contrat sous-agent figé |
| Mer 20/05 | J-15 | ORCHESTRATEUR | `subagents/tahoma_agent.py` (10 tools : list_devices, open/close_shutter, open_gate, open_garage, set_alarm, set_position…) | Sous-agent TaHoma testé en mock |
| Mer 20/05 | J-15 | ORCHESTRATEUR | `subagents/devialet_agent.py` (5 tools : play_zone, set_volume, stop, set_source, mute) | Sous-agent Devialet testé en mock |
| Jeu 21/05 | J-14 | ORCHESTRATEUR | `subagents/agenda_agent.py` (5 tools : list_today, list_tomorrow, create_event, find_slot, delete_event) — réutilise OAuth Creation Devis | Sous-agent Agenda testé sur calendrier réel |
| Jeu 21/05 | J-14 | ORCHESTRATEUR | `orchestrator/registry.py` + `orchestrator/tool_router.py` | Routage tool_call → DeviceCommand typée |
| Ven 22/05 | J-13 | ORCHESTRATEUR | Refactor `core/orchestrator.py` : fast-path local OR slow-path LLM (seuil confiance 0.85) | Pipeline complet bout-en-bout en mock |
| Ven 22/05 | J-13 | ORCHESTRATEUR | Tests : 5 commandes simples + 3 commandes composites ("mode cinéma" = 3 tool_calls) | 8/8 tests passent |
| Ven 22/05 | J-13 | FRONT | Squelette Next.js `jarvis-cloud` + déploiement Hostinger (skeleton landing) | URL publique vivante |
| Sam 23/05 | J-12 | FRONT | Landing page + Dashboard temps réel (lit audit SQLite via API) | Landing + dashboard visibles |
| Sam 23/05 | J-12 | FRONT | PWA manifest + service worker (installable mobile) | "Ajouter à l'écran d'accueil" fonctionne |
| Dim 24/05 | J-11 | FRONT | Composant MicButton + envoi audio HTTPS + retour TTS audio | Boucle vocale PWA → backend → PWA OK |
| Dim 24/05 | J-11 | FRONT | Avatar HUD Canvas 2D : 5 états (idle/listening/thinking/speaking/action) — **PRIORITAIRE** | Avatar réactif aux états |
| Lun 25/05 | J-10 | CLOUD | Cloudflare Tunnel installé sur PC Denis | Tunnel up + URL HTTPS atteignable |
| Lun 25/05 | J-10 | CLOUD | Workflow n8n forward vers tunnel (au lieu du mock) | Webhook PWA → n8n → tunnel → backend |

**Fin sem. 2 — Livrable :** Denis sort son téléphone, parle dans la PWA, l'orchestrateur LLM compose, les sous-agents exécutent (mode mock par défaut, prod si Denis active explicitement), l'avatar bouge les lèvres.

---

### Sem. 3 — 26 mai au 4 juin : Polish + Loom + Soumission

| Date | Jour | Axe | Tâche | Livrable |
|---|---|---|---|---|
| Mar 26/05 | J-9 | FRONT | Avatar : lip-sync Web Audio API (bouche varie selon amplitude TTS) — **NICE-TO-HAVE, fallback si timing serré** | Lip-sync visible |
| Mar 26/05 | J-9 | INTÉGRATION | Test end-to-end depuis téléphone réel (4G + WiFi maison) | Latence mesurée < 6s |
| Mer 27/05 | J-8 | POLISH | MOCK MODE complet sous-agents (jury clone → ça marche sans devices) | `docker-compose up` → démo locale |
| Mer 27/05 | J-8 | POLISH | Cache Claude (prompt caching) sur prompts système majordome | Latence Haiku < 300ms après warm-up |
| Jeu 28/05 | J-7 | POLISH | Fallbacks : mode replay vision (Phase E, optionnel), mode manuel bouton démo | Plan B sécurisé |
| Ven 29/05 | J-6 | POLISH | Personnalité majordome : few-shot examples + cache phrases canoniques | Voix cohérente sur 20 prompts test |
| Ven 29/05 | J-6 | DÉMO | Rédiger `DEMO_SCRIPT.md` (script précis 5 min, 5 scènes, transitions, voix off) | Script validé |
| Ven 29/05 | J-6 | TOURNAGE | **Replay Loom complet — tournage de sécurité (Codex)** | Backup Loom existant |
| **Sam 30/05** | J-5 | 🚧 FREEZE | **FREEZE CODE — plus aucune nouvelle feature** | Tag git `v1.0-freeze` |
| Sam 30/05 | J-5 | RÉPÉT | Répétition 1 (à blanc, sans tournage) | Note des bugs |
| Dim 31/05 | J-4 | RÉPÉT | Répétitions 2-3 (en conditions réelles) | Bugs critiques corrigés uniquement |
| Lun 1/06 | J-3 | RÉPÉT | Répétitions 4-6 | Timing optimisé |
| Mar 2/06 | J-2 | TOURNAGE | **Tournage vidéo Loom plan séquence (prise 1)** | Brouillon Loom |
| Mar 2/06 | J-2 | TOURNAGE | Tournage Loom plan séquence (prise 2 si nécessaire) | Loom validé |
| Mer 3/06 | J-1 | LIVRABLES | Tutoriel vidéo explicatif (architecture, 2 min) | Vidéo secondaire |
| Mer 3/06 | J-1 | LIVRABLES | README final + screenshots + lien Loom embed sur site | Repo public propre |
| **Jeu 4/06** | J-0 | 🏁 SOUMISSION | **Soumission formulaire avant minuit** | ✅ Soumis |

---

## Bonus / Stretch (si temps en sem. 3)

| Item | Effort | Priorité |
|---|---|---|
| Wake word "Jarvis" (porcupine / openwakeword) | 4h | Basse — pas critique pour démo |
| Vision ALPR caméra (Phase E) | 2j | Très basse — V2 explicite |
| Migration avatar 2D → 3D Three.js | 1j | Très basse — Canvas 2D suffit pour la démo |
| Sous-agent Lemlist (V1.5) | 0.5j | Basse — démo plus impressionnante mais non-essentiel |

---

## Checkpoints & garde-fous projet

### Calendrier Academy (info passive — pilotée par l'orga, pas un livrable)
- Lundi 18 mai : Atelier Jarvis + hardware avec Tom
- Lundi 25 mai : Networking Academy
- Jeudi 28 mai : DevWithMe #2 avec Tylian
- Lundi 1er juin : Q&R dernière ligne droite avec Tom

> Denis n'a rien à préparer pour ces sessions. Elles peuvent éclairer des choix mais ne sont pas comptées dans le planning de travail.

### Garde-fous projet (hors code)
- **Pas de nouvelle feature après 30 mai 23h59** — freeze strict
- **2 prises de tournage Loom minimum** prévues (2/06 + buffer 3/06)
- **Backup matériel** : laptop + 4G + 1 volet portable pour le meetup 19 juin si présélectionné

### Sécurité — règle absolue (rappel, §9 PRD)
À chaque session :
- [ ] `.env` non commité
- [ ] Aucune log avec secrets
- [ ] Tests mock passent
- [ ] Mode prod nécessite 2 variables env (`EXECUTION_MODE=production` + `ALLOW_REAL_DEVICES=true`)
- [ ] Audit HMAC vérifiable

---

## Risques bloquants identifiés (révisé post-Codex 17/05)

**Top 3 révisé par Codex (verdict GO-AVEC-CONDITIONS) :**

| # | Risque | Probabilité | Mitigation | Owner |
|---|---|---|---|---|
| 1 | **Scope front/avatar/PWA qui mange le calendrier** ⚠️ Codex risque #1 | Élevée | Avatar 5 états = obligatoire, lip-sync = nice-to-have repoussable. Freeze front à J-8 max. | Denis |
| 2 | **End-to-end mobile audio** (permissions micro, autoplay, latence STT/TTS, réseau 4G) | Élevée | Test sur téléphone réel dès J-11. Plan B = HTTPS local sur réseau maison si 4G foire. | Denis |
| 3 | **Démo dépendante du réel** (tunnel + VPS + LAN + TaHoma + APIs) | Moyenne | Mode mock complet à J-5, replay Loom déjà tourné à J-6 (Codex). | Denis + Anto |

**Risques secondaires :**

| Risque | Probabilité | Mitigation | Owner |
|---|---|---|---|
| **Latence orchestrateur LLM > 1.5s sur Haiku** | Moyenne | Speak-first pattern + prompt caching + fallback fast-path local | Denis + Anto |
| **Cloudflare Tunnel instable** | Faible | Tester tôt (J-10), fallback démo locale (PC + micro) | Denis |
| **Tournage Loom raté** | Faible | 2 prises prévues + replay backup tourné à J-6 (Codex) | Denis |
| **Hostinger PWA pas installable mobile** | Faible | Tester sur iPhone + Android dès J-12 | Denis |
| **OAuth Google Calendar à refaire** | Faible | Réutiliser celui de Creation Devis (Service Account déjà créé) | Denis |
| **Whisper local trop lent** | Faible | Modèle small déjà chargé, mesuré ~2s, OK | — |
| **Wake word non-fonctionnel** | Élevée | Bouton micro PWA = fallback assumé (pas critique) | — |
| **Prompt injection via audio (TV/enceinte) ou stored (mail/agenda V2)** | Moyenne | Validation Pydantic stricte `extra="forbid"`, enums fermées, marquage "données ≠ instructions", anti-replay nonce | Anto |
| **Vol Bearer Token n8n** | Faible | Rotation token avant démo, Cloudflare Access devant tunnel | Denis |

---

## Indicateurs hebdo (à updater chaque dimanche)

| Semaine | Livrable attendu | Statut |
|---|---|---|
| Sem. 2 (19-25/05) | Pipeline orchestrateur complet en mock + PWA installable + Cloudflare Tunnel up | ⬜ |
| Sem. 3 (26/05-1/06) | Démo Loom répétée 6 fois + freeze code | ⬜ |
| Final (2-4/06) | Loom tourné + soumis | ⬜ |

---

## Sources de vérité projet

| Doc | Rôle |
|---|---|
| [`PRD.md`](./PRD.md) | Cadrage produit, features, sécurité (§9), pivot orchestrateur (§15) |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Détail technique, schémas, couches, à mettre à jour §3 post-pivot |
| [`ROADMAP.md`](./ROADMAP.md) | Ce fichier — planning, chemin critique, checkpoints |
| `DEMO_SCRIPT.md` | À créer 29/05 — script précis 5 min |
| `jarvis-core/README.md` | Quick start backend, modes mock/prod/replay |
| `n8n-workflows/README.md` | Import workflow + curl examples |

---

*Roadmap créé le 17 mai 2026 — Denis Sole avec Anto (PAI). À updater chaque dimanche soir et après chaque checkpoint Academy.*

---

## Recommandations Codex (dual-review 17/05) — GO-AVEC-CONDITIONS

### Conditions du GO
1. **Pivot reste ADDITIF** : le backend `jarvis-core` actuel reste la source de vérité. Le LLM est ajouté comme couche mince **au-dessus**, jamais en remplacement.
2. **LLM = planificateur de `DeviceCommand` validées**, jamais d'exécuteur direct.
3. **Fast-path local prioritaire** : si `intent_engine_local.match()` confiance > 0.85 → bypass LLM.
4. **Pas de framework agentique lourd** (LangChain, mémoire complexe, agents autonomes) en V1.

### Critères de freeze 30/05 (J-5) — explicites Codex
- [ ] 5 scénarios démo passent en **mode mock** (replay déterministe)
- [ ] 2 scénarios passent en **mode réel** (devices physiques)
- [ ] Mode dégradé documenté (que se passe-t-il si Claude tombe ? si tunnel down ?)
- [ ] Test « commande LLM hallucinée rejetée » en démo/test (device_id absent du registry → audit log + réponse majordome)
- [ ] Test « commande critique demande confirmation » (PIN vocal 4 chiffres avant désactivation alarme)
- [ ] **Replay Loom complet déjà tourné AVANT le 2/06** (backup au cas où le tournage final foire)

### Garde-fous validation outputs LLM (à ajouter à l'orchestrateur)
- **Pydantic strict** : `model_config = ConfigDict(extra="forbid")` sur tous les types `DeviceCommand`
- **Enums fermées** : `action: Literal["open", "close", "set_position", ...]`
- **Registry allowlisté** : le LLM ne peut JAMAIS appeler un handler Python directement, uniquement `{domain, device_id, action, params}` résolu côté backend
- **Budgets par requête** : max N commandes/requête, max actions critiques/requête, timeout par tool
- **Confirmation obligatoire** sensible/critique même si le LLM « insiste »
- **Anti-replay** : nonce ou request_id + TTL côté n8n et backend
- **Logs complets** : transcript STT + tool-call brut LLM + DeviceCommand normalisée + décision Policy + résultat exécution
- **Marquage « données ≠ instructions »** : tout contenu mail/agenda/caméra injecté dans le prompt → bloc clairement délimité, jamais traité comme instruction

### Vecteurs d'attaque identifiés
| Vecteur | Surface | Mitigation |
|---|---|---|
| Injection audio via TV/enceinte | Whisper STT | Mode "écoute" explicite (push-to-talk PWA), pas de wake-word permanent en V1 |
| Stored prompt injection (mail/agenda en V2) | Sub-agent V2 | Marquage strict données/instructions + validation Pydantic |
| Hallucination device/action | Output LLM | Registry allowlisté + rejet + audit |
| Contournement par paramètres ambigus | tool_call args | Enums fermées + validation Pydantic |
| Répétition rapide d'ordres critiques | Policy | Élévation contextuelle automatique (déjà codé) |
| Vol Bearer Token n8n | Transport | Rotation token + Cloudflare Access |
| Tunnel exposant trop de surface | Cloud | Cloudflare Access auth Google devant tunnel |

### Désaccords actés avec Codex (mes positions initiales)
- ❌ Top 3 risques initial (tunnel/Haiku/Loom) → ✅ remplacé par top 3 Codex (scope front / audio mobile / dépendance réel)
- ❌ Compteur J+18 → ✅ corrigé en J-18
- ❌ Avatar lip-sync prioritaire → ✅ rétrogradé en nice-to-have (Codex risque #1)
- ✅ Confirmé : Option A (function-calling) suffisant pour V1
- ✅ Confirmé : Haiku 4.5 primaire, Sonnet 4.6 fallback, pas de LLM local pour démo
- ✅ Confirmé : sprint orchestrateur 2-3 jours réaliste **uniquement si MVP sec** (pas de framework lourd)

*Source dual-review : Codex GPT-5 (threadId `019e349b-6a71-7641-8625-3d62e6f4e138`), 17/05/2026.*
