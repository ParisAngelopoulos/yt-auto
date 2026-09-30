"""De afdaling: één hoge beeldkolom waar de camera doorheen zakt.

Waarom zo: een Short die uit stilstaande beelden bestaat leest als een
diashow, en daar scrolt iedereen voorbij. Hier beweegt het beeld van de
eerste tot de laatste seconde, zonder één snede. Dat kan omdat de hele reis
één keer getekend wordt als een heel hoog beeld; de camera is daarna niets
meer dan een uitsnede die omlaag schuift, en dat schuiven doet ffmpeg.

De diepteschaal is bewust niet lineair. Lineair zou de eerste honderd meter
— waar de duiker, de walvis en het wrak zitten — samenpersen tot een paar
pixels, terwijl de onderste kilometers leeg water zijn. Logaritmisch krijgt
elk tiental zijn eigen ruimte en versnelt de teller onderweg, wat precies
het gevoel geeft dat je zoekt: eerst herkenbaar, dan eindeloos.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

# Hoe het water van kleur verandert met de diepte. De omslagpunten volgen de
# gangbare indeling: zonlicht tot 200 meter, schemer tot 1000, daaronder
# middernacht — waar nooit meer licht komt.
WATER = [
    (0, (56, 182, 232)),
    (40, (32, 140, 196)),
    (200, (18, 78, 124)),
    (600, (11, 44, 78)),
    (1200, (6, 24, 44)),
    (4000, (3, 12, 24)),
    (11000, (1, 6, 12)),
]


@dataclass
class DepthScale:
    """Rekent meters om naar pixels, en terug."""

    total_m: float
    height_px: int
    softness: float = 8.0          # hoe ruim de eerste meters uitgesmeerd worden

    def __post_init__(self) -> None:
        self._span = math.log10(1.0 + self.total_m / self.softness)

    def y(self, meters: float) -> float:
        meters = max(0.0, min(float(meters), self.total_m))
        return self.height_px * math.log10(1.0 + meters / self.softness) / self._span

    def depth(self, y: float) -> float:
        deel = max(0.0, min(y / self.height_px, 1.0))
        return self.softness * (10.0 ** (deel * self._span) - 1.0)


def _water_color(meters: float) -> tuple[int, int, int]:
    vorige = WATER[0]
    for stop in WATER[1:]:
        if meters <= stop[0]:
            breuk = (meters - vorige[0]) / max(1e-6, stop[0] - vorige[0])
            return tuple(int(vorige[1][i] + (stop[1][i] - vorige[1][i]) * breuk)
                         for i in range(3))
        vorige = stop
    return WATER[-1][1]


def _light_rays(laag: Image.Image, width: int, tot_y: int, seed: int) -> None:
    """Zonlicht dat door het oppervlak breekt. Alleen bovenin, waar het kan."""
    rng = random.Random(seed)
    stralen = Image.new("L", (width, tot_y), 0)
    d = ImageDraw.Draw(stralen)
    for _ in range(7):
        x = rng.uniform(-0.1, 1.1) * width
        breedte = rng.uniform(0.04, 0.13) * width
        schuin = rng.uniform(-0.25, 0.25) * width
        d.polygon([(x - breedte / 2, 0), (x + breedte / 2, 0),
                   (x + schuin + breedte * 1.4, tot_y), (x + schuin - breedte * 1.4, tot_y)],
                  fill=rng.randint(30, 60))
    stralen = stralen.filter(ImageFilter.GaussianBlur(width * 0.045))

    # Naar onderen uitdoven, anders houdt het licht niet op waar het water dicht wordt.
    verloop = Image.new("L", (1, tot_y))
    for y in range(tot_y):
        verloop.putpixel((0, y), int(255 * (1.0 - y / tot_y) ** 1.7))
    stralen = Image.composite(stralen, Image.new("L", stralen.size, 0),
                              verloop.resize((width, tot_y)))

    licht = Image.new("RGBA", (width, tot_y), (180, 226, 255, 0))
    licht.putalpha(stralen)
    laag.alpha_composite(licht, (0, 0))


def _caustics(laag: Image.Image, width: int, tot_y: int, seed: int) -> None:
    """Het golfpatroon dat vlak onder het oppervlak over alles danst.

    Dit is wat ondiep water er ondiep uit laat zien. Zonder dit is de
    bovenkant een vlak blauw verloop, en een vlak verloop leest als papier.
    """
    if tot_y < 40:
        return
    rng = random.Random(seed + 41)
    patroon = Image.new("L", (width, tot_y), 0)
    d = ImageDraw.Draw(patroon)
    # Dunne, lange lijnen met een flauwe golf erin. Dik en sterk vervaagd
    # lopen ze in elkaar en wordt het camouflage in plaats van licht.
    for _ in range(int(tot_y / 11) + 24):
        y = rng.uniform(0, tot_y)
        dikte = rng.uniform(width * 0.0018, width * 0.0055)
        golf = rng.uniform(width * 0.015, width * 0.045)
        frequentie = rng.uniform(3, 7)
        fase = rng.random() * 6.28
        punten = [(x, y + golf * math.sin(x / width * frequentie + fase))
                  for x in range(0, width + 30, 30)]
        d.line(punten, fill=rng.randint(45, 105), width=max(1, int(dikte)))
    patroon = patroon.filter(ImageFilter.GaussianBlur(width * 0.005))

    verloop = Image.new("L", (width, tot_y))
    vd = ImageDraw.Draw(verloop)
    for y in range(tot_y):
        vd.line([(0, y), (width, y)], fill=int(255 * (1.0 - y / tot_y) ** 2.0))
    patroon = Image.composite(patroon, Image.new("L", patroon.size, 0), verloop)

    licht = Image.new("RGBA", (width, tot_y), (214, 244, 255, 0))
    licht.putalpha(patroon)
    laag.alpha_composite(licht, (0, 0))


def _marine_snow(laag: Image.Image, width: int, height: int, seed: int) -> None:
    """Zwevende deeltjes. Dit is wat de beweging zichtbaar maakt.

    Zonder deze stipjes schuift er een kleurverloop voorbij en ziet het oog
    niet dat er iets beweegt; mét is het meteen duidelijk dat je zakt.
    """
    rng = random.Random(seed + 11)
    d = ImageDraw.Draw(laag, "RGBA")
    aantal = int(height * width / 26000)
    for _ in range(aantal):
        y = rng.uniform(0, height)
        x = rng.uniform(0, width)
        straal = rng.uniform(1.0, 3.4)
        helder = rng.randint(120, 215)
        alpha = int(rng.uniform(0.25, 0.85) * 255 * (0.35 + 0.65 * (1 - y / height) ** 0.5))
        d.ellipse([x - straal, y - straal, x + straal, y + straal],
                  fill=(helder, helder + 12, helder + 20, alpha))


def _seabed(laag: Image.Image, width: int, height: int, seed: int) -> None:
    """De bodem: waar het ophoudt.

    Die moet lichter zijn dan het water eromheen. Op elf kilometer diepte is
    het water bijna zwart, en zwart slib op zwart water is geen einde maar
    een lege onderkant — precies het tegenovergestelde van wat je wilt na
    zeventig seconden afdalen.
    """
    rng = random.Random(seed + 23)
    top = height - int(width * 0.52)
    punten = [(0, height), (0, top + rng.uniform(-20, 20))]
    x = 0.0
    while x < width:
        x += rng.uniform(width * 0.05, width * 0.14)
        punten.append((min(x, width), top + rng.uniform(-width * 0.05, width * 0.06)))
    punten += [(width, height)]

    d = ImageDraw.Draw(laag, "RGBA")
    d.polygon(punten, fill=(22, 32, 42, 255))
    # Een randje licht op de bovenkant: het enige licht hier komt van de
    # camera, en dat valt op wat er naar boven steekt.
    d.line(punten[1:-1], fill=(96, 122, 140, 190), width=max(2, width // 360))


def _sky(laag: Image.Image, width: int, tot_y: int) -> None:
    """Boven het wateroppervlak, zodat de reis ergens begint."""
    d = ImageDraw.Draw(laag)
    for y in range(tot_y):
        deel = y / max(1, tot_y)
        kleur = tuple(int(a + (b - a) * deel)
                      for a, b in zip((188, 216, 236), (132, 196, 224)))
        d.line([(0, y), (width, y)], fill=(*kleur, 255))
    # De waterlijn zelf: een lichte rand waar het licht op het oppervlak valt.
    d.rectangle([0, tot_y - 5, width, tot_y + 2], fill=(236, 250, 255, 255))


def water_column(width: int, scale: DepthScale, seed: int = 0,
                 top_px: int = 0, floor_px: int = 0) -> Image.Image:
    """Tekent de hele reis als één hoog beeld.

    Boven het nulpunt zit lucht en onder het diepste punt zit bodem; zonder
    die marges begint en eindigt de reis midden in het water, en dan voelt
    geen van beide als een begin of een eind.
    """
    height = top_px + scale.height_px + floor_px
    kolom = Image.new("RGBA", (width, height))
    d = ImageDraw.Draw(kolom)

    for y in range(top_px, height):
        diepte = scale.depth(y - top_px)
        d.line([(0, y), (width, y)], fill=(*_water_color(diepte), 255))

    if top_px:
        _sky(kolom, width, top_px)

    water = Image.new("RGBA", (width, height - top_px), (0, 0, 0, 0))
    _caustics(water, width, int(scale.y(45)), seed)
    _light_rays(water, width, int(scale.y(160)), seed)
    kolom.alpha_composite(water, (0, top_px))

    if floor_px:
        _seabed(kolom, width, height, seed)
    return kolom


# ---------------------------------------------------------------------------
#  Mijlpalen in de kolom
# ---------------------------------------------------------------------------

# Hoe groot elk wezen in beeld komt, als deel van de breedte. Niet op ware
# schaal onderling — dat zou de walvis een pixel geven naast het wrak — maar
# groot genoeg om herkenbaar te zijn en klein genoeg om niet te schreeuwen.
SIZES = {
    "diver": 0.20, "whale": 0.62, "sperm_whale": 0.56, "shark": 0.34,
    "jellyfish": 0.22, "squid": 0.30, "anglerfish": 0.26, "wreck": 0.48,
    "submersible": 0.24, "tube_worms": 0.38,
}


def _rule(laag: Image.Image, y: int, width: int, sterkte: int) -> None:
    ImageDraw.Draw(laag, "RGBA").line([(int(width * 0.08), y), (int(width * 0.92), y)],
                                      fill=(210, 232, 248, sterkte), width=2)


def place_milestones(plaats: "Column", milestones: list[dict], seed: int = 0) -> None:
    """Zet elk wezen op zijn eigen diepte, met een streep en een naam erbij.

    Links en rechts om en om: twee dingen onder elkaar aan dezelfde kant
    leest als een rij, en dan lijkt het weer een lijst in plaats van een reis.
    """
    from .sea import creature_color, render_creature
    from .story_scene import load_font

    kolom = plaats.image
    width = kolom.width
    d = ImageDraw.Draw(kolom, "RGBA")
    naam_font = load_font(int(width * 0.043), "IBMPlexSans", 600)
    diep_font = load_font(int(width * 0.032), "IBMPlexMono-Medium", 400)

    for index, steen in enumerate(milestones):
        diepte = float(steen["depth"])
        y = int(plaats.row(diepte))
        links = index % 2 == 0
        kleur = creature_color(diepte)

        if steen.get("draw"):
            naam = steen["draw"]
            breed = int(width * float(steen.get("size", SIZES.get(naam, 0.28))))
            proef = render_creature(naam, 100, kleur)
            hoogte = max(12, int(breed * proef.height / max(1, proef.width)))
            beeld = render_creature(naam, hoogte, kleur)
            x = int(width * (0.09 if links else 0.91)) - (0 if links else beeld.width)
            boven = y - beeld.height - int(width * 0.03)

            # In het donker licht alles wat je ziet zelf op, of wordt het door
            # jouw lamp aangeschenen. Een harde rand tegen zwart water leest
            # als een sticker; een zachte gloed eromheen leest als diepte.
            if diepte > 500:
                straal = max(6, int(hoogte * 0.16))
                gloed = Image.new("RGBA", (beeld.width + straal * 4,
                                           beeld.height + straal * 4), (0, 0, 0, 0))
                gloed.alpha_composite(beeld, (straal * 2, straal * 2))
                gloed = gloed.filter(ImageFilter.GaussianBlur(straal))
                verf = Image.new("RGBA", gloed.size, (90, 170, 210, 0))
                verf.putalpha(gloed.getchannel("A").point(lambda v: int(v * 0.55)))
                kolom.alpha_composite(verf, (x - straal * 2, boven - straal * 2))

            kolom.alpha_composite(beeld, (x, boven))

        _rule(kolom, y, width, 60 if not steen.get("label") else 105)

        label = steen.get("label")
        if label:
            tekst_x = int(width * (0.09 if links else 0.91))
            anker = "ls" if links else "rs"
            d.text((tekst_x, y - int(width * 0.012)), label, font=naam_font,
                   anchor=anker, fill=(232, 244, 255, 240))
            d.text((tekst_x, y + int(width * 0.050)), _meters(diepte), font=diep_font,
                   anchor="lt" if links else "rt", fill=(150, 196, 226, 225))


def _meters(diepte: float) -> str:
    return f"{int(round(diepte)):,} m".replace(",", ".")


@dataclass
class Column:
    """Het hele beeld plus de omrekening van meters naar rijen erin."""

    image: Image.Image
    scale: DepthScale
    top_px: int

    def row(self, meters: float) -> float:
        """Op welke rij in dit beeld deze diepte staat."""
        return self.top_px + self.scale.y(meters)

    def depth_at(self, row: float) -> float:
        return self.scale.depth(row - self.top_px)


def build_column(width: int, journey: dict, seed: int = 0) -> Column:
    """De hele reis als één beeld, klaar om doorheen te zakken."""
    totaal = float(journey["total"])
    # Genoeg pixels om elk tiental zijn eigen ruimte te geven, en niet zoveel
    # dat het beeld onwerkbaar wordt: 24.000 rijen is 78 MB en tekent in een
    # halve seconde.
    hoogte = int(journey.get("height_px", 24000))
    scale = DepthScale(total_m=totaal, height_px=hoogte)
    top_px = int(journey.get("top_px", width * 0.62))
    floor_px = int(journey.get("floor_px", width * 1.5))

    kolom = water_column(width, scale, seed=seed, top_px=top_px, floor_px=floor_px)
    plaats = Column(image=kolom, scale=scale, top_px=top_px)
    place_milestones(plaats, journey["milestones"], seed=seed)
    return plaats


# ---------------------------------------------------------------------------
#  Zwevende deeltjes, in lagen
# ---------------------------------------------------------------------------


class ParticleField:
    """Deeltjes op drie afstanden, die dus niet even snel voorbijkomen.

    Dit is het verschil tussen 'een plaat schuift omhoog' en 'ik zak ergens
    doorheen'. Alles met dezelfde snelheid laten bewegen is precies wat een
    beeld plat maakt: het oog leidt diepte af uit snelheidsverschil, niet uit
    een kleurverloop. De verste laag beweegt op zes tiende van de camera, de
    dichtste op anderhalf — en die laatste is groter en waziger, zoals iets
    dat vlak voor je lens langsdrijft.
    """

    SPEEDS = (0.55, 1.0, 1.55)
    SIZES = (1.1, 2.0, 4.6)
    ALPHAS = (0.45, 0.8, 0.30)

    def __init__(self, width: int, column_height: int, view_height: int,
                 seed: int = 0, density: float = 1.0) -> None:
        import numpy as np

        self.width = width
        self.lagen = []
        rng = random.Random(seed + 77)
        for index, snelheid in enumerate(self.SPEEDS):
            bereik = column_height * snelheid + view_height
            aantal = int(bereik * width / 62000 * density)
            ys = sorted(rng.uniform(0, bereik) for _ in range(aantal))
            xs = [rng.uniform(0, width) for _ in range(aantal)]
            radii = [rng.uniform(0.6, 1.6) * self.SIZES[index] * width / 1080
                     for _ in range(aantal)]
            alphas = [rng.uniform(0.4, 1.0) * self.ALPHAS[index] for _ in range(aantal)]
            self.lagen.append((np.array(ys), xs, radii, alphas))

    def draw(self, frame: Image.Image, camera_y: float, view_height: int,
             fade: float = 1.0) -> None:
        import numpy as np

        d = ImageDraw.Draw(frame, "RGBA")
        for (ys, xs, radii, alphas), snelheid in zip(self.lagen, self.SPEEDS):
            boven = camera_y * snelheid
            eerste = int(np.searchsorted(ys, boven))
            laatste = int(np.searchsorted(ys, boven + view_height))
            for index in range(eerste, laatste):
                y = ys[index] - boven
                r = radii[index]
                a = int(255 * alphas[index] * fade)
                if a <= 2:
                    continue
                x = xs[index]
                d.ellipse([x - r, y - r, x + r, y + r], fill=(206, 230, 246, a))
