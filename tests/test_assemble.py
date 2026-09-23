"""De montage: de tijdlijn moet kloppen en het geheugen mag niet meelopen.

Waarom dit bestand er is: de montage zette eerst alle beelden in één
ffmpeg-aanroep. Elk beeld werd dan vanaf seconde nul gedecodeerd terwijl de
eerste overgang nog liep, dus het geheugengebruik groeide mee met de lengte
van het verhaal. Bij een aflevering van acht minuten liep dat op tot dertien
gigabyte en werd ffmpeg afgeschoten, halverwege het encoderen.
"""

import numpy as np
import pytest

from ytauto.audio.music import SAMPLE_RATE, write_wav
from ytauto.config import load_config
from ytauto.render.frame import render_frame
from ytauto.script_builder import Scene
from ytauto.video.assemble import (Timeline, _frame_counts, build_video,
                                   plan_segments, probe_duration)


def _timeline(holds):
    scenes = [
        Scene(id=f"{i:03d}-tell", narration="x",
              visual={"bg": {"style": "gradient", "top": "#101830", "bottom": "#303050"},
                      "layout": "row", "objects": []})
        for i in range(len(holds))
    ]
    starts, loopt = [], 0.0
    for hold in holds:
        starts.append(loopt)
        loopt += hold
    return Timeline(scenes=scenes, starts=starts, holds=list(holds), total=loopt)


# ---------------------------------------------------------------------------
#  De tijdlijn
# ---------------------------------------------------------------------------


def test_de_stukken_samen_zijn_even_lang_als_de_hele_video():
    holds = [4.0, 6.0, 5.0, 7.0]
    stukken = plan_segments(holds, 0.6)
    assert sum(s[2] for s in stukken) == pytest.approx(sum(holds) + 0.6)


def test_het_eerste_en_laatste_beeld_staan_langer_stil():
    """Daar zit maar aan één kant een overgang tegenaan."""
    holds = [4.0, 6.0, 5.0]
    stil = {index: duur for soort, index, duur in plan_segments(holds, 0.6)
            if soort == "hold"}
    assert stil[0] == pytest.approx(4.0)
    assert stil[1] == pytest.approx(6.0 - 0.6)
    assert stil[2] == pytest.approx(5.0)


def test_een_verhaal_van_één_beeld_heeft_geen_overgang():
    stukken = plan_segments([5.0], 0.6)
    assert stukken == [("hold", 0, 5.6)]


def test_er_zit_een_overgang_tussen_elk_paar():
    holds = [3.0] * 9
    soorten = [s[0] for s in plan_segments(holds, 0.6)]
    assert soorten.count("xfade") == len(holds) - 1
    assert soorten.count("hold") == len(holds)


def test_afrondingen_lopen_niet_op_bij_een_lang_verhaal():
    """Per stuk afronden zou een seconde kunnen schelen; dan loopt de stem uit de pas."""
    holds = [3.7, 4.1, 5.3, 6.9, 4.4] * 16          # 80 scenes
    fade, fps = 0.6, 30
    stukken = plan_segments(holds, fade)
    beeldjes = _frame_counts([s[2] for s in stukken], fps)
    assert sum(beeldjes) == round((sum(holds) + fade) * fps)
    assert all(aantal >= 1 for aantal in beeldjes)


# ---------------------------------------------------------------------------
#  Het geheugen
# ---------------------------------------------------------------------------


def test_er_gaan_nooit_meer_dan_twee_beelden_in_één_aanroep(tmp_path, monkeypatch):
    """Dit is de fout die ffmpeg liet afschieten, en dit houdt hem tegen."""
    from ytauto.video import assemble

    aanroepen: list[list[str]] = []
    monkeypatch.setattr(assemble, "_run_ffmpeg", lambda args: aanroepen.append(args))

    timeline = _timeline([4.0] * 60)
    (tmp_path / "frames").mkdir()
    build_video(load_config(), timeline, tmp_path / "geluid.wav",
                tmp_path / "video.mp4", tmp_path)

    assert aanroepen, "er is niets gecodeerd"
    for args in aanroepen:
        beelden = [a for a in args if str(a).endswith(".png")]
        assert len(beelden) <= 2, f"{len(beelden)} beelden in één aanroep"


# ---------------------------------------------------------------------------
#  Echt monteren
# ---------------------------------------------------------------------------


def test_een_echte_montage_heeft_de_lengte_die_beloofd_is(tmp_path):
    """Draait ffmpeg echt: drie beelden, een stil geluidsspoor, één mp4."""
    cfg = load_config()
    cfg.raw["video"].update({"width": 320, "height": 180, "fps": 24,
                             "encoder_preset": "ultrafast", "crf": 30,
                             "crossfade_seconds": 0.4})

    holds = [1.5, 2.0, 1.5]
    timeline = _timeline(holds)
    frames = tmp_path / "frames"
    frames.mkdir()
    for index, scene in enumerate(timeline.scenes):
        render_frame(scene.visual, (320, 180), seed=index).save(frames / f"{scene.id}.png")

    stilte = np.zeros(int(sum(holds) * SAMPLE_RATE), dtype=np.float32)
    geluid = tmp_path / "geluid.wav"
    write_wav(geluid, stilte)

    video = build_video(cfg, timeline, geluid, tmp_path / "video.mp4", tmp_path)

    assert video.exists() and video.stat().st_size > 1000
    assert probe_duration(video) == pytest.approx(sum(holds) + 0.4, abs=0.15)
    assert not (tmp_path / "segments").exists(), "tussenbestanden zijn blijven staan"
