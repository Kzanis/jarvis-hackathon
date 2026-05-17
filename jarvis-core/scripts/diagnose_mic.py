"""
diagnose_mic.py — Diagnostic du micro Windows.

1. Liste tous les périphériques audio
2. Identifie l'entrée par défaut
3. Enregistre 5s en affichant le niveau RMS temps réel
   → si le niveau reste à zéro = problème micro, sinon = OK
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.table import Table

console = Console(legacy_windows=False)


def main() -> int:
    console.print("\n[bold cyan]── Diagnostic micro Windows ──[/bold cyan]\n")

    # 1. Lister périphériques
    devices = sd.query_devices()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Type", width=8)
    table.add_column("Nom", style="bold")
    table.add_column("Hostapi", style="dim", width=15)
    table.add_column("Canaux IN", justify="right", width=10)

    default_in_idx = sd.default.device[0]
    hostapis = sd.query_hostapis()

    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            host = hostapis[dev["hostapi"]]["name"]
            is_default = " ⭐" if idx == default_in_idx else ""
            table.add_row(
                str(idx),
                "INPUT",
                dev["name"] + is_default,
                host,
                str(dev["max_input_channels"]),
            )

    console.print(table)
    console.print(f"\n[bold yellow]⭐ Périphérique d'entrée par défaut : #{default_in_idx} — {devices[default_in_idx]['name']}[/bold yellow]\n")

    # 2. Enregistrement avec niveau RMS temps réel
    console.print("[bold red]🎙️  Parle MAINTENANT pendant 5 secondes (fort, près du micro)…[/bold red]\n")

    sample_rate = 16000
    duration = 5.0
    chunk_size = int(sample_rate * 0.2)  # 200ms chunks
    all_chunks = []
    max_rms = 0.0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        start = time.time()
        while time.time() - start < duration:
            chunk, _ = stream.read(chunk_size)
            all_chunks.append(chunk.flatten())
            rms = float(np.sqrt(np.mean(chunk**2)))
            max_rms = max(max_rms, rms)
            db = 20 * np.log10(rms + 1e-10)
            # Barre de niveau visuelle
            level = int(min(rms * 200, 50))
            bar = "█" * level + "░" * (50 - level)
            print(f"\r  Niveau : [{bar}] RMS={rms:.4f}  dB={db:6.1f}", end="", flush=True)

    print()  # newline final
    audio = np.concatenate(all_chunks)

    console.print()
    console.print(f"[bold]Résultats enregistrement :[/bold]")
    console.print(f"  Durée    : {len(audio) / sample_rate:.1f} s")
    console.print(f"  Échantillons : {len(audio)}")
    console.print(f"  RMS max  : [bold cyan]{max_rms:.4f}[/bold cyan]")
    console.print(f"  Crête    : {np.max(np.abs(audio)):.4f}")

    # Diagnostic
    console.print()
    if max_rms < 0.001:
        console.print("[bold red]✗ AUCUN SON CAPTÉ[/bold red]")
        console.print("[yellow]Diagnostic possible :[/yellow]")
        console.print("  • Le micro n'est pas branché / pas activé")
        console.print("  • Le micro est sur 'Mute' (vérifier la touche dédiée du laptop)")
        console.print("  • Mauvais périphérique sélectionné par défaut")
        console.print("  • Permissions micro Windows refusées pour Python")
        return 1
    elif max_rms < 0.01:
        console.print("[bold yellow]⚠ Niveau micro très faible[/bold yellow]")
        console.print("[yellow]Solutions :[/yellow]")
        console.print("  • Augmenter le volume du micro dans Windows (clic droit haut-parleur → Paramètres son)")
        console.print("  • Parler plus fort ou plus près")
        console.print("  • Changer de micro si dispo")
        return 0
    else:
        console.print(f"[bold green]✓ Micro OK — niveau correct ({max_rms:.4f})[/bold green]")
        # Sauvegarde
        out = Path(__file__).resolve().parent.parent / "data" / "mic_test.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        from scipy.io import wavfile
        wavfile.write(str(out), sample_rate, (audio * 32767).astype(np.int16))
        console.print(f"[dim]Enregistrement sauvé : {out}[/dim]")
        return 0


if __name__ == "__main__":
    sys.exit(main())
