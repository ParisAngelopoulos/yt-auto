"""De gratis weg: welke schrijver en welke stem er gekozen worden.

Hier zit geen netwerk in. Alles wat naar buiten zou gaan — het stemmodel
ophalen, Ollama aanspreken — wordt nagebootst, zodat deze tests ook draaien
op een machine zonder internet.
"""

import json

import pytest

from ytauto.config import load_config
from ytauto.pipeline import PAID_PROVIDERS, resolve_script_provider, script_chain
from ytauto.tts import piper


# ---------------------------------------------------------------------------
#  De keten van schrijvers
# ---------------------------------------------------------------------------


def test_auto_eindigt_altijd_bij_de_eigen_verteller():
    cfg = load_config()
    cfg.raw["script"]["provider"] = "auto"
    assert script_chain(cfg)[-1] == "local"


def test_ook_claude_valt_terug_op_iets_gratis():
    """Een lege portemonnee mag de knop niet stukmaken."""
    cfg = load_config()
    cfg.raw["script"]["provider"] = "claude"
    assert script_chain(cfg) == ("claude", "local")


def test_een_onbekende_provider_wordt_de_eigen_verteller():
    cfg = load_config()
    cfg.raw["script"]["provider"] = "typefout"
    assert script_chain(cfg) == ("local",)


def test_zonder_sleutel_en_zonder_ollama_is_het_gratis(monkeypatch):
    from ytauto.scripting import ollama_writer

    monkeypatch.setattr(ollama_writer, "is_available", lambda cfg: False)
    cfg = load_config()
    cfg.raw["script"]["provider"] = "auto"
    cfg.secrets.anthropic_api_key = ""
    gekozen = resolve_script_provider(cfg)
    assert gekozen == "local"
    assert gekozen not in PAID_PROVIDERS


def test_met_sleutel_kiest_auto_claude(monkeypatch):
    cfg = load_config()
    cfg.raw["script"]["provider"] = "auto"
    cfg.secrets.anthropic_api_key = "sk-ant-test"
    pytest.importorskip("anthropic")
    assert resolve_script_provider(cfg) == "claude"


def test_ollama_gaat_voor_op_de_eigen_verteller(monkeypatch):
    from ytauto.scripting import ollama_writer

    monkeypatch.setattr(ollama_writer, "is_available", lambda cfg: True)
    cfg = load_config()
    cfg.raw["script"]["provider"] = "auto"
    cfg.secrets.anthropic_api_key = ""
    assert resolve_script_provider(cfg) == "ollama"
    assert "ollama" not in PAID_PROVIDERS


# ---------------------------------------------------------------------------
#  De gratis stem
# ---------------------------------------------------------------------------


def test_een_stemnaam_die_niet_klopt_geeft_meteen_een_duidelijke_fout():
    with pytest.raises(piper.PiperUnavailable) as fout:
        piper.model_paths("alan")
    assert "en_GB-alan-medium" in str(fout.value)


def test_het_model_komt_in_de_projectmap_te_staan():
    model, config = piper.model_paths("en_GB-alan-medium")
    assert model.name == "en_GB-alan-medium.onnx"
    assert config.name == "en_GB-alan-medium.onnx.json"
    assert model.parent == piper.VOICES_DIR


def test_een_half_binnengehaald_model_telt_niet_als_klaar(tmp_path, monkeypatch):
    """Een afgebroken download mag de volgende keer niet voor compleet doorgaan."""
    monkeypatch.setattr(piper, "VOICES_DIR", tmp_path)
    (tmp_path / "en_GB-alan-medium.onnx").write_bytes(b"x" * 100)
    (tmp_path / "en_GB-alan-medium.onnx.json").write_text("{}")
    assert piper.is_downloaded("en_GB-alan-medium") is False


def test_een_compleet_model_telt_wel(tmp_path, monkeypatch):
    monkeypatch.setattr(piper, "VOICES_DIR", tmp_path)
    (tmp_path / "en_GB-alan-medium.onnx").write_bytes(b"x" * 1_500_000)
    (tmp_path / "en_GB-alan-medium.onnx.json").write_text("{}")
    assert piper.is_downloaded("en_GB-alan-medium") is True


def test_een_mislukte_download_laat_niets_halfs_achter(tmp_path, monkeypatch):
    monkeypatch.setattr(piper, "VOICES_DIR", tmp_path)

    def stuk(url, timeout=0):
        raise OSError("de verbinding viel weg")

    monkeypatch.setattr(piper, "urlopen", stuk)
    with pytest.raises(piper.PiperUnavailable):
        piper.ensure_model("en_GB-alan-medium", log=lambda *a: None)
    assert list(tmp_path.iterdir()) == []


def test_de_snelheid_uit_channel_yaml_werkt_dezelfde_kant_op():
    """0.94 betekent langzamer, bij beide stemmen."""
    pytest.importorskip("piper")
    cfg = load_config()
    cfg.raw["tts"]["speed"] = 0.94
    langzaam = piper._synthesis_config(cfg).length_scale
    cfg.raw["tts"]["speed"] = 1.2
    snel = piper._synthesis_config(cfg).length_scale
    assert langzaam > 1.0 > snel


def test_de_voorgestelde_stemmen_hebben_een_geldige_naam():
    for naam in piper.SUGGESTED:
        assert piper.NAME_PATTERN.match(naam), naam


# ---------------------------------------------------------------------------
#  Ollama
# ---------------------------------------------------------------------------


class _Antwoord:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_ollama_zonder_server_is_gewoon_niet_beschikbaar(monkeypatch):
    import requests

    from ytauto.scripting import ollama_writer

    def weg(*args, **kwargs):
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(ollama_writer.requests, "get", weg)
    cfg = load_config()
    assert ollama_writer.is_available(cfg) is False
    assert ollama_writer.check_credentials(cfg)["ok"] is False


def test_ollama_herkent_het_model_ook_zonder_versielabel(monkeypatch):
    from ytauto.scripting import ollama_writer

    monkeypatch.setattr(ollama_writer.requests, "get",
                        lambda *a, **k: _Antwoord({"models": [{"name": "qwen2.5:14b"}]}))
    cfg = load_config()
    cfg.raw["script"]["ollama_model"] = "qwen2.5"
    assert ollama_writer.is_available(cfg) is True


def test_ollama_meldt_het_als_het_model_ontbreekt(monkeypatch):
    from ytauto.scripting import ollama_writer

    monkeypatch.setattr(ollama_writer.requests, "get",
                        lambda *a, **k: _Antwoord({"models": [{"name": "iets-anders"}]}))
    cfg = load_config()
    cfg.raw["script"]["ollama_model"] = "qwen2.5:14b"
    info = ollama_writer.check_credentials(cfg)
    assert info["ok"] is False
    assert "ollama pull" in info["reason"]


def test_ollama_stuurt_het_schema_mee(monkeypatch, story_cfg):
    """Zonder schema verzint een klein model velden die de renderer niet kent."""
    from ytauto.scripting import ollama_writer
    from ytauto.scripting.tale_writer import load_tales, to_blueprint

    verstuurd = {}
    monkeypatch.setattr(ollama_writer.requests, "get",
                        lambda *a, **k: _Antwoord({"models": [{"name": "qwen2.5:14b"}]}))

    verhaal = to_blueprint(load_tales()[0], story_cfg)
    antwoord = json.loads(verhaal.to_json())
    antwoord["tradition"] = antwoord.pop("lesson_kind")

    def nep_post(url, json=None, timeout=0):
        verstuurd.update(json)
        return _Antwoord({"message": {"content": __import__("json").dumps(antwoord)}})

    monkeypatch.setattr(ollama_writer.requests, "post", nep_post)
    story_cfg.raw["script"]["ollama_model"] = "qwen2.5:14b"

    bp = ollama_writer.write_blueprint(story_cfg)
    assert verstuurd["format"]["type"] == "object"
    assert "scenes" in verstuurd["format"]["properties"]
    assert verstuurd["stream"] is False
    assert bp.source == "ollama"
    assert bp.format == "folklore"
    assert bp.lesson_kind == verhaal.lesson_kind


def test_onbruikbare_json_van_een_klein_model_geeft_een_nette_fout(monkeypatch, story_cfg):
    from ytauto.scripting import ollama_writer
    from ytauto.scripting.blueprint import BlueprintError

    monkeypatch.setattr(ollama_writer.requests, "get",
                        lambda *a, **k: _Antwoord({"models": [{"name": "qwen2.5:14b"}]}))
    monkeypatch.setattr(ollama_writer.requests, "post",
                        lambda *a, **k: _Antwoord({"message": {"content": "geen json"}}))
    story_cfg.raw["script"]["ollama_model"] = "qwen2.5:14b"

    with pytest.raises(BlueprintError):
        ollama_writer.write_blueprint(story_cfg)
