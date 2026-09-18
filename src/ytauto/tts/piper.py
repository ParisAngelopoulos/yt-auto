"""Gratis stem die op je eigen computer draait.

Piper is een neuraal stemmodel dat lokaal werkt: geen sleutel, geen tegoed,
geen limiet op het aantal tekens. Het model wordt één keer opgehaald (rond de
60 MB) en staat daarna in `assets/voices/`. Daarna heb je geen internet meer
nodig om in te spreken.

Dit is de stem waarmee je kunt publiceren. De espeak-stem in `offline.py`
blijft bestaan als laatste redmiddel voor het geval Piper er niet is; die
klinkt als een robot en is alleen om de timing te controleren.
"""

from __future__ import annotations

import re
import shutil
import wave
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from ..config import ROOT, Config
from ..media import run as ffmpeg

VOICES_DIR = ROOT / "assets" / "voices"

# De modellen staan in één publieke verzameling; de map is per taal
# opgebouwd. Voorbeeld: en/en_GB/alan/medium/en_GB-alan-medium.onnx
URL_FORMAT = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "{family}/{lang}/{name}/{quality}/{lang}-{name}-{quality}{extension}"
    "?download=true"
)

DEFAULT_MODEL = "en_GB-alan-medium"

# Een korte lijst waar je uit kunt kiezen zonder te hoeven zoeken. De hele
# lijst staat op https://rhasspy.github.io/piper-samples — daar kun je elke
# stem eerst beluisteren.
SUGGESTED = {
    "en_GB-alan-medium":      "Britse man, bedaard — past bij volksverhalen",
    "en_GB-semaine-medium":   "Britse vrouw, warm",
    "en_GB-northern_english_male-medium": "Noord-Engelse man, donkerder",
    "en_US-ryan-high":        "Amerikaanse man, helder",
    "en_US-lessac-high":      "Amerikaanse vrouw, neutraal en duidelijk",
    "nl_NL-mls-medium":       "Nederlandse stem",
    "de_DE-thorsten-medium":  "Duitse man",
    "fr_FR-siwis-medium":     "Franse vrouw",
    "es_ES-sharvard-medium":  "Spaanse stem",
}

NAME_PATTERN = re.compile(r"^(?P<family>[a-z]{2,3})_(?P<region>[A-Z]{2})-(?P<name>.+)-(?P<quality>x_low|low|medium|high)$")

_LOADED: dict[str, object] = {}


class PiperUnavailable(RuntimeError):
    """Piper is niet geïnstalleerd, of het stemmodel ontbreekt."""


# ---------------------------------------------------------------------------
#  Beschikbaarheid
# ---------------------------------------------------------------------------


def is_installed() -> bool:
    """Of de package er is. Zonder Piper valt de studio terug op espeak."""
    try:
        import piper  # noqa: F401
    except Exception:                                           # noqa: BLE001
        return False
    return True


def model_name(cfg: Config) -> str:
    return str(cfg.tts.get("voice_model") or DEFAULT_MODEL).strip()


def model_paths(name: str) -> tuple[Path, Path]:
    """Waar het model en zijn instellingenbestand horen te staan."""
    if not NAME_PATTERN.match(name):
        raise PiperUnavailable(
            f"{name!r} is geen geldige Piper-stem. De vorm is taal-naam-kwaliteit, "
            f"bijvoorbeeld {DEFAULT_MODEL!r}."
        )
    return VOICES_DIR / f"{name}.onnx", VOICES_DIR / f"{name}.onnx.json"


def is_downloaded(name: str) -> bool:
    try:
        model, config = model_paths(name)
    except PiperUnavailable:
        return False
    return model.exists() and model.stat().st_size > 1_000_000 and config.exists()


# ---------------------------------------------------------------------------
#  Ophalen
# ---------------------------------------------------------------------------


def _download(url: str, target: Path) -> None:
    """Haalt één bestand op via een tijdelijke naam.

    Die tussenstap is er zodat een afgebroken download geen half bestand
    achterlaat dat de volgende keer voor compleet wordt aangezien.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tijdelijk = target.with_suffix(target.suffix + ".part")
    try:
        with urlopen(url, timeout=60) as antwoord, open(tijdelijk, "wb") as bestand:
            shutil.copyfileobj(antwoord, bestand)
    except HTTPError as exc:
        tijdelijk.unlink(missing_ok=True)
        raise PiperUnavailable(
            f"De stem kon niet opgehaald worden (status {exc.code}). "
            f"Bestaat {target.stem!r} wel? Kijk op https://rhasspy.github.io/piper-samples"
        ) from exc
    except (URLError, OSError) as exc:
        tijdelijk.unlink(missing_ok=True)
        raise PiperUnavailable(
            f"De stem kon niet opgehaald worden: {exc}. Staat je internet aan? "
            "Dit is eenmalig; daarna werkt de stem zonder verbinding."
        ) from exc
    tijdelijk.replace(target)


def ensure_model(name: str, log=print) -> Path:
    """Zorgt dat het stemmodel op schijf staat en geeft het pad terug."""
    model, config = model_paths(name)
    if is_downloaded(name):
        return model

    onderdelen = NAME_PATTERN.match(name).groupdict()
    velden = {
        "family": onderdelen["family"],
        "lang": f"{onderdelen['family']}_{onderdelen['region']}",
        "name": onderdelen["name"],
        "quality": onderdelen["quality"],
    }

    log(f"  Stem {name} wordt eenmalig opgehaald (ongeveer 60 MB)...")
    _download(URL_FORMAT.format(extension=".onnx", **velden), model)
    _download(URL_FORMAT.format(extension=".onnx.json", **velden), config)
    log(f"  Stem opgeslagen in {VOICES_DIR}. Dit gebeurt maar één keer.")
    return model


# ---------------------------------------------------------------------------
#  Spreken
# ---------------------------------------------------------------------------


def _synthesis_config(cfg: Config):
    from piper.config import SynthesisConfig

    # ElevenLabs telt snelheid: onder de 1 is langzamer. Piper telt lengte:
    # boven de 1 is langzamer. Dus omgekeerd, zodat dezelfde regel in
    # channel.yaml voor beide stemmen hetzelfde betekent.
    snelheid = float(cfg.tts.get("speed") or 1.0)
    snelheid = min(max(snelheid, 0.5), 2.0)

    return SynthesisConfig(
        length_scale=1.0 / snelheid,
        noise_scale=float(cfg.tts.get("noise", 0.667)),
        noise_w_scale=float(cfg.tts.get("noise_w", 0.8)),
        normalize_audio=True,
    )


def load_voice(cfg: Config):
    """Laadt het model één keer per proces; laden kost een seconde."""
    if not is_installed():
        raise PiperUnavailable(
            "De package 'piper-tts' ontbreekt. Draai: pip install -r requirements.txt"
        )

    naam = model_name(cfg)
    if naam in _LOADED:
        return _LOADED[naam]

    from piper import PiperVoice

    model = ensure_model(naam)
    stem = PiperVoice.load(model, config_path=model.with_suffix(".onnx.json"))
    _LOADED[naam] = stem
    return stem


def speak(cfg: Config, text: str, out_path: Path) -> None:
    stem = load_voice(cfg)
    wav_pad = out_path.with_suffix(".wav")

    with wave.open(str(wav_pad), "wb") as bestand:
        stem.synthesize_wav(text, bestand, _synthesis_config(cfg))

    ffmpeg(["-y", "-i", str(wav_pad), "-codec:a", "libmp3lame",
            "-b:a", "128k", "-ar", "44100", str(out_path)], check=True)
    wav_pad.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
#  Controle voor 'ytauto check' en de bedieningspagina
# ---------------------------------------------------------------------------


def check_voice(cfg: Config, download: bool = False) -> dict:
    """Zegt of er straks echt gesproken kan worden, zonder iets in te spreken."""
    if not is_installed():
        return {"ok": False, "reason": "piper-tts is niet geïnstalleerd "
                                       "(pip install -r requirements.txt)"}

    naam = model_name(cfg)
    try:
        model_paths(naam)
    except PiperUnavailable as exc:
        return {"ok": False, "reason": str(exc)}

    if is_downloaded(naam):
        return {"ok": True, "voice": naam, "detail": f"{naam}, staat lokaal klaar"}

    if not download:
        return {"ok": True, "voice": naam,
                "detail": f"{naam}, wordt bij de eerste video opgehaald"}

    try:
        ensure_model(naam)
    except PiperUnavailable as exc:
        return {"ok": False, "reason": str(exc)}
    return {"ok": True, "voice": naam, "detail": f"{naam}, opgehaald"}
