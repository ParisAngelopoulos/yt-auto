"""Gedeelde bouwstenen voor scripts: de Scene, het spreektempo en de taal.

Zowel de scriptschrijver van Claude als de sjabloonschrijver leveren een
Blueprint op; die wordt hier omgezet naar Scenes. Dit bestand bevat alleen
wat beide nodig hebben.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

# ----------------------------------------------------------------------------
#  Meervoud
# ----------------------------------------------------------------------------

IRREGULAR_PLURALS = {
    "fish": "fish",
    "sheep": "sheep",
    "goose": "geese",
    "mouse": "mice",
    "grapes": "grapes",
    "bus": "buses",
}


def pluralize(word: str) -> str:
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if word.endswith("y") and word[-2:-1] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


# ----------------------------------------------------------------------------
#  Spreektempo
# ----------------------------------------------------------------------------

# Rustig voorleestempo voor peuters, gemeten op ElevenLabs met speed 0.92.
# Wordt alleen gebruikt om de lengte vooraf te schatten; de echte duur komt
# later uit het gegenereerde audiobestand.
WORDS_PER_SECOND = 2.3
SPEECH_PADDING = 0.7          # adem voor en na de zin


def estimate_speech_seconds(text: str) -> float:
    words = len(text.split())
    if not words:
        return 0.0
    return words / WORDS_PER_SECOND + SPEECH_PADDING


# ----------------------------------------------------------------------------
#  Scene
# ----------------------------------------------------------------------------


@dataclass
class Scene:
    """Eén beeld met bijbehorende gesproken tekst."""

    id: str
    narration: str
    visual: dict[str, Any]
    pause_after: float = 0.0     # stilte na de zin: denktijd voor het kind
    min_duration: float = 3.0
    audio_path: str | None = None
    duration: float = 0.0        # ingevuld na het genereren van de stem

    @property
    def estimated_seconds(self) -> float:
        """Verwachte schermtijd zolang de echte audio er nog niet is."""
        speech = estimate_speech_seconds(self.narration)
        return max(self.min_duration, speech) + self.pause_after


# ----------------------------------------------------------------------------
#  Achtergrondpaletten per thema
# ----------------------------------------------------------------------------

THEME_BACKDROPS = {
    "farm":    ("#BFE3F5", "#B7E4A8"),
    "barn":    ("#FBDCC0", "#E9C39B"),
    "meadow":  ("#CFEAFB", "#A9DE94"),
    "jungle":  ("#CFEFD3", "#8FD79A"),
    "zoo":     ("#D8ECFB", "#AEE0B4"),
    "forest":  ("#D5EBDC", "#9BD3A6"),
    "basket":  ("#FDEBD0", "#F6D5AE"),
    "market":  ("#FCE4D6", "#F7CBB4"),
    "garden":  ("#DFF2C8", "#BFE6A6"),
    "town":    ("#D6E9FA", "#CBD9E8"),
    "road":    ("#DCEBF8", "#C9D6E3"),
    "city":    ("#DDE8F7", "#C6D4E6"),
    "candy":   ("#FDE0EF", "#F8C8DE"),
    "space":   ("#D9DCF5", "#BFC4EE"),
}
DEFAULT_BACKDROP = ("#DCEEFB", "#F6E4C8")


def backdrop_for(theme_id: str) -> tuple[str, str]:
    return THEME_BACKDROPS.get(theme_id, DEFAULT_BACKDROP)


# ----------------------------------------------------------------------------
#  Zinsvarianten
# ----------------------------------------------------------------------------

INTRO_GREETINGS = [
    "Hello, friends!",
    "Hi there, little one!",
    "Hello, hello!",
    "Well hello, friend!",
]

INTRO_INVITES = [
    "Are you ready to learn with me today?",
    "Let's learn something new together!",
    "Come and learn with me!",
    "Shall we learn something fun?",
]

PRAISE = [
    "Great job!",
    "Well done!",
    "You did it!",
    "Nice work!",
    "Wonderful!",
    "Hooray!",
    "Fantastic!",
]

OUTRO_LINES = [
    "You learned so much today. I am so proud of you!",
    "What a great job you did today. You are such a good learner!",
    "You worked so hard today. Give yourself a big clap!",
]

OUTRO_GOODBYE = [
    "Bye bye! See you next time!",
    "Goodbye, friend! Come back soon!",
    "See you soon! Bye bye!",
]
