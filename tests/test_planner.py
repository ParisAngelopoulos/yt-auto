"""Dubbel publiceren en te snel publiceren zijn de twee dure fouten."""

import pytest

from ytauto.config import load_config
from ytauto.planner import NothingToDo, check_rate_limit, pick_next
from ytauto.db import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


def test_kiest_steeds_een_andere_aflevering(store):
    cfg = load_config()
    gekozen = []
    for _ in range(8):
        plan = pick_next(cfg, store, enforce_rate_limit=False)
        store.mark_planned(plan.key, plan.lesson_id, plan.theme_id, plan.title)
        gekozen.append(plan.key)
    assert len(gekozen) == len(set(gekozen))


def test_weeklimiet_blokkeert(store):
    cfg = load_config()
    cfg.raw["publish"]["max_per_week"] = 2
    for i in range(2):
        store.mark_planned(f"k{i}", "colors", "t", "T")
        store.mark_uploaded(f"k{i}", f"vid{i}")
    with pytest.raises(NothingToDo, match="Weeklimiet"):
        check_rate_limit(cfg, store)


def test_minimale_tussentijd_blokkeert(store):
    cfg = load_config()
    cfg.raw["publish"]["max_per_week"] = 99
    cfg.raw["publish"]["min_hours_between"] = 24
    store.mark_planned("k", "colors", "t", "T")
    store.mark_uploaded("k", "vid")
    with pytest.raises(NothingToDo, match="uur"):
        check_rate_limit(cfg, store)


def test_mislukte_afleveringen_mogen_opnieuw(store):
    store.mark_planned("k", "colors", "t", "T")
    store.mark_failed("k", "ffmpeg kapot")
    assert "k" not in store.taken_keys()


def test_seed_is_stabiel_over_processen_heen():
    """hash() van een string verschilt per proces; dan zou dezelfde
    aflevering twee keer renderen een ander beeld opleveren."""
    import subprocess
    import sys

    code = ("import sys; sys.path.insert(0, 'src'); "
            "from ytauto.pipeline import episode_seed; "
            "print(episode_seed('colors:balloons'))")
    uitkomsten = {
        subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, env={"PYTHONHASHSEED": str(n), "PATH": "/usr/bin:/bin"}).stdout.strip()
        for n in (0, 1, 42)
    }
    assert len(uitkomsten) == 1
