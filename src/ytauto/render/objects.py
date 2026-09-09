"""Tekenbibliotheek: elk figuur wordt als losse RGBA-tegel gerenderd.

Alles wordt op een vergroot doek getekend en daarna verkleind. Pillow tekent
zelf zonder antialiasing; door 3x te vergroten en met LANCZOS terug te
schalen worden randen glad. Dat is de reden dat figuren als losse tegels
gemaakt worden in plaats van direct op de achtergrond.

Coordinaten zijn genormaliseerd: 0 is links/boven, 1 is rechts/onder van de
tegel. Een figuur is dus onafhankelijk van de uiteindelijke resolutie.
"""

from __future__ import annotations

import math
from typing import Callable

from PIL import Image, ImageDraw

from .palette import INK, RGB, shade, to_rgb

SUPERSAMPLE = 3
STROKE = 0.016          # lijndikte t.o.v. tegelbreedte


# ---------------------------------------------------------------------------
#  Pen
# ---------------------------------------------------------------------------


class Pen:
    """Tekent met genormaliseerde coordinaten op een vergroot doek."""

    def __init__(self, px: int) -> None:
        self.px = px
        self.img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    # -- omrekenen --
    def _x(self, v: float) -> float:
        return v * self.px

    def _w(self, v: float) -> int:
        return max(1, round(v * self.px))

    @property
    def stroke(self) -> int:
        return self._w(STROKE)

    # -- vormen --
    def ellipse(self, cx, cy, rx, ry, fill, outline=INK, width=None):
        box = [self._x(cx - rx), self._x(cy - ry), self._x(cx + rx), self._x(cy + ry)]
        self.d.ellipse(box, fill=fill, outline=outline,
                       width=self.stroke if width is None else self._w(width))

    def circle(self, cx, cy, r, fill, outline=INK, width=None):
        self.ellipse(cx, cy, r, r, fill, outline, width)

    def polygon(self, points, fill, outline=INK, width=None):
        pts = [(self._x(x), self._x(y)) for x, y in points]
        self.d.polygon(pts, fill=fill, outline=outline,
                       width=self.stroke if width is None else self._w(width))

    def rrect(self, x0, y0, x1, y1, radius, fill, outline=INK, width=None):
        box = [self._x(x0), self._x(y0), self._x(x1), self._x(y1)]
        self.d.rounded_rectangle(box, radius=self._x(radius), fill=fill, outline=outline,
                                 width=self.stroke if width is None else self._w(width))

    def line(self, points, fill=INK, width=STROKE):
        pts = [(self._x(x), self._x(y)) for x, y in points]
        self.d.line(pts, fill=fill, width=self._w(width), joint="curve")

    def arc(self, cx, cy, rx, ry, start, end, fill=INK, width=STROKE):
        box = [self._x(cx - rx), self._x(cy - ry), self._x(cx + rx), self._x(cy + ry)]
        self.d.arc(box, start, end, fill=fill, width=self._w(width))


def rotate_points(points, cx: float, cy: float, degrees: float):
    rad = math.radians(degrees)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a))
    return out


def star_points(cx, cy, outer, inner, n=5, rotation=-90.0):
    pts = []
    for i in range(n * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(rotation + i * 180.0 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------------------
#  Gezichtjes: gedeelde onderdelen
# ---------------------------------------------------------------------------


def eyes(pen: Pen, cx, cy, spread, r):
    for sx in (-1, 1):
        ex = cx + sx * spread
        pen.circle(ex, cy, r, INK, outline=None)
        pen.circle(ex + r * 0.34, cy - r * 0.36, r * 0.34, (255, 255, 255), outline=None)


def smile(pen: Pen, cx, cy, w, h=None):
    h = h or w * 0.8
    pen.arc(cx, cy, w, h, 15, 165, INK, STROKE * 0.9)


def blush(pen: Pen, cx, cy, spread, r, color=(244, 160, 170)):
    for sx in (-1, 1):
        pen.ellipse(cx + sx * spread, cy, r, r * 0.66, color, outline=None)


def ear_round(pen: Pen, cx, cy, r, fill, inner=None):
    pen.circle(cx, cy, r, fill)
    if inner:
        pen.circle(cx, cy, r * 0.52, inner, outline=None)


def ear_pointy(pen: Pen, cx, cy, size, fill, inner=None, flip=1):
    tip = (cx + flip * size * 0.15, cy - size)
    pts = [(cx - size * 0.62, cy + size * 0.42), tip, (cx + size * 0.62, cy + size * 0.42)]
    pen.polygon(pts, fill)
    if inner:
        pen.polygon([(cx - size * 0.3, cy + size * 0.22),
                     (cx + flip * size * 0.1, cy - size * 0.52),
                     (cx + size * 0.3, cy + size * 0.22)], inner, outline=None)


def ear_long(pen: Pen, cx, cy, w, h, fill, inner=None, tilt=0.0):
    pts = rotate_points(
        [(cx - w, cy), (cx, cy - h), (cx + w, cy), (cx, cy + h * 0.25)], cx, cy, tilt
    )
    pen.polygon(pts, fill)
    if inner:
        pts_in = rotate_points(
            [(cx - w * 0.5, cy), (cx, cy - h * 0.72), (cx + w * 0.5, cy), (cx, cy + h * 0.1)],
            cx, cy, tilt,
        )
        pen.polygon(pts_in, inner, outline=None)


# ---------------------------------------------------------------------------
#  Register
# ---------------------------------------------------------------------------

DrawFn = Callable[[Pen, RGB], None]
REGISTRY: dict[str, DrawFn] = {}
NATURAL: dict[str, str] = {}


def shape(name: str, natural: str | None = None):
    """Registreert een tekenfunctie onder een naam uit curriculum.yaml."""

    def decorate(fn: DrawFn) -> DrawFn:
        REGISTRY[name] = fn
        if natural:
            NATURAL[name] = natural
        return fn

    return decorate


# ---------------------------------------------------------------------------
#  Meetkundige vormen  --  de kleur is hier de leerstof, dus geen eigen kleur
# ---------------------------------------------------------------------------


@shape("circle")
def _circle(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.5, 0.40, c)


@shape("square")
def _square(p: Pen, c: RGB) -> None:
    p.rrect(0.12, 0.12, 0.88, 0.88, 0.05, c)


@shape("triangle")
def _triangle(p: Pen, c: RGB) -> None:
    p.polygon([(0.5, 0.11), (0.91, 0.85), (0.09, 0.85)], c)


@shape("star")
def _star(p: Pen, c: RGB) -> None:
    p.polygon(star_points(0.5, 0.52, 0.44, 0.185), c)


@shape("heart")
def _heart(p: Pen, c: RGB) -> None:
    # Parametrische hartkromme: levert één gesloten vorm op, zodat de
    # omlijning netjes rondom loopt in plaats van dwars door het midden.
    pts = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.5 + x / 40.0, 0.5 - y / 40.0))
    p.polygon(pts, c)


@shape("rectangle")
def _rectangle(p: Pen, c: RGB) -> None:
    p.rrect(0.06, 0.27, 0.94, 0.73, 0.04, c)


@shape("oval")
def _oval(p: Pen, c: RGB) -> None:
    p.ellipse(0.5, 0.5, 0.44, 0.30, c)


@shape("diamond")
def _diamond(p: Pen, c: RGB) -> None:
    p.polygon([(0.5, 0.07), (0.90, 0.5), (0.5, 0.93), (0.10, 0.5)], c)


# ---------------------------------------------------------------------------
#  Voorwerpen
# ---------------------------------------------------------------------------


@shape("balloon", "#E8483F")
def _balloon(p: Pen, c: RGB) -> None:
    p.line([(0.5, 0.78), (0.44, 0.86), (0.55, 0.93)], INK, STROKE * 0.7)
    p.ellipse(0.5, 0.44, 0.32, 0.37, c)
    p.polygon([(0.46, 0.78), (0.54, 0.78), (0.5, 0.85)], c)
    p.ellipse(0.38, 0.30, 0.07, 0.10, shade(c, 0.55), outline=None)


@shape("bubble", "#7FD2F0")
def _bubble(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.5, 0.40, shade(c, 0.45))
    p.arc(0.5, 0.5, 0.30, 0.30, 190, 265, (255, 255, 255), STROKE * 1.4)
    p.circle(0.34, 0.33, 0.075, (255, 255, 255), outline=None)


@shape("block", "#F2913D")
def _block(p: Pen, c: RGB) -> None:
    # Blokje in schuine projectie: bovenvlak lichter, zijvlak donkerder.
    p.polygon([(0.16, 0.36), (0.5, 0.18), (0.84, 0.36), (0.5, 0.54)], shade(c, 0.30))
    p.polygon([(0.16, 0.36), (0.5, 0.54), (0.5, 0.88), (0.16, 0.70)], c)
    p.polygon([(0.84, 0.36), (0.84, 0.70), (0.5, 0.88), (0.5, 0.54)], shade(c, -0.22))


@shape("ball", "#4A90D9")
def _ball(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.5, 0.40, c)
    p.arc(0.5, 0.5, 0.40, 0.40, 200, 340, shade(c, 0.55), STROKE * 2.2)
    p.arc(0.5, 0.72, 0.38, 0.34, 200, 340, shade(c, -0.25), STROKE * 2.0)


@shape("car", "#E8483F")
def _car(p: Pen, c: RGB) -> None:
    p.rrect(0.28, 0.30, 0.76, 0.56, 0.09, c)                  # cabine
    p.rrect(0.08, 0.48, 0.92, 0.76, 0.11, c)                  # carrosserie
    p.rrect(0.33, 0.35, 0.52, 0.52, 0.04, (214, 238, 250))    # ruit
    p.rrect(0.56, 0.35, 0.72, 0.52, 0.04, (214, 238, 250))
    for wx in (0.28, 0.72):
        p.circle(wx, 0.78, 0.11, (72, 66, 64))
        p.circle(wx, 0.78, 0.045, (216, 216, 216), outline=None)


@shape("bus", "#F4CE47")
def _bus(p: Pen, c: RGB) -> None:
    p.rrect(0.07, 0.22, 0.93, 0.74, 0.10, c)
    for x0 in (0.13, 0.35, 0.57):
        p.rrect(x0, 0.30, x0 + 0.17, 0.48, 0.03, (214, 238, 250))
    p.rrect(0.78, 0.30, 0.90, 0.55, 0.03, (214, 238, 250))
    for wx in (0.28, 0.72):
        p.circle(wx, 0.78, 0.105, (72, 66, 64))
        p.circle(wx, 0.78, 0.042, (216, 216, 216), outline=None)


@shape("train", "#5BB85C")
def _train(p: Pen, c: RGB) -> None:
    p.rrect(0.08, 0.44, 0.62, 0.74, 0.06, c)                  # ketel
    p.rrect(0.60, 0.26, 0.92, 0.74, 0.07, shade(c, -0.15))    # cabine
    p.rrect(0.65, 0.32, 0.87, 0.50, 0.03, (214, 238, 250))
    p.rrect(0.14, 0.28, 0.28, 0.46, 0.02, (72, 66, 64))       # schoorsteen
    p.ellipse(0.21, 0.20, 0.11, 0.07, (236, 236, 236))        # stoom
    for wx in (0.22, 0.46, 0.76):
        p.circle(wx, 0.80, 0.085, (72, 66, 64))


@shape("boat", "#4A90D9")
def _boat(p: Pen, c: RGB) -> None:
    p.line([(0.5, 0.18), (0.5, 0.66)], INK, STROKE * 1.2)
    p.polygon([(0.53, 0.20), (0.85, 0.60), (0.53, 0.60)], shade(c, 0.45))   # zeil
    p.polygon([(0.47, 0.24), (0.47, 0.60), (0.20, 0.60)], (255, 255, 255))
    p.polygon([(0.06, 0.62), (0.94, 0.62), (0.80, 0.86), (0.20, 0.86)], c)  # romp
    p.arc(0.5, 0.90, 0.42, 0.10, 190, 350, shade("#4A90D9", 0.30), STROKE * 1.4)


@shape("rocket", "#E8483F")
def _rocket(p: Pen, c: RGB) -> None:
    p.polygon([(0.5, 0.06), (0.70, 0.40), (0.30, 0.40)], shade(c, -0.20))  # neus
    p.rrect(0.32, 0.36, 0.68, 0.76, 0.08, (245, 245, 248))                 # romp
    p.polygon([(0.32, 0.58), (0.14, 0.84), (0.32, 0.78)], c)               # vinnen
    p.polygon([(0.68, 0.58), (0.86, 0.84), (0.68, 0.78)], c)
    p.circle(0.5, 0.52, 0.10, (140, 210, 240))
    p.polygon([(0.42, 0.76), (0.58, 0.76), (0.5, 0.95)], (244, 176, 66))   # vlam


@shape("plane", "#4A90D9")
def _plane(p: Pen, c: RGB) -> None:
    p.ellipse(0.5, 0.50, 0.42, 0.13, (245, 245, 248))                      # romp
    p.polygon([(0.44, 0.48), (0.62, 0.16), (0.72, 0.16), (0.60, 0.48)], c) # vleugel
    p.polygon([(0.44, 0.52), (0.62, 0.84), (0.72, 0.84), (0.60, 0.52)], shade(c, -0.15))
    p.polygon([(0.10, 0.48), (0.20, 0.26), (0.28, 0.26), (0.24, 0.48)], c) # staart
    for wx in (0.55, 0.68):
        p.circle(wx, 0.50, 0.045, (140, 210, 240))


@shape("kite", "#9B6DC4")
def _kite(p: Pen, c: RGB) -> None:
    p.line([(0.5, 0.68), (0.40, 0.80), (0.58, 0.90)], INK, STROKE * 0.7)
    p.polygon([(0.5, 0.05), (0.86, 0.40), (0.5, 0.70), (0.14, 0.40)], c)
    p.line([(0.5, 0.05), (0.5, 0.70)], shade(c, -0.30), STROKE * 0.8)
    p.line([(0.14, 0.40), (0.86, 0.40)], shade(c, -0.30), STROKE * 0.8)
    for i, y in enumerate((0.79, 0.87)):
        p.ellipse(0.42 + i * 0.11, y, 0.05, 0.035, (244, 206, 71))


@shape("cookie", "#C98A4B")
def _cookie(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.5, 0.40, c)
    chips = [(0.38, 0.36), (0.62, 0.40), (0.50, 0.56), (0.34, 0.62), (0.66, 0.64)]
    for cx, cy in chips:
        p.circle(cx, cy, 0.055, (86, 58, 42), outline=None)


@shape("cupcake", "#F08BB4")
def _cupcake(p: Pen, c: RGB) -> None:
    p.polygon([(0.24, 0.56), (0.76, 0.56), (0.68, 0.92), (0.32, 0.92)], (238, 176, 122))
    for x in (0.40, 0.50, 0.60):
        p.line([(x, 0.58), (x - 0.02, 0.90)], shade((238, 176, 122), -0.25), STROKE * 0.8)
    p.ellipse(0.5, 0.50, 0.30, 0.16, c)                       # glazuur
    p.ellipse(0.5, 0.38, 0.22, 0.14, shade(c, 0.20))
    p.ellipse(0.5, 0.28, 0.14, 0.10, shade(c, 0.35))
    p.circle(0.5, 0.17, 0.065, (216, 64, 72))                 # kersje


@shape("flower", "#F08BB4")
def _flower(p: Pen, c: RGB) -> None:
    p.line([(0.5, 0.52), (0.5, 0.95)], (86, 154, 84), STROKE * 1.3)
    p.ellipse(0.66, 0.76, 0.12, 0.06, (110, 178, 96))         # blad
    for i in range(6):
        a = math.radians(i * 60 - 90)
        p.ellipse(0.5 + 0.20 * math.cos(a), 0.44 + 0.20 * math.sin(a), 0.13, 0.13, c)
    p.circle(0.5, 0.44, 0.11, (244, 206, 71))


@shape("tree", "#5BB85C")
def _tree(p: Pen, c: RGB) -> None:
    p.rrect(0.43, 0.56, 0.57, 0.94, 0.03, (150, 106, 68))
    p.circle(0.34, 0.44, 0.19, shade(c, -0.10))
    p.circle(0.66, 0.44, 0.19, shade(c, -0.10))
    p.circle(0.5, 0.31, 0.23, c)


@shape("sun", "#F4CE47")
def _sun(p: Pen, c: RGB) -> None:
    for i in range(12):
        a = math.radians(i * 30)
        p.line([(0.5 + 0.30 * math.cos(a), 0.5 + 0.30 * math.sin(a)),
                (0.5 + 0.45 * math.cos(a), 0.5 + 0.45 * math.sin(a))],
               shade(c, -0.15), STROKE * 1.6)
    p.circle(0.5, 0.5, 0.29, c)
    eyes(p, 0.5, 0.46, 0.10, 0.035)
    smile(p, 0.5, 0.52, 0.12, 0.09)


# ---------------------------------------------------------------------------
#  Fruit
# ---------------------------------------------------------------------------


def _stem_and_leaf(p: Pen, x=0.5, y=0.18, leaf_side=1):
    p.line([(x, y + 0.10), (x - 0.02, y - 0.04)], (128, 92, 60), STROKE * 1.1)
    p.ellipse(x + leaf_side * 0.11, y - 0.01, 0.10, 0.055, (110, 178, 96))


@shape("apple", "#E8483F")
def _apple(p: Pen, c: RGB) -> None:
    p.ellipse(0.36, 0.60, 0.26, 0.30, c, outline=None)
    p.ellipse(0.64, 0.60, 0.26, 0.30, c, outline=None)
    p.ellipse(0.5, 0.60, 0.34, 0.31, c)
    p.ellipse(0.38, 0.48, 0.06, 0.09, shade(c, 0.45), outline=None)
    _stem_and_leaf(p, 0.5, 0.20)


@shape("banana", "#F4CE47")
def _banana(p: Pen, c: RGB) -> None:
    outer = [(0.5 + 0.40 * math.cos(math.radians(a)), 0.30 + 0.46 * math.sin(math.radians(a)))
             for a in range(15, 166, 10)]
    inner = [(0.5 + 0.28 * math.cos(math.radians(a)), 0.36 + 0.32 * math.sin(math.radians(a)))
             for a in range(165, 14, -10)]
    p.polygon(outer + inner, c)
    p.ellipse(0.12, 0.44, 0.035, 0.035, (128, 92, 60), outline=None)


@shape("orange", "#F2913D")
def _orange(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.56, 0.34, c)
    for i in range(9):
        a = math.radians(i * 40)
        p.circle(0.5 + 0.20 * math.cos(a), 0.56 + 0.20 * math.sin(a), 0.022,
                 shade(c, -0.20), outline=None)
    _stem_and_leaf(p, 0.5, 0.24)


@shape("strawberry", "#E8483F")
def _strawberry(p: Pen, c: RGB) -> None:
    p.polygon([(0.18, 0.36), (0.82, 0.36), (0.5, 0.94)], c)
    p.ellipse(0.5, 0.38, 0.32, 0.16, c)
    for sx, sy in [(0.40, 0.48), (0.60, 0.48), (0.50, 0.60), (0.36, 0.62), (0.64, 0.62), (0.50, 0.76)]:
        p.ellipse(sx, sy, 0.022, 0.030, (250, 226, 150), outline=None)
    for dx in (-0.13, 0.0, 0.13):
        p.polygon([(0.5 + dx - 0.09, 0.30), (0.5 + dx + 0.09, 0.30), (0.5 + dx, 0.14)],
                  (110, 178, 96), outline=None)


@shape("grapes", "#9B6DC4")
def _grapes(p: Pen, c: RGB) -> None:
    p.line([(0.5, 0.24), (0.5, 0.12)], (128, 92, 60), STROKE * 1.1)
    p.ellipse(0.63, 0.13, 0.10, 0.055, (110, 178, 96))
    rows = [(-2, 0.30), (-1.5, 0.30), (-1, 0.30), (-0.5, 0.30), (0, 0.30)]
    for row, (offset, _) in enumerate(rows[:4]):
        count = 4 - row
        for i in range(count):
            x = 0.5 + (i - (count - 1) / 2) * 0.17
            y = 0.34 + row * 0.15
            p.circle(x, y, 0.095, c if (i + row) % 2 else shade(c, 0.12))


@shape("pear", "#B7CF57")
def _pear(p: Pen, c: RGB) -> None:
    p.ellipse(0.5, 0.66, 0.30, 0.28, c, outline=None)
    p.ellipse(0.5, 0.42, 0.20, 0.20, c, outline=None)
    pts = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        radius = 0.20 + 0.10 * (0.5 - 0.5 * math.cos(t)) ** 1.4
        pts.append((0.5 + radius * math.sin(t) * 1.0, 0.53 - 0.28 * math.cos(t)))
    p.polygon(pts, c)
    _stem_and_leaf(p, 0.5, 0.16)


@shape("watermelon", "#5BB85C")
def _watermelon(p: Pen, c: RGB) -> None:
    p.polygon([(0.06, 0.28)] + [(0.5 + 0.44 * math.cos(math.radians(a)),
                                 0.28 + 0.62 * math.sin(math.radians(a)))
                                for a in range(0, 181, 10)], c)
    p.polygon([(0.13, 0.32)] + [(0.5 + 0.37 * math.cos(math.radians(a)),
                                 0.32 + 0.52 * math.sin(math.radians(a)))
                                for a in range(0, 181, 10)], (250, 250, 245), outline=None)
    p.polygon([(0.18, 0.36)] + [(0.5 + 0.32 * math.cos(math.radians(a)),
                                 0.36 + 0.45 * math.sin(math.radians(a)))
                                for a in range(0, 181, 10)], (232, 78, 88), outline=None)
    for sx, sy in [(0.36, 0.52), (0.50, 0.58), (0.64, 0.52), (0.43, 0.68), (0.57, 0.68)]:
        p.ellipse(sx, sy, 0.022, 0.032, (58, 44, 38), outline=None)


@shape("lemon", "#F4CE47")
def _lemon(p: Pen, c: RGB) -> None:
    p.ellipse(0.5, 0.52, 0.36, 0.26, c)
    p.polygon([(0.84, 0.52), (0.95, 0.46), (0.95, 0.58)], c)
    p.polygon([(0.16, 0.52), (0.05, 0.46), (0.05, 0.58)], c)
    p.ellipse(0.38, 0.44, 0.08, 0.05, shade(c, 0.45), outline=None)


# ---------------------------------------------------------------------------
#  Dieren
# ---------------------------------------------------------------------------


@shape("cat", "#F2A65A")
def _cat(p: Pen, c: RGB) -> None:
    ear_pointy(p, 0.30, 0.28, 0.15, c, shade(c, 0.45))
    ear_pointy(p, 0.70, 0.28, 0.15, c, shade(c, 0.45))
    p.circle(0.5, 0.50, 0.30, c)
    eyes(p, 0.5, 0.46, 0.115, 0.045)
    p.polygon([(0.46, 0.58), (0.54, 0.58), (0.5, 0.63)], (232, 140, 150))
    smile(p, 0.5, 0.62, 0.09, 0.06)
    for sx in (-1, 1):
        for dy in (-0.02, 0.02):
            p.line([(0.5 + sx * 0.15, 0.62 + dy), (0.5 + sx * 0.34, 0.60 + dy * 2.4)],
                   INK, STROKE * 0.55)
    blush(p, 0.5, 0.58, 0.22, 0.05)


@shape("dog", "#C98A4B")
def _dog(p: Pen, c: RGB) -> None:
    ear_long(p, 0.22, 0.50, 0.10, 0.20, shade(c, -0.20), tilt=-14)
    ear_long(p, 0.78, 0.50, 0.10, 0.20, shade(c, -0.20), tilt=14)
    p.circle(0.5, 0.48, 0.29, c)
    eyes(p, 0.5, 0.44, 0.115, 0.045)
    p.ellipse(0.5, 0.62, 0.16, 0.12, shade(c, 0.45))
    p.ellipse(0.5, 0.575, 0.055, 0.042, INK, outline=None)
    smile(p, 0.5, 0.62, 0.075, 0.055)
    blush(p, 0.5, 0.56, 0.24, 0.05)


@shape("cow", "#FAF6F0")
def _cow(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.32, 0.44, 0.10, 0.07, (240, 200, 205))     # oren
    for sx in (-1, 1):
        p.polygon([(0.5 + sx * 0.20, 0.26), (0.5 + sx * 0.28, 0.16),
                   (0.5 + sx * 0.14, 0.22)], (238, 226, 200))             # horens
    p.circle(0.5, 0.48, 0.30, c)
    p.ellipse(0.34, 0.36, 0.10, 0.08, (72, 64, 62), outline=None)         # vlekken
    p.ellipse(0.68, 0.56, 0.08, 0.06, (72, 64, 62), outline=None)
    eyes(p, 0.5, 0.44, 0.13, 0.045)
    p.ellipse(0.5, 0.65, 0.17, 0.11, (240, 190, 195))                     # snuit
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.06, 0.64, 0.026, 0.020, (168, 120, 128), outline=None)


@shape("pig", "#F3A9BE")
def _pig(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.polygon([(0.5 + sx * 0.30, 0.34), (0.5 + sx * 0.16, 0.22),
                   (0.5 + sx * 0.10, 0.36)], shade(c, -0.10))
    p.circle(0.5, 0.52, 0.30, c)
    eyes(p, 0.5, 0.46, 0.13, 0.042)
    p.ellipse(0.5, 0.66, 0.15, 0.11, shade(c, -0.14))
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.055, 0.66, 0.028, 0.036, (196, 122, 142), outline=None)
    blush(p, 0.5, 0.60, 0.24, 0.05, (236, 148, 168))


@shape("sheep", "#FAF6F0")
def _sheep(p: Pen, c: RGB) -> None:
    for i in range(9):
        a = math.radians(i * 40)
        p.circle(0.5 + 0.25 * math.cos(a), 0.48 + 0.25 * math.sin(a), 0.13, c)
    p.circle(0.5, 0.48, 0.22, c, outline=None)
    p.ellipse(0.5, 0.58, 0.16, 0.18, (86, 74, 70))                        # gezicht
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.18, 0.54, 0.075, 0.045, (86, 74, 70))      # oren
    eyes(p, 0.5, 0.55, 0.065, 0.030)
    smile(p, 0.5, 0.62, 0.05, 0.04)


@shape("horse", "#B07B4F")
def _horse(p: Pen, c: RGB) -> None:
    ear_pointy(p, 0.34, 0.24, 0.11, c, shade(c, 0.35))
    ear_pointy(p, 0.66, 0.24, 0.11, c, shade(c, 0.35))
    p.polygon([(0.22, 0.30), (0.34, 0.20), (0.36, 0.50), (0.24, 0.56)], (92, 66, 48))  # manen
    p.ellipse(0.52, 0.52, 0.26, 0.32, c)
    p.ellipse(0.52, 0.72, 0.17, 0.14, shade(c, 0.35))                     # snuit
    for sx in (-1, 1):
        p.ellipse(0.52 + sx * 0.055, 0.71, 0.022, 0.028, (110, 80, 62), outline=None)
    eyes(p, 0.52, 0.44, 0.115, 0.040)


@shape("chicken", "#FAF3E4")
def _chicken(p: Pen, c: RGB) -> None:
    for dx in (-0.07, 0.0, 0.07):
        p.circle(0.5 + dx, 0.20, 0.055, (216, 72, 68))                    # kam
    p.ellipse(0.5, 0.58, 0.28, 0.30, c)
    p.circle(0.5, 0.36, 0.19, c)
    eyes(p, 0.5, 0.34, 0.075, 0.032)
    p.polygon([(0.44, 0.42), (0.56, 0.42), (0.5, 0.52)], (242, 166, 60))  # snavel
    p.ellipse(0.30, 0.62, 0.09, 0.13, shade(c, -0.12))                    # vleugel
    for sx in (-1, 1):
        p.line([(0.5 + sx * 0.09, 0.86), (0.5 + sx * 0.09, 0.95)], (242, 166, 60), STROKE * 1.2)


@shape("duck", "#F4CE47")
def _duck(p: Pen, c: RGB) -> None:
    p.ellipse(0.52, 0.62, 0.30, 0.26, c)                                  # lijf
    p.circle(0.38, 0.34, 0.18, c)                                         # kop
    eyes(p, 0.36, 0.31, 0.065, 0.030)
    p.ellipse(0.19, 0.38, 0.11, 0.055, (242, 152, 60))                    # snavel
    p.ellipse(0.60, 0.62, 0.13, 0.11, shade(c, -0.16))                    # vleugel
    p.polygon([(0.78, 0.54), (0.94, 0.46), (0.88, 0.64)], shade(c, -0.10))


@shape("bear", "#B98A5E")
def _bear(p: Pen, c: RGB) -> None:
    ear_round(p, 0.26, 0.26, 0.11, c, shade(c, 0.40))
    ear_round(p, 0.74, 0.26, 0.11, c, shade(c, 0.40))
    p.circle(0.5, 0.52, 0.31, c)
    eyes(p, 0.5, 0.46, 0.12, 0.045)
    p.ellipse(0.5, 0.66, 0.16, 0.13, shade(c, 0.42))
    p.ellipse(0.5, 0.615, 0.055, 0.042, INK, outline=None)
    smile(p, 0.5, 0.665, 0.07, 0.05)


@shape("fox", "#E4813C")
def _fox(p: Pen, c: RGB) -> None:
    ear_pointy(p, 0.26, 0.26, 0.16, c, (58, 44, 38))
    ear_pointy(p, 0.74, 0.26, 0.16, c, (58, 44, 38))
    p.circle(0.5, 0.50, 0.29, c)
    p.polygon([(0.28, 0.56), (0.72, 0.56), (0.5, 0.86)], (250, 246, 240))  # snuit
    eyes(p, 0.5, 0.46, 0.125, 0.042)
    p.ellipse(0.5, 0.66, 0.045, 0.035, INK, outline=None)


@shape("lion", "#E8A33D")
def _lion(p: Pen, c: RGB) -> None:
    for i in range(12):
        a = math.radians(i * 30)
        p.circle(0.5 + 0.27 * math.cos(a), 0.52 + 0.27 * math.sin(a), 0.11,
                 (196, 122, 56))                                          # manen
    p.circle(0.5, 0.52, 0.26, c)
    eyes(p, 0.5, 0.47, 0.105, 0.040)
    p.ellipse(0.5, 0.62, 0.13, 0.10, shade(c, 0.42))
    p.polygon([(0.455, 0.585), (0.545, 0.585), (0.5, 0.625)], INK, outline=None)
    for sx in (-1, 1):
        p.line([(0.5 + sx * 0.12, 0.62), (0.5 + sx * 0.28, 0.60)], INK, STROKE * 0.55)


@shape("monkey", "#A9764F")
def _monkey(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.circle(0.5 + sx * 0.31, 0.50, 0.11, c)
        p.circle(0.5 + sx * 0.31, 0.50, 0.06, shade(c, 0.45), outline=None)
    p.circle(0.5, 0.50, 0.28, c)
    p.ellipse(0.5, 0.56, 0.22, 0.20, shade(c, 0.42))                      # gezicht
    eyes(p, 0.5, 0.45, 0.10, 0.042)
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.045, 0.575, 0.020, 0.016, INK, outline=None)
    smile(p, 0.5, 0.62, 0.085, 0.055)


@shape("frog", "#5BB85C")
def _frog(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.circle(0.5 + sx * 0.19, 0.26, 0.13, c)
        p.circle(0.5 + sx * 0.19, 0.26, 0.075, (255, 255, 255), outline=None)
        p.circle(0.5 + sx * 0.19, 0.27, 0.040, INK, outline=None)
    p.ellipse(0.5, 0.58, 0.34, 0.28, c)
    p.ellipse(0.5, 0.66, 0.20, 0.13, shade(c, 0.35), outline=None)
    smile(p, 0.5, 0.56, 0.15, 0.10)
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.30, 0.78, 0.10, 0.06, shade(c, -0.12))


@shape("owl", "#A9764F")
def _owl(p: Pen, c: RGB) -> None:
    p.polygon([(0.24, 0.30), (0.34, 0.14), (0.42, 0.28)], c)              # pluimpjes
    p.polygon([(0.76, 0.30), (0.66, 0.14), (0.58, 0.28)], c)
    p.ellipse(0.5, 0.54, 0.32, 0.36, c)
    p.ellipse(0.5, 0.62, 0.22, 0.24, shade(c, 0.35), outline=None)        # buik
    for sx in (-1, 1):
        p.circle(0.5 + sx * 0.13, 0.42, 0.115, (250, 248, 242))
        p.circle(0.5 + sx * 0.13, 0.42, 0.055, INK, outline=None)
        p.circle(0.5 + sx * 0.145, 0.405, 0.020, (255, 255, 255), outline=None)
    p.polygon([(0.455, 0.50), (0.545, 0.50), (0.5, 0.58)], (242, 166, 60))
    for sx in (-1, 1):
        p.line([(0.5 + sx * 0.07, 0.90), (0.5 + sx * 0.07, 0.95)], (242, 166, 60), STROKE * 1.2)


@shape("penguin", "#3D4A5C")
def _penguin(p: Pen, c: RGB) -> None:
    p.ellipse(0.5, 0.56, 0.30, 0.36, c)
    p.ellipse(0.5, 0.62, 0.20, 0.28, (250, 248, 242), outline=None)       # buik
    p.circle(0.5, 0.32, 0.20, c)
    p.ellipse(0.5, 0.36, 0.13, 0.13, (250, 248, 242), outline=None)
    eyes(p, 0.5, 0.31, 0.075, 0.030)
    p.polygon([(0.44, 0.38), (0.56, 0.38), (0.5, 0.46)], (242, 152, 60))
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.31, 0.58, 0.06, 0.16, shade(c, -0.15))     # vleugels
        p.ellipse(0.5 + sx * 0.11, 0.91, 0.08, 0.045, (242, 152, 60))


@shape("elephant", "#9AA7B4")
def _elephant(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.30, 0.46, 0.16, 0.19, shade(c, -0.10))     # oren
    p.circle(0.5, 0.46, 0.27, c)
    eyes(p, 0.5, 0.42, 0.12, 0.040)
    p.polygon([(0.44, 0.56), (0.56, 0.56), (0.60, 0.84), (0.52, 0.92),
               (0.44, 0.86), (0.48, 0.76)], c)                            # slurf
    for sx in (-1, 1):
        p.polygon([(0.5 + sx * 0.14, 0.62), (0.5 + sx * 0.22, 0.76),
                   (0.5 + sx * 0.16, 0.66)], (250, 248, 242))             # slagtanden


@shape("fish", "#4FC3C0")
def _fish(p: Pen, c: RGB) -> None:
    p.polygon([(0.86, 0.50), (0.98, 0.30), (0.98, 0.70)], shade(c, -0.15))  # staart
    p.ellipse(0.48, 0.50, 0.36, 0.25, c)
    p.polygon([(0.44, 0.28), (0.58, 0.14), (0.60, 0.32)], shade(c, -0.15))  # rugvin
    p.circle(0.28, 0.44, 0.055, (255, 255, 255))
    p.circle(0.275, 0.445, 0.028, INK, outline=None)
    smile(p, 0.24, 0.54, 0.055, 0.04)
    p.arc(0.62, 0.50, 0.13, 0.20, 250, 290, shade(c, -0.25), STROKE * 0.9)


@shape("bee", "#F4CE47")
def _bee(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.20, 0.28, 0.16, 0.11, (222, 240, 250))     # vleugels
    p.ellipse(0.5, 0.56, 0.30, 0.24, c)
    for dx in (-0.09, 0.06):
        p.polygon([(0.5 + dx, 0.34), (0.5 + dx + 0.09, 0.34),
                   (0.5 + dx + 0.09, 0.78), (0.5 + dx, 0.78)],
                  (72, 64, 60), outline=None)                             # strepen
    p.ellipse(0.5, 0.56, 0.30, 0.24, None, INK)
    p.circle(0.24, 0.46, 0.13, c)
    eyes(p, 0.22, 0.44, 0.05, 0.028)
    for sx in (-1, 1):
        p.line([(0.22 + sx * 0.02, 0.34), (0.20 + sx * 0.10, 0.22)], INK, STROKE * 0.7)


@shape("butterfly", "#9B6DC4")
def _butterfly(p: Pen, c: RGB) -> None:
    for sx in (-1, 1):
        p.ellipse(0.5 + sx * 0.24, 0.36, 0.21, 0.19, c)                   # bovenvleugels
        p.ellipse(0.5 + sx * 0.20, 0.66, 0.17, 0.15, shade(c, 0.28))      # ondervleugels
        p.circle(0.5 + sx * 0.26, 0.36, 0.06, shade(c, 0.55), outline=None)
    p.ellipse(0.5, 0.52, 0.045, 0.26, (86, 66, 58), outline=None)         # lijf
    for sx in (-1, 1):
        p.line([(0.5 + sx * 0.02, 0.30), (0.5 + sx * 0.12, 0.16)], INK, STROKE * 0.7)


@shape("ladybug", "#E8483F")
def _ladybug(p: Pen, c: RGB) -> None:
    p.circle(0.5, 0.54, 0.34, c)
    p.line([(0.5, 0.22), (0.5, 0.88)], INK, STROKE * 1.1)
    for sx, sy in [(0.33, 0.44), (0.67, 0.44), (0.36, 0.68), (0.64, 0.68), (0.5, 0.78)]:
        p.circle(sx, sy, 0.055, (58, 44, 38), outline=None)
    p.ellipse(0.5, 0.26, 0.20, 0.14, (72, 64, 60), outline=None)          # kop
    eyes(p, 0.5, 0.24, 0.075, 0.030)
    for sx in (-1, 1):
        p.line([(0.5 + sx * 0.06, 0.16), (0.5 + sx * 0.16, 0.06)], INK, STROKE * 0.7)


# ---------------------------------------------------------------------------
#  Renderen
# ---------------------------------------------------------------------------

_CACHE: dict[tuple[str, int, str | None], Image.Image] = {}


def available_shapes() -> list[str]:
    """Alle namen die in curriculum.yaml of in een script gebruikt mogen worden."""
    return sorted(REGISTRY)


def natural_color(name: str) -> str:
    return NATURAL.get(name, "#F4CE47")


def render_object(name: str, size: int, color: str | None = None) -> Image.Image:
    """Tekent één figuur als RGBA-tegel van size x size pixels.

    color=None gebruikt de natuurlijke kleur van het figuur. Resultaten
    worden gecached: binnen één video komt hetzelfde figuur tientallen keren
    terug en opnieuw tekenen op 3x formaat is het duurste in de pipeline.
    """
    if name not in REGISTRY:
        raise KeyError(
            f"Onbekend figuur {name!r}. Beschikbaar: {', '.join(available_shapes())}"
        )

    cache_key = (name, size, color)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    resolved = to_rgb(color) if color else to_rgb(NATURAL.get(name, "#F4CE47"))
    pen = Pen(size * SUPERSAMPLE)
    REGISTRY[name](pen, resolved)
    tile = pen.img.resize((size, size), Image.LANCZOS)

    _CACHE[cache_key] = tile
    return tile
