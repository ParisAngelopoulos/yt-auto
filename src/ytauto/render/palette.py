"""Kleurgereedschap: omrekenen, lichter/donkerder maken, leesbaar contrast."""

from __future__ import annotations

RGB = tuple[int, int, int]

# Donkerbruin in plaats van zwart. Zwarte lijnen ogen hard; deze tint is
# zachter voor jonge kijkers en houdt het contrast ruim voldoende.
INK: RGB = (58, 44, 38)
WHITE: RGB = (255, 255, 255)


def to_rgb(color: str | RGB) -> RGB:
    if isinstance(color, tuple):
        return color
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def to_hex(color: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*color)


def shade(color: str | RGB, amount: float) -> RGB:
    """amount < 0 maakt donkerder, > 0 lichter. Bereik -1 tot 1."""
    r, g, b = to_rgb(color)
    if amount >= 0:
        return (
            round(r + (255 - r) * amount),
            round(g + (255 - g) * amount),
            round(b + (255 - b) * amount),
        )
    factor = 1 + amount
    return (round(r * factor), round(g * factor), round(b * factor))


def relative_luminance(color: str | RGB) -> float:
    """Waargenomen helderheid, 0 (zwart) tot 1 (wit). Volgt sRGB/WCAG."""
    channels = []
    for value in to_rgb(color):
        c = value / 255.0
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str | RGB, b: str | RGB) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def readable_ink(background: str | RGB) -> RGB:
    """Kiest de tekstkleur die het best leest op deze achtergrond."""
    return INK if contrast_ratio(background, INK) >= contrast_ratio(background, WHITE) else WHITE
