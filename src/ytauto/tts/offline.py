"""Laatste redmiddel: espeak-ng, of stilte van de juiste lengte.

Klinkt robotachtig en is niet geschikt om te publiceren. Hiervoor wordt
alleen gekozen als Piper er niet is — zie `piper.py`, dat is de gratis stem
waar je wél mee kunt publiceren. Het doel van deze is dat je de hele pipeline
kunt doorlopen en de timing kunt controleren, wat er ook ontbreekt.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..config import Config
from ..media import run as ffmpeg


def speak(cfg: Config, text: str, out_path: Path) -> None:
    voice = "en" if cfg.channel.get("language", "en").startswith("en") else cfg.channel["language"]
    wav = out_path.with_suffix(".wav")

    if shutil.which("espeak-ng"):
        subprocess.run(
            ["espeak-ng", "-v", voice, "-s", "135", "-p", "62", "-w", str(wav), text],
            check=True, capture_output=True,
        )
    else:
        # Geen espeak: maak stilte van een geschatte lengte, puur zodat de
        # timing van de video klopt en je het beeld kunt beoordelen.
        from ..script_builder import estimate_speech_seconds
        seconds = max(1.0, estimate_speech_seconds(text))
        ffmpeg(["-y", "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=mono:d={seconds:.2f}", str(wav)], check=True)

    ffmpeg(["-y", "-i", str(wav), "-codec:a", "libmp3lame",
            "-b:a", "128k", str(out_path)], check=True)
    wav.unlink(missing_ok=True)
