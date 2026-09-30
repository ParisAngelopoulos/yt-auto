"""Ondertiteling die in het beeld gebrand wordt.

Waarom dit er is: het grootste deel van de Shorts wordt zonder geluid
bekeken — in de trein, naast iemand die slaapt, op kantoor. Een verhaal dat
alleen verteld wordt is dan een reeks landschappen zonder betekenis. Met
tekst in beeld blijft het een verhaal.

Hoe het werkt: elke gesproken zin wordt in stukjes van een paar woorden
geknipt, en die stukjes krijgen tijd naar rato van hun lengte. Dat is geen
echte uitlijning op de stem — daarvoor zou je het audiobestand moeten
analyseren — maar bij een verteller die gelijkmatig spreekt zit het er dicht
genoeg tegenaan, en het loopt nooit uit de pas omdat elke zin opnieuw begint
op zijn eigen starttijd.
"""

from __future__ import annotations

import re

from dataclasses import dataclass

from PIL import Image, ImageDraw

from ..render.story_scene import load_font

# Een regel van ongeveer deze lengte past op één regel in beeld en is in één
# oogopslag te lezen. Langer en de kijker leest nog terwijl de zin al verder is.
MAX_CHARS = 30


@dataclass
class Chunk:
    """Eén stukje tekst met de tijd waarin het in beeld staat."""

    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _phrases(zin: str) -> list[str]:
    """Knipt op leestekens. Daar ademt de verteller, dus daar knipt het oog ook."""
    return [deel for deel in re.split(r"(?<=[,;:.!?])\s+", zin.strip()) if deel]


def _by_words(deel: str, max_chars: int) -> list[str]:
    stukjes: list[str] = []
    regel = ""
    for woord in deel.split():
        kandidaat = f"{regel} {woord}".strip()
        if regel and len(kandidaat) > max_chars:
            stukjes.append(regel)
            regel = woord
        else:
            regel = kandidaat
    if regel:
        stukjes.append(regel)
    return stukjes


def split_text(zin: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Knipt een zin in stukjes die elk op één regel passen.

    Eerst op leestekens, want daar valt de natuurlijke pauze; wat dan nog te
    lang is gaat op woorden. Een laatste stukje van één woord wordt bij het
    vorige getrokken: 'to' alleen in beeld leest als een fout.
    """
    stukjes: list[str] = []
    for deel in _phrases(zin) or [zin]:
        if stukjes and len(f"{stukjes[-1]} {deel}") <= max_chars:
            stukjes[-1] = f"{stukjes[-1]} {deel}"
        else:
            stukjes += _by_words(deel, max_chars)

    if len(stukjes) > 1 and len(stukjes[-1].split()) < 2:
        samen = f"{stukjes[-2]} {stukjes[-1]}"
        if len(samen) <= max_chars + 8:
            stukjes[-2:] = [samen]
    return stukjes


def time_chunks(zin: str, start: float, duration: float,
                max_chars: int = MAX_CHARS) -> list[Chunk]:
    """Verdeelt de spreektijd van een zin over zijn stukjes.

    Naar rato van het aantal tekens: een stukje van vijf letters staat korter
    in beeld dan een van vijfentwintig, en dat is ongeveer hoe iemand het ook
    uitspreekt.
    """
    stukjes = split_text(zin, max_chars)
    if not stukjes or duration <= 0:
        return []

    totaal = sum(len(s) for s in stukjes)
    chunks: list[Chunk] = []
    verstreken = start
    for index, stukje in enumerate(stukjes):
        deel = duration * len(stukje) / totaal
        einde = start + duration if index == len(stukjes) - 1 else verstreken + deel
        chunks.append(Chunk(start=verstreken, end=einde, text=stukje))
        verstreken = einde
    return chunks


def render_caption(tekst: str, size: tuple[int, int]) -> Image.Image:
    """Tekent één regel ondertiteling op een doorzichtig vlak.

    Wit met een zwarte rand eromheen: dat blijft leesbaar boven een lichte
    lucht én boven een donker bos, zonder dat er een balk overheen hoeft.
    """
    breedte, hoogte = size
    laag = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(laag)

    grootte = int(breedte * 0.062)
    font = load_font(grootte, "IBMPlexSans", 600)
    while grootte > 18 and d.textlength(tekst, font=font) > breedte * 0.86:
        grootte = int(grootte * 0.94)
        font = load_font(grootte, "IBMPlexSans", 600)

    # Iets onder het midden: hoog genoeg om buiten de knoppen van YouTube te
    # blijven, laag genoeg om het landschap niet door te snijden.
    y = hoogte * 0.61
    d.text((breedte / 2, y), tekst, font=font, anchor="mm",
           fill=(255, 255, 255, 255), stroke_width=max(2, grootte // 12),
           stroke_fill=(0, 0, 0, 225))
    return laag


def burn_in(frame: Image.Image, tekst: str) -> Image.Image:
    """Zet de ondertiteling op een kopie van het beeld."""
    doek = frame.convert("RGBA")
    doek.alpha_composite(render_caption(tekst, doek.size))
    return doek.convert("RGB")
