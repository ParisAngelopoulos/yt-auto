"""ffmpeg vinden en de lengte van een bestand bepalen.

Het bijgeleverde ffmpeg heeft geen ffprobe. De terugval daarvoor moet
even nauwkeurig zijn, anders lopen beeld en geluid uit elkaar.
"""

import os
import subprocess

import pytest

from ytauto import media


@pytest.fixture(scope="module")
def toon(tmp_path_factory):
    """Een toon van precies 2,5 seconde."""
    pad = tmp_path_factory.mktemp("media") / "toon.wav"
    subprocess.run(
        [media.ffmpeg_bin(), "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2.5",
         str(pad)],
        capture_output=True, check=True,
    )
    return pad


def test_ffmpeg_is_te_vinden():
    binary = media.ffmpeg_bin()
    assert os.path.exists(binary) or binary == "ffmpeg"


def test_ffmpeg_kan_alles_wat_de_pipeline_gebruikt():
    """Een uitgeklede ffmpeg zou pas tijdens het monteren opvallen."""
    encoders = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-encoders"],
                              capture_output=True, text=True).stdout
    filters = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-filters"],
                             capture_output=True, text=True).stdout
    for naam in ("libx264", "aac", "libmp3lame"):
        assert naam in encoders, naam
    for naam in ("xfade", "loudnorm", "anullsrc"):
        assert naam in filters, naam


def test_duur_klopt(toon):
    assert media.duration(toon) == pytest.approx(2.5, abs=0.05)


def test_duur_klopt_ook_zonder_ffprobe(toon, monkeypatch):
    monkeypatch.setattr(media, "ffprobe_bin", lambda: None)
    assert media.duration(toon) == pytest.approx(2.5, abs=0.05)


def test_beide_wegen_geven_hetzelfde(toon, monkeypatch):
    met = media.duration(toon)
    monkeypatch.setattr(media, "ffprobe_bin", lambda: None)
    zonder = media.duration(toon)
    assert met == pytest.approx(zonder, abs=0.05)


def test_onbruikbaar_bestand_geeft_een_duidelijke_fout(tmp_path, monkeypatch):
    rommel = tmp_path / "rommel.mp3"
    rommel.write_bytes(b"dit is geen audio")
    monkeypatch.setattr(media, "ffprobe_bin", lambda: None)
    with pytest.raises(media.MediaError, match="lengte"):
        media.duration(rommel)


def test_describe_zegt_waar_ffmpeg_vandaan_komt():
    tekst = media.describe()
    assert "systeem" in tekst or "meegeleverd" in tekst
