"""Beeld: elk figuur moet tekenbaar zijn en scenes de juiste maat hebben."""

import pytest

from ytauto.render.objects import available_shapes, render_object
from ytauto.render.palette import contrast_ratio, readable_ink, shade, to_rgb
from ytauto.render.scene import render_scene


@pytest.mark.parametrize("naam", available_shapes())
def test_elk_figuur_tekent_zonder_fout(naam):
    tegel = render_object(naam, 96)
    assert tegel.size == (96, 96)
    assert tegel.mode == "RGBA"
    # Een figuur dat nergens dekkend is, is in de video onzichtbaar.
    assert tegel.getchannel("A").getextrema()[1] > 200


def test_onbekend_figuur_geeft_een_duidelijke_fout():
    with pytest.raises(KeyError, match="Beschikbaar"):
        render_object("eenhoorn", 64)


def test_kleur_wordt_toegepast():
    rood = render_object("circle", 64, "#FF0000")
    blauw = render_object("circle", 64, "#0000FF")
    assert rood.tobytes() != blauw.tobytes()


@pytest.mark.parametrize("layout", ["title", "hero", "row", "count"])
def test_elke_layout_rendert(layout):
    spec = {
        "bg": {"top": "#DCEEFB", "bottom": "#F6E4C8"},
        "layout": layout,
        "objects": [{"draw": "duck", "color": None} for _ in range(3)],
        "title": {"text": "TEST"},
        "count": 3,
    }
    beeld = render_scene(spec, (640, 360), seed=2)
    assert beeld.size == (640, 360)
    assert beeld.mode == "RGB"


def test_tekstkleur_houdt_genoeg_contrast():
    for achtergrond in ("#FFFFFF", "#F4CE47", "#2A3F6B", "#000000"):
        inkt = readable_ink(achtergrond)
        assert contrast_ratio(achtergrond, inkt) >= 4.5


def test_shade_blijft_binnen_bereik():
    for waarde in (-1.0, -0.3, 0.0, 0.5, 1.0):
        for kanaal in shade("#4A90D9", waarde):
            assert 0 <= kanaal <= 255
