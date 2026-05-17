"""Couche orchestrateur LLM — pivot 17 mai 2026 (PRD §15).

Ajoute un planificateur Claude Haiku 4.5 au-dessus de jarvis-core hexagonal.
Le LLM PROPOSE des DeviceCommand ; Policy + Audit + Handlers décident et exécutent.
"""
