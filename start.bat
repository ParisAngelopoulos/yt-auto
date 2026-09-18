@echo off
REM Dubbelklik dit bestand om de videostudio te openen (Windows).
REM De eerste keer duurt dit een paar minuten. Daarna paar seconden.

cd /d "%~dp0"
echo.
echo   ==============================
echo        V I D E O S T U D I O
echo   ==============================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo   Python is niet geinstalleerd.
  echo   Haal het op bij https://www.python.org/downloads/
  echo   Zet bij het installeren een vinkje bij "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

if not exist .venv (
  echo   Eerste keer opstarten. Even installeren, dit duurt een paar minuten...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip --quiet
  REM Eerst met de gratis stem erbij; lukt dat niet, dan zonder.
  .venv\Scripts\python -m pip install -e ".[voice]" --quiet
  if errorlevel 1 (
    echo   De gratis stem kon niet geinstalleerd worden; de rest wel.
    .venv\Scripts\python -m pip install -e . --quiet
  )
  echo   Klaar met installeren. ffmpeg en de stem zijn meegekomen.
  echo.
)

if not exist .env (
  copy .env.example .env >nul
  echo   Er is een bestand .env aangemaakt.
  echo   Sleutels zijn optioneel: script en stem zijn gratis.
  echo   Alleen voor het uploaden naar YouTube heb je ze nodig.
  echo.
)

echo   De pagina opent zo vanzelf in je browser.
echo   Dit venster mag open blijven staan; sluiten stopt de studio.
echo.

.venv\Scripts\ytauto panel
pause
