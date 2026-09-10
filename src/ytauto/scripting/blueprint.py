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
from ..render.silhouettes import available_silhouettes
from ..render.story_scene import available_settings, available_times, available_weather
from ..script_builder import Scene, estimate_speech_seconds

# Twee vormen delen dezelfde machinerie. Wat verschilt is hoe een aflevering
# is opgebouwd: een les gaat over items, een verhaal beweegt door plekken.
FORMATS = ("kids", "folklore")

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

# Beats van een volksverhaal. Anders dan bij de les zit hier geen oefening
# in; het ritme komt van de stiltes tussen de zinnen.
STORY_MODES = {
    "title":   {"pause": 1.2, "min": 5.0},   # titelkaart
    "open":    {"pause": 0.8, "min": 4.0},   # de plek en de tijd
    "tell":    {"pause": 0.5, "min": 3.0},   # het verhaal zelf
    "turn":    {"pause": 0.9, "min": 3.5},   # een wending; het beeld verandert
    "speech":  {"pause": 0.6, "min": 3.0},   # iemand spreekt
    "close":   {"pause": 1.0, "min": 4.0},   # de afloop
    "moral":   {"pause": 1.2, "min": 4.5},   # wat het verhaal wil zeggen
    "source":  {"pause": 0.6, "min": 4.0},   # waar het vandaan komt
}


@dataclass
class Item:
    """Wat er in een leervideo geleerd wordt."""

    word: str
    draw: str
    label: str
    color: str | None = None
    count: int | None = None


@dataclass
class StoryScene:
    """Een plek in het verhaal: waar het speelt en wie er staat.

    Meerdere beats delen dezelfde scene. Dat scheelt de scriptschrijver werk
    en zorgt dat het beeld rustig blijft: pas bij een echte plaats- of
    tijdsprong verandert er iets.
    """

    setting: str
    time: str
    weather: str | None = None
    caption: str | None = None
    subjects: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Beat:
    mode: str
    narration: str
    item: int | None = None          # leervideo: welk item
    title: str | None = None
    subtitle: str | None = None
    scene: int | None = None         # verhaal: op welke plek


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
    format: str = "kids"            # kids | folklore
    scenes: list[StoryScene] = field(default_factory=list)

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
            items=[Item(**i) for i in data.get("items", [])],
            beats=[Beat(**b) for b in data["beats"]],
            source=data.get("source", "claude"),
            key=data.get("key", ""),
            format=data.get("format", "kids"),
            scenes=[StoryScene(**sc) for sc in data.get("scenes", [])],
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
        tabel = STORY_MODES if self.is_story else MODES
        standaard = tabel["tell"] if self.is_story else tabel["reveal"]
        total = 0.0
        for beat in self.beats:
            mode = tabel.get(beat.mode, standaard)
            total += max(mode["min"], estimate_speech_seconds(beat.narration)) + mode["pause"]
        return total

    @property
    def is_story(self) -> bool:
        return self.format == "folklore"

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
    if bp.format not in FORMATS:
        raise BlueprintError(f"format {bp.format!r} bestaat niet")
    if not bp.beats:
        raise BlueprintError("blueprint heeft geen beats")

    for i, beat in enumerate(bp.beats):
        if not beat.narration.strip():
            raise BlueprintError(f"beat {i} heeft geen tekst")

    return _validate_story(bp) if bp.is_story else _validate_kids(bp)


def _validate_kids(bp: Blueprint) -> Blueprint:
    shapes = set(available_shapes())

    if bp.lesson_kind not in LESSON_KINDS:
        raise BlueprintError(f"lesson_kind {bp.lesson_kind!r} bestaat niet")
    if not bp.items:
        raise BlueprintError("blueprint heeft geen items")

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

    for naam, waarde in (("backdrop_top", bp.backdrop_top),
                         ("backdrop_bottom", bp.backdrop_bottom)):
        if not _is_hex(waarde):
            raise BlueprintError(f"{naam} is geen geldige kleur: {waarde!r}")

    return bp


def _validate_story(bp: Blueprint) -> Blueprint:
    settings = set(available_settings())
    tijden = set(available_times())
    weersoorten = set(available_weather())
    silhouetten = set(available_silhouettes())

    if not bp.scenes:
        raise BlueprintError("verhaal heeft geen scenes")

    for i, scene in enumerate(bp.scenes):
        if scene.setting not in settings:
            raise BlueprintError(f"scene {i} speelt in {scene.setting!r}, dat bestaat niet")
        if scene.time not in tijden:
            raise BlueprintError(f"scene {i} heeft tijd {scene.time!r}, die bestaat niet")
        if scene.weather and scene.weather not in weersoorten:
            raise BlueprintError(f"scene {i} heeft weer {scene.weather!r}, dat bestaat niet")
        for j, onderwerp in enumerate(scene.subjects):
            naam = onderwerp.get("draw")
            if naam not in silhouetten:
                raise BlueprintError(
                    f"scene {i}, figuur {j}: {naam!r} bestaat niet als silhouet"
                )

    for i, beat in enumerate(bp.beats):
        if beat.mode not in STORY_MODES:
            raise BlueprintError(f"beat {i} heeft onbekende mode {beat.mode!r}")
        if beat.scene is None:
            raise BlueprintError(f"beat {i} verwijst niet naar een scene")
        if not (0 <= beat.scene < len(bp.scenes)):
            raise BlueprintError(f"beat {i} verwijst naar scene {beat.scene}, die bestaat niet")

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
    if bp.is_story:
        return _story_scenes(bp, seed)
    return _kids_scenes(bp, seed)


def _story_scenes(bp: Blueprint, seed: int = 0) -> list[Scene]:
    """Elke beat krijgt het beeld van zijn scene.

    Opeenvolgende beats in dezelfde scene leveren hetzelfde beeld op. Dat is
    de bedoeling: bij een verhaal hoort het beeld te blijven staan terwijl er
    verteld wordt, en pas te veranderen als het verhaal van plek verandert.
    """
    scenes: list[Scene] = []
    for index, beat in enumerate(bp.beats):
        plek = bp.scenes[beat.scene or 0]
        visual: dict[str, Any] = {
            "kind": "story",
            "setting": plek.setting,
            "time": plek.time,
            "subjects": list(plek.subjects),
        }
        if plek.weather and plek.weather != "none":
            visual["weather"] = plek.weather

        if beat.mode == "title":
            visual["title"] = {"text": beat.title or bp.title}
            if beat.subtitle:
                visual["subtitle"] = {"text": beat.subtitle}
            visual["vignette"] = 0.68
        elif plek.caption and _first_beat_of_scene(bp, index):
            # Een plaatsnaam hoort één keer in beeld, bij aankomst.
            visual["caption"] = plek.caption

        mode = STORY_MODES[beat.mode]
        scenes.append(Scene(
            id=f"{index:03d}-{beat.mode}",
            narration=beat.narration,
            visual=visual,
            pause_after=mode["pause"],
            min_duration=mode["min"],
        ))
    return scenes


def _first_beat_of_scene(bp: Blueprint, index: int) -> bool:
    if index == 0:
        return True
    return bp.beats[index - 1].scene != bp.beats[index].scene


def _kids_scenes(bp: Blueprint, seed: int = 0) -> list[Scene]:
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
