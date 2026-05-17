"""
find_butler_voices.py — Cherche les voix les plus 'majordome' dans la Voice Library ElevenLabs.

Filtre british + male, score selon tags/description pour 'butler/posh/dignified/narrator'.
Génère ensuite la phrase test avec les 5 meilleures candidates.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
import httpx
from rich.console import Console
from rich.table import Table

from jarvis.core.voice import JarvisTTS

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


# Mots-clés qui donnent des points "majordome"
BUTLER_KEYWORDS = {
    "butler": 30,
    "alfred": 30,
    "majordom": 30,
    "narrator": 8,
    "narration": 8,
    "audiobook": 6,
    "posh": 15,
    "aristocrat": 15,
    "dignified": 12,
    "elegant": 10,
    "refined": 10,
    "sophisticated": 10,
    "classy": 8,
    "gentleman": 12,
    "documentary": 5,
    "calm": 4,
    "warm": 3,
    "mature": 5,
    "deep": 4,
    "old": 6,
    "elderly": 8,
    "british": 5,
    "english": 3,
    "rp": 8,        # Received Pronunciation
    "queen": 6,
    "royal": 6,
    "downton": 30,  # Downton Abbey style
    "victorian": 12,
    "edwardian": 12,
}

NEGATIVE_KEYWORDS = {
    "young": -10,
    "child": -50,
    "teenager": -30,
    "casual": -5,
    "rough": -10,
    "horror": -20,
    "scary": -20,
    "villain": -15,
    "robot": -5,
    "drunk": -50,
}

PHRASE_TEST = (
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. "
    "Permettez-moi de vous présenter votre journée."
)


def score_voice(voice: dict) -> int:
    """Calcule un score 'majordome' d'après les tags et la description."""
    text = " ".join([
        voice.get("name", ""),
        voice.get("description", "") or "",
        voice.get("use_case", "") or "",
        voice.get("category", "") or "",
        " ".join(voice.get("descriptive", []) if isinstance(voice.get("descriptive"), list) else [voice.get("descriptive", "") or ""]),
        " ".join(voice.get("language_codes", []) if isinstance(voice.get("language_codes"), list) else []),
    ]).lower()

    score = 0
    for kw, pts in BUTLER_KEYWORDS.items():
        if kw in text:
            score += pts
    for kw, pts in NEGATIVE_KEYWORDS.items():
        if kw in text:
            score += pts

    # Bonus si âge "middle_aged" ou "old"
    age = (voice.get("age") or "").lower()
    if age in ("middle_aged", "old", "middle-aged"):
        score += 8

    return score


def main() -> int:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY absente[/red]")
        return 1

    console.print("[bold cyan]── Recherche Voice Library : male + british + majordome ──[/bold cyan]\n")

    # Endpoint Voice Library
    url = "https://api.elevenlabs.io/v1/shared-voices"
    params = {
        "gender": "male",
        "language": "en",
        "accent": "british",
        "page_size": 100,
    }
    headers = {"xi-api-key": api_key}

    try:
        r = httpx.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[red]Erreur API : {type(e).__name__} : {e}[/red]")
        return 1

    voices = data.get("voices", [])
    console.print(f"[dim]{len(voices)} voix male/british récupérées[/dim]\n")

    # Score
    scored = [(score_voice(v), v) for v in voices]
    scored.sort(key=lambda x: -x[0])
    top = scored[:8]

    # Tableau récap
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Nom", style="bold", width=22)
    table.add_column("Age", width=12)
    table.add_column("Voice ID (court)", style="dim", width=12)
    table.add_column("Description", width=60)

    for i, (score, v) in enumerate(top, start=1):
        name = v.get("name", "?")
        age = v.get("age", "?")
        vid = v.get("voice_id", "?")
        short_vid = vid[:10] + "…"
        desc = (v.get("description", "") or "")[:58]
        table.add_row(str(i), str(score), name, age, short_vid, desc)
    console.print(table)
    console.print()

    # Génère 5 échantillons des meilleures
    console.print("[bold yellow]Génération des 5 meilleures candidates…[/bold yellow]\n")
    out_dir = ROOT / "data" / "butler_compare"
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = top[:5]
    for i, (score, v) in enumerate(candidates, start=1):
        name = v.get("name", "?")
        vid = v.get("voice_id", "")
        safe_name = name.lower().replace(" ", "_").replace("/", "_")
        out = out_dir / f"{i:02d}_{safe_name}.mp3"
        console.print(f"[{i}/{len(candidates)}] [bold]{name}[/bold] (score={score}) → {out.name}")
        try:
            tts = JarvisTTS(api_key=api_key, voice_id=vid)
            t0 = time.perf_counter()
            tts.synthesize(PHRASE_TEST, out)
            duration = int((time.perf_counter() - t0) * 1000)
            console.print(f"     [green]✓[/green] {duration} ms — voice_id={vid}")
        except Exception as e:
            console.print(f"     [red]✗ {type(e).__name__} : {e}[/red]")

    console.print(f"\n[bold green]✓ Échantillons dans {out_dir}[/bold green]")
    console.print("\n[bold yellow]→ Écoute-les dans l'ordre :[/bold yellow]")
    for f in sorted(out_dir.glob("*.mp3")):
        console.print(f"   start \"\" \"{f}\"")

    # Lance le premier
    first = sorted(out_dir.glob("*.mp3"))
    if first:
        os.startfile(str(first[0]))  # type: ignore[attr-defined]
        console.print(f"\n[dim]Lecture de {first[0].name} lancée…[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
