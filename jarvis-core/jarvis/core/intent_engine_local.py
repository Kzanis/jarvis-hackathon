"""
IntentEngine version locale — 100% offline, zéro API, gratuit.

Algorithme :
  1. Détecte le verbe d'action (lookup table français)
  2. Retire le wake word "Jarvis" et le verbe de la phrase
  3. Fuzzy match le reste contre tous les aliases des devices
  4. Retourne le device avec le meilleur score

Limites : pas de compréhension contextuelle subtile. Mais 80-90% correct
sur les commandes courantes type "ferme le rideau de la buanderie".
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz import fuzz, process

from jarvis.domain.types import CommandAction, Intent


# Mapping verbe français → CommandAction
VERB_TO_ACTION: dict[str, CommandAction] = {
    # Fermer
    "ferme": CommandAction.close,
    "fermer": CommandAction.close,
    "fermes": CommandAction.close,
    "baisse": CommandAction.close,
    "baisser": CommandAction.close,
    "baisses": CommandAction.close,
    "descends": CommandAction.close,
    "descend": CommandAction.close,
    # Ouvrir
    "ouvre": CommandAction.open,
    "ouvrir": CommandAction.open,
    "ouvres": CommandAction.open,
    "monte": CommandAction.open,
    "monter": CommandAction.open,
    "montes": CommandAction.open,
    "remonte": CommandAction.open,
    "lève": CommandAction.open,
    # Stop
    "stop": CommandAction.stop,
    "arrête": CommandAction.stop,
    "arrêter": CommandAction.stop,
    "stoppe": CommandAction.stop,
    # On/Off
    "allume": CommandAction.on,
    "allumer": CommandAction.on,
    "éteins": CommandAction.off,
    "éteindre": CommandAction.off,
    "éteint": CommandAction.off,
    # Alarme
    "active": CommandAction.arm,
    "activer": CommandAction.arm,
    "arme": CommandAction.arm,
    "armer": CommandAction.arm,
    "désactive": CommandAction.disarm,
    "désactiver": CommandAction.disarm,
    "désarme": CommandAction.disarm,
    "désarmer": CommandAction.disarm,
}

# Mots à ignorer pendant le matching (stop words)
STOP_WORDS = {
    "le", "la", "les", "l", "de", "du", "des", "d", "un", "une",
    "tu", "peux", "pouvez", "s'il", "te", "vous", "plaît", "plait",
    "jarvis", "joris", "jaris", "monsieur", "stp", "svp",
    "merci", "à", "au", "aux", "et", "ou", "puis",
    "ce", "cette", "ces", "moi", "toi",
}

# Scènes pré-définies (mots-clés)
SCENE_KEYWORDS: dict[str, list[str]] = {
    "bonjour": ["bonjour", "bonne matinée", "réveil", "lève-toi"],
    "je_pars": ["je pars", "je sors", "je quitte", "départ"],
    "mode_cinema": ["mode cinéma", "cinéma", "film", "regarder un film"],
    "bonne_nuit": ["bonne nuit", "dodo", "je vais me coucher", "au lit"],
}


def normalize(text: str) -> str:
    """Lowercase + retire accents + supprime ponctuation."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    return normalize(text).split()


def find_verb(tokens: list[str]) -> tuple[CommandAction | None, int]:
    """Cherche le verbe d'action dans les tokens. Retourne (action, index)."""
    for i, tok in enumerate(tokens):
        # Normalise pour la lookup (retire accents)
        for verb, action in VERB_TO_ACTION.items():
            if normalize(verb) == tok:
                return action, i
    return None, -1


def detect_scene(text: str) -> str | None:
    """Détecte une scène pré-définie par mots-clés."""
    normalized = normalize(text)
    for scene, keywords in SCENE_KEYWORDS.items():
        for kw in keywords:
            if normalize(kw) in normalized:
                return scene
    return None


class IntentEngineLocal:
    """
    Classificateur d'intent local (fuzzy matching).

    Pas d'API, pas de coût, latence < 5 ms.
    """

    def __init__(self, settings_path: Path):
        self.settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
        self._build_alias_index()

    def _build_alias_index(self) -> None:
        """Construit l'index : (device_name, normalized_alias)."""
        self.alias_index: list[tuple[str, str]] = []
        devices = self.settings.get("tahoma", {}).get("devices", {})
        for name, info in devices.items():
            # Le label principal + tous les aliases
            phrases = [info.get("label_voix", name)] + (info.get("aliases", []) or [])
            # Ajoute aussi le nom logique (volet_salon → "volet salon")
            phrases.append(name.replace("_", " "))
            for phrase in phrases:
                self.alias_index.append((name, normalize(phrase)))

    async def classify(self, text: str) -> Intent:
        # 1. Détecter une scène (priorité haute, plus rapide)
        scene = detect_scene(text)
        if scene:
            # Map vers une action de base
            action_for_scene = {
                "bonjour": CommandAction.open,
                "je_pars": CommandAction.close,
                "mode_cinema": CommandAction.close,
                "bonne_nuit": CommandAction.close,
            }.get(scene, CommandAction.stop)
            return Intent(
                name=scene,
                action=action_for_scene,
                target=scene,
                confidence=0.95,
                raw_text=text,
            )

        # 2. Tokeniser
        tokens = tokenize(text)
        if not tokens:
            return Intent(
                name="unknown",
                action=CommandAction.stop,
                target=None,
                confidence=0.0,
                raw_text=text,
            )

        # 3. Détecter le verbe d'action
        action, verb_idx = find_verb(tokens)
        if action is None:
            return Intent(
                name="unknown",
                action=CommandAction.stop,
                target=None,
                confidence=0.0,
                raw_text=text,
                params={"raison": "aucun verbe d'action détecté"},
            )

        # 4. Construire la query (tout ce qui n'est pas verbe ni stop word)
        query_tokens = [
            t for i, t in enumerate(tokens)
            if i != verb_idx and t not in STOP_WORDS
        ]
        query = " ".join(query_tokens)

        if not query:
            return Intent(
                name="unknown",
                action=action,
                target=None,
                confidence=0.2,
                raw_text=text,
                params={"raison": "verbe trouvé mais pas de cible"},
            )

        # 5. Fuzzy match : loop manuel sur tous les aliases (plus fiable)
        best_score = 0.0
        best_device: str | None = None
        best_alias = ""
        for device_name, alias in self.alias_index:
            score = fuzz.token_set_ratio(query, alias)
            if score > best_score:
                best_score = score
                best_device = device_name
                best_alias = alias

        if best_device is None or best_score < 50:
            return Intent(
                name="unknown",
                action=action,
                target=None,
                confidence=0.3,
                raw_text=text,
                params={"raison": f"aucun device matché pour '{query}' (best score={best_score:.0f})"},
            )

        device_name = best_device
        matched_alias = best_alias
        score = best_score
        confidence = score / 100.0

        return Intent(
            name=f"{action.value}_{device_name}",
            action=action,
            target=device_name,
            confidence=confidence,
            raw_text=text,
            params={"matched_alias": matched_alias, "fuzzy_score": score},
        )
