"""De afdaling: de schaal, de camera en de inhoud van journeys.yaml.

Deze vorm bestaat omdat een reeks stilstaande beelden als diashow leest en
weggescrold wordt. Wat hier bewaakt wordt is dus vooral: beweegt hij, klopt
de diepte, en staat elke mijlpaal in beeld op het moment dat hij genoemd
wordt.
"""

import pytest

from ytauto.config import load_config
from ytauto.pipeline import load_journeys, shorts_config
from ytauto.render.descent import DepthScale, build_column
from ytauto.render.sea import available_sea, creature_color, render_creature
from ytauto.video.descent_video import Line, _rounded, camera_path


# ---------------------------------------------------------------------------
#  De schaal
# ---------------------------------------------------------------------------


def test_de_schaal_begint_bovenaan_en_eindigt_onderaan():
    s = DepthScale(total_m=10935, height_px=24000)
    assert s.y(0) == pytest.approx(0)
    assert s.y(10935) == pytest.approx(24000)


def test_meters_en_pixels_zijn_omkeerbaar():
    s = DepthScale(total_m=10935, height_px=24000)
    for meters in (5, 50, 200, 1000, 4000, 10000):
        assert s.depth(s.y(meters)) == pytest.approx(meters, rel=1e-6)


def test_dieper_is_altijd_lager_in_beeld():
    s = DepthScale(total_m=10935, height_px=24000)
    rijen = [s.y(m) for m in (1, 10, 100, 1000, 10000)]
    assert rijen == sorted(rijen)


def test_de_eerste_meters_krijgen_ruimte():
    """Lineair zou de duiker en de walvis op dezelfde pixel zetten."""
    s = DepthScale(total_m=10935, height_px=24000)
    ondiep = s.y(100) - s.y(10)
    diep = s.y(10000) - s.y(9910)          # hetzelfde verschil in meters
    assert ondiep > diep * 20


def test_buiten_bereik_wordt_vastgehouden():
    s = DepthScale(total_m=1000, height_px=1000)
    assert s.y(-50) == pytest.approx(0)
    assert s.y(99999) == pytest.approx(1000)
    assert s.depth(-10) == pytest.approx(0)
    assert s.depth(99999) == pytest.approx(1000)


# ---------------------------------------------------------------------------
#  De camera
# ---------------------------------------------------------------------------


def _column():
    return build_column(240, {"key": "t", "total": 10935, "height_px": 2400,
                              "top_px": 150, "floor_px": 300,
                              "milestones": [{"depth": 100, "label": "A"},
                                             {"depth": 5000, "label": "B"}]},
                        seed=1)


def test_de_camera_gaat_alleen_maar_omlaag():
    kolom = _column()
    lijnen = [Line("hook", 0.3, 2.0, None),
              Line("a", 2.5, 3.0, kolom.row(100)),
              Line("b", 6.0, 3.0, kolom.row(5000))]
    pad = camera_path(lijnen, kolom, 400, 11.0, 30)
    assert all(b >= a - 1e-6 for a, b in zip(pad, pad[1:])), "de camera gaat terug omhoog"


def test_de_camera_blijft_binnen_het_beeld():
    kolom = _column()
    lijnen = [Line("a", 0.3, 2.0, kolom.row(100)), Line("b", 3.0, 2.0, kolom.row(5000))]
    pad = camera_path(lijnen, kolom, 400, 6.0, 30)
    assert pad.min() >= 0
    assert pad.max() <= kolom.image.height - 400


def test_de_mijlpaal_staat_in_beeld_als_hij_genoemd_wordt():
    """Anders schiet het wezen voorbij precies terwijl erover verteld wordt."""
    kolom = _column()
    hoogte = 400
    lijnen = [Line("hook", 0.3, 1.5, None),
              Line("a", 2.0, 3.0, kolom.row(100)),
              Line("b", 6.0, 3.0, kolom.row(5000))]
    pad = camera_path(lijnen, kolom, hoogte, 11.0, 30)
    for lijn in lijnen:
        if lijn.row is None:
            continue
        boven = pad[int(lijn.middle * 30)]
        assert boven <= lijn.row <= boven + hoogte, f"{lijn.text} staat buiten beeld"


def test_hij_beweegt_de_hele_tijd():
    """Stilstand is precies wat deze vorm moest oplossen."""
    kolom = _column()
    lijnen = [Line("a", 0.3, 2.0, kolom.row(100)), Line("b", 4.0, 2.0, kolom.row(5000))]
    pad = camera_path(lijnen, kolom, 400, 7.0, 30)
    stilstand = sum(1 for a, b in zip(pad, pad[1:]) if abs(b - a) < 0.05)
    assert stilstand < len(pad) * 0.35, "de camera staat te vaak stil"


# ---------------------------------------------------------------------------
#  De teller
# ---------------------------------------------------------------------------


def test_de_teller_rondt_af_maar_niet_op_het_diepste_punt():
    assert _rounded(42.4) == "42"
    assert _rounded(1234, 10935) == "1.250"
    assert _rounded(10935, 10935) == "10.935"
    assert _rounded(10930, 10935) == "10.935"


# ---------------------------------------------------------------------------
#  De inhoud
# ---------------------------------------------------------------------------


def test_er_is_minstens_een_reis():
    assert load_journeys()


@pytest.mark.parametrize("reis", load_journeys(), ids=lambda r: r["key"])
def test_de_reis_klopt(reis):
    for veld in ("key", "title", "hook", "total", "milestones"):
        assert reis.get(veld), f"{reis.get('key')} mist {veld}"

    dieptes = [float(m["depth"]) for m in reis["milestones"]]
    assert dieptes == sorted(dieptes), "de mijlpalen staan niet op volgorde"
    assert max(dieptes) <= float(reis["total"])
    assert len(set(dieptes)) == len(dieptes), "twee mijlpalen op dezelfde diepte"

    tekenbaar = set(available_sea())
    for steen in reis["milestones"]:
        if steen.get("draw"):
            assert steen["draw"] in tekenbaar, f"{steen['draw']} bestaat niet"
        assert steen.get("say"), f"mijlpaal op {steen['depth']} heeft geen tekst"


def test_de_reis_past_in_een_short():
    for reis in load_journeys():
        woorden = sum(len(m["say"].split()) for m in reis["milestones"])
        woorden += len(reis["hook"].split()) + len(reis.get("closing", "").split())
        seconden = woorden / 2.4 + len(reis["milestones"]) * 0.28
        assert 30 < seconden < 170, f"{reis['key']}: ongeveer {seconden:.0f}s"


# ---------------------------------------------------------------------------
#  Het beeld
# ---------------------------------------------------------------------------


def test_elk_zeewezen_is_te_tekenen():
    for naam in available_sea():
        beeld = render_creature(naam, 80, (150, 172, 188))
        assert beeld.width > 4 and beeld.height == 80, naam


def test_ondiep_is_donker_en_diep_is_licht():
    """Bovenin kijk je tegen het licht in; beneden is jouw lamp het enige licht."""
    ondiep = creature_color(20)
    diep = creature_color(3000)
    assert sum(ondiep) < sum(diep)


def test_de_kolom_is_hoger_dan_het_beeld():
    kolom = _column()
    assert kolom.image.height > 1000
    assert kolom.row(0) == kolom.top_px
    assert kolom.depth_at(kolom.row(500)) == pytest.approx(500, rel=1e-6)


def test_de_afdaling_is_staand():
    breedte, hoogte = shorts_config(load_config()).resolution
    assert hoogte > breedte
