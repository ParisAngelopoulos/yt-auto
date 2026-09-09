"""Het curriculum en de tekenbibliotheek moeten op elkaar aansluiten."""

import pytest

from ytauto.config import load_config
from ytauto.planner import all_candidates, build_title
from ytauto.render.objects import available_shapes


def test_config_laadt():
    cfg = load_config()
    assert cfg.channel["name"]
    assert cfg.resolution == (1920, 1080)
    assert cfg.lessons


def test_elk_figuur_in_het_curriculum_bestaat():
    """Een typefout in curriculum.yaml mag niet pas tijdens het renderen opvallen."""
    cfg = load_config()
    shapes = set(available_shapes())
    for lesson in cfg.lessons:
        for item in lesson["items"]:
            if "draw" in item:
                assert item["draw"] in shapes, f"{lesson['id']}: {item['draw']}"
        for theme in lesson["themes"]:
            if "draw" in theme:
                assert theme["draw"] in shapes, f"{lesson['id']}/{theme['id']}: {theme['draw']}"


def test_afleveringen_hebben_unieke_sleutels():
    cfg = load_config()
    keys = [p.key for p in all_candidates(cfg)]
    assert len(keys) == len(set(keys))
    assert len(keys) >= 20


def test_titel_krijgt_het_juiste_voorzetsel():
    lesson = {"title": "Learn Animals"}
    assert build_title(lesson, {"id": "z", "label": "the Zoo", "prep": "at"}) == \
        "Learn Animals at the Zoo"
    assert build_title(lesson, {"id": "b", "label": "Balloons"}) == \
        "Learn Animals with Balloons"
    # Zonder prep in de config valt het terug op 'in', niet op de losse label.
    assert build_title(lesson, {"id": "f", "label": "the Farm"}) == "Learn Animals in the Farm"
