# MAKING_OF — Jarvis

> Le parcours du projet : par où on est passé, les problèmes rencontrés et comment on les a résolus, les virages stratégiques et leur justification — et le point d'honneur qui a guidé chaque choix technique : **zéro coût récurrent**.
>
> Hackathon Académie IApreneurs × Hostinger — Thème 01 « Assistant personnel IA, vocal, temps réel ».
> Période : 12 mai → 4 juin 2026. Repo public : https://github.com/Kzanis/jarvis-hackathon

---

## 0. En une page

Jarvis est un majordome IA qui **pilote physiquement une vraie maison** (volets, portail, garage, alarme, store, TV, son) et **gère le numérique** (mails, agenda, recherche web), commandé **à la voix depuis un téléphone**, le tout hébergé **dans la box internet** de Denis — sans aucun matériel supplémentaire ni abonnement cloud.

Le différenciateur assumé : là où 90 % des participants livreront un assistant qui *lit des mails dans un terminal*, Jarvis **ouvre le portail en live devant le jury**.

Trois semaines, un seul développeur (Denis Solé) assisté de son IA (Anto). Du dossier vide au système en production 24h/24, avec une règle non négociable : **la sécurité d'abord**, et un point d'honneur : **ne dépenser que le strict minimum** — zéro abonnement, zéro matériel acheté, zéro hébergement payant. Les seuls euros du projet vont à l'inférence IA, facturée à l'usage pour quelques centimes par interaction.

---

## 1. L'ambition et la contrainte fondatrice

**L'ambition** n'était pas modeste : pas un chatbot qui répond sur un écran, mais un **J.A.R.V.I.S. à la Tony Stark** — un majordome britannique qui agit sur le monde réel, parle naturellement (voix grave, humour pince-sans-rire), et s'utilise en mains libres.

**La contrainte fondatrice** posée dès le premier jour : comment empêcher Jarvis de faire une bêtise **irréversible** (ouvrir le portail à 3 h du matin sur une mauvaise interprétation, désactiver l'alarme par erreur) **sans** l'asphyxier de garde-fous au point de le rendre inutilisable ?

Toute l'architecture découle de cette tension. La réponse : un moteur de sécurité à **3 niveaux** (sûr / sensible / critique), une **élévation contextuelle** (la nuit, une commande sensible devient critique), un **journal d'audit cryptographique** infalsifiable, et un **double verrou** qui interdit toute action physique tant que deux variables d'environnement explicites ne sont pas posées.

---

## 2. Chronologie

| Date | Étape | Résultat |
|---|---|---|
| **12-14 mai** | **Phase A — le squelette** | Moteur Python `jarvis-core` en service : architecture hexagonale, 24 types métier, politique de sécurité 3 niveaux, audit HMAC. Premier volet ouvert pour de vrai (buanderie, 14/05). |
| **17 mai** | **Pivot orchestrateur LLM** | Ajout d'un planificateur Claude Haiku **au-dessus** du backend, pour gérer les commandes composées (« mode cinéma ») et les conversations multi-tours. Validé par dual-review Codex sous 4 conditions strictes. |
| **17 mai** | **Émancipation du PC** | Migration sur une **VM Ubuntu dans la Freebox Delta**. Jarvis tourne 24h/24 sans qu'aucun ordinateur ne reste allumé. PWA mise en ligne sur Hostinger (`jarvis.creatorsystemia.fr`). |
| **17-26 mai** | **Empilage des sous-agents** | TaHoma (domotique), Agenda Google (22/05), Mail Gmail (25/05), Recherche web Perplexity (25/05), TV Freebox (24/05). |
| **25 mai** | **Bugs P0 résolus** | Garage « ouvre mais ne ferme pas » + portail mal paramétré → corrigés (voir §3). PWA mains libres fiabilisée. |
| **28 mai** | **Journée des découvertes** | Pilier V2 « intendant énergie » émerge ; OAuth Anthropic invalidé ; TV streaming KO ; wow factor recentré sur le sous-agent dev. Auto-présentation interactive déployée. |
| **29 mai** | **Mise en vitrine** | Repo rendu **public et sécurisé** (historique réécrit, 0 secret, double garde-fou anti-fuite). `DEMO_SCRIPT.md` 6 scènes créé. |
| **2-4 juin** | **Tournage & soumission** | Répétitions, Loom (5 min max), soumission le 4 juin minuit. |

---

## 3. Les problèmes rencontrés et comment on les a résolus

> La partie la plus instructive du projet. Chaque ligne est un vrai obstacle vécu, son diagnostic, sa résolution et la leçon retenue.

### 3.1 La latence du pipeline : 1017 ms → 3 ms
- **Symptôme** : premier appel bout-en-bout mesuré à **1017 ms**. Inutilisable pour une démo « au premier appui ».
- **Résolution** : cache de signature d'audit, court-circuit des appels asynchrones inutiles, pré-compilation des regex d'intention, mémoïsation des alias.
- **Résultat** : **3 ms en moyenne** — une amélioration ×340.
- **Leçon** : la perception de « magie » en démo se joue sur la latence ressentie. On a aussi adopté le motif *« parler d'abord, exécuter ensuite »* (l'accusé vocal part avant la fin de l'action).

### 3.2 Le garage « ouvre mais ne ferme pas » (résolu 25/05)
- **Symptôme** : « ouvre le garage » marche, « ferme le garage » ne fait **rien**. Suspecté pendant des jours d'être un bug de l'orchestrateur LLM.
- **Vrai diagnostic** : l'outil `close_garage` **n'existait pas** dans le sous-agent TaHoma (seul `open_garage` était défini). Le LLM ne pouvait pas demander une action absente de son répertoire.
- **Résolution** : ajout de `close_garage` + `close_gate` par symétrie, branches `resolve()`, verbes de confirmation dans le routeur. Niveau sensible conservé (confirmation orale).
- **Leçon** : avant d'accuser le LLM, vérifier que **l'outil existe**.

### 3.3 Le portail qui ne répondait pas (résolu 25/05)
- **Symptôme** : le portail répond par intermittence, puis plus du tout. Logs : commande envoyée, accusé OK, mais le moteur ne bouge pas.
- **Vrai diagnostic** : **ce n'était pas le code Jarvis**. Le moteur du portail était **neuf** — posé peu avant par l'installateur, **sous garantie** (suite à un souci antérieur au hackathon). Mais il avait été **mal paramétré au niveau de sa carte mère**, et donc **pas correctement déclaré côté TaHoma**. Tant que ce réglage n'était pas corrigé, aucune commande ne pouvait l'atteindre de façon fiable.
- **Résolution** : Denis **diagnostique et corrige lui-même le paramétrage** — réglage de la carte mère du moteur + déclaration propre dans TaHoma. Côté code, le nouvel identifiant RTS est pris en compte, et un détail est traité : le label TaHoma comportait une **espace finale** → ajout d'un `.strip()` sur les labels au démarrage, sinon « Portail » ≠ « Portail ».
- **Leçon** : **tous les bugs ne sont pas dans le logiciel**. Ici le code était sain — le vrai problème était un paramétrage matériel à reprendre.

### 3.4 Le polling d'exécution abandonné
- **Symptôme** : on voulait confirmer le **mouvement réel** des appareils via `/exec/current` + `/history/executions`.
- **Problème** : faux négatifs (l'API locale renvoie 404/400 pour les appareils IO) + latence rédhibitoire (~60 s) pour une réponse vocale.
- **Résolution** : retour à un comportement simple — **succès = HTTP 200** (la box a accepté l'ordre). Bon comportement de majordome = confirmer la prise en compte immédiatement, pas attendre la fin physique.
- **Leçon** : la perfection technique (vérifier le mouvement réel) peut tuer l'expérience. On a choisi la réactivité.

### 3.5 n8n bloque `crypto` : HMAC → Bearer
- **Symptôme** : l'implémentation visée signait chaque requête en **HMAC-SHA256**. Or la version de n8n bloque `require('crypto')` dans les nœuds Code (`Module 'crypto' is disallowed`).
- **Résolution** : pont sécurisé par **Bearer Token sur HTTPS** (transmission chiffrée TLS, token 256 bits, rotation facile). Migration HMAC repoussée à quand n8n autorisera `crypto`.
- **Leçon** : s'adapter aux limites de la plateforme sans sacrifier la sécurité réelle (TLS + token long restent solides).

### 3.6 L'OAuth Anthropic ne marche pas en non-interactif (28/05)
- **Symptôme** : tentative de brancher Claude Code (sous-agent dev) avec le **token OAuth Max**. Verdict du CLI : `Credit balance is too low` — alors que le compte Max affichait 80 € disponibles.
- **Vrai diagnostic** : le mode `--bare` du CLI **rejette explicitement l'OAuth** (« *Anthropic auth is strictly ANTHROPIC_API_KEY...* »). L'abonnement Max et le crédit API console.anthropic.com sont **deux portefeuilles séparés**.
- **Résolution** : 5 € de crédit sur console.anthropic.com + clé API dédiée `jarvis-vm-freebox`. Premier appel OK en 1,3 s, coût 0,01 €.
- **Leçon** : mémorisée pour ne plus la refaire. Ce crédit Anthropic s'ajoute aux micro-paiements OpenRouter (voir §5) — l'IA reste le seul poste de dépense, et toujours à l'usage.

### 3.7 OpenRouter n'honore pas `ANTHROPIC_MODEL`
- **Symptôme** : on voulait Sonnet 4.6 via la variable `ANTHROPIC_MODEL` ; OpenRouter sert quand même **Haiku 4.5** par défaut.
- **Résolution / arbitrage** : Haiku est **largement suffisant** pour la planification d'intentions (et ~10× moins cher). Conservé. Si Sonnet est vraiment voulu un jour → passer par l'API Anthropic directe.
- **Leçon** : vérifier ce que le fournisseur **fait réellement**, pas ce qu'on lui demande.

### 3.8 La TV répond à l'auth mais pas au streaming (28/05)
- **Symptôme** : pairing Freebox réussi, session HMAC obtenue, receiver Airmedia identifié. Mais le cast d'une vidéo depuis une URL HTTPS externe renvoie `success: true` et… la TV **revient au tableau de bord** sans rien diffuser.
- **Résolution** : `success: true` côté API **≠** succès utilisateur. Sur dual-review Codex, **affichage TV repoussé en V2** (micro-spike plus tard avec critères stricts), pour ne pas mettre en péril le calendrier.
- **Leçon** : à J-7 du freeze, on **protège la démo** plutôt que de lancer une R&D incertaine.

### 3.9 Le mot-clé séparé de la commande (mains libres, 25/05)
- **Symptôme** : en dictée continue, « OK Jarvis, ferme le garage » arrive souvent en **deux résultats** (« OK Jarvis » puis « ferme le garage »).
- **Résolution** : le mot-clé **arme l'agent pour 12 s** ; le premier énoncé final suivant est traité comme commande. Si la phrase est dite d'un trait, ça marche aussi.
- **Bonus** : accusé vocal « Oui, Monsieur » **instantané** (voix locale du navigateur, pas d'aller-retour réseau) pour savoir que Jarvis écoute sans regarder l'écran.

### 3.10 L'erreur d'arrêt fortuite sur iOS
- **Symptôme** : l'API Web Speech d'Apple jette une erreur d'arrêt parasite → l'agent passait en ERREUR après chaque commande, rechargement de page obligatoire.
- **Résolution** : cette erreur précise est désormais **ignorée comme un simple silence** ; l'écoute reprend automatiquement. Bouton « quitter » réparé au passage.

### 3.11 Le gotcha des sessions en mémoire (à connaître pour la démo)
- **Symptôme** : après un redémarrage du service, le PWA renvoie une erreur « JSON input ».
- **Cause** : les sessions de login sont stockées **en mémoire** (`_SESSIONS` dans `main.py`). Tout `systemctl restart` les vide → jeton périmé → 401.
- **Parade démo** : se reconnecter au PWA **après le dernier redémarrage**, puis ne plus redémarrer. (Persistance disque = amélioration V2, hors scope freeze.)

---

## 4. Les pivots stratégiques et leur justification

| Pivot | De → vers | Pourquoi |
|---|---|---|
| **Cerveau** | Moteur d'intention local seul → **+ orchestrateur LLM par-dessus** | Le local attrape 80-90 % des commandes simples en 5 ms, mais bute sur les enchaînements et le multi-tours. Le LLM est **ajouté, jamais en remplacement** (fast-path local prioritaire si confiance > 0,85). |
| **Hébergement** | PC de bureau → **VM dans la Freebox** | Si le PC s'éteint, Jarvis meurt. La VM Freebox = gratuite, 24h/24, zéro hardware en plus. |
| **Signature du pont** | HMAC → **Bearer/TLS** | n8n bloque `crypto`. TLS + token 256 bits restent sûrs. |
| **Voix** | ElevenLabs (payant) → **Edge-TTS Andrew (gratuit)** | Qualité comparable, **0 €**, tourne sans GPU. |
| **Recherche web** | Module DuckDuckGo/Brave custom (4-6 h) → **Perplexity sonar via OpenRouter (1 h)** | Recherche + résumé en un appel, clé déjà payée. |
| **Démo portail** | Reconnaissance de plaque (caméra/ALPR) → **portail à la voix** | L'ALPR est trop risqué pour un plan séquence. Plaque = **V2**. |
| **Présentation** | Audio préenregistré → **auto-présentation interactive (LLM)** | Plus impressionnant ; Jarvis **se raconte lui-même** en direct. MP3 gardés en **filet de secours**. |
| **Wow factor** | Afficher sur la TV → **sous-agent dev (Jarvis qui code)** | Codex : le vrai effet wow n'est pas « la TV affiche une page », c'est « Jarvis comprend, délègue, produit, restitue ». La TV est un multiplicateur, pas le cœur. |

---

## 5. Le point d'honneur : zéro coût récurrent

C'est une **fierté du projet** et un argument de fond face au jury : Jarvis a été construit pour ne **rien coûter en récurrent**. Chaque brique a été choisie pour éviter l'abonnement, en assumant parfois un peu plus d'effort technique en échange.

| Brique | Solution **gratuite** retenue | Alternative **payante** écartée |
|---|---|---|
| Reconnaissance vocale (voix → texte) | **Whisper local** (offline, français) | API STT cloud (OpenAI/Google) |
| Compréhension d'intention (NLU) | **rapidfuzz local**, 0 API, < 5 ms | LLM systématique sur chaque commande |
| Synthèse vocale (texte → voix) | **Edge-TTS Microsoft « Andrew »**, illimité | ElevenLabs (~5-22 €/mois) |
| Backend 24h/24 | **VM Ubuntu dans la Freebox Delta** | VPS dédié (5-10 €/mois) ou Raspberry Pi (≈ 80 €) |
| Orchestration cloud (pont) | **n8n self-hosted** sur le VPS Hostinger **déjà payé** | Make / Zapier (abonnement) |
| Exposition maison ↔ cloud | **Port forwarding Freebox / Cloudflare Tunnel** | ngrok payant, IP fixe |
| Front PWA | **Next.js statique** sur l'hébergement Hostinger **déjà là** | Vercel Pro (20 $/mois) |
| Journal & stockage | **SQLite local** (audit HMAC) | Base de données cloud |

### Les seuls coûts : l'inférence IA, à l'usage

La frugalité ne porte pas sur l'intelligence elle-même : comprendre le langage naturel et chercher sur le web a un coût. Mais ce coût est **minime, à l'usage** (jamais d'abonnement), et il transite par des comptes **déjà existants** :

| Brique IA payante | Fournisseur | Modèle | Facturation |
|---|---|---|---|
| Orchestrateur (comprend les commandes) | **OpenRouter** | Claude Haiku 4.5 | à l'usage — ~0,01 € par commande |
| Recherche web (actualité, questions factuelles) | **OpenRouter** | Perplexity `sonar` | à l'usage — facturé par requête |
| Sous-agent dev (Claude Code, V2) | **Anthropic API** | Sonnet 4.6 | 5 € de crédit ajoutés le 28/05 |

> **Aucun abonnement. Aucun matériel acheté. Aucun hébergement payant dédié.** Les seuls euros du projet vont à l'inférence IA, facturée à l'usage pour quelques centimes par interaction.

Cette discipline n'est pas qu'une coquetterie : elle rend le projet **reproductible et défendable**. Un assistant qui coûte 30 €/mois d'abonnements n'a pas le même avenir qu'un assistant qui tourne dans la box qu'on possède déjà, et dont la seule dépense variable est l'IA, payée à la goutte.

---

## 6. Architecture finale en bref

```
☁️  COUCHE CLOUD (Hostinger)          🏠  COUCHE MAISON (VM Freebox)      🔌  COUCHE PHYSIQUE (LAN)
   PWA Next.js + avatar HUD              FastAPI jarvis-core                Somfy TaHoma (volets, portail,
   n8n « Command Bridge » (Bearer)  ──►  Orchestrateur + Policy Engine ──► garage, alarme, store, lampe)
   Login + jeton 4 h                     Intent local (rapidfuzz)          Freebox Player (TV, son Devialet)
                                         Audit SQLite HMAC
                                         Sous-agents (TaHoma, TV,
                                         Agenda, Mail, Recherche)
```

**Asymétrie de sécurité voulue** : la PWA n'a **aucun** accès direct à TaHoma, à la Freebox ou à Google. Tout transite par le backend sur la VM. Si la PWA est compromise, l'attaquant n'a que des jetons éphémères et un journal d'audit qui trace ses tentatives.

---

## 7. État au 30 mai + ce qui reste

**Bouclé** : core sécurisé, orchestrateur LLM, déploiement VM 24h/24, sous-agents (domotique, TV, agenda, mail, recherche), PWA mains libres, bugs P0 résolus, repo public assaini, `DEMO_SCRIPT` v2 (6 scènes), auto-présentation interactive, 4 MP3 de secours.

**Reste avant le 4 juin** :
1. Tester la **prise de RDV** (écriture agenda) → la garder en démo ou la passer en promesse V2.
2. Régler le **délai n8n** (le pont coupe au-delà de ~10-15 s sur les réponses longues).
3. **Répétitions** → tournage Loom (2-3/06) → soumission (4/06 minuit).

**Roadmap V2 (slide jury)** : pilier « **intendant énergie** » (chasse aux veilles + tableau de bord conso + présence/chauffage), sous-agent dev (Jarvis qui code), affichage TV, auto-correction, briefing matinal, envoi de mail, alertes intrusion.

---

## 8. Ce que ce projet démontre

- Un assistant vocal **qui agit sur le monde réel**, pas un chatbot de plus.
- Une **sécurité par conception** (3 niveaux, élévation contextuelle, audit cryptographique, double verrou prod).
- Une **frugalité radicale** : zéro abonnement, zéro matériel, hébergé dans la box ; les seuls coûts sont l'inférence IA à l'usage (quelques centimes par interaction).
- Une **honnêteté d'ingénierie** : on a documenté les échecs (TV, OAuth, portail mort) autant que les réussites — c'est ce qui rend le parcours crédible.

> *« Une phrase, et la maison se range. Pas un chatbot : un majordome qui agit. »*

---

*Document rédigé le 30/05/2026 par Denis Solé avec Anto (PAI). Sources : `PRD.md`, `auto_introduction.md`, journal des sessions. Aucun secret n'y figure (placeholders conformes au repo public).*
