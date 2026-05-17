"""
scan_all_mics.py — Balaie TOUS les devices d'entrée et test 2s d'enregistrement sur chacun.

Affiche le niveau RMS capté par chaque device → identifie celui qui marche.
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
    console.print("\n[bold cyan]── Scan TOUS les micros : 2s chacun, parle en continu ──[/bold cyan]")
    console.print("[bold red]PARLE EN CONTINU pendant le test entier (~30s) — répète 'un deux trois un deux trois'[/bold red]\n")
    console.print("[yellow]Le script va tester chaque device l'un après l'autre.[/yellow]\n")
    time.sleep(3)

    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    results = []

    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) == 0:
            continue
        name = dev["name"]
        host = hostapis[dev["hostapi"]]["name"]
        native_rate = int(dev.get("default_samplerate", 16000))

        console.print(f"  [{idx:2d}] [bold]{name[:40]:40s}[/bold] [{host[:15]:15s}] {native_rate} Hz ", end="")
        try:
            audio = sd.rec(
                int(2 * native_rate),
                samplerate=native_rate,
                channels=1,
                dtype="float32",
                device=idx,
            )
            sd.wait()
            audio = audio.flatten()
            rms = float(np.sqrt(np.mean(audio**2)))
            peak = float(np.max(np.abs(audio)))
            level_indicator = "🟢" if rms > 0.02 else ("🟡" if rms > 0.005 else "🔴")
            console.print(f"{level_indicator} RMS={rms:.4f}  Peak={peak:.4f}")
            results.append((idx, name, host, rms, peak))
        except Exception as e:
            err = str(e)[:30]
            console.print(f"[red]✗ {err}[/red]")
            results.append((idx, name, host, None, None))

    console.print("\n[bold green]── Résultats triés par RMS ──[/bold green]\n")
    valid = [r for r in results if r[3] is not None]
    valid.sort(key=lambda r: -(r[3] or 0))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rang", style="dim", width=4)
    table.add_column("Device #", width=8)
    table.add_column("Nom", style="bold", width=40)
    table.add_column("Hostapi", style="dim", width=15)
    table.add_column("RMS", justify="right", width=8)
    table.add_column("Statut", width=8)

    for rank, (idx, name, host, rms, peak) in enumerate(valid[:10], start=1):
        statut = "🟢 OK" if rms and rms > 0.02 else ("🟡 Faible" if rms and rms > 0.005 else "🔴 Silence")
        table.add_row(str(rank), str(idx), name[:38], host[:13], f"{rms:.4f}", statut)
    console.print(table)

    # Identifie le meilleur
    if valid and valid[0][3] and valid[0][3] > 0.02:
        idx, name, host, rms, peak = valid[0]
        console.print(f"\n[bold green]🎯 MEILLEUR MICRO : #{idx} — {name} ({host})[/bold green]")
        console.print(f"   Niveau capté : RMS={rms:.4f}")
        console.print(f"   [yellow]→ Forcer ce device dans le code Jarvis : device={idx}[/yellow]")
        return 0
    else:
        console.print("\n[bold red]🔴 AUCUN micro ne capte au-dessus du seuil de bruit.[/bold red]")
        console.print("[yellow]Hypothèses restantes :[/yellow]")
        console.print("  • Antivirus bloque l'accès micro pour python.exe")
        console.print("  • Pilote audio buggé")
        console.print("  • Casque G535 muté physiquement (rotation bras-micro)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
