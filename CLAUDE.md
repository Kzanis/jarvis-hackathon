# CLAUDE.md — Projet Jarvis (Hackathon Creator Academy)

> Mémoire de projet pour Claude Code. Lue automatiquement à l'ouverture du dépôt.
> Repo **public** : https://github.com/Kzanis/jarvis-hackathon — **JAMAIS de secret ici** (placeholders only).

## C'est quoi
Jarvis = majordome IA personnel **vocal, temps réel**, qui pilote la vraie maison de Denis Solé (volets, portail, garage, TV, agenda, mail). Thème 1 du hackathon (assistant vocal). Deadline soumission : **4 juin 2026 minuit**, vidéo Loom 5 min max.

## Architecture (3 couches)
1. **PWA** (front Next.js, dossier `jarvis-cloud/`, build statique) → hébergée sur **Hostinger**, `jarvis.creatorsystemia.fr`. Déploiement **FTP** (écraser le contenu de `out/` dans `/jarvis/`).
2. **n8n** (Hostinger, `creatorweb.fr`) → pont PWA ↔ backend : webhooks `/jarvis-login` + `/jarvis-command` (« Command Bridge »).
3. **Backend** FastAPI (`jarvis-core/`, Python) → tourne sur une **VM Ubuntu dans la Freebox Delta** (`192.168.1.142`, port `8765`), service systemd `jarvis.service`, repo cloné dans `/opt/jarvis`. Pilote les devices physiques.

`jarvis-core` suit une **architecture hexagonale** : `domain / policy / core / handlers / mocks / audit`, orchestrateur LLM multi-agents + **sous-agents** (`subagents/`) : `tahoma` (domotique), `freebox` (TV), `agenda` (Google Calendar), `mail` (Gmail IMAP lecture), `search` (web), `devialet`.

## Règles ABSOLUES
- 🔒 **Aucun secret dans le repo** (tokens, clés API, PIN box, IP publique, mots de passe). Tout vit dans `/opt/jarvis/jarvis-core/.env` sur la VM. Dans les docs : placeholders `<...>`.
- 🛡️ **Hook anti-secrets actif** : `git config core.hooksPath .githooks` (bloque tout commit contenant un secret). + GitHub Push Protection activé.
- 🚨 **Sécurité domotique** = priorité 1. Mode **mock par défaut** ; `ALLOW_REAL_DEVICES` requis pour le réel. **Confirmation orale obligatoire** pour les actions sensibles (portail, garage, alarme) et critiques. Au moindre doute → option la plus restrictive.
- Auth réelle = **login user/mot de passe** (sessions Bearer en mémoire, jeton 4h). `JARVIS_N8N_TOKEN` est un vestige non utilisé par le code.

## Gotchas exploitation
- **Sessions en mémoire** : tout `systemctl restart jarvis.service` les vide → se **reconnecter au PWA** après chaque redémarrage (sinon 401 → erreur « JSON input » côté PWA).
- **Pont n8n** coupe au-delà de ~15 s → garder les réponses LLM **courtes** (2-4 phrases).
- Succès API ≠ succès utilisateur (ex : TV Airmedia accepte mais ne diffuse pas le streaming externe).
- Modèle LLM : OpenRouter ne respecte pas `ANTHROPIC_MODEL` (Haiku par défaut) ; pour Sonnet, passer par l'API Anthropic directe.

## Documents clés
- `PRD.md` — cahier des charges + journal de sessions (récaps datés, V1/V2, roadmap).
- `ARCHITECTURE.md` — détail technique.
- `DEMO_SCRIPT.md` — script du Loom (6 scènes, plan séquence 5 min).
- `README.md` / `ARCHITECTURE.md` = vitrine jury (propres, sans secret).

## Sauvegarde
- Bundle git complet : `C:\Dev\jarvis-backup-20260529.bundle` (avant réécriture d'historique du 29/05).
