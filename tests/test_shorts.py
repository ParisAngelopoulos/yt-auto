"""Shorts: staand beeld, een haak vooraan, en rond de minuut.

Een Short is geen ingekort verhaal. Wat hier bewaakt wordt is dat hij begint
met iets dat vasthoudt, dat de zinnen in de volgorde van het verhaal staan,
en dat de veiligheidscontrole een video van een minuut niet afkeurt omdat de
ondergrens voor lange video's geldt.
"""

import re

import pytest

from ytauto.config import load_config
from ytauto.pipeline import shorts_config
from ytauto.safety import check_blueprint
from ytauto.scripting.blueprint import SHORT_MODES, STORY_MODES, to_scenes, validate
from ytauto.scripting.folk_bank import TRADITIONS
from ytauto.scripting.folk_patterns import PATTERNS
from ytauto.scripting.local_writer import compose_short, write_blueprint, write_short


@pytest.fixture
def short_cfg(story_cfg):
    return shorts_config(story_cfg)


# ---------------------------------------------------------------------------
#  Vorm
# ---------------------------------------------------------------------------


def test_de_short_is_staand(short_cfg):
    breedte, hoogte = short_cfg.resolution
    assert hoogte > breedte, "een Short hoort staand te zijn"
    assert (breedte, hoogte) == (1080, 1920)


def test_de_lange_video_blijft_liggend(story_cfg):
    """shorts_config mag de gewone config niet aanpassen."""
    shorts_config(story_cfg)
    breedte, hoogte = story_cfg.resolution
    assert breedte > hoogte


def test_hij_begint_met_een_haak(short_cfg):
    for seed in range(12):
        bp = write_short(short_cfg, seed=seed)
        assert bp.beats[0].mode == "hook", bp.title
        assert bp.shorts is True


def test_hij_eindigt_met_de_herkomst(short_cfg):
    """Een hervertelling zonder bronvermelding hoort niet online."""
    for seed in range(8):
        bp = write_short(short_cfg, seed=seed)
        assert bp.beats[-1].mode == "source"


def test_de_lengte_past_bij_shorts(short_cfg):
    for seed in range(20):
        bp = write_short(short_cfg, seed=seed)
        assert 30 < bp.estimated_duration < 110, f"{bp.title}: {bp.estimated_duration:.0f}s"


def test_het_tempo_is_strakker_dan_bij_een_lang_verhaal():
    for mode, kort in SHORT_MODES.items():
        if mode in STORY_MODES:
            assert kort["pause"] <= STORY_MODES[mode]["pause"], mode
            assert kort["min"] <= STORY_MODES[mode]["min"], mode


def test_een_short_krijgt_het_korte_tempo(short_cfg):
    bp = write_short(short_cfg, seed=3)
    scenes = to_scenes(bp, seed=1)
    assert scenes[0].min_duration == SHORT_MODES["hook"]["min"]


# ---------------------------------------------------------------------------
#  Inhoud
# ---------------------------------------------------------------------------


def test_de_zinnen_staan_in_de_volgorde_van_het_verhaal(short_cfg):
    """Er sprak iemand voordat hij er was; dat is waar dit tegen beschermt."""
    for tradition in TRADITIONS[:4]:
        for pattern in PATTERNS:
            bp = compose_short(short_cfg, tradition, pattern, seed=5)
            # Elke gekozen beat hoort verder in de arc te staan dan de vorige.
            vorige = -1
            for beat in bp.beats[1:-1]:
                plekken = [i for i, e in enumerate(pattern["arc"])
                           if e["mode"] == beat.mode and i > vorige]
                assert plekken, f"{pattern['key']}: {beat.mode} staat te vroeg"
                vorige = plekken[0]


def test_de_haak_herhaalt_de_openingszin_niet(short_cfg):
    """Twee keer dezelfde mededeling in de eerste tien seconden is dodelijk."""
    for seed in range(20):
        bp = write_short(short_cfg, seed=seed)
        haak = bp.beats[0].narration.lower()
        opening = next((b.narration.lower() for b in bp.beats if b.mode == "open"), "")
        if not opening:
            continue
        klein = {"the", "a", "an", "and", "that", "it", "is", "was", "of", "to",
                 "in", "at", "on", "for", "you", "they", "not", "but", "would"}
        def kern(t):
            return {w.strip('.,"\'').lower() for w in t.split()} - klein
        gedeeld = kern(haak) & kern(opening)
        assert len(gedeeld) < 4, f"{bp.title}: haak en opening delen {gedeeld}"


def test_elk_patroon_levert_een_geldige_short(short_cfg):
    for tradition in TRADITIONS:
        for pattern in PATTERNS:
            bp = compose_short(short_cfg, tradition, pattern, seed=9)
            validate(bp)
            rapport = check_blueprint(short_cfg, bp)
            assert rapport.ok, f"{bp.title}: {rapport.summary()}"
            assert not rapport.warnings, f"{bp.title}: {rapport.warnings}"


def test_de_sleutel_botst_niet_met_het_lange_verhaal(short_cfg):
    bp = write_short(short_cfg, seed=4)
    assert bp.key.endswith("-short")


def test_hij_slaat_over_wat_al_gemaakt_is(short_cfg):
    eerste = write_short(short_cfg, seed=6)
    tweede = write_short(short_cfg, taken={eerste.key}, seed=6)
    assert tweede.key != eerste.key


# ---------------------------------------------------------------------------
#  Taal
# ---------------------------------------------------------------------------

# 'a the last week of the harvest' — het seizoen brengt zijn eigen lidwoord
# mee, dus een lidwoord ervoor levert onzin op.
STRUIKELT = re.compile(r"\b(a|an|every|one)\s+(the|that|those)\b", re.IGNORECASE)


def test_geen_dubbele_lidwoorden_in_lange_verhalen_of_shorts(story_cfg, short_cfg):
    for seed in range(30):
        for bp in (write_blueprint(story_cfg, seed=seed), write_short(short_cfg, seed=seed)):
            for beat in bp.beats:
                assert not STRUIKELT.search(beat.narration), beat.narration


def test_een_short_is_niet_te_kort_maar_mag_wel_kort(story_cfg, short_cfg):
    """De ondergrens van anderhalve minuut geldt niet voor een Short."""
    kort = write_short(short_cfg, seed=2)
    assert kort.estimated_duration < 90
    assert check_blueprint(short_cfg, kort).ok

    lang = write_blueprint(story_cfg, seed=2)
    lang.shorts = True                      # net doen alsof: te lang voor een Short
    rapport = check_blueprint(short_cfg, lang)
    assert not rapport.ok
    assert "Short" in rapport.summary()


# ---------------------------------------------------------------------------
#  Beeld
# ---------------------------------------------------------------------------


def test_het_bijschrift_blijft_uit_de_knoppen_van_youtube():
    """Onderin een Short staat de interface van YouTube, niet jouw tekst."""
    from PIL import ImageChops

    from ytauto.render.frame import render_frame

    spec = {"kind": "story", "setting": "hills", "time": "dusk",
            "subjects": [], "caption": "Rjukan"}
    zonder = render_frame({**spec, "caption": None}, (360, 640), seed=1)
    met = render_frame(spec, (360, 640), seed=1)

    verschil = ImageChops.difference(zonder.convert("L"), met.convert("L"))
    vak = verschil.getbbox()
    assert vak is not None, "het bijschrift is helemaal niet getekend"
    onderkant = vak[3] / 640
    assert onderkant < 0.85, f"bijschrift loopt tot {onderkant:.0%} van de hoogte"


def test_bij_liggend_beeld_blijft_het_bijschrift_waar_het_stond():
    from PIL import ImageChops

    from ytauto.render.frame import render_frame

    spec = {"kind": "story", "setting": "hills", "time": "dusk",
            "subjects": [], "caption": "Rjukan"}
    zonder = render_frame({**spec, "caption": None}, (640, 360), seed=1)
    met = render_frame(spec, (640, 360), seed=1)
    vak = ImageChops.difference(zonder.convert("L"), met.convert("L")).getbbox()
    assert vak is not None and vak[3] / 360 > 0.85
