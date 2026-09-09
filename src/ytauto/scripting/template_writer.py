"""Schrijft een aflevering uit curriculum.yaml, zonder API.

Dit is het vangnet: geen sleutel, geen internet, geen kosten. Het levert
dezelfde Blueprint op als Claude, dus de rest van de pipeline merkt geen
verschil. Handig om de knoppen te testen en om door te draaien als een
API-aanroep een keer mislukt.
"""

from __future__ import annotations

import random
from typing import Any

from ..config import Config
from ..planner import EpisodePlan, select_items
from ..script_builder import (
    INTRO_GREETINGS,
    INTRO_INVITES,
    OUTRO_GOODBYE,
    OUTRO_LINES,
    PRAISE,
    article,
    backdrop_for,
    estimate_speech_seconds,
    pluralize,
)
from .blueprint import MODES, Beat, Blueprint, Item, validate

MAX_FILLER_ROUNDS = 6


class TemplateWriter:
    def __init__(self, cfg: Config, plan: EpisodePlan) -> None:
        self.cfg = cfg
        self.plan = plan
        self.rng = random.Random(plan.seed)
        self.top, self.bottom = backdrop_for(plan.theme_id)

    # -- items --

    def _item_count(self) -> int:
        available = len(self.plan.lesson["items"])
        return available if self.plan.kind == "counting" else min(available, 8)

    def _build_items(self) -> tuple[list[Item], list[dict[str, Any]]]:
        raw = select_items(self.plan, self._item_count())
        items: list[Item] = []
        for i, src in enumerate(raw):
            items.append(Item(
                word=src["word"],
                draw=self._draw_name(src),
                label=str(src["value"]) if self.plan.kind == "counting" else src["word"].upper(),
                color=self._color(src, i),
                count=src.get("value") if self.plan.kind == "counting" else None,
            ))
        return items, raw

    def _draw_name(self, src: dict[str, Any]) -> str:
        return src.get("draw") or self.plan.theme.get("draw", "circle")

    def _color(self, src: dict[str, Any], index: int) -> str | None:
        if "hex" in src:
            return src["hex"]
        if self.plan.kind == "shapes":
            wheel = ["#E8483F", "#F2913D", "#F4CE47", "#5BB85C",
                     "#4A90D9", "#9B6DC4", "#F08BB4", "#4FC3C0"]
            return self.plan.theme.get("accent") or wheel[index % len(wheel)]
        return None

    def _noun(self, src: dict[str, Any]) -> str:
        if self.plan.kind in ("naming", "shapes"):
            return src["word"]
        return self.plan.theme.get("draw", "thing")

    # -- beats --

    def _intro(self, raw: list[dict[str, Any]]) -> list[Beat]:
        subject = pluralize(self.plan.lesson.get("teach_word", "thing"))
        preview = {
            "colors": f"Today we are going to learn {subject}!",
            "counting": "Today we are going to count all the way to ten!",
            "shapes": f"Today we are going to learn {subject}!",
            "naming": f"Today we are going to meet some {subject}!",
        }[self.plan.kind]
        return [
            Beat("intro_title",
                 f"{self.rng.choice(INTRO_GREETINGS)} {self.rng.choice(INTRO_INVITES)}",
                 title=self.plan.lesson["title"].upper(),
                 subtitle=self.plan.theme.get("label", "")),
            Beat("intro_preview", preview),
        ]

    def _teach_round(self, raw: list[dict[str, Any]]) -> list[Beat]:
        beats: list[Beat] = []
        for i, src in enumerate(raw):
            word, noun = src["word"], self._noun(src)
            if self.plan.kind == "colors":
                reveal = self.rng.choice([
                    f"Look! {article(word).capitalize()} {word} {noun}.",
                    f"Here comes {article(word)} {word} {noun}!",
                    f"Wow, look at this {word} {noun}!",
                ])
                teach = f"This color is {word}. Can you say {word}?"
                echo = f"{word.capitalize()}! Nice and clear."
            elif self.plan.kind == "counting":
                n = src["value"]
                plural = pluralize(noun) if n > 1 else noun
                reveal = self.rng.choice([
                    f"Let's count. {word.capitalize()}!",
                    f"Now we have {word} {plural}.",
                    f"Here is number {word}!",
                ])
                teach = f"{word.capitalize()}. Can you say {word}?"
                echo = f"{word.capitalize()}! That is {word} {plural}."
            elif self.plan.kind == "shapes":
                reveal = self.rng.choice([
                    f"Look! This is {article(word)} {word}.",
                    f"Here is {article(word)} {word}!",
                ])
                teach = f"{article(word).capitalize()} {word}. Can you say {word}?"
                echo = f"{word.capitalize()}! You found the {word}."
            else:
                sound = src.get("sound")
                reveal = self.rng.choice([
                    f"Look, it's {article(word)} {word}!",
                    f"Say hello to the {word}!",
                ])
                teach = (f"This is {article(word)} {word}. The {word} says {sound}"
                         if sound else f"This is {article(word)} {word}. Can you say {word}?")
                echo = f"{word.capitalize()}! Say it with me. {word.capitalize()}."

            beats += [Beat("reveal", reveal, item=i),
                      Beat("teach", teach, item=i),
                      Beat("echo", echo, item=i)]
        return beats

    def _practice_round(self, raw: list[dict[str, Any]]) -> list[Beat]:
        beats = [Beat("card", "Let's practice together!", title="PRACTICE TIME")]
        for i, src in enumerate(raw):
            word, noun = src["word"], self._noun(src)
            if self.plan.kind == "colors":
                q = self.rng.choice([f"What color is this {noun}?", "Do you know this color?"])
                a = f"Yes! It is {word}. {self.rng.choice(PRAISE)}"
            elif self.plan.kind == "counting":
                n = src["value"]
                plural = pluralize(noun) if n > 1 else noun
                q = self.rng.choice([f"How many {pluralize(noun)} do you see?",
                                     f"Can you count the {pluralize(noun)}?"])
                a = f"{word.capitalize()}! There are {word} {plural}. {self.rng.choice(PRAISE)}"
            elif self.plan.kind == "shapes":
                q = self.rng.choice(["What shape is this?", "Do you know this shape?"])
                a = f"Yes! It is {article(word)} {word}. {self.rng.choice(PRAISE)}"
            else:
                q = self.rng.choice(["What is this?", "Can you say its name?"])
                a = f"It is {article(word)} {word}! {self.rng.choice(PRAISE)}"
            beats += [Beat("question", q, item=i), Beat("answer", a, item=i)]
        return beats

    def _find_round(self, raw: list[dict[str, Any]]) -> list[Beat]:
        beats = [Beat("card", "Now let's play a finding game!", title="FIND IT!")]
        for i, src in enumerate(raw):
            word = src["word"]
            q = self.rng.choice([
                f"Can you find the {word} one?" if self.plan.kind == "colors"
                else f"Can you find the {word}?",
                f"Where is the {word}?",
                f"Point to the {word}!",
            ])
            a = f"There it is! The {word}. {self.rng.choice(PRAISE)}"
            beats += [Beat("find_question", q, item=i), Beat("find_answer", a, item=i)]
        return beats

    def _review_round(self, raw: list[dict[str, Any]]) -> list[Beat]:
        beats = [Beat("card", "Let's say them all one more time!", title="REVIEW")]
        for i, src in enumerate(raw):
            beats.append(Beat("review", f"{src['word'].capitalize()}!", item=i))
        return beats

    def _outro(self) -> list[Beat]:
        return [
            Beat("outro", self.rng.choice(OUTRO_LINES)),
            Beat("outro_title", self.rng.choice(OUTRO_GOODBYE),
                 title="BYE BYE!", subtitle=self.cfg.channel["name"]),
        ]

    # -- publiek --

    def build(self) -> Blueprint:
        items, raw = self._build_items()
        target = float(self.cfg.video["target_duration_minutes"]) * 60.0

        intro, outro = self._intro(raw), self._outro()
        review = self._review_round(raw)

        def seconds(beats: list[Beat]) -> float:
            total = 0.0
            for b in beats:
                mode = MODES[b.mode]
                total += max(mode["min"], estimate_speech_seconds(b.narration)) + mode["pause"]
            return total

        fixed = seconds(intro) + seconds(outro) + seconds(review)
        body = self._teach_round(raw)
        fillers = (self._practice_round, self._find_round)
        for i in range(MAX_FILLER_ROUNDS):
            if fixed + seconds(body) >= target:
                break
            body += fillers[i % len(fillers)](raw)

        lesson_title = self.plan.lesson["title"]
        return validate(Blueprint(
            idea=f"{lesson_title} — {self.plan.theme.get('label', self.plan.theme_id)}",
            title=f"{self.plan.title} | Learning Video for Toddlers",
            description=(
                f"{self.plan.title}. A calm, friendly learning video for toddlers "
                f"and preschoolers. Your little one learns to recognise and name "
                f"each one, with plenty of time to join in out loud."
            ),
            tags=self._tags(),
            lesson_kind=self.plan.kind,
            backdrop_top=self.top,
            backdrop_bottom=self.bottom,
            items=items,
            beats=intro + body + review + outro,
            source="template",
            key=self.plan.key,
        ))

    def _tags(self) -> list[str]:
        base = ["toddler learning", "preschool", "learning for kids",
                "educational video for toddlers", "kids learning"]
        return base + [self.plan.lesson["title"].lower(),
                       self.plan.theme.get("label", "").lower()]


def write_blueprint(cfg: Config, plan: EpisodePlan) -> Blueprint:
    return TemplateWriter(cfg, plan).build()
