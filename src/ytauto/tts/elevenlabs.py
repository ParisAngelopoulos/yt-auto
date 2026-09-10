"""ElevenLabs text-to-speech."""

from __future__ import annotations

import time
from pathlib import Path

import requests

from ..config import Config

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
OUTPUT_FORMAT = "mp3_44100_128"
MAX_ATTEMPTS = 4


class ElevenLabsError(RuntimeError):
    pass


def voice_settings(cfg: Config) -> dict:
    settings = {
        "stability": float(cfg.tts.get("stability", 0.45)),
        "similarity_boost": float(cfg.tts.get("similarity_boost", 0.75)),
        "style": float(cfg.tts.get("style", 0.35)),
        "use_speaker_boost": True,
    }
    speed = cfg.tts.get("speed")
    if speed is not None:
        settings["speed"] = float(speed)
    return settings


def speak(cfg: Config, text: str, out_path: Path) -> None:
    api_key = cfg.secrets.elevenlabs_api_key
    if not api_key:
        raise ElevenLabsError(
            "ELEVENLABS_API_KEY ontbreekt. Zet hem in .env, of zet "
            "tts.provider op 'offline' om zonder stem te testen."
        )

    voice_id = cfg.tts.get("voice_id")
    if not voice_id:
        raise ElevenLabsError("tts.voice_id ontbreekt in channel.yaml")

    payload = {
        "text": text,
        "model_id": cfg.tts.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": voice_settings(cfg),
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json",
               "Accept": "audio/mpeg"}
    url = API_URL.format(voice_id=voice_id)

    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                url, json=payload, headers=headers,
                params={"output_format": OUTPUT_FORMAT}, timeout=90,
            )
        except requests.RequestException as exc:
            last_error = f"netwerkfout: {exc}"
            time.sleep(2 ** attempt)
            continue

        if response.status_code == 200:
            out_path.write_bytes(response.content)
            if out_path.stat().st_size < 512:
                raise ElevenLabsError("ElevenLabs gaf een leeg audiobestand terug")
            return

        # 422 betekent meestal dat deze stem of dit model een instelling niet
        # kent. Eén keer opnieuw zonder 'speed' is dan bijna altijd genoeg.
        if response.status_code == 422 and "speed" in payload["voice_settings"]:
            payload["voice_settings"].pop("speed")
            last_error = f"422, opnieuw zonder speed: {response.text[:200]}"
            continue

        if response.status_code == 401:
            raise ElevenLabsError("ElevenLabs weigert de sleutel (401). Controleer ELEVENLABS_API_KEY.")

        if response.status_code == 429 or response.status_code >= 500:
            wait = int(response.headers.get("retry-after", 2 ** attempt))
            last_error = f"status {response.status_code}"
            time.sleep(min(wait, 30))
            continue

        raise ElevenLabsError(
            f"ElevenLabs gaf status {response.status_code}: {response.text[:300]}"
        )

    raise ElevenLabsError(f"ElevenLabs bleef falen na {MAX_ATTEMPTS} pogingen ({last_error})")


def check_credentials(cfg: Config) -> dict:
    """Haalt het abonnement op. Wordt door de bedieningspagina gebruikt."""
    api_key = cfg.secrets.elevenlabs_api_key
    if not api_key:
        return {"ok": False, "reason": "Geen ELEVENLABS_API_KEY gevonden"}
    try:
        response = requests.get(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": api_key}, timeout=20,
        )
    except requests.RequestException:
        # De onderliggende melding is een lange stacktrace-achtige tekst die
        # niemand helpt. Wat je moet weten is dat de dienst onbereikbaar is.
        return {"ok": False, "reason": "ElevenLabs is niet bereikbaar. Staat je internet aan?"}

    if response.status_code == 401:
        return {"ok": False, "reason": "De sleutel wordt geweigerd. Kloppen alle tekens?"}
    if response.status_code != 200:
        return {"ok": False, "reason": f"ElevenLabs antwoordde met status {response.status_code}"}

    data = response.json()
    used = data.get("character_count", 0)
    limit = data.get("character_limit", 0)
    return {
        "ok": True,
        "tier": data.get("tier", "onbekend"),
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


def list_voices(cfg: Config) -> list[dict]:
    api_key = cfg.secrets.elevenlabs_api_key
    if not api_key:
        return []
    try:
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key}, timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", ""),
         "labels": v.get("labels", {})}
        for v in response.json().get("voices", [])
    ]
