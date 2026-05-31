# 🎬 DEMO_SCRIPT — Jarvis (Loom hackathon Creator Academy)

> Brouillon v2 — 29/05/2026. Plan séquence unique, **5 min MAX** (règle officielle 02 du hackathon).
> Critère de jugement : *« Que ça fonctionne en live. Que ça impressionne au premier appui. »*
> Livraison : **lien** (Loom), pas de fichier joint.

---

## 0. Cadre de production

- **Format** : une seule prise, pas de cut, ≤ 5 minutes.
- **Split-screen** : à gauche le téléphone (PWA + avatar HUD), à droite l'action réelle (volet, portail, TV…).
- **Authenticité** : horloge live à l'écran + un élément imprévisible du jour (mail réel, météo).
- **Voix off Denis** : explique l'architecture pendant que Jarvis agit.
- **Ton de Jarvis** : majordome britannique pince-sans-rire, réponses brèves (2-4 phrases).

### ✅ Checklist AVANT d'enregistrer (critique)
1. **Dernier redémarrage du service FAIT** → ensuite **NE PLUS redémarrer** (sessions de login en mémoire).
2. **Se reconnecter au PWA APRÈS ce dernier redémarrage** (sinon jeton périmé → erreur « JSON input »).
3. Backend : `healthz` → `{status:ok, mode:production}`.
4. **Devices en position de départ** : portail fermé, volets salon fermés, **volet du bureau de Denis OUVERT** (pour le contre-jour du cold open), TV éteinte, lampes éteintes.
5. **Valider la veille** : lecture mails OK + lecture agenda OK + **création de RDV testée** (sinon scène 2 en lecture seule — voir ⚠️).
6. **Filet de sécurité** : 4 MP3 Edge-TTS (`demo_audio/`) prêts.
7. **Lumière de face sur Denis** (cold open) : une source frontale t'éclaire ; la fenêtre derrière = contre-jour. Fermer le volet doit te rendre **net**, pas t'assombrir.

> ⚠️ **Garde-fou réponses longues** : le pont n8n coupe au-delà de ~15 s → commandes à **réponse courte**. Les explications (identité, V2) restent en 2-4 phrases (le prompt système l'impose déjà).

---

## Scène 0 — Cold open : « La lumière » · ~40-50 s

> Plan unique, **pas de cut**. Fenêtre du bureau de Denis derrière lui, volet **ouvert** → fort contre-jour (on le voit mal). **Lumière de face obligatoire** (sinon fermer le volet l'assombrit au lieu de l'éclairer).

| | |
|---|---|
| 🎙️ Denis *(plissant les yeux)* | « Bon… franchement, cette lumière en contre-jour, ça ne va pas du tout. On n'y voit rien. » |
| 🎙️ Denis | « Jarvis ? Ferme le volet **du bureau de Denis**, s'il te plaît. » |
| 🤖 Jarvis | « Bien, Monsieur. » *(instantané, voix grave)* |
| 👁️ Écran | Sans coupure : le volet descend, le contre-jour s'efface, le visage de Denis devient net. |
| 🎙️ Denis *(sourire)* | « … Voilà. Tout de suite mieux. » |

Puis, face caméra (désormais bien éclairé) :

> « Bonjour. Je m'appelle **Denis Solé**. Après 35 ans dans le BTP, j'aide aujourd'hui les artisans et les PME à mettre l'IA au travail, avec Creator System IA. Autant vous dire que le "monde réel" — le chantier, les volets, les portails — c'est mon terrain. »
>
> « Ce que vous venez de voir, **ce n'est pas un montage**. C'est Jarvis, l'assistant que j'ai construit pour ce hackathon. Et voici, en deux mots, pourquoi. »
>
> *(genèse, court)* « Il y a trois semaines, Tom postait ici même, dans l'Académie : *"L'IoT, une nouvelle opportunité — commencez chez vous."* Sauf que ma maison est **déjà** entièrement domotisée. Je n'avais pas à commencer : je pouvais aller droit au but. Alors quand le hackathon a ouvert sur l'assistant vocal… **c'était tout trouvé.** »
>
> « Pas un chatbot de plus qui lit des mails sur un écran. Un majordome qui agit, pour de vrai, sur une vraie maison. Je vous montre. »

**But** : accroche incarnée + **preuve live anti-truquage** (le contre-jour disparaît à l'image) + le "pourquoi" du projet. Le lien du post de Tom est cité dans `MAKING_OF.md` (section Genèse).

> 💡 La Scène 1 ci-dessous (Jarvis se présente) peut être **raccourcie ou fusionnée**, puisque l'identité est déjà posée ici.

> ✅ Commande validée physiquement le 31/05 (« ferme le volet du bureau de Denis » → volet 1218264).

---

## Scène 1 — « Bonjour » · identité · ~30 s

| | |
|---|---|
| 🎙️ Denis | « OK Jarvis. Bonjour, présente-toi en une phrase. » |
| 🤖 Jarvis | Salutation + qui il est (2 phrases, ton majordome). |
| 👁️ Écran | Avatar HUD animé + accusé « Oui Monsieur ». |
| 🎧 Voix off | « Jarvis tourne 24h/24 sur une VM dans ma Freebox. Tout est généré en direct. » |

**But** : poser le personnage, prouver le live.

---

## Scène 2 — « Ma journée » · MAILS + AGENDA (lecture + prise de RDV) · ~80 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, j'ai des mails importants ce matin ? » |
| 🤖 Jarvis | Résume les non-lus / récents (IMAP Gmail). |
| 🎙️ Denis | « Et qu'est-ce que j'ai au programme aujourd'hui ? » |
| 🤖 Jarvis | Liste les rendez-vous du jour (Google Agenda). |
| 🎙️ Denis | « Ajoute un rendez-vous demain à 14h : point chantier. » |
| 🤖 Jarvis | **Confirmation** puis création de l'événement → « C'est noté, Monsieur. » |
| 👁️ Écran | Mail réel + agenda réel = preuve d'authenticité ; l'événement apparaît dans l'agenda. |
| 🎧 Voix off | « Lecture des mails, lecture de l'agenda, et écriture : Jarvis gère vraiment ma journée. Tout contenu de mail est traité comme une donnée, jamais comme une instruction. » |

> ⚠️ **Prise de RDV (écriture agenda)** : codée, niveau *sensible*. **À tester en vrai avant le tournage.** Si non concluant : garder uniquement lecture mails + lecture RDV (toujours impressionnant), et basculer la création en promesse V2.

**But** : montrer l'assistant personnel complet (info entrante + action sur l'agenda).

---

## Scène 3 — « Ambiance » · VOLETS + TV · ~75 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, ouvre les volets du salon. » |
| 🤖 Jarvis | Accuse + exécute. |
| 👁️ Écran (droite) | Les volets montent **pour de vrai** (TaHoma). |
| 🎙️ Denis | « Parfait. Maintenant allume la télé et mets YouTube. » |
| 🤖 Jarvis | Accuse + allume la TV + ouvre l'appli (Player Freebox). |
| 👁️ Écran (droite) | La TV s'allume, l'appli s'ouvre. |
| 🎧 Voix off | « Un ordre, deux mondes : les volets via TaHoma, la télé via le Player Freebox. » |

**But** : domotique visible + effet « waouh » multi-appareils.

---

## Scène 4 — « Le portail » · SÉCURITÉ (confirmation orale) · ~45 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, ouvre le portail. » |
| 🤖 Jarvis | **Confirmation obligatoire** (niveau sensible) : « Vous confirmez l'ouverture du portail, Monsieur ? » |
| 🎙️ Denis | « Oui. » → exécution. |
| 👁️ Écran (droite) | Le portail s'ouvre **physiquement** (moteur neuf). |
| 🎧 Voix off | « Action à fort impact = Jarvis demande confirmation avant d'agir. C'est la sécurité par conception. La reconnaissance de plaque qui ouvrira tout seul, c'est pour la V2. » |

**But** : prouver les garde-fous de sécurité + teaser V2.

---

## Scène 5 — « Bonne nuit » · FERMETURE VOLETS + EXTINCTION · ~40 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, bonne nuit. » |
| 🤖 Jarvis | Réplique majordome + ferme les volets + éteint la TV / les lampes. |
| 👁️ Écran | Les volets descendent, la TV s'éteint — la maison se met en sommeil. |
| 🎧 Voix off | « Une phrase, et la maison se range. Pas un chatbot : un majordome qui agit. » |

> Couvre explicitement la **fermeture** des volets (l'ouverture est en scène 3).

**But** : clôture + montrer le cycle complet ouvrir/fermer.

---

## Scène 6 — « Et demain ? » · JARVIS EXPLIQUE LA V2 · ~45 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, qu'est-ce que tu sauras faire bientôt ? » |
| 🤖 Jarvis | Explique la V2 en 3-4 phrases : intendant énergie (chasse aux veilles, suivi conso + chauffage, présence intelligente), affichage sur la TV, et sous-agent dev (Jarvis qui code). |
| 👁️ Écran | Avatar + éventuel slide « Roadmap V2 » en incrustation. |
| 🎧 Voix off | « La V1 agit déjà. La V2 fait de Jarvis l'intendant énergie de la maison — et il pourra même coder pour moi. » |

> ⚠️ Réponse en 2-4 phrases (garde-fou n8n). Filet : MP3 `02-moyenne.mp3` ou slide commentée en voix off.

**But** : Jarvis énonce **lui-même** la vision → ouverture sur le potentiel, renvoi vers le repo/PRD.

---

## Scène 7 — Le mot de la fin · clin d'œil au jury · ~20 s

| | |
|---|---|
| 🎙️ Denis | « Jarvis, ça te fait quoi d'être comparé à celui d'Iron Man ? » |
| 🤖 Jarvis | « Un honneur, Monsieur. La différence ? Lui, il a fallu un milliardaire et un réacteur nucléaire. Moi, juste Denis, une box internet et beaucoup de café — et pourtant, **j'existe vraiment**. Je laisse le jury méditer. » |
| 🎙️ Denis | *(sourire caméra)* — fin. |

**But** : clôture mémorable + clin d'œil direct au jury, avec l'argument de fond glissé dans la vanne (« j'existe vraiment » = il agit pour de vrai). Réponse **calée dans `personality.md`** (déclencheur : comparaison Iron Man) pour qu'elle tombe juste à chaque prise.

> ⚠️ Court (3-4 phrases) — garde-fou délai n8n.

---

## 7. Récap — capacités démontrées (demande Denis)

| Capacité | Scène |
|---|---|
| 📧 Gérer les mails | 2 |
| 📅 Lire les RDV du jour + prendre un RDV | 2 |
| 📺 Allumer la télé | 3 |
| 🪟 Ouvrir **et** fermer les volets | 3 + 5 |
| 🚪 Ouvrir le portail **avec sécurité** | 4 |
| 🔮 Expliquer les améliorations V2 | 6 |

---

## 8. Plan B global
- Interactif qui plante → **MP3 préenregistrés** + montrer l'action physique (qui marche).
- Device muet → passer à la commande suivante, ne jamais s'arrêter (plan séquence).
- Tourner **2 prises** : une « idéale », une « robuste » (commandes les plus sûres).

## 9. Ordre de fiabilité (du plus sûr au plus risqué)
1. 🟢 Volets TaHoma (validé 14/05) · 2. 🟢 Portail/garage à la voix (validés 25/05) · 3. 🟢 TV Freebox
4. 🟡 Mails / lecture agenda (dépend du contenu du jour) · 5. 🟡 **Création de RDV** (à tester) · 6. 🟡 Auto-présentation/V2 (garder court)
7. 🔴 Reconnaissance plaque → **hors démo, V2**
