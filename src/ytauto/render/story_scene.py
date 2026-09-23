"""Bouwt één compleet beeld voor een volksverhaal.

De opbouw is altijd dezelfde: lucht, hemellichaam, landschapslagen, weer,
silhouetten, vignet, en eventueel tekst. Wat er verandert is de setting, de
tijd van de dag en welke figuren erin staan — en dat is precies wat de
scriptschrijver per scene aanlevert.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import ROOT
from .landscape import (GROUNDS, SETTINGS, SKIES, WEATHER, add_mist, add_moon,
                        add_rain, add_snow, add_stars, add_sun, draw_landscape,
                        foreground_top, horizon_of, scene_colors,
                        silhouette_color, sky_gradient)
from .palette import to_rgb
from .silhouettes import available_silhouettes, render_silhouette

FONT_DIR = ROOT / "assets" / "fonts"
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

NIGHTS = ("night", "moonlit", "underworld")
GOLDEN = ("dusk", "dawn")


@lru_cache(maxsize=64)
def load_font(size: int, familie: str = "EBGaramond", gewicht: int = 400):
    """Klassieke letters: Cinzel voor titels, EB Garamond voor de rest."""
    pad = FONT_DIR / f"{familie}.ttf"
    font = ImageFont.truetype(str(pad) if pad.exists() else FALLBACK, size)
    try:
        font.set_variation_by_axes([gewicht])
    except (AttributeError, OSError):
        pass
    return font


# ---------------------------------------------------------------------------
#  Onderdelen
# ---------------------------------------------------------------------------


def add_vignette(img: Image.Image, sterkte: float = 0.55) -> None:
    """Donkere hoeken. Houdt de blik in het midden en helpt tekst leesbaar
    te blijven, ook als de lucht achter de letters licht is."""
    w, h = img.size
    masker = Image.new("L", (w, h), 0)
    ImageDraw.Draw(masker).ellipse(
        [-w * 0.28, -h * 0.34, w * 1.28, h * 1.34], fill=255)
    masker = masker.filter(ImageFilter.GaussianBlur(min(w, h) * 0.10))

    donker = Image.new("RGBA", (w, h), (0, 0, 0, int(235 * sterkte)))
    donker.putalpha(Image.eval(masker, lambda v: int((255 - v) * sterkte)))
    img.alpha_composite(donker)


def place_silhouette(img: Image.Image, spec: dict[str, Any], time_of_day: str,
                     setting: str) -> None:
    """Zet één figuur neer, met de kleur en de plek die bij zijn afstand horen."""
    naam = spec.get("draw")
    if naam not in available_silhouettes():
        return

    w, h = img.size
    diepte = float(spec.get("depth", 0.8))
    hoogte = max(6, int(float(spec.get("scale", 0.18)) * h))
    tegel = render_silhouette(naam, hoogte, silhouette_color(time_of_day, diepte))

    # Verder weg staat hoger in beeld, dichterbij lager. De onderkant is de
    # bovenrand van de voorgrondlaag: daaronder zou een figuur erachter
    # verdwijnen zonder dat iemand dat bedoeld heeft.
    horizon = horizon_of(setting)
    onder = min(0.98, foreground_top(setting) + 0.04)
    grondlijn = float(spec.get("y", horizon + max(0.0, onder - horizon) * (0.2 + 0.8 * diepte)))

    x = float(spec.get("x", 0.5)) * w
    img.alpha_composite(tegel, (int(x - tegel.width / 2), int(grondlijn * h - tegel.height)))


def draw_title(img: Image.Image, titel: str, ondertitel: str = "") -> None:
    """Titelkaart: kapitalen met ruime spatiëring, zoals op een grafsteen
    of een oude bandrug. Geen kader, geen balk; het vignet doet het werk."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")

    grootte = int(h * 0.088)
    font = load_font(grootte, "Cinzel", 600)
    letters = " ".join(titel.upper()) if len(titel) <= 22 else titel.upper()
    while grootte > 22 and d.textlength(letters, font=font) > w * 0.82:
        grootte = int(grootte * 0.94)
        font = load_font(grootte, "Cinzel", 600)

    y = h * (0.46 if ondertitel else 0.50)
    for dx, dy in ((0, 3), (0, -1)):                      # zachte schaduw eronder
        d.text((w / 2 + dx, y + dy), letters, font=font, fill=(0, 0, 0, 120), anchor="mm")
    d.text((w / 2, y), letters, font=font, fill=(240, 236, 226, 255), anchor="mm")

    lijn_y = y + grootte * 0.95
    d.line([(w * 0.34, lijn_y), (w * 0.66, lijn_y)], fill=(214, 198, 160, 190), width=2)

    if ondertitel:
        sub = load_font(int(h * 0.036), "EBGaramond-Italic", 400)
        d.text((w / 2, lijn_y + h * 0.055), ondertitel, font=sub,
               fill=(216, 208, 192, 220), anchor="mm")


def draw_caption(img: Image.Image, tekst: str) -> None:
    """Korte regel onderin, voor een plaatsnaam of een tijdsaanduiding.

    Bij een staand beeld staat hij hoger. Onderin een Short leggen YouTube
    en TikTok hun eigen titel, kanaalnaam en knoppen neer; wat daar staat is
    onleesbaar, hoe mooi het ook gezet is.
    """
    w, h = img.size
    staand = h > w
    d = ImageDraw.Draw(img, "RGBA")
    font = load_font(int(min(h * 0.040, w * 0.055)), "EBGaramond-Italic", 400)
    y = h * (0.78 if staand else 0.90)
    d.text((w / 2, y + 2), tekst, font=font, fill=(0, 0, 0, 130), anchor="mm")
    d.text((w / 2, y), tekst, font=font, fill=(226, 220, 206, 225), anchor="mm")


# ---------------------------------------------------------------------------
#  Publiek
# ---------------------------------------------------------------------------

# Waar de zon of maan staat, per tijd van de dag. De weerspiegeling op water
# volgt deze plek, dus hij moet vastliggen en niet per scene verspringen.
LIGHT_X = 0.72


def render_story_scene(spec: dict[str, Any], size: tuple[int, int], seed: int = 0) -> Image.Image:
    """Bouwt één beeld op uit een scene-spec.

    Verwacht `setting` en `time`; al het andere is optioneel. Onbekende
    waarden vallen terug op iets redelijks, zodat een script nooit een
    zwart beeld kan opleveren.
    """
    setting = spec.get("setting", "hills")
    if setting not in SETTINGS:
        setting = "hills"
    tijd = spec.get("time", "night")
    if tijd not in SKIES:
        tijd = "night"

    canvas = sky_gradient(size, tijd).convert("RGBA")

    if tijd in NIGHTS:
        add_stars(canvas, seed, count=170 if tijd != "underworld" else 40)
        if tijd != "underworld":
            add_moon(canvas, x=LIGHT_X, y=0.17, phase=spec.get("moon_phase", 0.12))
    elif tijd in GOLDEN:
        kleur = "#F5B36E" if tijd == "dusk" else "#F7D08A"
        add_sun(canvas, x=LIGHT_X, y=0.60, color=kleur)

    draw_landscape(canvas, setting, tijd, seed, light_x=LIGHT_X, skip_last=True)

    onderwerpen = spec.get("subjects", [])[:6]
    for onderwerp in onderwerpen:
        if float(onderwerp.get("depth", 0.8)) < 0.92:
            place_silhouette(canvas, onderwerp, tijd, setting)

    draw_landscape(canvas, setting, tijd, seed, light_x=LIGHT_X, only_last=True)

    # Wie heel dichtbij staat hoort vóór de voorste laag.
    for onderwerp in onderwerpen:
        if float(onderwerp.get("depth", 0.8)) >= 0.92:
            place_silhouette(canvas, onderwerp, tijd, setting)

    weer = spec.get("weather")
    if weer == "mist":
        _, nevel = scene_colors(tijd)
        add_mist(canvas, horizon_of(setting) + 0.10, nevel, seed, 0.75)
    elif weer == "rain":
        add_rain(canvas, seed)
    elif weer == "snow":
        add_snow(canvas, seed)

    add_vignette(canvas, float(spec.get("vignette", 0.55)))

    titel = (spec.get("title") or {}).get("text")
    if titel:
        draw_title(canvas, titel, (spec.get("subtitle") or {}).get("text", ""))
    elif spec.get("caption"):
        draw_caption(canvas, str(spec["caption"]))

    return canvas.convert("RGB")


def available_settings() -> list[str]:
    return sorted(SETTINGS)


def available_times() -> list[str]:
    return sorted(SKIES)


def available_weather() -> list[str]:
    return ["none", *sorted(WEATHER)]
