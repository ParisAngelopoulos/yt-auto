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

# --- ffmpeg ---
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "  ffmpeg ontbreekt. Dat heeft de studio nodig om video te maken."
  echo ""
  if [ "$(uname)" = "Darwin" ]; then
    echo "    macOS:  brew install ffmpeg"
    echo "    (geen brew? installeer die eerst via https://brew.sh)"
  else
    echo "    Linux:  sudo apt-get install ffmpeg"
  fi
  echo ""
  read -p "  Druk op Enter om te sluiten." _
  exit 1
fi

# --- Eigen omgeving, zodat dit project niets op je systeem verandert ---
if [ ! -d .venv ]; then
  echo "  Eerste keer opstarten. Even installeren, dit duurt een paar minuten..."
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip --quiet
  ./.venv/bin/python -m pip install -e . --quiet
  echo "  Klaar met installeren."
  echo ""
fi

# --- Sleutels ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Er is een bestand .env aangemaakt."
  echo "  Zet je sleutels daarin voor de echte stem en om te kunnen publiceren."
  echo "  Zonder sleutels werkt alles ook, maar met een robotstem."
  echo ""
fi

echo "  De pagina opent zo vanzelf in je browser."
echo "  Dit zwarte venster mag open blijven staan; sluiten stopt de studio."
echo ""

exec ./.venv/bin/ytauto panel
