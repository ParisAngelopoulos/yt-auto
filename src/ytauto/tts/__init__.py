"""Spraak: tekst naar audiobestand.

De pipeline vraagt alleen om 'zeg deze zin en geef me het bestand'. Welke
dienst dat doet staat in channel.yaml. Elke zin wordt gecachet op een hash
van tekst en steminstellingen, zodat opnieuw renderen van dezelfde
aflevering niets extra kost.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import Config
from ..media import duration as media_duration


class TTSError(RuntimeError):
    pass


def audio_duration(path: Path) -> float:
    """Lengte van een audiobestand in seconden."""
    return media_duration(path)


def _cache_key(text: str, settings: dict) -> str:
    payload = json.dumps({"text": text, **settings}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def effective_provider(cfg: Config) -> str:
    """Welke stem er werkelijk gebruikt wordt.

    Staat ElevenLabs ingesteld maar ontbreekt de sleutel, dan wordt het de
    offline teststem. Een knop die niets doet is erger dan een knop die een
    robotstem oplevert met de melding erbij.
    """
    provider = cfg.tts.get("provider", "elevenlabs")
    if provider == "elevenlabs" and not cfg.secrets.elevenlabs_api_key:
        return "offline"
    return provider


def synthesize(cfg: Config, text: str, out_path: Path, cache_dir: Path | None = None) -> float:
    """Spreekt één zin in en geeft de duur terug.

    Bestaat het bestand al met dezelfde tekst en instellingen, dan wordt de
    cache gebruikt en gebeurt er geen enkele API-aanroep.
    """
    provider = effective_provider(cfg)
    settings = dict(cfg.tts)
    settings["_provider"] = provider          # cache per stem gescheiden houden
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cache_dir = cache_dir or out_path.parent.parent / "voice-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{_cache_key(text, settings)}.mp3"

    if cached.exists() and cached.stat().st_size > 512:
        out_path.write_bytes(cached.read_bytes())
        return audio_duration(out_path)

    if provider == "elevenlabs":
        from .elevenlabs import speak
    elif provider == "offline":
        from .offline import speak
    else:
        raise TTSError(f"Onbekende tts.provider: {provider!r}")

    speak(cfg, text, out_path)
    cached.write_bytes(out_path.read_bytes())
    return audio_duration(out_path)
