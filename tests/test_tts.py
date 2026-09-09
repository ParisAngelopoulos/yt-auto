"""Spraak: de terugval op de teststem en de cache."""

import pytest

from ytauto.config import load_config
from ytauto.tts import _cache_key, effective_provider, synthesize


def test_zonder_sleutel_valt_hij_terug_op_de_teststem():
    """De tweede knop moet altijd iets opleveren, ook zonder ElevenLabs."""
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "elevenlabs"
    cfg.secrets.elevenlabs_api_key = ""
    assert effective_provider(cfg) == "offline"


def test_met_sleutel_gebruikt_hij_elevenlabs():
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "elevenlabs"
    cfg.secrets.elevenlabs_api_key = "sleutel"
    assert effective_provider(cfg) == "elevenlabs"


def test_offline_blijft_offline_ook_met_sleutel():
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "offline"
    cfg.secrets.elevenlabs_api_key = "sleutel"
    assert effective_provider(cfg) == "offline"


def test_cache_scheidt_de_stemmen():
    """Anders krijg je robotstem uit de cache nadat je ElevenLabs koppelt."""
    zin = "Look, a red balloon!"
    basis = {"voice_id": "abc", "stability": 0.45}
    offline = _cache_key(zin, {**basis, "_provider": "offline"})
    echt = _cache_key(zin, {**basis, "_provider": "elevenlabs"})
    assert offline != echt


def test_cache_scheidt_ook_op_steminstellingen():
    zin = "Look, a red balloon!"
    a = _cache_key(zin, {"_provider": "elevenlabs", "voice_id": "abc", "speed": 0.92})
    b = _cache_key(zin, {"_provider": "elevenlabs", "voice_id": "abc", "speed": 1.0})
    c = _cache_key(zin, {"_provider": "elevenlabs", "voice_id": "xyz", "speed": 0.92})
    assert len({a, b, c}) == 3


def test_dezelfde_zin_geeft_dezelfde_sleutel():
    instellingen = {"_provider": "elevenlabs", "voice_id": "abc"}
    assert _cache_key("hallo", instellingen) == _cache_key("hallo", instellingen)


def test_tweede_keer_komt_uit_de_cache(tmp_path):
    """Opnieuw renderen mag geen tegoed kosten."""
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "offline"
    zin = "This color is red."

    eerste = synthesize(cfg, zin, tmp_path / "scenes" / "a.mp3", cache_dir=tmp_path / "cache")
    bestanden = list((tmp_path / "cache").glob("*.mp3"))
    tweede = synthesize(cfg, zin, tmp_path / "scenes" / "b.mp3", cache_dir=tmp_path / "cache")

    assert eerste == pytest.approx(tweede, abs=0.02)
    assert len(list((tmp_path / "cache").glob("*.mp3"))) == len(bestanden) == 1
