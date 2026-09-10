"""Haalt een volksverhaal uit config/tales.yaml.

Dit is het vangnet voor de volksverhalen-vorm: geen sleutel, geen kosten.
De verhalen staan al in de blueprint-vorm, dus er valt hier weinig te
bouwen — alleen kiezen welk verhaal aan de beurt is en het omzetten.

De echte variatie komt van Claude. Deze bank is er om de machine te kunnen
draaien en om te laten zien hoe een aflevering eruit hoort te zien.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..config import ROOT, Config
from .blueprint import Beat, Blueprint, StoryScene, validate

TALES_PATH = ROOT / "config" / "tales.yaml"


class NoTalesLeft(RuntimeError):
    """Alle verhalen uit de bank zijn gebruikt."""


def load_tales(path: Path | None = None) -> list[dict[str, Any]]:
    pad = path or TALES_PATH
    if not pad.exists():
        return []
    return yaml.safe_load(pad.read_text(encoding="utf-8")).get("tales", [])


def to_blueprint(tale: dict[str, Any], cfg: Config) -> Blueprint:
    return validate(Blueprint(
        idea=tale.get("idea", ""),
        title=tale["title"],
        description=" ".join(tale.get("description", "").split()),
        tags=list(tale.get("tags", [])),
        lesson_kind=tale.get("tradition", ""),      # bij verhalen: de traditie
        backdrop_top="#0B1026",
        backdrop_bottom="#2A2B52",
        items=[],
        beats=[Beat(mode=b["mode"], narration=b["narration"], scene=b.get("scene"),
                    title=b.get("title"), subtitle=b.get("subtitle"))
               for b in tale["beats"]],
        source="template",
        key=tale["key"],
        format="folklore",
        scenes=[StoryScene(setting=s["setting"], time=s["time"],
                           weather=s.get("weather"), caption=s.get("caption"),
                           subjects=list(s.get("subjects", [])))
                for s in tale["scenes"]],
    ))


def write_blueprint(cfg: Config, taken: set[str] | None = None) -> Blueprint:
    """Kiest het eerste verhaal dat nog niet gemaakt is."""
    taken = taken or set()
    verhalen = load_tales()
    if not verhalen:
        raise NoTalesLeft("config/tales.yaml bevat geen verhalen.")

    for tale in verhalen:
        if tale["key"] not in taken:
            return to_blueprint(tale, cfg)

    raise NoTalesLeft(
        f"Alle {len(verhalen)} verhalen uit config/tales.yaml zijn gemaakt. "
        "Voeg er een toe, of zet een ANTHROPIC_API_KEY in .env zodat Claude "
        "zelf verhalen kan schrijven."
    )
