"""
IntentEngine version OpenAI (gpt-4o-mini).

Même interface que la version Anthropic, mais utilise OpenAI.
Coût : ~$0.0001 par commande (5€ = 50 000 commandes).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

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

Tu retournes UNIQUEMENT un objet JSON sur une seule ligne, sans markdown, sans commentaire :

{{"name":"<nom_intent>","action":"<action>","target":"<nom_logique_du_device_ou_scene>","confidence":<0_a_1>,"params":{{}}}}

# RÈGLES IMPORTANTES

1. Si la phrase est ambiguë ou ne correspond à AUCUN device/scène, retourne :
   {{"name":"unknown","action":"stop","target":null,"confidence":0.0,"params":{{}}}}

2. Synonymes courants :
   - rideau / store intérieur / jalousie = volet
   - barrière / grille = portail
   - garage = porte_garage
   - auvent / pare-soleil = store_banne

3. Si Denis dit "Jarvis" au début, ignore-le (wake word).

# EXEMPLES

"Jarvis, ferme le volet du salon" → {{"name":"close_shutter","action":"close","target":"volet_salon","confidence":0.98,"params":{{}}}}
"Tu peux baisser le rideau de la buanderie ?" → {{"name":"close_shutter","action":"close","target":"volet_buanderie","confidence":0.92,"params":{{}}}}
"Ouvre le portail" → {{"name":"open_gate","action":"open","target":"portail","confidence":0.98,"params":{{}}}}
"Je pars" → {{"name":"je_pars","action":"close","target":"je_pars","confidence":0.95,"params":{{}}}}
"Quel temps fait-il ?" → {{"name":"unknown","action":"stop","target":null,"confidence":0.0,"params":{{}}}}
"""


class IntentEngineOpenAI:
    def __init__(self, api_key: str, settings_path: Path, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY requise")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
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
        def _call() -> dict[str, Any]:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=200,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
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
            params=data.get("params", {}) or {},
            confidence=float(data.get("confidence", 0.0)),
            raw_text=text,
        )
