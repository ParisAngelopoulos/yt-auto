"""Bouwt complete beelden van 1920x1080 uit een visual-spec.

Een spec is een dict die de scriptschrijver oplevert, bijvoorbeeld:

    {"bg": {"style": "gradient", "top": "#DCEEFB", "bottom": "#F6E4C8"},
     "layout": "hero",
     "objects": [{"draw": "duck", "color": "#F4CE47", "scale": 1.0}],
     "title": {"text": "YELLOW"}}

De renderer weet niets van lesinhoud; hij tekent alleen wat er gevraagd wordt.
Daardoor kan zowel het sjabloon als Claude dezelfde specs opleveren.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import ROOT
from .objects import render_object
from .palette import INK, WHITE, readable_ink, shade, to_rgb

FONT_DIR = ROOT / "assets" / "fonts"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


@lru_cache(maxsize=64)
def load_font(size: int, family: str = "Baloo2") -> ImageFont.FreeTypeFont:
    """Rond, vriendelijk lettertype. Valt terug op een systeemfont als het mist."""
    candidate = FONT_DIR / f"{family}.ttf"
    path = str(candidate) if candidate.exists() else FALLBACK_FONT
    font = ImageFont.truetype(path, size)
    try:                                    # Baloo2 is een variabel font
        font.set_variation_by_axes([700])   # 700 = bold
    except (AttributeError, OSError):
        pass
    return font


# ---------------------------------------------------------------------------
#  Achtergrond
# ---------------------------------------------------------------------------


def gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    """Verticaal verloop. Wordt klein getekend en opgeschaald: veel sneller."""
    w, h = size
    strip = Image.new("RGB", (1, h))
    t, b = to_rgb(top), to_rgb(bottom)
    px = strip.load()
    for y in range(h):
        f = y / max(1, h - 1)
        px[0, y] = (
            round(t[0] + (b[0] - t[0]) * f),
            round(t[1] + (b[1] - t[1]) * f),
            round(t[2] + (b[2] - t[2]) * f),
        )
    return strip.resize(size, Image.BILINEAR)


def draw_backdrop(img: Image.Image, spec: dict, seed: int) -> None:
    """Zachte heuvels, wolken en stipjes. Geeft diepte zonder af te leiden."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed)
    bottom = to_rgb(spec.get("bottom", "#F6E4C8"))

    # heuvels
    for i, (scale, alpha) in enumerate(((1.00, 40), (0.72, 70))):
        hill_h = h * (0.26 * scale)
        cy = h - hill_h * 0.35 + i * h * 0.04
        d.ellipse(
            [-w * 0.15 + i * w * 0.2, cy, w * 1.15 - i * w * 0.1, cy + hill_h * 3],
            fill=(*shade(bottom, -0.10 - i * 0.08), alpha),
        )

    # wolken
    for _ in range(3):
        cx = rng.uniform(0.05, 0.95) * w
        cy = rng.uniform(0.06, 0.26) * h
        r = rng.uniform(0.035, 0.06) * w
        for dx, dy, m in ((-0.9, 0.15, 0.75), (0, 0, 1.0), (0.95, 0.2, 0.7)):
            d.ellipse(
                [cx + dx * r - r * m, cy + dy * r - r * m * 0.8,
                 cx + dx * r + r * m, cy + dy * r + r * m * 0.8],
                fill=(255, 255, 255, 105),
            )

    # stipjes
    for _ in range(22):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.75)
        r = rng.uniform(3, 7)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 70))


# ---------------------------------------------------------------------------
#  Tekst
# ---------------------------------------------------------------------------


def text_pill(
    img: Image.Image,
    text: str,
    cy: int,
    font_size: int,
    fill=WHITE,
    ink=INK,
    max_width_frac: float = 0.86,
) -> tuple[int, int]:
    """Tekst in een afgeronde witte balk. Leest op elke achtergrond."""
    w, h = img.size
    font = load_font(font_size)
    d = ImageDraw.Draw(img, "RGBA")

    # krimp tot het past
    while font_size > 24:
        box = d.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= w * max_width_frac - font_size:
            break
        font_size = int(font_size * 0.92)
        font = load_font(font_size)

    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = font_size * 0.55, font_size * 0.30
    x0, x1 = w / 2 - tw / 2 - pad_x, w / 2 + tw / 2 + pad_x
    y0, y1 = cy - th / 2 - pad_y, cy + th / 2 + pad_y
    radius = (y1 - y0) / 2

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x0, y0 + font_size * 0.10, x1, y1 + font_size * 0.10], radius, fill=(0, 0, 0, 46)
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(font_size * 0.10)))

    d.rounded_rectangle([x0, y0, x1, y1], radius, fill=fill)
    d.text((w / 2, cy), text, font=font, fill=ink, anchor="mm")
    return int(y0), int(y1)


# ---------------------------------------------------------------------------
#  Versiering
# ---------------------------------------------------------------------------

CONFETTI_COLORS = ["#E8483F", "#F2913D", "#F4CE47", "#5BB85C", "#4A90D9", "#9B6DC4", "#F08BB4"]


def draw_confetti(img: Image.Image, seed: int, amount: int = 34) -> None:
    """Feestelijke snippers langs de randen, nooit over het midden."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed + 99)
    for _ in range(amount):
        x = rng.choice([rng.uniform(0.02, 0.22), rng.uniform(0.78, 0.98)]) * w
        y = rng.uniform(0.04, 0.94) * h
        s = rng.uniform(10, 22)
        color = (*to_rgb(rng.choice(CONFETTI_COLORS)), 235)
        pts = [(-s, -s * 0.45), (s, -s * 0.45), (s, s * 0.45), (-s, s * 0.45)]
        a = math.radians(rng.uniform(0, 180))
        d.polygon(
            [(x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a))
             for px, py in pts],
            fill=color,
        )


def draw_glow(img: Image.Image, cx: int, cy: int, radius: int) -> None:
    """Zachte lichtvlek om het juiste antwoord in de zoekronde.

    Eerst een wazige warme vlek, daarna een scherpe witte ring. De vlek
    alleen verzuipt in een groene achtergrond; de ring geeft de rand terug.
    """
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse(
        [cx - radius * 1.12, cy - radius * 1.12, cx + radius * 1.12, cy + radius * 1.12],
        fill=(255, 236, 150, 190),
    )
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(radius * 0.20)))

    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255, 245), width=max(4, int(radius * 0.075)),
    )
    img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(radius * 0.012)))


def draw_question_mark(img: Image.Image) -> None:
    """Vraagteken rechtsboven tijdens een vraagscene."""
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    r = int(h * 0.085)
    cx, cy = int(w * 0.90), int(h * 0.14)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 235), outline=INK, width=6)
    d.text((cx, cy + 2), "?", font=load_font(int(r * 1.5)), fill=INK, anchor="mm")


# ---------------------------------------------------------------------------
#  Layouts
# ---------------------------------------------------------------------------


def _paste(canvas: Image.Image, tile: Image.Image, cx: int, cy: int) -> None:
    canvas.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))


def _obj(spec: dict, size: int) -> Image.Image:
    tile = render_object(spec["draw"], size, spec.get("color"))
    rot = spec.get("rot", 0)
    if rot:
        tile = tile.rotate(rot, resample=Image.BICUBIC, expand=False)
    return tile


def layout_title(canvas: Image.Image, spec: dict, seed: int) -> None:
    w, h = canvas.size
    title = spec.get("title", {}).get("text", "")
    subtitle = spec.get("subtitle", {}).get("text", "")

    cy = int(h * (0.40 if subtitle else 0.46))
    if title:
        text_pill(canvas, title, cy, int(h * 0.155))
    if subtitle:
        text_pill(canvas, subtitle, int(h * 0.60), int(h * 0.070),
                  fill=(255, 255, 255, 210))

    for obj in spec.get("objects", []):
        size = int(h * 0.42 * obj.get("scale", 1.0))
        _paste(canvas, _obj(obj, size), int(obj.get("x", 0.5) * w), int(obj.get("y", 0.80) * h))


def layout_hero(canvas: Image.Image, spec: dict, seed: int) -> None:
    """Eén groot figuur in beeld, met het woord eronder."""
    w, h = canvas.size
    objects = spec.get("objects", [])
    if not objects:
        return
    title = spec.get("title", {}).get("text")

    size = int(h * 0.64 * objects[0].get("scale", 1.0))
    cy = int(h * (0.44 if title else 0.50))
    _paste(canvas, _obj(objects[0], size), w // 2, cy)

    if title:
        text_pill(canvas, title, int(h * 0.83), int(h * 0.135))


def layout_row(canvas: Image.Image, spec: dict, seed: int) -> None:
    """Meerdere figuren naast elkaar. highlight markeert het juiste antwoord."""
    w, h = canvas.size
    objects = spec.get("objects", [])
    if not objects:
        return
    count = len(objects)
    highlight = spec.get("highlight")

    slot = w / (count + 0.6)
    size = int(min(slot * 0.92, h * 0.54))
    cy = int(h * 0.50)

    for i, obj in enumerate(objects):
        cx = int(w * 0.5 + (i - (count - 1) / 2) * slot)
        scale = obj.get("scale", 1.0)
        tile_size = int(size * scale)
        if highlight == i:
            draw_glow(canvas, cx, cy, int(tile_size * 0.62))
            tile_size = int(tile_size * 1.12)
        _paste(canvas, _obj(obj, tile_size), cx, cy)

    title = spec.get("title", {}).get("text")
    if title:
        text_pill(canvas, title, int(h * 0.86), int(h * 0.105))


def layout_count(canvas: Image.Image, spec: dict, seed: int) -> None:
    """Tellen: N figuren in een raster plus een groot cijfer."""
    w, h = canvas.size
    objects = spec.get("objects", [])
    number = spec.get("count", len(objects))
    if not objects:
        return

    # Raster dat het aantal netjes verdeelt: max 5 per rij.
    per_row = min(5, max(1, math.ceil(len(objects) / math.ceil(len(objects) / 5))))
    rows = math.ceil(len(objects) / per_row)
    size = int(min(w * 0.66 / per_row, h * 0.58 / rows))

    left = w * 0.36
    field_w = w - left - w * 0.05
    for i, obj in enumerate(objects):
        r, c = divmod(i, per_row)
        in_row = min(per_row, len(objects) - r * per_row)
        cx = left + field_w / 2 + (c - (in_row - 1) / 2) * size * 1.06
        cy = h * 0.46 + (r - (rows - 1) / 2) * size * 1.06
        _paste(canvas, _obj(obj, size), int(cx), int(cy))

    # cijferbadge links
    d = ImageDraw.Draw(canvas, "RGBA")
    r = int(h * 0.155)
    cx, cy = int(w * 0.17), int(h * 0.46)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 240), outline=INK, width=8)
    d.text((cx, cy + 4), str(number), font=load_font(int(r * 1.35)), fill=INK, anchor="mm")

    title = spec.get("title", {}).get("text")
    if title and str(title) != str(number):
        text_pill(canvas, str(title), int(h * 0.86), int(h * 0.10))


LAYOUTS = {
    "title": layout_title,
    "hero": layout_hero,
    "row": layout_row,
    "count": layout_count,
}


# ---------------------------------------------------------------------------
#  Publiek
# ---------------------------------------------------------------------------


def render_scene(spec: dict, size: tuple[int, int], seed: int = 0) -> Image.Image:
    """Bouwt één compleet beeld. Levert RGB op, klaar om als PNG te bewaren."""
    bg = spec.get("bg", {})
    canvas = gradient(size, bg.get("top", "#DCEEFB"), bg.get("bottom", "#F6E4C8")).convert("RGBA")
    draw_backdrop(canvas, bg, seed)

    layout = LAYOUTS.get(spec.get("layout", "hero"), layout_hero)
    layout(canvas, spec, seed)

    if spec.get("question") or spec.get("dim"):
        draw_question_mark(canvas)
    if spec.get("confetti"):
        draw_confetti(canvas, seed)

    return canvas.convert("RGB")
