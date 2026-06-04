"""RBAC Jarvis (Vitesse 1) — accès par rôle. Cf. PRD §30.

Trois rôles prédéfinis. Chaque rôle possède un ensemble de **niveaux d'action
autorisés** (safe / sensible / critique). Converser (poser des questions,
recherche web, réponses parlées) est TOUJOURS permis : cela ne produit aucune
commande domotique, donc aucun niveau d'action n'est requis.

- ``admin``     : toutes les actions (safe + sensible + critique). C'est Denis.
- ``locataire`` : actions safe de sa zone (volets, store, TV, son…). Jamais
                  portail/garage (sensible) ni alarme (critique). Angle gîte.
- ``visiteur``  : AUCUNE action — converse seulement. C'est le rôle « jury ».

L'instance ``RolePolicy`` porte un **override en mémoire** des capacités, pour
l'« élévation en direct » depuis l'écran admin pendant la démo (ex. accorder
``safe`` au visiteur le temps d'une scène). Aucune persistance en Vitesse 1
(PRD §30.7) : un redémarrage du service rétablit les capacités par défaut.

Les textes (accueil, refus) emploient le vocatif « Monsieur » comme
**placeholder** : ``main._apply_title`` le remplace ensuite par le titre réel
de l'utilisateur connecté (« Votre Sagacité » pour le jury, « Madame »…).
"""
from __future__ import annotations

from jarvis.domain.types import SensitivityLevel

ADMIN = "admin"
LOCATAIRE = "locataire"
VISITEUR = "visiteur"

KNOWN_ROLES: tuple[str, ...] = (ADMIN, LOCATAIRE, VISITEUR)

# Au moindre doute, le rôle le plus restrictif (règle de sécurité Denis).
DEFAULT_ROLE = VISITEUR

# Niveaux d'action autorisés par défaut pour chaque rôle.
_DEFAULT_CAPABILITIES: dict[str, set[SensitivityLevel]] = {
    ADMIN: {SensitivityLevel.safe, SensitivityLevel.sensible, SensitivityLevel.critique},
    LOCATAIRE: {SensitivityLevel.safe},
    VISITEUR: set(),
}

# Titre d'adresse par défaut selon le rôle. Défaut neutre « Monsieur » : à la
# connexion, Jarvis demande à l'utilisateur comment il souhaite être appelé et
# ce nom prime ensuite (PRD §30.4). On évite ainsi un titre figé trop lourd.
DEFAULT_TITLE_BY_ROLE: dict[str, str] = {
    ADMIN: "Monsieur",
    LOCATAIRE: "Monsieur",
    VISITEUR: "Monsieur",
}

# Capacités modifiables depuis l'écran admin (converse est implicite et permanent).
EDITABLE_CAPABILITIES: tuple[str, ...] = (
    SensitivityLevel.safe.value,
    SensitivityLevel.sensible.value,
    SensitivityLevel.critique.value,
)


class RolePolicy:
    """Capacités par rôle, avec override mémoire (élévation en direct)."""

    def __init__(self, capabilities: dict[str, set[SensitivityLevel]] | None = None) -> None:
        base = capabilities or _DEFAULT_CAPABILITIES
        self._caps: dict[str, set[SensitivityLevel]] = {
            role: set(levels) for role, levels in base.items()
        }

    def normalize_role(self, role: str | None) -> str:
        r = (role or "").strip().lower()
        return r if r in self._caps else DEFAULT_ROLE

    def allowed_levels(self, role: str | None) -> set[SensitivityLevel]:
        return set(self._caps.get(self.normalize_role(role), set()))

    def is_allowed(self, role: str | None, level: SensitivityLevel) -> bool:
        return level in self._caps.get(self.normalize_role(role), set())

    # ----- override mémoire (écran admin / élévation en direct) -----

    def set_level(self, role: str, capability: str, allowed: bool) -> None:
        """Accorde/retire un niveau d'action à un rôle.

        L'``admin`` est intouchable (garde-fou anti-verrouillage : on ne doit
        jamais pouvoir se priver soi-même de l'accès via l'UI).
        """
        norm = self.normalize_role(role)
        if norm == ADMIN:
            return
        try:
            level = SensitivityLevel(capability)
        except ValueError:
            return  # capacité inconnue : on ignore (la route /admin valide déjà en amont)
        bucket = self._caps.setdefault(norm, set())
        if allowed:
            bucket.add(level)
        else:
            bucket.discard(level)

    def reset(self) -> None:
        """Rétablit les capacités par défaut (annule toutes les élévations)."""
        self._caps = {role: set(levels) for role, levels in _DEFAULT_CAPABILITIES.items()}

    def snapshot(self) -> dict[str, dict[str, bool]]:
        """État courant pour l'écran admin : {role: {converse, safe, sensible, critique}}."""
        out: dict[str, dict[str, bool]] = {}
        for role in KNOWN_ROLES:
            caps = self._caps.get(role, set())
            out[role] = {
                "converse": True,  # toujours permis, non modifiable
                "safe": SensitivityLevel.safe in caps,
                "sensible": SensitivityLevel.sensible in caps,
                "critique": SensitivityLevel.critique in caps,
            }
        return out


# ----------------------------------------------------------------------
# Textes parlés (vocatif « Monsieur » = placeholder, converti par _apply_title)
# ----------------------------------------------------------------------

def title_for_role(role: str | None) -> str:
    r = (role or "").strip().lower()
    return DEFAULT_TITLE_BY_ROLE.get(r, "Monsieur")


def refusal_line(role: str | None) -> str:
    """Réplique de refus quand un rôle tente une action interdite."""
    r = (role or "").strip().lower()
    if r == VISITEUR:
        return (
            "Je crains que cette commande ne dépasse vos prérogatives, Monsieur. "
            "Le pilotage de la demeure demeure le privilège de Denis. "
            "Si l'envie vous prend de l'essayer vous-même, conviez-le en visioconférence : "
            "il vous ouvrira l'accès, et vous commanderez en personne."
        )
    if r == LOCATAIRE:
        return (
            "Cette commande est réservée au propriétaire des lieux, Monsieur. "
            "Je ne saurais l'exécuter pour vous, mais le reste de la maison demeure à votre service."
        )
    # admin : ne devrait jamais être refusé ; filet de sécurité neutre.
    return "Je préfère m'abstenir de cette commande, Monsieur."


def welcome_speech(role: str | None) -> str:
    """Discours d'accueil prononcé à la connexion, selon le rôle (PRD §30).

    Volontairement bref (synthèse vocale rapide) et toujours doté du **conseil
    d'usage** : appuyer sur le bouton du micro pour parler, le mode mains libres
    étant encore perfectible (demande Denis 03/06).
    """
    r = (role or "").strip().lower()
    mic_tip = (
        "Pour me parler, appuyez sur le bouton du micro avant d'énoncer votre demande : "
        "le mode mains libres est encore perfectible, mieux vaut l'éviter pour l'instant. "
    )
    if r == VISITEUR:
        return (
            "Bonjour, et soyez le bienvenu. Je suis Jarvis, le majordome numérique de Denis Solé, "
            "conçu pour l'IApreneurs Academy. " + mic_tip +
            "En tant que visiteur, vos accès sont volontairement restreints pour des raisons de sécurité : "
            "vous pouvez m'interroger tout votre soûl, mais le pilotage de la maison — "
            "volets, portail, garage, alarme — vous demeure verrouillé. "
            "Si vous souhaitez commander vous-même, conviez Denis en visioconférence : "
            "d'un geste, il vous ouvrira l'accès, et vous prendrez les commandes en personne."
        )
    if r == LOCATAIRE:
        return (
            "Bonjour, et bienvenue chez vous pour la durée de votre séjour. Je suis Jarvis. " + mic_tip +
            "Vous pouvez me confier l'ambiance du logement — volets, store, télévision, son ; "
            "les fonctions de sécurité demeurent réservées au propriétaire."
        )
    # admin
    return "Bonjour Monsieur. Tous les systèmes sont à votre disposition. " + mic_tip + "Je vous écoute."
