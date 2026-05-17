"""
IntentEngine — Claude classe une phrase en Intent structuré.

Transforme : "Jarvis, ferme le rideau de la buanderie"
En        : Intent(action=close, target=volet_buanderie, confidence=0.95)

Gère les synonymes (rideau/volet/store), les pièces, les scènes prédéfinies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from anthropic import Anthropic

from jarvis.domain.types import CommandAction, Intent


SYSTEM_PROMPT_TEMPLATE = """Tu es l'analyseur d'intention de Jarvis, un assistant majordome pour la maison de Denis.

Ton rôle : recevoir une phrase en français, identifier l'action et la cible exacte parmi la liste ci-dessous, et retourner UNIQUEMENT un JSON valide.

# DEVICES DISPONIBLES

{devices_list}

# SCÈNES DISPONIBLES

- bonjour : ouvre tous les volets, désactive l'alarme, brief vocal
- je_pars : ferme tous les volets, active l'alarme, ouvre le portail 2 minutes
- mode_cinema : ferme le volet du salon, monte le son
- bonne_nuit : ferme tous les volets, ferme le store, active l'alarme

# ACTIONS POSSIBLES

- open : ouvrir
- close : fermer
- stop : arrêter
- set_closure : positionner (avec param value 0-100)
- on : allumer
- off : éteindre
- arm : activer (alarme)
- disarm : désactiver (alarme)

# FORMAT DE RÉPONSE OBLIGATOIRE

Tu retournes UNIQUEMENT un JSON sur une seule ligne, sans markdown, sans commentaire :

{{"name":"<nom_intent>","action":"<action>","target":"<nom_logique_du_device_ou_scene>","confidence":<0_a_1>,"params":{{}}}}

# RÈGLES IMPORTANTES

1. Si la phrase est ambiguë ou ne correspond à AUCUN device/scène, retourne :
   {{"name":"unknown","action":"stop","target":null,"confidence":0.0,"params":{{"raison":"<explication>"}}}}

2. Si plusieurs interprétations possibles, choisis celle avec la confiance la plus élevée.

3. Synonymes courants à mapper :
   - "rideau" / "store intérieur" / "jalousie" = volet
   - "barrière" / "grille" = portail
   - "garage" / "porte garage" = porte_garage
   - "auvent" / "pare-soleil" = store_banne (le store extérieur)

4. Pour les commandes type "ouvre/ferme tout" ou "tous les volets", utilise target="tous_les_volets" et action open/close.

5. Si Denis dit "Jarvis" au début, ignore-le (c'est juste le wake word).

# EXEMPLES

Phrase : "Jarvis, ferme le volet du salon"
→ {{"name":"close_shutter","action":"close","target":"volet_salon","confidence":0.98,"params":{{}}}}

Phrase : "Tu peux baisser le rideau de la buanderie ?"
→ {{"name":"close_shutter","action":"close","target":"volet_buanderie","confidence":0.92,"params":{{}}}}

Phrase : "Ouvre le portail"
→ {{"name":"open_gate","action":"open","target":"portail","confidence":0.98,"params":{{}}}}

Phrase : "Je pars"
→ {{"name":"je_pars","action":"close","target":"je_pars","confidence":0.95,"params":{{}}}}

Phrase : "Mets le volet salon à 50 %"
→ {{"name":"set_closure","action":"set_closure","target":"volet_salon","confidence":0.95,"params":{{"value":50}}}}

Phrase : "Quel temps fait-il ?"
→ {{"name":"unknown","action":"stop","target":null,"confidence":0.0,"params":{{"raison":"Question météo, pas une commande device"}}}}
"""


class IntentEngine:
    def __init__(self, api_key: str, settings_path: Path, model: str = "claude-haiku-4-5"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Construit la liste des devices avec leurs aliases pour le prompt."""
        lines: list[str] = []
        devices = self.settings.get("tahoma", {}).get("devices", {})
        for name, info in devices.items():
            label = info.get("label_voix", name)
            aliases = info.get("aliases", []) or []
            alias_str = " | ".join([label] + aliases) if aliases else label
            lines.append(f"- {name} : {alias_str}")
        devices_list = "\n".join(lines)
        return SYSTEM_PROMPT_TEMPLATE.format(devices_list=devices_list)

    async def classify(self, text: str) -> Intent:
        """Demande à Claude de classifier le texte. Retourne un Intent."""
        # Appel synchrone Anthropic, on l'isole dans un thread
        import asyncio

        def _call() -> dict[str, Any]:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system=self.system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            raw = message.content[0].text.strip()
            # Nettoie des éventuels markdown blocks
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            return json.loads(raw)

        data = await asyncio.to_thread(_call)

        action_str = data.get("action", "stop")
        try:
            action = CommandAction(action_str)
        except ValueError:
            action = CommandAction.stop

        return Intent(
            name=data.get("name", "unknown"),
            action=action,
            target=data.get("target"),
            params=data.get("params", {}),
            confidence=float(data.get("confidence", 0.0)),
            raw_text=text,
        )
