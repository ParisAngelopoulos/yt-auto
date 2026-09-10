"""Gelaagde silhouetlandschappen.

De kindervideo's tekenden één vrolijk figuur op een effen lucht. Een
volksverhaal vraagt iets anders: sfeer, diepte, en een beeld waar je een
halve minuut naar kunt kijken zonder dat het gaat vervelen.

De opbouw volgt hoe een landschapsschilder het doet. Eerst de lucht, dan
lagen die naar de kijker toe steeds donkerder worden. Dat laatste is de
hele truc: verre bergen zijn bleek omdat er lucht tussen zit, en de boom
vlak voor je is bijna zwart. Zonder dat verloop is het een plaatje; mét
dat verloop is het diepte.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from .palette import RGB, to_rgb

# ---------------------------------------------------------------------------
#  Luchten
# ---------------------------------------------------------------------------

# Boven, midden, onder aan de horizon. Volksverhalen spelen zich zelden op
# een stralende middag af, dus de nacht- en schemertinten zijn het rijkst.
SKIES: dict[str, tuple[str, str, str]] = {
    "night":     ("#0B1026", "#131A3A", "#2A2B52"),
    "moonlit":   ("#0D1430", "#1B2450", "#3A4272"),
    "dusk":      ("#2A2350", "#7A4468", "#D9805A"),
    "dawn":      ("#2E3566", "#8A6A8E", "#E8A579"),
    "day":       ("#5A86B8", "#93B3D4", "#D6DCE4"),
    "overcast":  ("#41485A", "#5B6474", "#8A9099"),
    "storm":     ("#1C2029", "#2E3644", "#4A4F55"),
    "winter":    ("#4A5878", "#7C8CA8", "#C6CEDA"),
    "underworld":("#0A0710", "#1F0F1C", "#43172A"),
}

# Waar de laatste laag in overgaat: de grondtoon van het landschap.
GROUNDS: dict[str, str] = {
    "night": "#070A16", "moonlit": "#080C1C", "dusk": "#1E1428",
    "dawn": "#1F1A2E", "day": "#233021", "overcast": "#22262C",
    "storm": "#0F1218", "winter": "#1A2030", "underworld": "#0A050C",
}


def sky_gradient(size: tuple[int, int], time_of_day: str) -> Image.Image:
    """Verticaal verloop over drie kleuren, met de horizon op tweederde."""
    w, h = size
    top, mid, low = (to_rgb(c) for c in SKIES.get(time_of_day, SKIES["night"]))

    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        f = y / max(1, h - 1)
        if f < 0.66:
            t = f / 0.66
            a, b = top, mid
        else:
            t = (f - 0.66) / 0.34
            a, b = mid, low
        px[0, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return strip.resize(size, Image.BILINEAR)


def add_stars(img: Image.Image, seed: int, count: int = 140) -> None:
    """Sterren, dichter naar boven toe en met wisselende helderheid."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.uniform(0, w)
        # kwadratisch: bijna alle sterren in de bovenste helft
        y = (rng.random() ** 1.7) * h * 0.62
        r = rng.uniform(0.7, 2.0)
        helder = rng.randint(120, 255)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 253, 240, helder))
    # een handjevol grotere met een zachte gloed
    for _ in range(7):
        x, y = rng.uniform(0, w), (rng.random() ** 1.7) * h * 0.5
        gloed = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(gloed).ellipse([x - 7, y - 7, x + 7, y + 7],
                                      fill=(255, 250, 230, 110))
        img.alpha_composite(gloed.filter(ImageFilter.GaussianBlur(5)))


def add_moon(img: Image.Image, x: float = 0.74, y: float = 0.19,
             radius: float = 0.055, phase: float = 0.0) -> None:
    """Maan met halo. phase 0 is vol; hoger schuift er een schaduw overheen."""
    w, h = img.size
    cx, cy, r = x * w, y * h, radius * h

    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - r * 3.4, cy - r * 3.4, cx + r * 3.4, cy + r * 3.4],
                                 fill=(220, 228, 255, 46))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(r * 1.5)))

    schijf = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(schijf)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 245, 232, 255))
    if phase > 0.02:
        offset = r * 2 * phase
        dd.ellipse([cx - r + offset, cy - r, cx + r + offset, cy + r], fill=(0, 0, 0, 0))
    img.alpha_composite(schijf)


def add_sun(img: Image.Image, x: float = 0.5, y: float = 0.62,
            radius: float = 0.075, color: str = "#F5C77E") -> None:
    """Lage zon met brede gloed. Bedoeld voor schemer en dageraad."""
    w, h = img.size
    cx, cy, r = x * w, y * h, radius * h
    tint = to_rgb(color)

    for schaal, alpha in ((5.0, 30), (3.0, 46), (1.9, 72)):
        gloed = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(gloed).ellipse(
            [cx - r * schaal, cy - r * schaal, cx + r * schaal, cy + r * schaal],
            fill=(*tint, alpha))
        img.alpha_composite(gloed.filter(ImageFilter.GaussianBlur(r * schaal * 0.4)))

    schijf = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(schijf).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*tint, 235))
    img.alpha_composite(schijf)


# ---------------------------------------------------------------------------
#  Diepte
# ---------------------------------------------------------------------------


def desaturate(kleur: RGB, hoeveelheid: float) -> RGB:
    """Trekt een kleur naar zijn eigen grijswaarde toe."""
    grijs = round(0.299 * kleur[0] + 0.587 * kleur[1] + 0.114 * kleur[2])
    return tuple(round(k + (grijs - k) * hoeveelheid) for k in kleur)


def depth_color(ground: RGB, haze: RGB, depth: float) -> RGB:
    """Kleur van een laag op afstand `depth` (0 = ver weg, 1 = vlakbij).

    Verre lagen lopen naar de luchtkleur toe, dichtbije naar de grondtoon.
    Dat is luchtperspectief, en het is het enige dat een stapel silhouetten
    in diepte omzet.
    """
    f = max(0.0, min(1.0, depth))
    meng = (1.0 - f) ** 1.35
    zacht = desaturate(haze, 0.45)
    return tuple(round(ground[i] + (zacht[i] - ground[i]) * meng) for i in range(3))


# ---------------------------------------------------------------------------
#  Bergkammen
# ---------------------------------------------------------------------------


def ridge_points(width: int, base_y: float, amplitude: float,
                 roughness: float, seed: int, steps: int = 8) -> list[tuple[float, float]]:
    """Natuurlijke bergkam via herhaalde middenpuntsverschuiving.

    Begint met twee punten en verdeelt telkens elk segment, waarbij het
    nieuwe middenpunt willekeurig omhoog of omlaag schuift. De schommeling
    halveert per ronde; dat levert grillige toppen met rustige flanken op,
    zoals een echte bergketen.
    """
    rng = random.Random(seed)
    punten = [0.0, rng.uniform(-1, 1), 0.0]

    schommel = 1.0
    for _ in range(steps):
        nieuw: list[float] = []
        for i in range(len(punten) - 1):
            nieuw.append(punten[i])
            midden = (punten[i] + punten[i + 1]) / 2
            nieuw.append(midden + rng.uniform(-schommel, schommel))
        nieuw.append(punten[-1])
        punten = nieuw
        schommel *= roughness

    hoogste = max(abs(p) for p in punten) or 1.0
    stap = width / (len(punten) - 1)
    return [(i * stap, base_y - p / hoogste * amplitude) for i, p in enumerate(punten)]


def draw_ridge(img: Image.Image, punten: list[tuple[float, float]], kleur: RGB) -> None:
    """Vult een kam tot de onderkant van het beeld."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(-2, h + 2), *punten, (w + 2, h + 2)], fill=(*kleur, 255))


def draw_hill_layer(img: Image.Image, base_y: float, amplitude: float,
                    kleur: RGB, seed: int, roughness: float = 0.52) -> None:
    w, h = img.size
    draw_ridge(img, ridge_points(w, base_y * h, amplitude * h, roughness, seed), kleur)


def draw_forest_band(img: Image.Image, base_y: float, kleur: RGB, seed: int,
                     density: float = 1.0, height: float = 0.085) -> None:
    """Rij naaldbomen langs een kamlijn.

    Elke boom is een driehoek met een lichte kromming in de stam; genoeg
    om als bos te lezen zonder dat het een zaagtand wordt.
    """
    w, h = img.size
    rng = random.Random(seed)
    d = ImageDraw.Draw(img, "RGBA")

    kam = ridge_points(w, base_y * h, h * 0.02, 0.5, seed + 11, steps=6)
    d.polygon([(-2, h + 2), *kam, (w + 2, h + 2)], fill=(*kleur, 255))

    stap = max(7, int(15 / max(0.25, density)))
    for x in range(-10, w + 10, stap):
        i = min(len(kam) - 1, max(0, int(x / w * (len(kam) - 1))))
        grond = kam[i][1] + 2
        boomhoogte = h * height * rng.uniform(0.55, 1.35)
        breedte = boomhoogte * rng.uniform(0.24, 0.36)
        helling = rng.uniform(-0.08, 0.08) * boomhoogte
        d.polygon(
            [(x - breedte, grond), (x + helling, grond - boomhoogte), (x + breedte, grond)],
            fill=(*kleur, 255),
        )


def draw_water(img: Image.Image, horizon: float, kleur: RGB, seed: int,
               glans: RGB | None = None, bron_x: float = 0.5) -> None:
    """Wateroppervlak met een lichtpad, zoals maanlicht op een meer."""
    w, h = img.size
    y = horizon * h
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, y, w, h], fill=(*kleur, 255))

    if glans is None:
        return
    rng = random.Random(seed)
    baan = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(baan)
    midden = w * bron_x          # de weerspiegeling staat onder de lichtbron
    afstand = max(1.0, h - y)
    regels = max(14, int(afstand / 7))
    for i in range(regels):
        t = i / regels
        yy = y + t * afstand
        # smal bij de horizon, breder naar de kijker toe: zo valt licht op water
        breedte = (0.03 + t * 0.16) * w
        for _ in range(rng.randint(1, 3)):
            lengte = breedte * rng.uniform(0.15, 0.55)
            xx = midden + rng.uniform(-breedte, breedte) * 0.5
            alpha = int(170 * (1 - t) ** 1.2 * rng.uniform(0.45, 1.0))
            dd.rectangle([xx - lengte / 2, yy, xx + lengte / 2, yy + 1.8],
                         fill=(*glans, alpha))
    img.alpha_composite(baan.filter(ImageFilter.GaussianBlur(1.1)))


# ---------------------------------------------------------------------------
#  Weer
# ---------------------------------------------------------------------------


def add_mist(img: Image.Image, y: float, kleur: RGB, seed: int, sterkte: float = 0.5) -> None:
    """Nevelbanken die tussen de lagen blijven hangen."""
    w, h = img.size
    rng = random.Random(seed)
    laag = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(laag)
    for i in range(5):
        yy = y * h + rng.uniform(-0.05, 0.05) * h
        dikte = rng.uniform(0.02, 0.05) * h
        alpha = int(90 * sterkte * rng.uniform(0.5, 1.0))
        d.ellipse([-w * 0.2, yy - dikte, w * 1.2, yy + dikte], fill=(*kleur, alpha))
    img.alpha_composite(laag.filter(ImageFilter.GaussianBlur(h * 0.035)))


def add_rain(img: Image.Image, seed: int, dichtheid: int = 320) -> None:
    w, h = img.size
    rng = random.Random(seed)
    laag = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(laag)
    for _ in range(dichtheid):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        lengte = rng.uniform(0.012, 0.030) * h
        d.line([(x, y), (x - lengte * 0.28, y + lengte)],
               fill=(200, 214, 232, rng.randint(40, 105)), width=1)
    img.alpha_composite(laag.filter(ImageFilter.GaussianBlur(0.6)))


def add_snow(img: Image.Image, seed: int, dichtheid: int = 130) -> None:
    """Vlokken in twee lagen: veel kleine ver weg, een paar grote vlakbij."""
    w, h = img.size
    rng = random.Random(seed)
    laag = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(laag)
    for _ in range(dichtheid):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(0.8, 1.7)
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(240, 245, 255, rng.randint(60, 130)))
    img.alpha_composite(laag.filter(ImageFilter.GaussianBlur(0.4)))

    voorgrond = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(voorgrond)
    for _ in range(dichtheid // 5):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(2.2, 3.6)
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(246, 250, 255, rng.randint(110, 170)))
    img.alpha_composite(voorgrond.filter(ImageFilter.GaussianBlur(1.6)))


WEATHER = {"mist": add_mist, "rain": add_rain, "snow": add_snow}


# ---------------------------------------------------------------------------
#  Settings
# ---------------------------------------------------------------------------

# Elke setting is een receptje van lagen, van ver naar dichtbij. De diepte
# per laag stuurt de kleur; de horizon bepaalt waar de lucht ophoudt.
#   ("ridge", basis_y, hoogte, ruwheid, diepte)
#   ("forest", basis_y, dichtheid, hoogte, diepte)
#   ("water", horizon, diepte, lichtpad)
SETTINGS: dict[str, list[tuple]] = {
    "mountains": [
        ("ridge", 0.60, 0.26, 0.60, 0.10), ("ridge", 0.68, 0.20, 0.56, 0.32),
        ("ridge", 0.78, 0.16, 0.52, 0.58), ("ridge", 0.92, 0.13, 0.48, 0.90),
    ],
    "forest": [
        ("ridge", 0.66, 0.10, 0.50, 0.12), ("forest", 0.74, 0.7, 0.075, 0.36),
        ("forest", 0.85, 1.0, 0.105, 0.64), ("forest", 1.02, 1.4, 0.150, 0.95),
    ],
    "hills": [
        ("ridge", 0.68, 0.09, 0.44, 0.14), ("ridge", 0.79, 0.10, 0.42, 0.44),
        ("ridge", 0.93, 0.11, 0.40, 0.82),
    ],
    "valley": [
        ("ridge", 0.55, 0.28, 0.60, 0.08), ("ridge", 0.66, 0.22, 0.56, 0.30),
        ("forest", 0.82, 0.9, 0.085, 0.60), ("ridge", 0.97, 0.09, 0.44, 0.92),
    ],
    "lake": [
        ("ridge", 0.56, 0.22, 0.58, 0.08), ("forest", 0.68, 0.8, 0.065, 0.30),
        ("water", 0.70, 0.52, True), ("ridge", 0.94, 0.05, 0.36, 0.92),
    ],
    "coast": [
        ("ridge", 0.60, 0.20, 0.62, 0.10), ("water", 0.68, 0.46, True),
        ("ridge", 0.96, 0.045, 0.34, 0.94),
    ],
    "moor": [
        ("ridge", 0.72, 0.05, 0.36, 0.16), ("ridge", 0.83, 0.05, 0.34, 0.46),
        ("ridge", 0.96, 0.06, 0.32, 0.86),
    ],
    "cliffs": [
        ("ridge", 0.50, 0.34, 0.72, 0.10), ("ridge", 0.70, 0.26, 0.68, 0.40),
        ("ridge", 0.98, 0.22, 0.64, 0.92),
    ],
    "plain": [
        ("ridge", 0.80, 0.03, 0.30, 0.20), ("ridge", 0.95, 0.04, 0.28, 0.85),
    ],
    "village": [
        ("ridge", 0.64, 0.12, 0.48, 0.12), ("forest", 0.74, 0.5, 0.060, 0.34),
        ("ridge", 0.90, 0.08, 0.40, 0.72), ("ridge", 1.02, 0.07, 0.36, 0.96),
    ],
}


def horizon_of(setting: str) -> float:
    """Hoogte waarop het land begint. Gebruikt om figuren neer te zetten."""
    lagen = SETTINGS.get(setting, SETTINGS["hills"])
    return min(laag[1] for laag in lagen)


def foreground_top(setting: str) -> float:
    """Bovenkant van de voorste laag: daaronder verdwijnt een figuur erachter."""
    lagen = SETTINGS.get(setting, SETTINGS["hills"])
    laatste = lagen[-1]
    return laatste[1] - (laatste[2] if laatste[0] == "ridge" else laatste[3])


def draw_landscape(img: Image.Image, setting: str, time_of_day: str, seed: int,
                   light_x: float = 0.5, skip_last: bool = False,
                   only_last: bool = False) -> None:
    """Bouwt de lagen op van ver naar dichtbij.

    skip_last laat de voorste laag weg en only_last tekent alleen die. Zo
    kan de renderer figuren ertussen zetten: een reiziger loopt dan achter
    de bomen op de voorgrond langs in plaats van erbovenop te plakken.
    """
    grond = to_rgb(GROUNDS.get(time_of_day, GROUNDS["night"]))
    nevel = to_rgb(SKIES.get(time_of_day, SKIES["night"])[2])

    lagen = SETTINGS.get(setting, SETTINGS["hills"])
    if skip_last:
        lagen = lagen[:-1]
    elif only_last:
        lagen = lagen[-1:]

    for index, laag in enumerate(lagen):
        soort = laag[0]
        if soort == "ridge":
            _, basis, hoogte, ruw, diepte = laag
            draw_hill_layer(img, basis, hoogte, depth_color(grond, nevel, diepte),
                            seed + index * 37, ruw)
        elif soort == "forest":
            _, basis, dicht, hoogte, diepte = laag
            draw_forest_band(img, basis, depth_color(grond, nevel, diepte),
                             seed + index * 53, dicht, hoogte)
        elif soort == "water":
            _, horizon, diepte, lichtpad = laag
            maanlicht = time_of_day in ("night", "moonlit", "dusk", "dawn")
            glans = (222, 228, 250) if (lichtpad and maanlicht) else None
            draw_water(img, horizon, depth_color(grond, nevel, diepte),
                       seed + index * 71, glans, light_x)


# ---------------------------------------------------------------------------
#  Een complete scene
# ---------------------------------------------------------------------------


def scene_colors(time_of_day: str) -> tuple[RGB, RGB]:
    """Grondtoon en nevelkleur voor deze tijd van de dag."""
    grond = to_rgb(GROUNDS.get(time_of_day, GROUNDS["night"]))
    nevel = to_rgb(SKIES.get(time_of_day, SKIES["night"])[2])
    return grond, nevel


def silhouette_color(time_of_day: str, depth: float) -> RGB:
    """Hoe donker een figuur op deze afstand moet zijn.

    Vlakbij vrijwel zwart, verder weg opgelost in de nevel. Zonder dit staat
    een reiziger op de horizon net zo hard in beeld als een boom vlak voor
    de kijker, en valt de diepte weg.
    """
    grond, nevel = scene_colors(time_of_day)
    donker = tuple(round(k * 0.55) for k in grond)
    return depth_color(donker, nevel, depth)
