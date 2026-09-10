"""De blueprint is het contract; die moet fouten vroeg vangen."""

import pytest

from ytauto.config import load_config
from ytauto.planner import all_candidates
from ytauto.render.scene import render_scene
from ytauto.scripting.blueprint import (
    Beat,
    Blueprint,
    BlueprintError,
    Item,
    to_scenes,
    validate,
)
from ytauto.scripting.template_writer import write_blueprint


def _minimal(**overrides) -> Blueprint:
    data = dict(
        idea="test", title="Test", description="d", tags=["t"],
        lesson_kind="naming", backdrop_top="#DCEEFB", backdrop_bottom="#F6E4C8",
        items=[Item(word="cow", draw="cow", label="COW")],
        beats=[Beat("reveal", "Look, a cow!", item=0)],
    )
    data.update(overrides)
    return Blueprint(**data)


def test_geldige_blueprint_komt_erdoor():
    assert validate(_minimal()) is not None


def test_onbekend_figuur_wordt_geweigerd():
    bp = _minimal(items=[Item(word="dragon", draw="dragon", label="DRAGON")])
    with pytest.raises(BlueprintError, match="bestaat niet"):
        validate(bp)


def test_onbekende_mode_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="mode"):
        validate(_minimal(beats=[Beat("dansen", "hoi")]))


def test_beat_die_naar_een_onbestaand_item_wijst_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="item"):
        validate(_minimal(beats=[Beat("reveal", "hoi", item=7)]))


def test_ongeldige_kleur_wordt_geweigerd():
    bp = _minimal(items=[Item(word="cow", draw="cow", label="COW", color="rood")])
    with pytest.raises(BlueprintError, match="kleur"):
        validate(bp)


def test_lege_tekst_wordt_geweigerd():
    with pytest.raises(BlueprintError, match="geen tekst"):
        validate(_minimal(beats=[Beat("reveal", "   ", item=0)]))


def test_blueprint_overleeft_opslaan_en_laden(tmp_path):
    bp = _minimal()
    path = tmp_path / "bp.json"
    bp.save(path)
    assert Blueprint.load(path).title == bp.title


def test_slug_is_veilig_als_mapnaam():
    assert _minimal().slug == "episode"
    bp = _minimal()
    bp.key = "colors:balloons"
    assert bp.slug == "colors-balloons"


@pytest.mark.parametrize("key", ["colors:balloons", "numbers:ducks", "animals_farm:farm"])
def test_elke_scene_uit_het_sjabloon_is_te_renderen(key):
    """Als to_scenes iets oplevert wat de renderer niet aankan, valt de hele
    productie halverwege om. Dit dekt alle vier de layouts af."""
    cfg = load_config()
    plan = next(p for p in all_candidates(cfg) if p.key == key)
    bp = write_blueprint(cfg, plan)
    scenes = to_scenes(bp, seed=plan.seed)
    assert scenes

    gezien = set()
    for scene in scenes:
        gezien.add(scene.visual["layout"])
    for layout in gezien:
        eerste = next(s for s in scenes if s.visual["layout"] == layout)
        beeld = render_scene(eerste.visual, (480, 270), seed=1)
        assert beeld.size == (480, 270)


def test_sjabloon_haalt_de_doellengte(kids_cfg):
    cfg = kids_cfg
    doel = float(cfg.video["target_duration_minutes"])
    for plan in all_candidates(cfg):
        bp = write_blueprint(cfg, plan)
        minuten = bp.estimated_duration / 60
        assert doel * 0.8 <= minuten <= 15, f"{plan.key}: {minuten:.1f} min"
