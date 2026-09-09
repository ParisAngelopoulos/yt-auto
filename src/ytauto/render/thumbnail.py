"""Thumbnail van 1280x720.

Voor deze doelgroep klikt de ouder, maar herkent het kind het plaatje.
Daarom: één groot figuur, één kort woord, veel contrast en geen tekst die
je moet lezen om te snappen waar het over gaat.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..scripting.blueprint import Blueprint
from .objects import render_object
from .palette import INK, to_rgb
from .scene import gradient, load_font

SIZE = (1280, 720)


def build_thumbnail(bp: Blueprint, out_path: Path) -> Path:
    width, height = SIZE
    canvas = gradient(SIZE, bp.backdrop_top, bp.backdrop_bottom).convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # zachte grondtoon onderin, zodat het figuur niet zweeft
    draw.ellipse([-width * 0.2, height * 0.62, width * 1.2, height * 1.6],
                 fill=(*to_rgb(bp.backdrop_bottom), 120))

    items = bp.items[:5] or []
    if items:
        hero = items[0]
        size = int(height * 0.66)
        tile = render_object(hero.draw, size, hero.color)
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 70), (int(width * 0.30) - size // 2 + 8,
                                     int(height * 0.44) - size // 2 + 16), tile)
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
        canvas.alpha_composite(tile, (int(width * 0.30) - size // 2,
                                      int(height * 0.44) - size // 2))

        # kleine rij metgezellen rechtsonder
        for i, item in enumerate(items[1:4]):
            small = render_object(item.draw, int(height * 0.20), item.color)
            canvas.alpha_composite(small, (int(width * 0.60) + i * int(width * 0.12),
                                           int(height * 0.66)))

    headline = _headline(bp)
    font_size = int(height * 0.155)
    font = load_font(font_size)
    while font_size > 40 and draw.textlength(headline, font=font) > width * 0.60:
        font_size = int(font_size * 0.92)
        font = load_font(font_size)

    cx, cy = int(width * 0.68), int(height * 0.30)
    box = draw.textbbox((cx, cy), headline, font=font, anchor="mm")
    pad = font_size * 0.34
    draw.rounded_rectangle(
        [box[0] - pad, box[1] - pad * 0.7, box[2] + pad, box[3] + pad * 0.7],
        radius=int(pad), fill=(255, 255, 255, 242),
    )
    draw.text((cx, cy), headline, font=font, fill=INK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, quality=90, optimize=True)
    return out_path


def _headline(bp: Blueprint) -> str:
    """Kort en in hoofdletters. Twee regels als het niet op één past."""
    words = {
        "colors": "LEARN\nCOLORS",
        "counting": "LET'S\nCOUNT!",
        "shapes": "LEARN\nSHAPES",
    }.get(bp.lesson_kind)
    if words:
        return words.replace("\n", " ")
    return "LEARN " + (bp.items[0].label if bp.items else "WITH ME")
