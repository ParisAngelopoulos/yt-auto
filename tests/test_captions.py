"""Ondertiteling: leesbaar geknipt, op tijd, en zonder de tijdlijn te verzetten.

Het grootste deel van de Shorts wordt zonder geluid bekeken. Een verhaal-Short
zonder tekst in beeld is dan een reeks landschappen zonder betekenis, dus dit
is geen opsmuk maar de helft van het product.
"""

import pytest

from ytauto.config import load_config
from ytauto.pipeline import shorts_config
from ytauto.script_builder import Scene
from ytauto.video.assemble import Timeline, plan_segments, with_captions
from ytauto.video.captions import MAX_CHARS, burn_in, render_caption, split_text, time_chunks


def _timeline(zinnen, holds, duren):
    scenes = []
    for index, (zin, duur) in enumerate(zip(zinnen, duren)):
        scene = Scene(id=f"{index:03d}-tell", narration=zin,
                      visual={"kind": "story", "setting": "hills", "time": "dusk",
                              "subjects": []})
        scene.duration = duur
        scenes.append(scene)
    starts, loopt = [], 0.0
    for hold in holds:
        starts.append(loopt)
        loopt += hold
    return Timeline(scenes=scenes, starts=starts, holds=list(holds), total=loopt)


# ---------------------------------------------------------------------------
#  Knippen
# ---------------------------------------------------------------------------


def test_een_korte_zin_blijft_heel():
    assert split_text("He was gone one night.") == ["He was gone one night."]


def test_er_wordt_op_leestekens_geknipt():
    """Daar ademt de verteller, dus daar knipt het oog ook."""
    stukjes = split_text("Everybody at Naxos goes the long way round. "
                         "Nobody will tell you why.")
    assert any(s.endswith("round.") for s in stukjes)
    assert stukjes[-1] == "Nobody will tell you why."


def test_er_blijft_nooit_een_los_woord_over():
    """'to' alleen in beeld leest als een fout."""
    for zin in ["Maria was a turf cutter there, young enough to find that funny.",
                "The old road is older than the village and nobody uses it now.",
                "He came into the village at first light, from the wrong direction."]:
        stukjes = split_text(zin)
        assert len(stukjes[-1].split()) >= 2, stukjes


def test_de_stukjes_samen_zijn_de_hele_zin():
    zin = 'He said, "You are early," and walked on into the dark.'
    assert " ".join(split_text(zin)).split() == zin.split()


def test_de_regels_passen_op_het_scherm():
    zin = ("There is a kind of cold that does not feel like cold at all, "
           "and that is the kind to be afraid of.")
    for stukje in split_text(zin):
        assert len(stukje) <= MAX_CHARS + 8, stukje


# ---------------------------------------------------------------------------
#  Tijd
# ---------------------------------------------------------------------------


def test_de_stukjes_vullen_precies_de_spreektijd():
    chunks = time_chunks("He was gone one night. They had been looking for him.", 2.0, 4.0)
    assert chunks[0].start == pytest.approx(2.0)
    assert chunks[-1].end == pytest.approx(6.0)


def test_er_zitten_geen_gaten_tussen_de_stukjes():
    chunks = time_chunks("One night, one road, and nobody on it but him.", 1.0, 5.0)
    for eerste, tweede in zip(chunks, chunks[1:]):
        assert eerste.end == pytest.approx(tweede.start)


def test_een_langer_stukje_staat_langer_in_beeld():
    chunks = time_chunks("A short one. And here is a considerably longer one.", 0.0, 6.0)
    assert len(chunks) > 1
    kortste = min(chunks, key=lambda c: len(c.text))
    langste = max(chunks, key=lambda c: len(c.text))
    assert langste.duration > kortste.duration


def test_zonder_spreektijd_komt_er_niets():
    assert time_chunks("Wat dan ook.", 0.0, 0.0) == []


# ---------------------------------------------------------------------------
#  In de montage
# ---------------------------------------------------------------------------


@pytest.fixture
def short_cfg():
    return shorts_config(load_config())


def test_de_tijdlijn_wordt_niet_langer_of_korter(short_cfg, tmp_path):
    """Opknippen mag geen beeldje toevoegen; anders loopt het uit de pas."""
    holds = [4.0, 5.0, 4.5]
    timeline = _timeline(["He was gone one night. They looked for three days.",
                          "The road is older than the village itself.",
                          "Nobody ever said what it was."], holds, [3.0, 3.4, 2.6])
    fade = float(short_cfg.video["crossfade_seconds"])
    stukken = plan_segments(holds, fade)

    (tmp_path / "frames").mkdir()
    from ytauto.render.frame import render_frame
    for scene in timeline.scenes:
        render_frame(scene.visual, (180, 320), seed=1).save(
            tmp_path / "frames" / f"{scene.id}.png")

    shots = with_captions(short_cfg, timeline, stukken, fade,
                          tmp_path / "frames", tmp_path)
    assert sum(s.seconds for s in shots) == pytest.approx(sum(s[2] for s in stukken))
    assert len(shots) > len(stukken), "er is niets opgeknipt"


def test_er_staat_nooit_tekst_op_een_overgang(short_cfg, tmp_path):
    """Tekst die half door een crossfade heen zweeft leest niet."""
    holds = [4.0, 5.0, 4.5]
    timeline = _timeline(["Een zin die lang genoeg is om te knippen in stukjes.",
                          "Nog een zin die lang genoeg is om te knippen.",
                          "En de laatste zin van dit korte verhaal."], holds, [3.0, 3.4, 2.6])
    fade = float(short_cfg.video["crossfade_seconds"])
    (tmp_path / "frames").mkdir()
    from ytauto.render.frame import render_frame
    for scene in timeline.scenes:
        render_frame(scene.visual, (180, 320), seed=1).save(
            tmp_path / "frames" / f"{scene.id}.png")

    shots = with_captions(short_cfg, timeline, plan_segments(holds, fade), fade,
                          tmp_path / "frames", tmp_path)
    for shot in shots:
        if shot.kind == "xfade":
            assert shot.image is None


def test_zonder_ondertiteling_verandert_er_niets(story_cfg, tmp_path):
    holds = [4.0, 5.0]
    timeline = _timeline(["Een zin.", "Nog een zin."], holds, [2.0, 2.0])
    stukken = plan_segments(holds, 0.6)
    shots = with_captions(story_cfg, timeline, stukken, 0.6, tmp_path, tmp_path)
    assert len(shots) == len(stukken)
    assert all(shot.image is None for shot in shots)


# ---------------------------------------------------------------------------
#  Beeld
# ---------------------------------------------------------------------------


def test_de_tekst_staat_in_de_veilige_zone():
    """Onderin legt YouTube zijn eigen knoppen; bovenin staat de lucht."""
    laag = render_caption("Nobody will tell you why.", (360, 640))
    vak = laag.getbbox()
    assert vak is not None
    boven, onder = vak[1] / 640, vak[3] / 640
    assert 0.45 < boven and onder < 0.80, (boven, onder)


def test_de_tekst_wordt_kleiner_als_hij_niet_past():
    kort = render_caption("Kort.", (360, 640)).getbbox()
    lang = render_caption("Een aanzienlijk langere regel tekst hier.", (360, 640)).getbbox()
    # Inclusief de zwarte rand eromheen moet het binnen het beeld blijven.
    assert lang[2] - lang[0] <= 360 * 0.95
    assert (lang[3] - lang[1]) < (kort[3] - kort[1]) * 1.2


def test_inbranden_laat_het_landschap_heel():
    from PIL import ImageChops

    from ytauto.render.frame import render_frame

    frame = render_frame({"kind": "story", "setting": "hills", "time": "dusk",
                          "subjects": []}, (360, 640), seed=1)
    met = burn_in(frame, "Nobody will tell you why.")
    vak = ImageChops.difference(frame.convert("L"), met.convert("L")).getbbox()
    assert vak is not None
    assert vak[1] / 640 > 0.45, "de tekst zit te hoog"
    assert vak[3] / 640 < 0.80, "de tekst zit te laag"
