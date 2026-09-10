"""Sleutels opslaan en controleren."""

import pytest

from ytauto.config import SECRET_KEYS, load_config, write_secrets
from ytauto.scripting import claude_writer


# ---------------------------------------------------------------------------
#  .env schrijven
# ---------------------------------------------------------------------------


def test_maakt_het_bestand_aan(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    pad = tmp_path / ".env"
    assert write_secrets({"ANTHROPIC_API_KEY": "sk-test"}, pad) == ["ANTHROPIC_API_KEY"]
    assert "ANTHROPIC_API_KEY=sk-test" in pad.read_text()


def test_werkt_een_bestaande_regel_bij_zonder_de_rest_te_raken(tmp_path):
    pad = tmp_path / ".env"
    pad.write_text("# mijn notitie\nANTHROPIC_API_KEY=oud\nELEVENLABS_API_KEY=blijft\n")
    write_secrets({"ANTHROPIC_API_KEY": "nieuw"}, pad)
    inhoud = pad.read_text()
    assert "ANTHROPIC_API_KEY=nieuw" in inhoud
    assert "ELEVENLABS_API_KEY=blijft" in inhoud
    assert "# mijn notitie" in inhoud
    assert "oud" not in inhoud


def test_leeg_veld_wist_een_bestaande_sleutel_niet(tmp_path):
    """In het formulier laat je een veld leeg als je het niet wilt wijzigen."""
    pad = tmp_path / ".env"
    pad.write_text("ELEVENLABS_API_KEY=bestaand\n")
    assert write_secrets({"ELEVENLABS_API_KEY": "   "}, pad) == []
    assert "ELEVENLABS_API_KEY=bestaand" in pad.read_text()


def test_onbekende_namen_worden_genegeerd(tmp_path):
    """Anders zou een aanroep van buitenaf willekeurige variabelen kunnen zetten."""
    pad = tmp_path / ".env"
    assert write_secrets({"PATH": "/kwaad", "AWS_SECRET": "x"}, pad) == []
    assert not pad.exists()


def test_bestand_is_alleen_voor_jou_leesbaar(tmp_path):
    pad = tmp_path / ".env"
    write_secrets({"ANTHROPIC_API_KEY": "sk-test"}, pad)
    assert oct(pad.stat().st_mode)[-3:] == "600"


def test_alle_sleutels_worden_geaccepteerd(tmp_path):
    pad = tmp_path / ".env"
    opgeslagen = write_secrets({k: f"waarde-{k}" for k in SECRET_KEYS}, pad)
    assert set(opgeslagen) == set(SECRET_KEYS)
    assert len(pad.read_text().strip().splitlines()) == len(SECRET_KEYS)


# ---------------------------------------------------------------------------
#  Sleutel controleren
# ---------------------------------------------------------------------------


def _nep_client(monkeypatch, modellen=None, fout=None):
    class Model:
        def __init__(self, mid): self.id = mid

    class Models:
        def list(self):
            if fout:
                raise fout
            return [Model(m) for m in (modellen or [])]

    class Client:
        def __init__(self, api_key=None): self.models = Models()

    monkeypatch.setattr("anthropic.Anthropic", Client)


def test_zonder_sleutel_geen_netwerkaanroep():
    cfg = load_config()
    cfg.secrets.anthropic_api_key = ""
    info = claude_writer.check_credentials(cfg)
    assert not info["ok"] and "ANTHROPIC_API_KEY" in info["reason"]


def test_werkende_sleutel(monkeypatch):
    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-test"
    _nep_client(monkeypatch, modellen=[cfg.script["model"], "claude-sonnet-5"])
    info = claude_writer.check_credentials(cfg)
    assert info["ok"] and "warning" not in info


def test_ingesteld_model_niet_beschikbaar_geeft_waarschuwing(monkeypatch):
    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-test"
    _nep_client(monkeypatch, modellen=["claude-haiku-4-5"])
    info = claude_writer.check_credentials(cfg)
    assert info["ok"] and "warning" in info


def test_geweigerde_sleutel_geeft_leesbare_uitleg(monkeypatch):
    class AuthenticationError(Exception):
        pass

    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-fout"
    _nep_client(monkeypatch, fout=AuthenticationError("401"))
    info = claude_writer.check_credentials(cfg)
    assert not info["ok"] and "geweigerd" in info["reason"]


def test_geen_tegoed_geeft_leesbare_uitleg(monkeypatch):
    class PermissionDeniedError(Exception):
        pass

    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-test"
    _nep_client(monkeypatch, fout=PermissionDeniedError("403"))
    info = claude_writer.check_credentials(cfg)
    assert not info["ok"] and "tegoed" in info["reason"]


# ---------------------------------------------------------------------------
#  Wat de pagina te zien krijgt
# ---------------------------------------------------------------------------


def test_status_verraadt_geen_sleutelwaarden():
    """De pagina mag weten of een sleutel er is, nooit wat hij is."""
    import json

    from ytauto.ui.server import status_payload

    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-geheim-abc123"
    cfg.secrets.elevenlabs_api_key = "sk_geheim_xyz789"

    tekst = json.dumps(status_payload(cfg))
    assert "sk-geheim-abc123" not in tekst
    assert "sk_geheim_xyz789" not in tekst
    assert json.loads(tekst)["keys"]["anthropic"] is True


def test_alleen_ingevulde_sleutels_worden_getest(monkeypatch):
    """Zonder sleutel geen netwerkaanroep, dus ook geen wachttijd."""
    from ytauto.ui.server import test_all_keys

    cfg = load_config()
    cfg.secrets.anthropic_api_key = "sk-test"
    cfg.secrets.elevenlabs_api_key = ""
    cfg.secrets.youtube_refresh_token = ""
    _nep_client(monkeypatch, modellen=[cfg.script["model"]])

    uitslag = test_all_keys(cfg)
    assert set(uitslag) == {"anthropic"}
