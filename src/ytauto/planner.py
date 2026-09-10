"""Kiest welke aflevering nu aan de beurt is.

Twee regels sturen de keuze:
  * nooit een aflevering herhalen die al bestaat;
  * lessen afwisselen, zodat er geen tien kleuren-video's achter elkaar komen.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from .config import Config
from .db import Store


class NothingToDo(Exception):
    """Geen aflevering beschikbaar: alles gemaakt, of de rem staat erop."""


@dataclass
class EpisodePlan:
    key: str
    lesson: dict[str, Any]
    theme: dict[str, Any]
    title: str
    seed: int

    @property
    def lesson_id(self) -> str:
        return self.lesson["id"]

    @property
    def theme_id(self) -> str:
        return self.theme["id"]

    @property
    def kind(self) -> str:
        return self.lesson["kind"]

    @property
    def slug(self) -> str:
        return f"{self.lesson_id}-{self.theme_id}"


def build_title(lesson: dict[str, Any], theme: dict[str, Any]) -> str:
    """'Learn Colors' + 'Balloons' -> 'Learn Colors with Balloons'.

    Thema's die een plek beschrijven ('the Farm') krijgen hun eigen
    voorzetsel uit curriculum.yaml: 'on the Farm', 'in the Jungle'.
    """
    label = theme.get("label", theme["id"].title())
    base = lesson["title"]
    if label.lower().startswith("the "):
        return f"{base} {theme.get('prep', 'in')} {label}"
    return f"{base} with {label}"


def all_candidates(cfg: Config) -> list[EpisodePlan]:
    plans: list[EpisodePlan] = []
    for lesson in cfg.lessons:
        for theme in lesson.get("themes", []):
            key = f"{lesson['id']}:{theme['id']}"
            seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
            plans.append(
                EpisodePlan(
                    key=key,
                    lesson=lesson,
                    theme=theme,
                    title=build_title(lesson, theme),
                    seed=seed,
                )
            )
    return plans


def check_rate_limit(cfg: Config, store: Store) -> None:
    """Blokkeert publiceren als het tempo boven de ingestelde rem uitkomt."""
    max_per_week = int(cfg.publish.get("max_per_week", 4))
    min_hours = float(cfg.publish.get("min_hours_between", 24))

    published_7d = store.published_since(days=7)
    if published_7d >= max_per_week:
        raise NothingToDo(
            f"Weeklimiet bereikt: {published_7d}/{max_per_week} video's in 7 dagen. "
            "Verhoog publish.max_per_week als je sneller wilt."
        )

    hours = store.hours_since_last_publish()
    if hours is not None and hours < min_hours:
        raise NothingToDo(
            f"Nog maar {hours:.1f} uur sinds de vorige upload "
            f"(minimum is {min_hours:.0f} uur)."
        )


def pick_next(cfg: Config, store: Store, *, enforce_rate_limit: bool = True) -> EpisodePlan:
    if enforce_rate_limit:
        check_rate_limit(cfg, store)

    taken = store.taken_keys()
    available = [p for p in all_candidates(cfg) if p.key not in taken]
    if not available:
        raise NothingToDo(
            "Alle afleveringen in curriculum.yaml zijn gemaakt. "
            "Voeg thema's of lessen toe om door te gaan."
        )

    # Lessen die het langst niet aan bod zijn geweest, gaan voor.
    last_seen = store.last_touched_per_lesson()
    def lesson_rank(plan: EpisodePlan) -> tuple[str, int]:
        # "" sorteert vóór elke timestamp, dus nooit-gepubliceerde lessen eerst.
        return (last_seen.get(plan.lesson_id, ""), plan.seed)

    available.sort(key=lesson_rank)
    best_lesson = available[0].lesson_id

    # Binnen die les een vaste, maar niet-alfabetische volgorde.
    same_lesson = [p for p in available if p.lesson_id == best_lesson]
    same_lesson.sort(key=lambda p: p.seed)
    return same_lesson[0]


def select_items(plan: EpisodePlan, count: int) -> list[dict[str, Any]]:
    """Kiest en ordent de items voor deze aflevering.

    Tellen moet op volgorde (1, 2, 3...). Bij de rest zorgt een vaste seed
    ervoor dat elke aflevering een andere volgorde krijgt, maar wel steeds
    dezelfde bij opnieuw renderen.
    """
    items = list(plan.lesson["items"])
    if plan.kind == "counting":
        return items[:count]

    rng = random.Random(plan.seed)
    rng.shuffle(items)
    chosen = items[:count]
    return chosen
