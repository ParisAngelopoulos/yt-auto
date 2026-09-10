import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ytauto.config import load_config      # noqa: E402


@pytest.fixture
def kids_cfg():
    """Een kanaalconfig voor leervideo's, los van wat channel.yaml nu zegt.

    Zonder deze fixture zouden de tests omvallen zodra iemand de niche van
    het kanaal omzet, en dat zegt niets over de code.
    """
    cfg = load_config()
    cfg.raw["channel"]["format"] = "kids"
    cfg.raw["channel"]["name"] = "Test Learning"
    cfg.raw["channel"]["audience"] = "toddlers and preschoolers, ages 2-5"
    cfg.raw["video"]["target_duration_minutes"] = 8
    cfg.raw["publish"]["made_for_kids"] = True
    return cfg


@pytest.fixture
def story_cfg():
    """Een kanaalconfig voor volksverhalen."""
    cfg = load_config()
    cfg.raw["channel"]["format"] = "folklore"
    cfg.raw["channel"]["name"] = "Test Folklore"
    cfg.raw["channel"]["audience"] = "adults who like folklore and myth"
    cfg.raw["video"]["target_duration_minutes"] = 11
    cfg.raw["publish"]["made_for_kids"] = False
    return cfg
