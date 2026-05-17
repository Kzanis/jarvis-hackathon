# Jarvis Core

Backend Python du majordome IA domotique. Pilote TaHoma, Freebox, Devialet, Calendar, Gmail, Lemlist via voix.

Hackathon Creator Academy — partenaire Hostinger.

## Setup rapide

```powershell
# 1. Créer un environnement virtuel
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Copier .env.example en .env et remplir les valeurs
copy .env.example .env

# 4. Tester la connectivité aux 3 devices physiques
python scripts\test_devices.py
```

## Modes d'exécution

| Mode | Usage | Activation |
|---|---|---|
| `production` | Chez Denis, devices réels | `JARVIS_MODE=production` (défaut) |
| `mock` | Jury, simulateur de devices | `JARVIS_MODE=mock` |
| `replay` | Rejoue une session enregistrée | `JARVIS_MODE=replay` |

## Arborescence

```
jarvis-core/
├── requirements.txt
├── .env.example         ← copier en .env
├── config/
│   └── settings.yaml    ← devices, chaînes, volumes
├── jarvis/
│   ├── core/            ← intent engine, voice pipeline
│   ├── handlers/        ← TaHoma, Freebox, Devialet, etc.
│   └── mocks/           ← simulateurs pour le jury
├── scripts/
│   └── test_devices.py  ← validation connectivité
└── tests/
```

## Étape suivante

Voir le PRD : `../PRD.md` (planning S1-S3).
