"""Spraak: tekst naar audiobestand.

De pipeline vraagt alleen om 'zeg deze zin en geef me het bestand'. Welke
stem dat doet staat in channel.yaml. Elke zin wordt gecachet op een hash
van tekst en steminstellingen, zodat opnieuw renderen van dezelfde
aflevering niets extra kost.

Er zijn drie stemmen:

    piper       gratis, draait op je eigen computer, goed genoeg om te
                publiceren. Dit is de standaard.
    elevenlabs  betaald, klinkt nog natuurlijker. Alleen met een sleutel.
    offline     espeak: een robotstem, puur om de timing te controleren
                als Piper er niet is.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import Config
from ..media import duration as media_duration

PROVIDERS = ("piper", "elevenlabs", "offline")

LABELS = {
    "piper": "Piper (gratis, lokaal)",
    "elevenlabs": "ElevenLabs (betaald)",
    "offline": "teststem (espeak, robotachtig)",
}

# Welke stemmen niets kosten. De bedieningspagina en 'ytauto check' gebruiken
# dit om te laten zien dat er niets afgeschreven wordt.
FREE = {"piper", "offline"}


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

    Staat ElevenLabs ingesteld maar ontbreekt de sleutel, dan wordt het
    Piper: gratis en goed genoeg om mee te publiceren. Ontbreekt Piper ook,
    dan de teststem. Een knop die niets doet is erger dan een knop die een
    robotstem oplevert met de melding erbij.
    """
    from . import piper

    provider = str(cfg.tts.get("provider", "piper"))

    if provider == "elevenlabs" and not cfg.secrets.elevenlabs_api_key:
        provider = "piper"
    if provider in ("piper", "auto"):
        return "piper" if piper.is_installed() else "offline"
    if provider not in PROVIDERS:
        raise TTSError(f"Onbekende tts.provider: {provider!r}")
    return provider


def provider_label(provider: str) -> str:
    return LABELS.get(provider, provider)


def voice_status(cfg: Config) -> dict:
    """Korte samenvatting voor 'ytauto check' en de bedieningspagina."""
    from . import piper

    provider = effective_provider(cfg)
    info: dict = {
        "provider": provider,
        "label": provider_label(provider),
        "free": provider in FREE,
        "publishable": provider != "offline",
    }
    if provider == "piper":
        info.update(piper.check_voice(cfg))
    elif provider == "offline":
        info["reason"] = (
            "piper-tts ontbreekt, dus de video krijgt de robotstem. "
            "Herstellen met: pip install -r requirements.txt"
        )
    return info


def synthesize(cfg: Config, text: str, out_path: Path, cache_dir: Path | None = None) -> float:
    """Spreekt één zin in en geeft de duur terug.

    Bestaat het bestand al met dezelfde tekst en instellingen, dan wordt de
    cache gebruikt en gebeurt er geen enkele aanroep.
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
    elif provider == "piper":
        from .piper import speak
    elif provider == "offline":
        from .offline import speak
    else:
        raise TTSError(f"Onbekende tts.provider: {provider!r}")

    speak(cfg, text, out_path)
    cached.write_bytes(out_path.read_bytes())
    return audio_duration(out_path)
