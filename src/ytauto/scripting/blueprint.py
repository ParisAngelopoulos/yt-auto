"""Het contract tussen de scriptschrijver en de beeldbouwer.

Claude levert een blueprint: het idee, de items en alle gesproken zinnen.
De code zet die blueprint om in scenes met geldige beeld-specs. Zo houdt
Claude alle vrijheid over de taal, terwijl het beeld nooit kan verwijzen
naar een figuur dat niet bestaat.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..render.objects import available_shapes
from ..script_builder import Scene, estimate_speech_seconds

LESSON_KINDS = ("colors", "counting", "shapes", "naming")

# Wat elke beat op het scherm doet en hoeveel stilte erna komt.
MODES = {
    "intro_title":   {"layout": "title",  "pause": 0.0, "min": 4.0},
    "intro_preview": {"layout": "row",    "pause": 0.4, "min": 4.0},
    "card":          {"layout": "title",  "pause": 0.0, "min": 3.0},
    "reveal":        {"layout": "hero",   "pause": 0.0, "min": 3.2},
    "teach":         {"layout": "hero",   "pause": 1.8, "min": 3.4},
    "echo":          {"layout": "hero",   "pause": 0.6, "min": 3.2, "confetti": True},
    "question":      {"layout": "hero",   "pause": 2.6, "min": 3.0, "question": True},
    "answer":        {"layout": "hero",   "pause": 0.4, "min": 3.4, "confetti": True, "label": True},
    "find_question": {"layout": "row",    "pause": 2.8, "min": 3.0, "question": True},
    "find_answer":   {"layout": "row",    "pause": 0.4, "min": 3.2, "confetti": True, "highlight": True},
    "review":        {"layout": "hero",   "pause": 1.2, "min": 2.6, "label": True},
    "outro":         {"layout": "row",    "pause": 0.3, "min": 4.2, "confetti": True},
    "outro_title":   {"layout": "title",  "pause": 0.0, "min": 4.0, "confetti": True},
}


@dataclass
class Item:
    word: str
    draw: str
    label: str
    color: str | None = None
    count: int | None = None


@dataclass
class Beat:
    mode: str
    narration: str
    item: int | None = None
    title: str | None = None
    subtitle: str | None = None


@dataclass
class Blueprint:
    """Alles wat nodig is om een aflevering te maken."""

    idea: str
    title: str
    description: str
    tags: list[str]
    lesson_kind: str
    backdrop_top: str
    backdrop_bottom: str
    items: list[Item]
    beats: list[Beat]
    source: str = "claude"          # claude | template
    key: str = ""                   # unieke sleutel voor de boekhouding

    # -- opslag --

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Blueprint":
        return cls(
            idea=data["idea"],
            title=data["title"],
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
            lesson_kind=data["lesson_kind"],
            backdrop_top=data.get("backdrop_top") or data.get("backdrop", {}).get("top", "#DCEEFB"),
            backdrop_bottom=data.get("backdrop_bottom") or data.get("backdrop", {}).get("bottom", "#F6E4C8"),
            items=[Item(**i) for i in data["items"]],
            beats=[Beat(**b) for b in data["beats"]],
            source=data.get("source", "claude"),
            key=data.get("key", ""),
        )

    @classmethod
    def load(cls, path: Path) -> "Blueprint":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    # -- afgeleide gegevens --

    @property
    def slug(self) -> str:
        """Mapnaam op schijf. De key zelf kan tekens bevatten die niet mogen."""
        import re

        return re.sub(r"[^a-z0-9]+", "-", self.key.lower()).strip("-") or "episode"

    @property
    def word_count(self) -> int:
        return sum(len(b.narration.split()) for b in self.beats)

    @property
    def estimated_duration(self) -> float:
        total = 0.0
        for beat in self.beats:
            mode = MODES.get(beat.mode, MODES["reveal"])
            total += max(mode["min"], estimate_speech_seconds(beat.narration)) + mode["pause"]
        return total

    def transcript(self) -> str:
        """Leesbaar script, zoals het in de bedieningspagina getoond wordt."""
        lines = []
        for beat in self.beats:
            who = beat.mode.replace("_", " ")
            lines.append(f"[{who}] {beat.narration}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Validatie
# ---------------------------------------------------------------------------


class BlueprintError(ValueError):
    """De blueprint klopt niet en kan niet gerenderd worden."""


def validate(bp: Blueprint) -> Blueprint:
    """Controleert alles waar de renderer op vertrouwt.

    Liever hier een duidelijke fout dan halverwege het renderen van scene 87.
    """
    shapes = set(available_shapes())

    if bp.lesson_kind not in LESSON_KINDS:
        raise BlueprintError(f"lesson_kind {bp.lesson_kind!r} bestaat niet")
    if not bp.items:
        raise BlueprintError("blueprint heeft geen items")
    if not bp.beats:
        raise BlueprintError("blueprint heeft geen beats")

    for i, item in enumerate(bp.items):
        if item.draw not in shapes:
            raise BlueprintError(
                f"item {i} ({item.word!r}) tekent {item.draw!r}, dat figuur bestaat niet"
            )
        if item.color and not _is_hex(item.color):
            raise BlueprintError(f"item {i} heeft ongeldige kleur {item.color!r}")

    for i, beat in enumerate(bp.beats):
        if beat.mode not in MODES:
            raise BlueprintError(f"beat {i} heeft onbekende mode {beat.mode!r}")
        if beat.item is not None and not (0 <= beat.item < len(bp.items)):
            raise BlueprintError(f"beat {i} verwijst naar item {beat.item}, dat bestaat niet")
        if not beat.narration.strip():
            raise BlueprintError(f"beat {i} heeft geen tekst")

    for name, value in (("backdrop_top", bp.backdrop_top), ("backdrop_bottom", bp.backdrop_bottom)):
        if not _is_hex(value):
            raise BlueprintError(f"{name} is geen geldige kleur: {value!r}")

    return bp


def _is_hex(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("#")
        and len(value) in (4, 7)
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )


# ---------------------------------------------------------------------------
#  Blueprint -> scenes
# ---------------------------------------------------------------------------


def to_scenes(bp: Blueprint, seed: int = 0) -> list[Scene]:
    """Zet de blueprint om in renderbare scenes."""
    rng = random.Random(seed)
    bg = {"style": "gradient", "top": bp.backdrop_top, "bottom": bp.backdrop_bottom}
    scenes: list[Scene] = []

    for index, beat in enumerate(bp.beats):
        mode = MODES[beat.mode]
        item = bp.items[beat.item] if beat.item is not None else None
        visual: dict[str, Any] = {"bg": dict(bg), "layout": mode["layout"]}

        if mode["layout"] == "title":
            visual["title"] = {"text": beat.title or bp.title.upper()}
            if beat.subtitle:
                visual["subtitle"] = {"text": beat.subtitle}
            visual["objects"] = [
                {"draw": bp.items[i % len(bp.items)].draw,
                 "color": bp.items[i % len(bp.items)].color,
                 "x": 0.16 + 0.68 * (i / 3), "y": 0.80, "scale": 0.40, "rot": -8 + 8 * i}
                for i in range(min(4, len(bp.items)))
            ]

        elif mode["layout"] == "hero" and item is not None:
            if bp.lesson_kind == "counting" and item.count:
                visual["layout"] = "count"
                visual["count"] = item.count
                visual["objects"] = [
                    {"draw": item.draw, "color": item.color} for _ in range(item.count)
                ]
            else:
                visual["objects"] = [{"draw": item.draw, "color": item.color, "scale": 1.0}]
            if mode.get("label") or beat.mode in ("reveal", "teach", "echo"):
                visual["title"] = {"text": beat.title or item.label}

        elif mode["layout"] == "row":
            if beat.mode in ("find_question", "find_answer") and item is not None:
                # Twee afleiders naast het juiste antwoord, op een vaste plek
                # zodat vraag en antwoord hetzelfde beeld tonen.
                others = [x for x in bp.items if x.word != item.word]
                local = random.Random(seed + (beat.item or 0))
                local.shuffle(others)
                row = [item] + others[:2]
                order = list(range(len(row)))
                local.shuffle(order)
                visual["objects"] = [
                    {"draw": row[o].draw, "color": row[o].color, "scale": 0.80} for o in order
                ]
                if mode.get("highlight"):
                    visual["highlight"] = order.index(0)
            else:
                visual["objects"] = [
                    {"draw": it.draw, "color": it.color, "scale": 0.66}
                    for it in bp.items[:5]
                ]

        else:
            visual["objects"] = [{"draw": bp.items[0].draw, "color": bp.items[0].color}]

        if mode.get("question"):
            visual["question"] = True
        if mode.get("confetti"):
            visual["confetti"] = True

        scenes.append(Scene(
            id=f"{index:03d}-{beat.mode}",
            narration=beat.narration,
            visual=visual,
            pause_after=mode["pause"],
            min_duration=mode["min"],
        ))

    return scenes
