"""Spraak: welke stem er gekozen wordt, en de cache."""

import pytest

from ytauto.config import load_config
from ytauto.tts import _cache_key, effective_provider, synthesize, voice_status


@pytest.fixture
def met_piper(monkeypatch):
    """Doet alsof piper-tts geïnstalleerd is, los van deze machine."""
    from ytauto.tts import piper

    monkeypatch.setattr(piper, "is_installed", lambda: True)


@pytest.fixture
def zonder_piper(monkeypatch):
    from ytauto.tts import piper

    monkeypatch.setattr(piper, "is_installed", lambda: False)


def test_zonder_sleutel_valt_hij_terug_op_de_gratis_stem(met_piper):
    """Geen sleutel is geen reden voor een robotstem: Piper kost niets."""
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "elevenlabs"
    cfg.secrets.elevenlabs_api_key = ""
    assert effective_provider(cfg) == "piper"


def test_zonder_piper_blijft_de_teststem_over(zonder_piper):
    """De tweede knop moet altijd iets opleveren, ook als er niets staat."""
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "piper"
    assert effective_provider(cfg) == "offline"


def test_de_gratis_stem_is_gratis_en_publiceerbaar(met_piper):
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "piper"
    stem = voice_status(cfg)
    assert stem["free"] is True
    assert stem["publishable"] is True


def test_elevenlabs_is_niet_gratis():
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "elevenlabs"
    cfg.secrets.elevenlabs_api_key = "sleutel"
    stem = voice_status(cfg)
    assert stem["free"] is False


def test_de_teststem_is_gratis_maar_niet_om_te_publiceren(zonder_piper):
    cfg = load_config()
    cfg.raw["tts"]["provider"] = "offline"
    stem = voice_status(cfg)
    assert stem["free"] is True
    assert stem["publishable"] is False
    assert "piper" in stem["reason"].lower()


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
    """Anders krijg je de oude stem uit de cache nadat je een andere kiest."""
    zin = "Look, a red balloon!"
    basis = {"voice_id": "abc", "stability": 0.45}
    offline = _cache_key(zin, {**basis, "_provider": "offline"})
    gratis = _cache_key(zin, {**basis, "_provider": "piper"})
    echt = _cache_key(zin, {**basis, "_provider": "elevenlabs"})
    assert len({offline, gratis, echt}) == 3


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
