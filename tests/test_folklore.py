"""De volksverhalen-vorm.

Twee dingen moeten kloppen: het schema laat Claude alleen dingen kiezen die
de renderer ook kan tekenen, en elke scene uit de verhalenbank komt er als
beeld uit. Dat laatste is de test die het duurst is om te missen — een
verzonnen setting valt anders pas op bij scene zestig.
"""

import pytest

from ytauto.render.landscape import SETTINGS, SKIES
from ytauto.render.silhouettes import available_silhouettes, render_silhouette
from ytauto.render.story_scene import (available_settings, available_times,
                                       available_weather, render_story_scene)
from ytauto.safety import check_blueprint, check_text
from ytauto.scripting.blueprint import (STORY_MODES, Beat, Blueprint, BlueprintError,
                                        StoryScene, to_scenes, validate)
from ytauto.scripting.claude_writer import output_schema
from ytauto.scripting.tale_writer import NoTalesLeft, load_tales, to_blueprint
from ytauto.scripting.tale_writer import write_blueprint as tale_write


def maak_verhaal(**overrides) -> Blueprint:
    data = dict(
        idea="test", title="The Tale", description="Een verhaal.", tags=["folklore"],
        lesson_kind="norse", backdrop_top="#0B1026", backdrop_bottom="#2A2B52",
        items=[],
        scenes=[StoryScene(setting="forest", time="night", weather="mist",
                           caption="The wood", subjects=[
                               {"draw": "traveller", "x": 0.4, "scale": 0.16, "depth": 0.9}])],
        beats=[Beat("title", "The Tale.", scene=0, title="THE TALE"),
               Beat("tell", "He walked into the wood.", scene=0),
               Beat("source", "Collected in the north.", scene=0)],
        format="folklore",
    )
    data.update(overrides)
    return Blueprint(**data)


# ---------------------------------------------------------------------------
#  Validatie
# ---------------------------------------------------------------------------


def test_geldig_verhaal_komt_erdoor():
    assert validate(maak_verhaal()) is not None


def test_verzonnen_setting_wordt_geweigerd():
    bp = maak_verhaal(scenes=[StoryScene(setting="mordor", time="night")])
    with pytest.raises(BlueprintError, match="bestaat niet"):
        validate(bp)


def test_verzonnen_tijd_wordt_geweigerd():
    bp = maak_verhaal(scenes=[StoryScene(setting="forest", time="teatime")])
    with pytest.raises(BlueprintError, match="tijd"):
        validate(bp)


def test_verzonnen_silhouet_wordt_geweigerd():
    bp = maak_verhaal(scenes=[StoryScene(setting="forest", time="night",
                                         subjects=[{"draw": "unicorn"}])])
    with pytest.raises(BlueprintError, match="silhouet"):
        validate(bp)


def test_beat_zonder_scene_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="scene"):
        validate(maak_verhaal(beats=[Beat("tell", "Hoi")]))


def test_beat_naar_onbestaande_scene_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="scene 7"):
        validate(maak_verhaal(beats=[Beat("tell", "Hoi", scene=7)]))


def test_lesmode_mag_niet_in_een_verhaal():
    with pytest.raises(BlueprintError, match="mode"):
        validate(maak_verhaal(beats=[Beat("reveal", "Hoi", scene=0)]))


def test_verhaal_zonder_scenes_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="geen scenes"):
        validate(maak_verhaal(scenes=[]))


# ---------------------------------------------------------------------------
#  Beeld
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("naam", available_silhouettes())
def test_elk_silhouet_tekent(naam):
    tegel = render_silhouette(naam, 80, (20, 24, 32))
    assert tegel.height == 80 and tegel.width > 0
    assert tegel.getchannel("A").getextrema()[1] > 200


def test_onbekend_silhouet_geeft_een_duidelijke_fout():
    with pytest.raises(KeyError, match="Beschikbaar"):
        render_silhouette("eenhoorn", 40, (0, 0, 0))


@pytest.mark.parametrize("setting", sorted(SETTINGS))
def test_elke_setting_rendert(setting):
    beeld = render_story_scene({"setting": setting, "time": "night"}, (320, 180), seed=3)
    assert beeld.size == (320, 180) and beeld.mode == "RGB"


@pytest.mark.parametrize("tijd", sorted(SKIES))
def test_elke_tijd_rendert(tijd):
    beeld = render_story_scene({"setting": "hills", "time": tijd}, (320, 180), seed=3)
    assert beeld.size == (320, 180)


@pytest.mark.parametrize("weer", ["mist", "rain", "snow"])
def test_elk_weertype_rendert(weer):
    spec = {"setting": "moor", "time": "overcast", "weather": weer}
    assert render_story_scene(spec, (320, 180), seed=3).size == (320, 180)


def test_onzin_valt_terug_op_iets_dat_werkt():
    """Een beeld dat niet te maken is, mag geen zwart vlak worden."""
    beeld = render_story_scene({"setting": "atlantis", "time": "never"}, (240, 135))
    assert beeld.size == (240, 135)
    assert beeld.getextrema()[0][1] > 5          # niet volledig zwart


def test_titelkaart_krijgt_tekst():
    kaal = render_story_scene({"setting": "hills", "time": "night"}, (480, 270), seed=1)
    met = render_story_scene({"setting": "hills", "time": "night",
                              "title": {"text": "THE TALE"}}, (480, 270), seed=1)
    assert kaal.tobytes() != met.tobytes()


# ---------------------------------------------------------------------------
#  De verhalenbank
# ---------------------------------------------------------------------------


def test_de_bank_bevat_verhalen():
    verhalen = load_tales()
    assert len(verhalen) >= 3
    assert all({"key", "title", "tradition", "scenes", "beats"} <= set(t) for t in verhalen)


def test_elk_verhaal_uit_de_bank_is_geldig(story_cfg):
    for tale in load_tales():
        bp = to_blueprint(tale, story_cfg)
        assert bp.is_story and bp.beats and bp.scenes


def test_elke_scene_uit_de_bank_is_te_renderen(story_cfg):
    """Als dit breekt, klapt een productie halverwege om."""
    for tale in load_tales():
        bp = to_blueprint(tale, story_cfg)
        gezien = set()
        for scene in to_scenes(bp, seed=1):
            sleutel = (scene.visual["setting"], scene.visual["time"])
            if sleutel in gezien:
                continue
            gezien.add(sleutel)
            assert render_story_scene(scene.visual, (240, 135), seed=1).size == (240, 135)


def test_elk_verhaal_uit_de_bank_is_veilig(story_cfg):
    for tale in load_tales():
        rapport = check_blueprint(story_cfg, to_blueprint(tale, story_cfg))
        assert rapport.ok, f"{tale['key']}: {rapport.summary()}"


def test_geen_verhaal_wordt_twee_keer_gekozen(story_cfg):
    gekozen = set()
    for _ in range(len(load_tales())):
        bp = tale_write(story_cfg, taken=gekozen)
        assert bp.key not in gekozen
        gekozen.add(bp.key)
    with pytest.raises(NoTalesLeft, match="zijn gemaakt"):
        tale_write(story_cfg, taken=gekozen)


def test_als_de_bank_op_is_schrijft_de_verteller_verder(story_cfg):
    """Drie verhalen was vroeger het einde. Nu gaat het gewoon door."""
    from ytauto.pipeline import _write_with

    class NepStore:
        def taken_keys(self):
            return {tale["key"] for tale in load_tales()}

        def all_episodes(self):
            return []

    bp = _write_with(story_cfg, "local", NepStore(), hint=None)
    assert bp.source == "local"
    assert bp.key not in NepStore().taken_keys()
    assert check_blueprint(story_cfg, bp).ok


def test_beats_in_dezelfde_scene_delen_hun_beeld(story_cfg):
    """Het beeld hoort te blijven staan terwijl er verteld wordt."""
    bp = to_blueprint(load_tales()[0], story_cfg)
    scenes = to_scenes(bp, seed=1)
    paren = [(a, b) for a, b in zip(bp.beats, bp.beats[1:])]
    for index, (eerste, tweede) in enumerate(paren):
        if eerste.scene == tweede.scene and "title" not in scenes[index].id:
            assert scenes[index].visual["setting"] == scenes[index + 1].visual["setting"]


# ---------------------------------------------------------------------------
#  Schema en veiligheid
# ---------------------------------------------------------------------------


def test_schema_staat_alleen_bestaande_plekken_toe():
    scene = output_schema("folklore")["properties"]["scenes"]["items"]["properties"]
    assert set(scene["setting"]["enum"]) == set(available_settings())
    assert set(scene["time"]["enum"]) == set(available_times())
    assert set(scene["weather"]["enum"]) == set(available_weather())
    assert set(scene["subjects"]["items"]["properties"]["draw"]["enum"]) == \
        set(available_silhouettes())


def test_schema_kent_dezelfde_beats_als_de_renderer():
    beats = output_schema("folklore")["properties"]["beats"]["items"]["properties"]
    assert set(beats["mode"]["enum"]) == set(STORY_MODES)


def test_een_wolf_mag_in_een_sage():
    """De kinderregels horen hier niet te gelden."""
    assert check_text("The wolf came out of the trees and the child was afraid.",
                      "folklore").ok


def test_expliciet_geweld_wordt_wel_geblokkeerd():
    assert not check_text("He was disembowelled on the stones.", "folklore").ok


def test_onterecht_als_kindervideo_aanmerken_blokkeert(story_cfg):
    story_cfg.raw["publish"]["made_for_kids"] = True
    rapport = check_blueprint(story_cfg, maak_verhaal())
    assert not rapport.ok
    assert any("kindercontent" in i for i in rapport.issues)


def test_ontbrekende_bronvermelding_geeft_een_waarschuwing(story_cfg):
    bp = maak_verhaal(beats=[Beat("title", "The Tale.", scene=0),
                             Beat("tell", "He walked.", scene=0)])
    rapport = check_blueprint(story_cfg, bp)
    assert any("bronvermelding" in w for w in rapport.warnings)
