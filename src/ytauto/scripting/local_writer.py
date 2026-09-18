"""De gratis verteller: schrijft een volksverhaal zonder sleutel en zonder kosten.

Claude bedenkt een verhaal. Deze schrijver stelt er een samen, en dat is iets
anders. Hij kiest een traditie uit `folk_bank.py`, een vorm uit
`folk_patterns.py`, en vult die vorm met mensen, plekken en een wezen die bij
die streek horen. Dezelfde vorm levert in Noorwegen een ander verhaal op dan
in Ierland, en met een andere hoofdpersoon weer een ander.

Wat hij niet kan, is verrassen. De verhalen zijn correct, ze zijn lang genoeg,
ze zijn van jou, en ze kosten niets — maar ze volgen een patroon, en wie er
twintig achter elkaar bekijkt ziet dat. Wil je meer variatie zonder te
betalen, zet dan Ollama ernaast (zie README); wil je het allerbeste, dan is
Claude het waard.

Waarom het toch de moeite waard is om dit goed te doen: de bank in
`config/tales.yaml` bevat drie verhalen. Na drie video's stond de studio
stil. Nu niet meer.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..script_builder import estimate_speech_seconds
from .blueprint import STORY_MODES, Beat, Blueprint, StoryScene, validate
from .folk_bank import (HOURS, ROLE_KINDS, SCENERY, SEASONS, TOKENS, TRADITIONS,
                        texture)
from .folk_patterns import PATTERNS

MAX_BEATS = 170              # harde bovengrens; een video van een uur wil niemand
MAX_ATTEMPTS = 60            # pogingen om een combinatie te vinden die nieuw is


class LocalWriterError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
#  Slots
# ---------------------------------------------------------------------------


def _the(phrase: str) -> str:
    """'a turf-roofed cottage' -> 'the turf-roofed cottage'."""
    return re.sub(r"^(a|an)\s+", "the ", phrase)


def _bare(phrase: str) -> str:
    """'a grey wolf' -> 'grey wolf'."""
    return re.sub(r"^(a|an|the)\s+", "", phrase)


def _titlecase(phrase: str) -> str:
    """Titelvorm met het lidwoord klein: 'the lough' -> 'the Lough'."""
    woorden = phrase.split()
    return " ".join(
        woord if index == 0 and woord.lower() in ("a", "an", "the")
        else woord[:1].upper() + woord[1:]
        for index, woord in enumerate(woorden)
    )


def _article(phrase: str) -> str:
    return ("an " if phrase[:1].lower() in "aeiou" else "a ") + phrase


def bind_slots(rng: random.Random, tradition: dict, pattern: dict) -> dict[str, str]:
    """Kiest de mensen, de plek en het wezen voor dit ene verhaal."""
    vrouw = rng.random() < 0.5
    naam = rng.choice(tradition["women"] if vrouw else tradition["men"])
    rollen = list(tradition[pattern["role_from"]]) if pattern.get("role_from") \
        else list(tradition["roles"])
    soort = pattern.get("role_kind")
    if soort:
        passend = [r for r in rollen if any(k in r for k in ROLE_KINDS[soort])]
        rollen = passend or list(tradition["roles"])
    rol = rng.choice(rollen)

    toegestaan = pattern.get("being_kinds")
    wezens = [w for w in tradition["beings"]
              if not toegestaan or w["draw"] in toegestaan] or tradition["beings"]
    wezen = rng.choice(wezens)

    huis = rng.choice(tradition["homes"])
    beest = rng.choice(tradition["beasts"])
    water = rng.choice(tradition["water"])

    return {
        "hero": naam, "Hero": naam,
        "he": "she" if vrouw else "he", "He": "She" if vrouw else "He",
        "him": "her" if vrouw else "him",
        "his": "her" if vrouw else "his", "His": "Her" if vrouw else "His",
        "himself": "herself" if vrouw else "himself",
        "role": rol, "Role": rol.title(), "a_role": _article(rol),
        "place": rng.choice(tradition["places"]),
        "water": water, "water_title": _titlecase(water),
        "wild": rng.choice(tradition["wild"]),
        "home": huis, "the_home": _the(huis),
        "being": wezen["name"], "the_being": wezen["short"],
        "the_Being": _titlecase(wezen["short"]),
        "beast": beest, "the_beast": _the(beest),
        "Beast_the": "The " + _bare(beest),
        "Beast_Title": _bare(beest).title(),
        "token": rng.choice(TOKENS),
        "season": rng.choice(SEASONS),
        "hour": rng.choice(HOURS),
        "origin": tradition["origin"],
        "adjective": tradition["adjective"],
        "origin_sentence": f"Versions of it are told across {tradition['origin']}.",
        "_draw_hero": "woman" if vrouw else "man",
        "_draw_being": wezen["draw"],
        "_being_scale": wezen.get("scale", 0.12),
        "_beast_draw": _beast_draw(beest),
    }


# Welke dieren als silhouet bestaan. Alles wat er niet in staat wordt een
# hert: dat is neutraal genoeg om nooit verkeerd te staan.
BEAST_DRAWS = {
    "wolf": "wolf", "reindeer": "deer", "raven": "raven", "fox": "fox",
    "heron": "raven", "dog": "wolf", "boar": "bear", "stag": "deer",
    "bear": "bear", "stork": "raven", "crane": "raven", "eagle": "raven",
    "goat": "deer", "lynx": "fox", "grouse": "raven", "elk": "deer",
    "kite": "raven", "pony": "horse", "badger": "fox",
}


def _beast_draw(beest: str) -> str:
    for woord, silhouet in BEAST_DRAWS.items():
        if woord in beest:
            return silhouet
    return "deer"


def fill(template: str, slots: dict[str, str]) -> str:
    """Vult de slots in en zet de zin op een hoofdletter.

    Een zin die met een slot begint ({water}, {the_being}) kwam er anders uit
    als 'the sound at that time of year goes grey'. Een onbekend slot is een
    fout in het patroon en wordt daarom niet stilletjes overgeslagen.
    """
    def vervang(match: re.Match) -> str:
        sleutel = match.group(1)
        if sleutel not in slots:
            raise LocalWriterError(f"onbekend slot {{{sleutel}}} in: {template}")
        return str(slots[sleutel])

    zin = re.sub(r"\{([A-Za-z_]+)\}", vervang, template)
    return zin[:1].upper() + zin[1:]


# ---------------------------------------------------------------------------
#  Scenes
# ---------------------------------------------------------------------------


# Hoe licht een beeld wordt, per tijdstip. Gemeten aan de renderer zelf, op
# dezelfde manier als de veiligheidscontrole meet: het landschap maakt maar
# een paar honderdsten verschil, het tijdstip bepaalt bijna alles.
TIME_BRIGHTNESS = {
    "underworld": 0.08, "night": 0.13, "moonlit": 0.16, "storm": 0.17,
    "dusk": 0.29, "overcast": 0.34, "dawn": 0.37, "winter": 0.45, "day": 0.56,
}

# Hoeveel een beeld hoogstens mag verspringen ten opzichte van het vorige.
# De veiligheidscontrole staat 0.45 toe; hier wordt ruimer gerekend, omdat
# silhouetten en weer een beeld nog een paar honderdsten donkerder maken dan
# de tabel hierboven zegt.
MAX_BRIGHTNESS_STEP = 0.30


def smooth_times(scenes: list[StoryScene], volgorde: list[int],
                 max_step: float = MAX_BRIGHTNESS_STEP) -> None:
    """Haalt te grote helderheidssprongen uit de opeenvolging van beelden.

    Een verhaal dat 's nachts eindigt en dan ineens op klaarlichte dag in het
    dorp staat, springt van 0.08 naar 0.56. Dat blokkeert de
    veiligheidscontrole — terecht, want zulke sprongen zijn een risico voor
    kijkers met epilepsie. Het beeld schuift daarom op naar het dichtstbijzijnde
    tijdstip dat wél kan: 'first light' wordt dan dawn in plaats van day, wat
    het verhaal meestal ook beter past.
    """
    vorige: float | None = None
    gezien: set[int] = set()

    for index in volgorde:
        scene = scenes[index]
        helderheid = TIME_BRIGHTNESS.get(scene.time, 0.3)

        if (vorige is not None and index not in gezien
                and abs(helderheid - vorige) > max_step):
            haalbaar = [t for t, waarde in TIME_BRIGHTNESS.items()
                        if abs(waarde - vorige) <= max_step]
            scene.time = min(haalbaar,
                             key=lambda t: abs(TIME_BRIGHTNESS[t] - helderheid))
            helderheid = TIME_BRIGHTNESS[scene.time]

        gezien.add(index)
        vorige = helderheid


def scene_order(pattern: dict, aantal_scenes: int) -> list[int]:
    """In welke volgorde de beelden op het scherm komen.

    De titelkaart hoort bij de eerste scene en de bronvermelding bij de
    laatste; daartussen staat de arc.
    """
    volgorde = [0] + [entry["scene"] for entry in pattern["arc"]] + [aantal_scenes - 1]
    return [index for teller, index in enumerate(volgorde)
            if teller == 0 or volgorde[teller - 1] != index]



def _pick(rng: random.Random, waarde) -> Any:
    return rng.choice(waarde) if isinstance(waarde, list) else waarde


def build_scenes(rng: random.Random, tradition: dict, pattern: dict,
                 slots: dict) -> list[StoryScene]:
    landschap = SCENERY[tradition["key"]]
    scenes: list[StoryScene] = []

    for spec in pattern["scenes"]:
        subjects = []
        for draw, x, scale, depth in spec["subjects"]:
            if draw == "hero":
                naam = slots["_draw_hero"]
            elif draw == "being":
                naam = slots["_draw_being"]
            elif draw == "beast":
                naam = slots["_beast_draw"]
            elif draw == "home":
                naam = "cottage"
            else:
                naam = draw
            hoogte = slots["_being_scale"] if scale == "being" else float(scale)
            subjects.append({"draw": naam, "x": float(x),
                             "scale": round(float(hoogte), 3), "depth": float(depth)})

        caption = spec.get("caption")
        scenes.append(StoryScene(
            setting=landschap[spec["role"]],
            time=_pick(rng, spec["time"]),
            weather=_pick(rng, spec.get("weather", "none")),
            caption=fill(caption, slots) if caption else None,
            subjects=subjects,
        ))
    return scenes


# ---------------------------------------------------------------------------
#  Beats
# ---------------------------------------------------------------------------


@dataclass
class Step:
    """Eén stap uit het patroon, met de zinnen die er al uit gekozen zijn.

    De zinnen van een stap staan in de volgorde waarin ze geschreven zijn, en
    die volgorde blijft staan. Wat per aflevering verschilt is *welke* zinnen
    gekozen worden, niet in welke volgorde ze langskomen — anders begint het
    verhaal bij de derde zin en dat is te horen.
    """

    mode: str
    scene: int
    grow: bool
    lines: list[str]              # eigen zinnen, op verhaalvolgorde
    order: list[int]              # welke daarvan als eerste aan de beurt is
    pool: list[str]               # gedeelde zinnen om mee bij te vullen
    limit: int                    # hoeveel zinnen deze stap hoogstens krijgt
    taken: set[int] = field(default_factory=set)
    extra: list[str] = field(default_factory=list)

    @property
    def chosen(self) -> list[str]:
        return [self.lines[i] for i in sorted(self.taken)] + self.extra

    def room(self, used: set[str]) -> bool:
        if len(self.taken) + len(self.extra) >= self.limit:
            return False
        return bool(self._next_own() or self._next_pool(used))

    def _next_own(self) -> int | None:
        for index in self.order:
            if index not in self.taken:
                return index
        return None

    def _next_pool(self, used: set[str]) -> str | None:
        for regel in self.pool:
            if regel not in used and regel not in self.extra:
                return regel
        return None

    def add(self, used: set[str]) -> str | None:
        """Neemt er één zin bij: eerst de eigen zinnen, dan de gedeelde."""
        index = self._next_own()
        if index is not None:
            self.taken.add(index)
            used.add(self.lines[index])
            return self.lines[index]
        regel = self._next_pool(used)
        if regel is not None:
            self.extra.append(regel)
            used.add(regel)
        return regel


def _beat_seconds(mode: str, tekst: str) -> float:
    vorm = STORY_MODES.get(mode, STORY_MODES["tell"])
    return max(vorm["min"], estimate_speech_seconds(tekst)) + vorm["pause"]


def build_steps(rng: random.Random, pattern: dict, slots: dict) -> list[Step]:
    """Zet elke stap van het patroon om in zinnen."""
    stappen: list[Step] = []
    gebruikt: set[str] = set()

    for entry in pattern["arc"]:
        regels = [fill(t, slots) for t in entry["lines"]]
        volgorde = list(range(len(regels)))
        rng.shuffle(volgorde)                 # welke zinnen, niet in welke volgorde
        pool = [fill(t, slots) for t in texture(entry.get("pool", ""))]
        rng.shuffle(pool)

        aantal = int(entry.get("count", 1))
        stap = Step(
            mode=entry["mode"], scene=entry["scene"], grow=bool(entry.get("grow")),
            lines=regels, order=volgorde, pool=pool,
            # Een stap mag hooguit ruim verdubbelen. Zonder die rem groeit de
            # laatste rekbare stap door tot het slot tien zinnen lang is.
            limit=aantal + (6 if entry.get("grow") else 0),
        )
        for _ in range(aantal):
            stap.add(gebruikt)
        stappen.append(stap)

    return stappen


def grow_to_length(stappen: list[Step], target_seconds: float,
                   vaste_seconden: float) -> None:
    """Vult de rekbare stappen aan tot het verhaal lang genoeg is.

    Er wordt steeds bijgevuld bij de stap die tot nu toe het minst gekregen
    heeft. Zo groeit een verhaal gelijkmatig in plaats van dat één stuk in het
    midden uitdijt.
    """
    gebruikt = {regel for stap in stappen for regel in stap.chosen}
    totaal = vaste_seconden + sum(
        _beat_seconds(stap.mode, regel) for stap in stappen for regel in stap.chosen
    )
    beats = sum(len(stap.chosen) for stap in stappen)

    while totaal < target_seconds and beats < MAX_BEATS:
        kandidaten = [s for s in stappen if s.grow and s.room(gebruikt)]
        if not kandidaten:
            return
        stap = min(kandidaten, key=lambda s: (len(s.chosen), stappen.index(s)))
        regel = stap.add(gebruikt)
        if regel is None:                                       # pragma: no cover
            return
        totaal += _beat_seconds(stap.mode, regel)
        beats += 1


# ---------------------------------------------------------------------------
#  Het hele verhaal
# ---------------------------------------------------------------------------


def _sentences(tekst: str) -> list[str]:
    return [zin.strip() for zin in re.split(r"(?<=[.!?])\s+", tekst.strip()) if zin.strip()]


def compose(cfg: Config, tradition: dict, pattern: dict, seed: int) -> Blueprint:
    """Bouwt één compleet verhaal uit een traditie en een patroon."""
    rng = random.Random(seed)
    slots = bind_slots(rng, tradition, pattern)
    scenes = build_scenes(rng, tradition, pattern, slots)
    grens = float(cfg.safety.get("max_luminance_delta", 0.45))
    smooth_times(scenes, scene_order(pattern, len(scenes)),
                 min(MAX_BRIGHTNESS_STEP, grens * 0.66))

    titel = fill(rng.choice(pattern["titles"]), slots)
    ondertitel = tradition["label"]
    laatste = len(scenes) - 1

    kop = f"{titel}. {ondertitel}."
    bron = _sentences(tradition["source"])
    vast = _beat_seconds("title", kop) + sum(_beat_seconds("source", z) for z in bron)

    stappen = build_steps(rng, pattern, slots)
    minuten = float(cfg.video.get("target_duration_minutes", 11))
    grow_to_length(stappen, minuten * 60, vast)

    beats = [Beat(mode="title", narration=kop, scene=0,
                  title=titel, subtitle=ondertitel)]
    for stap in stappen:
        for regel in stap.chosen:
            beats.append(Beat(mode=stap.mode, narration=regel, scene=stap.scene))
    for zin in bron:
        beats.append(Beat(mode="source", narration=zin, scene=laatste))

    beschrijving = " ".join(fill(rng.choice(pattern["description"]), slots).split())
    labels = ["folklore", "myths and legends", "folk tale retold", "storytelling",
              f"{tradition['adjective'].lower()} folklore",
              f"{tradition['origin'].lower()} folk tale"]
    labels += pattern["tags"]

    blueprint = Blueprint(
        idea=f"{pattern['idea']} ({tradition['origin']})",
        title=titel[:100],
        description=beschrijving,
        tags=list(dict.fromkeys(labels))[:12],
        lesson_kind=tradition["key"],          # bij verhalen: de traditie
        backdrop_top="#0B1026",
        backdrop_bottom="#2A2B52",
        items=[],
        beats=beats,
        source="local",
        key=make_key(titel),
        format="folklore",
        scenes=scenes,
    )
    return validate(blueprint)


def make_key(titel: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", titel.lower()).strip("-")[:60]
    return slug or "tale"


# ---------------------------------------------------------------------------
#  Kiezen wat er nu aan de beurt is
# ---------------------------------------------------------------------------


def _matches_hint(hint: str, tradition: dict, pattern: dict) -> bool:
    woorden = hint.lower().split()
    doelen = " ".join([
        tradition["key"], tradition["origin"], tradition["adjective"],
        pattern["key"], pattern["idea"], " ".join(pattern["tags"]),
    ]).lower()
    return any(woord in doelen for woord in woorden if len(woord) > 3)


def write_blueprint(cfg: Config, taken: set[str] | None = None,
                    hint: str | None = None, seed: int | None = None) -> Blueprint:
    """Schrijft een verhaal dat nog niet eerder gemaakt is.

    `taken` zijn de sleutels die al in de boekhouding staan. Er wordt net zo
    lang een andere combinatie geprobeerd tot er een nieuwe titel uitkomt.
    """
    taken = taken or set()
    basis = random.Random(seed if seed is not None else random.randrange(1 << 30))

    tradities = list(TRADITIONS)
    patronen = list(PATTERNS)
    if hint:
        gefilterd = [(t, p) for t in tradities for p in patronen
                     if _matches_hint(hint, t, p)]
    else:
        gefilterd = []

    laatste: Blueprint | None = None
    for poging in range(MAX_ATTEMPTS):
        if gefilterd:
            tradition, pattern = basis.choice(gefilterd)
        else:
            tradition = basis.choice(tradities)
            pattern = basis.choice(patronen)

        blueprint = compose(cfg, tradition, pattern, basis.randrange(1 << 30))
        if blueprint.key not in taken:
            return blueprint
        laatste = blueprint

    # Alles wat we probeerden bestond al. Dan maar met een nummer erachter:
    # beter een variant van een bestaand verhaal dan een knop die niets doet.
    if laatste is None:                                         # pragma: no cover
        raise LocalWriterError("geen enkel patroon kon een verhaal opleveren")
    nummer = 2
    while f"{laatste.key}-{nummer}" in taken:
        nummer += 1
    laatste.key = f"{laatste.key}-{nummer}"
    return laatste


def available() -> dict:
    """Wat de gratis verteller in huis heeft. Voor 'ytauto check'."""
    return {
        "traditions": [t["key"] for t in TRADITIONS],
        "patterns": [p["key"] for p in PATTERNS],
        "combinations": len(TRADITIONS) * len(PATTERNS),
    }
