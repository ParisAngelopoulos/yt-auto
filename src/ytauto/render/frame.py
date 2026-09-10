"""Kiest de juiste tekenaar voor een beeld.

De pipeline weet niet welke niche er draait; hij vraagt alleen om een beeld
bij een spec. Welke renderer dat wordt, staat in de spec zelf.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from .scene import render_scene
from .story_scene import render_story_scene


def render_frame(visual: dict[str, Any], size: tuple[int, int], seed: int = 0) -> Image.Image:
    if visual.get("kind") == "story":
        return render_story_scene(visual, size, seed)
    return render_scene(visual, size, seed)
