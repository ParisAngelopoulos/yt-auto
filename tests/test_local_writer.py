"""De gratis verteller: hij moet geldige, complete en verschillende verhalen leveren.

Dit is de schrijver die het doet als er geen sleutel is. Als hij stuk is,
staat de studio stil, en dat is precies wat hij moest oplossen.
"""

import re

import pytest

from ytauto.safety import check_blueprint
from ytauto.scripting.blueprint import STORY_MODES, validate
from ytauto.scripting.folk_bank import ROLE_KINDS, SCENERY, TRADITIONS
from ytauto.scripting.folk_patterns import PATTERNS
from ytauto.scripting.local_writer import (available, bind_slots, compose, fill,
                                           write_blueprint)
from ytauto.render.silhouettes import available_silhouettes
from ytauto.render.story_scene import (available_settings, available_times,
                                       available_weather)


def test_er_komt_een_geldig_verhaal_uit(story_cfg):
    bp = write_blueprint(story_cfg, seed=1)
    validate(bp)
    assert bp.format == "folklore"
    assert bp.source == "local"
    assert bp.beats[0].mode == "title"
    assert bp.beats[-1].mode == "source"


def test_het_verhaal_is_lang_genoeg_om_te_publiceren(story_cfg):
    """Onder de acht minuten is het geen aflevering meer."""
    for seed in range(12):
        bp = write_blueprint(story_cfg, seed=seed)
        assert bp.estimated_duration > 7 * 60, f"{bp.title} is te kort"
        assert bp.estimated_duration < 20 * 60


def test_dezelfde_seed_geeft_hetzelfde_verhaal(story_cfg):
    """Anders levert opnieuw renderen een andere video op dan je gelezen hebt."""
    eerste = write_blueprint(story_cfg, seed=42)
    tweede = write_blueprint(story_cfg, seed=42)
    assert eerste.title == tweede.title
    assert eerste.transcript() == tweede.transcript()


def test_verschillende_seeds_geven_verschillende_verhalen(story_cfg):
    titels = {write_blueprint(story_cfg, seed=s).title for s in range(20)}
    assert len(titels) > 10


def test_hij_slaat_over_wat_al_gemaakt_is(story_cfg):
    eerste = write_blueprint(story_cfg, seed=3)
    tweede = write_blueprint(story_cfg, taken={eerste.key}, seed=3)
    assert tweede.key != eerste.key


def test_zelfs_als_alles_al_bestaat_komt_er_iets(story_cfg):
    """De knop mag nooit niets opleveren; dat was de hele klacht."""
    bp = write_blueprint(story_cfg, seed=5)
    alles = {bp.key} | {f"{bp.key}-{n}" for n in range(2, 6)}
    nieuw = write_blueprint(story_cfg, taken=alles, seed=5)
    assert nieuw.key not in alles


def test_de_veiligheidscontrole_komt_er_doorheen(story_cfg):
    for seed in range(25):
        bp = write_blueprint(story_cfg, seed=seed)
        report = check_blueprint(story_cfg, bp)
        assert report.ok, f"{bp.title}: {report.summary()}"
        assert not report.warnings, f"{bp.title}: {report.warnings}"


def test_geen_lege_slots_of_kapotte_zinnen(story_cfg):
    for seed in range(25):
        bp = write_blueprint(story_cfg, seed=seed)
        for beat in bp.beats:
            tekst = beat.narration
            assert "{" not in tekst and "}" not in tekst, tekst
            assert tekst[0].isupper() or tekst.startswith('"'), tekst
            assert tekst.rstrip()[-1] in '.!?"', tekst
            assert "  " not in tekst, tekst


def test_geen_zin_komt_twee_keer_voor(story_cfg):
    """Herhaling binnen één aflevering hoor je meteen."""
    for seed in range(10):
        bp = write_blueprint(story_cfg, seed=seed)
        zinnen = [b.narration for b in bp.beats]
        assert len(zinnen) == len(set(zinnen))


def test_elke_traditie_en_elk_patroon_werkt(story_cfg):
    for tradition in TRADITIONS:
        for pattern in PATTERNS:
            bp = compose(story_cfg, tradition, pattern, seed=11)
            validate(bp)
            assert check_blueprint(story_cfg, bp).ok


def test_elk_patroon_gebruikt_alleen_bestaande_beeldelementen(story_cfg):
    settings = set(available_settings())
    tijden = set(available_times())
    weersoorten = set(available_weather())
    silhouetten = set(available_silhouettes())

    for tradition in TRADITIONS:
        for pattern in PATTERNS:
            bp = compose(story_cfg, tradition, pattern, seed=2)
            for scene in bp.scenes:
                assert scene.setting in settings
                assert scene.time in tijden
                assert scene.weather in weersoorten
                for onderwerp in scene.subjects:
                    assert onderwerp["draw"] in silhouetten


def test_elke_beat_hoort_bij_een_bestaande_scene(story_cfg):
    for seed in range(8):
        bp = write_blueprint(story_cfg, seed=seed)
        for beat in bp.beats:
            assert beat.mode in STORY_MODES
            assert 0 <= beat.scene < len(bp.scenes)


def test_elke_traditie_heeft_alles_wat_een_patroon_vraagt():
    """Een ontbrekende lijst zou pas bij de honderdste aflevering opvallen."""
    for tradition in TRADITIONS:
        assert tradition["key"] in SCENERY
        for veld in ("men", "women", "roles", "musicians", "homes", "beings",
                     "beasts", "places", "water", "wild", "settings"):
            assert tradition[veld], f"{tradition['key']} mist {veld}"
        for soort, sleutels in ROLE_KINDS.items():
            passend = [r for r in tradition["roles"]
                       if any(k in r for k in sleutels)]
            assert passend, f"{tradition['key']} heeft geen beroep voor {soort}"


def test_het_beroep_past_bij_het_verhaal(story_cfg):
    """Een herder die zijn netten ophaalt, is waar dit tegen beschermt."""
    water = [p for p in PATTERNS if p.get("role_kind") == "water"][0]
    for tradition in TRADITIONS:
        slots = bind_slots(__import__("random").Random(4), tradition, water)
        assert any(k in slots["role"] for k in ROLE_KINDS["water"]), slots["role"]


def test_een_vrouwelijke_hoofdpersoon_krijgt_geen_mannelijke_woorden(story_cfg):
    """'She walked down to the water himself' was een echte fout."""
    for seed in range(40):
        bp = write_blueprint(story_cfg, seed=seed)
        tekst = bp.transcript()
        if " she " not in tekst.lower():
            continue
        # Een verhaal met een vrouwelijke hoofdpersoon mag nog wel andere
        # mannen bevatten; waar het om gaat is dat 'himself' niet op haar slaat.
        for zin in tekst.splitlines():
            if re.search(r"\bShe\b.*\bhimself\b", zin) or re.search(r"\bshe\b[^.]*\bhimself\b", zin):
                pytest.fail(f"mannelijke vorm bij een vrouwelijke hoofdpersoon: {zin}")


def test_een_onbekend_slot_is_een_fout_en_geen_stille_lege_plek():
    with pytest.raises(Exception):
        fill("Hier hoort {ditbestaatniet} te staan.", {"hero": "Eirik"})


def test_de_hint_stuurt_de_keuze(story_cfg):
    tradities = {write_blueprint(story_cfg, hint="norse", seed=s).lesson_kind
                 for s in range(6)}
    assert tradities == {"norse"}


def test_de_bank_is_groot_genoeg_om_niet_op_te_raken():
    bank = available()
    assert bank["combinations"] >= 40
    assert len(bank["traditions"]) >= 6
    assert len(bank["patterns"]) >= 5


# ---------------------------------------------------------------------------
#  Helderheid
# ---------------------------------------------------------------------------


def _luminance(visual, seed=0):
    """Meet hetzelfde als de veiligheidscontrole in safety.check_frames."""
    from PIL import ImageStat

    from ytauto.render.frame import render_frame

    beeld = render_frame(visual, (320, 180), seed=seed)
    return ImageStat.Stat(beeld.convert("L").resize((32, 18))).mean[0] / 255.0


def _grootste_sprong(bp, pattern):
    """De grootste helderheidssprong tussen twee opeenvolgende beelden."""
    from ytauto.scripting.blueprint import to_scenes

    scenes = to_scenes(bp, seed=1)
    vorige, ergste = None, 0.0
    for index, scene in enumerate(scenes):
        waarde = _luminance(scene.visual, seed=index)
        if vorige is not None:
            ergste = max(ergste, abs(waarde - vorige))
        vorige = waarde
    return ergste


@pytest.mark.parametrize("pattern", PATTERNS, ids=lambda p: p["key"])
def test_het_beeld_springt_nergens_te_hard(story_cfg, pattern):
    """Een sprong van nacht naar klaarlichte dag blokkeert het renderen.

    Dat is geen theorie: 'The Road After Dark' eindigde met 0.09 -> 0.57 en
    werd afgekeurd nadat alle beelden en alle spraak al gemaakt waren.
    """
    grens = float(story_cfg.safety["max_luminance_delta"])
    for tradition in TRADITIONS[:3]:
        bp = compose(story_cfg, tradition, pattern, seed=7)
        sprong = _grootste_sprong(bp, pattern)
        assert sprong <= grens, (
            f"{bp.title}: sprong van {sprong:.2f}, grens {grens}"
        )


def test_de_gemeten_helderheid_klopt_met_de_tabel():
    """De tabel is met de hand gemeten; de renderer kan veranderen."""
    from ytauto.scripting.local_writer import TIME_BRIGHTNESS

    for tijd, verwacht in TIME_BRIGHTNESS.items():
        gemeten = _luminance({"kind": "story", "setting": "hills",
                              "time": tijd, "subjects": []}, seed=3)
        assert abs(gemeten - verwacht) < 0.06, f"{tijd}: {gemeten:.2f} vs {verwacht}"
