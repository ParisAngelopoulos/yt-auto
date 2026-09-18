#!/usr/bin/env bash
# Dubbelklik dit bestand om de videostudio te openen.
# Werkt op macOS en Linux. Windows: gebruik start.bat
#
# De eerste keer duurt dit een paar minuten (installeren). Daarna paar seconden.

set -e
cd "$(dirname "$0")"

echo ""
echo "  ┌──────────────────────────────┐"
echo "  │      V I D E O S T U D I O   │"
echo "  └──────────────────────────────┘"
echo ""

# --- Python ---
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "  Python is niet geïnstalleerd."
  echo "  Haal het op bij https://www.python.org/downloads/ en probeer opnieuw."
  echo ""
  read -p "  Druk op Enter om te sluiten." _
  exit 1
fi

# --- Eigen omgeving, zodat dit project niets op je systeem verandert ---
if [ ! -d .venv ]; then
  echo "  Eerste keer opstarten. Even installeren, dit duurt een paar minuten..."
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip --quiet
  # Eerst met de gratis stem erbij. Lukt dat niet (zeldzaam, maar het kan op
  # een ongebruikelijk systeem), dan zonder: dan werkt alles behalve de stem.
  if ! ./.venv/bin/python -m pip install -e ".[voice]" --quiet; then
    echo "  De gratis stem kon niet geinstalleerd worden; de rest wel."
    ./.venv/bin/python -m pip install -e . --quiet
  fi
  echo "  Klaar met installeren. ffmpeg en de stem zijn meegekomen."
  echo ""
fi

# --- Sleutels ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Er is een bestand .env aangemaakt."
  echo "  Sleutels zijn optioneel: script en stem zijn gratis."
  echo "  Alleen voor het uploaden naar YouTube heb je ze nodig."
  echo ""
fi

echo "  De pagina opent zo vanzelf in je browser."
echo "  Dit zwarte venster mag open blijven staan; sluiten stopt de studio."
echo ""

exec ./.venv/bin/ytauto panel
