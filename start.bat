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

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo   ffmpeg ontbreekt. Dat heeft de studio nodig om video te maken.
  echo.
  echo     winget install Gyan.FFmpeg
  echo.
  echo   Sluit daarna dit venster en start opnieuw.
  echo.
  pause
  exit /b 1
)

if not exist .venv (
  echo   Eerste keer opstarten. Even installeren, dit duurt een paar minuten...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip --quiet
  .venv\Scripts\python -m pip install -e . --quiet
  echo   Klaar met installeren.
  echo.
)

if not exist .env (
  copy .env.example .env >nul
  echo   Er is een bestand .env aangemaakt.
  echo   Zet je sleutels daarin voor de echte stem en om te kunnen publiceren.
  echo   Zonder sleutels werkt alles ook, maar met een robotstem.
  echo.
)

echo   De pagina opent zo vanzelf in je browser.
echo   Dit venster mag open blijven staan; sluiten stopt de studio.
echo.

.venv\Scripts\ytauto panel
pause
