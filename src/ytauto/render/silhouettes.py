"""Silhouetten voor volksverhalen.

Anders dan de figuren voor de kindervideo's hebben deze geen kleur, geen
ogen en geen omlijning: het zijn vlakke vormen in één donkere tint tegen de
lucht. Dat is niet alleen makkelijker te tekenen, het is ook de juiste
stijl — een reiziger op een heuvel hoort een vorm te zijn waar de kijker
zichzelf in kan projecteren, geen personage met een gezicht.

Alles wordt daarom in één kleur getekend. De renderer bepaalt welke: hoe
dichterbij, hoe donkerder.
"""

from __future__ import annotations

import math
from typing import Callable

from PIL import Image

from .objects import SUPERSAMPLE, Pen, rotate_points, star_points
from .palette import RGB

SilhouetteFn = Callable[[Pen, RGB], None]
SILHOUETTES: dict[str, SilhouetteFn] = {}

def silhouette(naam: str):
    def registreer(fn: SilhouetteFn) -> SilhouetteFn:
        SILHOUETTES[naam] = fn
        return fn
    return registreer


def _vlak(p: Pen, punten, kleur: RGB) -> None:
    """Eén dichte vorm, zonder rand."""
    p.polygon(punten, kleur, outline=None)


# ---------------------------------------------------------------------------
#  Bouwsels
# ---------------------------------------------------------------------------


@silhouette("cottage")
def _cottage(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.10, 1.0), (0.10, 0.55), (0.50, 0.24), (0.90, 0.55), (0.90, 1.0)], c)
    _vlak(p, [(0.66, 0.46), (0.66, 0.16), (0.76, 0.16), (0.76, 0.54)], c)   # schoorsteen


@silhouette("castle")
def _castle(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.06, 1.0), (0.06, 0.52), (0.94, 0.52), (0.94, 1.0)], c)
    for x0 in (0.06, 0.22, 0.38, 0.54, 0.70, 0.86):                          # kantelen
        _vlak(p, [(x0, 0.52), (x0, 0.44), (x0 + 0.08, 0.44), (x0 + 0.08, 0.52)], c)
    for cx, top in ((0.16, 0.22), (0.84, 0.26)):                             # torens
        _vlak(p, [(cx - 0.10, 1.0), (cx - 0.10, top), (cx + 0.10, top), (cx + 0.10, 1.0)], c)
        _vlak(p, [(cx - 0.14, top), (cx, top - 0.14), (cx + 0.14, top)], c)


@silhouette("tower")
def _tower(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.24, 1.0), (0.30, 0.26), (0.70, 0.26), (0.76, 1.0)], c)
    _vlak(p, [(0.18, 0.26), (0.50, 0.02), (0.82, 0.26)], c)


@silhouette("church")
def _church(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.14, 1.0), (0.14, 0.60), (0.46, 0.40), (0.78, 0.60), (0.78, 1.0)], c)
    _vlak(p, [(0.78, 1.0), (0.78, 0.34), (0.94, 0.34), (0.94, 1.0)], c)      # toren
    _vlak(p, [(0.74, 0.34), (0.86, 0.06), (0.98, 0.34)], c)                  # spits
    _vlak(p, [(0.845, 0.06), (0.845, -0.06), (0.875, -0.06), (0.875, 0.06)], c)


@silhouette("windmill")
def _windmill(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.34, 1.0), (0.40, 0.44), (0.60, 0.44), (0.66, 1.0)], c)
    _vlak(p, [(0.36, 0.44), (0.50, 0.30), (0.64, 0.44)], c)
    for hoek in (28, 118, 208, 298):                                          # wieken
        blad = rotate_points([(0.50, 0.36), (0.53, 0.36), (0.55, 0.02), (0.48, 0.02)],
                             0.50, 0.36, hoek)
        _vlak(p, blad, c)


@silhouette("bridge")
def _bridge(p: Pen, c: RGB) -> None:
    # Stenen boogbrug: een licht gebogen dek op gedrongen pijlers. De bogen
    # zelf worden niet uitgespaard maar gesuggereerd door de pijlers; op de
    # schaal waarop dit in beeld komt leest dat beter dan echte gaten.
    dek = [(0.02, 0.56)]
    for i in range(21):
        t = i / 20
        dek.append((0.02 + t * 0.96, 0.56 - 0.10 * math.sin(math.pi * t)))
    dek += [(0.98, 0.56), (0.98, 0.66), *reversed(
        [(0.02 + i / 20 * 0.96, 0.66 - 0.10 * math.sin(math.pi * (i / 20)))
         for i in range(21)]), (0.02, 0.66)]
    _vlak(p, dek, c)
    for x, top in ((0.14, 0.62), (0.42, 0.53), (0.70, 0.55)):
        _vlak(p, [(x - 0.055, 1.0), (x - 0.045, top), (x + 0.045, top), (x + 0.055, 1.0)], c)
    for x in (0.08, 0.30, 0.52, 0.74, 0.92):                                  # leuningpaaltjes
        y = 0.56 - 0.10 * math.sin(math.pi * ((x - 0.02) / 0.96))
        _vlak(p, [(x - 0.014, y), (x - 0.014, y - 0.10), (x + 0.014, y - 0.10), (x + 0.014, y)], c)


@silhouette("well")
def _well(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.24, 1.0), (0.24, 0.62), (0.76, 0.62), (0.76, 1.0)], c)
    for x in (0.26, 0.70):
        _vlak(p, [(x, 0.62), (x, 0.24), (x + 0.05, 0.24), (x + 0.05, 0.62)], c)
    _vlak(p, [(0.16, 0.24), (0.50, 0.08), (0.84, 0.24), (0.84, 0.30), (0.50, 0.15),
              (0.16, 0.30)], c)


@silhouette("standing_stones")
def _standing_stones(p: Pen, c: RGB) -> None:
    for x, top, breedte in ((0.10, 0.30, 0.09), (0.34, 0.16, 0.10),
                            (0.60, 0.24, 0.08), (0.82, 0.36, 0.07)):
        _vlak(p, [(x - breedte, 1.0), (x - breedte * 0.75, top),
                  (x + breedte * 0.75, top - 0.03), (x + breedte, 1.0)], c)


@silhouette("campfire")
def _campfire(p: Pen, c: RGB) -> None:
    # Gekruiste blokken met een druppelvormige vlam erboven. Een vlam die
    # naar één kant omkrult leest als een haak, dus hij staat rechtop met
    # alleen een lichte zwiep in de punt.
    _vlak(p, [(0.08, 0.84), (0.92, 0.72), (0.94, 0.84), (0.10, 0.96)], c)
    _vlak(p, [(0.08, 0.72), (0.92, 0.84), (0.90, 0.96), (0.06, 0.84)], c)
    _vlak(p, [
        (0.50, 0.04), (0.60, 0.24), (0.66, 0.42), (0.68, 0.58),
        (0.64, 0.72), (0.54, 0.80), (0.42, 0.80), (0.33, 0.71),
        (0.31, 0.56), (0.36, 0.40), (0.44, 0.26),
    ], c)
    _vlak(p, [(0.50, 0.36), (0.58, 0.54), (0.54, 0.70), (0.44, 0.70),
              (0.42, 0.54)], c)


@silhouette("ship")
def _ship(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.06, 0.78), (0.94, 0.78), (0.80, 0.96), (0.20, 0.96)], c)     # romp
    _vlak(p, [(0.48, 0.76), (0.48, 0.06), (0.52, 0.06), (0.52, 0.76)], c)     # mast
    _vlak(p, [(0.52, 0.14), (0.86, 0.44), (0.52, 0.44)], c)                   # zeilen
    _vlak(p, [(0.46, 0.20), (0.16, 0.46), (0.46, 0.46)], c)


@silhouette("rowboat")
def _rowboat(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.04, 0.60), (0.96, 0.60), (0.82, 0.86), (0.18, 0.86)], c)
    _vlak(p, [(0.40, 0.58), (0.40, 0.30), (0.44, 0.30), (0.44, 0.58)], c)     # roeier
    _vlak(p, [(0.34, 0.30), (0.50, 0.22), (0.52, 0.30)], c)
    _vlak(p, [(0.52, 0.44), (0.84, 0.66), (0.86, 0.70), (0.52, 0.50)], c)     # riem


@silhouette("lighthouse")
def _lighthouse(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.22, 1.0), (0.34, 0.28), (0.66, 0.28), (0.78, 1.0)], c)
    _vlak(p, [(0.28, 0.28), (0.28, 0.16), (0.72, 0.16), (0.72, 0.28)], c)     # lantaarn
    _vlak(p, [(0.32, 0.16), (0.50, 0.03), (0.68, 0.16)], c)


@silhouette("ruin")
def _ruin(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.08, 1.0), (0.08, 0.44), (0.24, 0.34), (0.24, 1.0)], c)
    _vlak(p, [(0.32, 1.0), (0.32, 0.62), (0.46, 0.56), (0.46, 1.0)], c)
    _vlak(p, [(0.58, 1.0), (0.58, 0.30), (0.72, 0.22), (0.76, 0.66), (0.88, 0.60),
              (0.88, 1.0)], c)


@silhouette("gate")
def _gate(p: Pen, c: RGB) -> None:
    for x in (0.12, 0.72):
        _vlak(p, [(x, 1.0), (x, 0.22), (x + 0.16, 0.22), (x + 0.16, 1.0)], c)
    _vlak(p, [(0.06, 0.22), (0.94, 0.22), (0.94, 0.34), (0.06, 0.34)], c)


@silhouette("oak")
def _oak(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.43, 1.0), (0.45, 0.52), (0.55, 0.52), (0.57, 1.0)], c)       # stam
    for cx, cy, r in ((0.50, 0.34, 0.30), (0.27, 0.44, 0.19), (0.73, 0.44, 0.19),
                      (0.38, 0.22, 0.16), (0.63, 0.24, 0.15)):
        p.circle(cx, cy, r, c, outline=None)


@silhouette("dead_tree")
def _dead_tree(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.44, 1.0), (0.47, 0.34), (0.55, 0.34), (0.58, 1.0)], c)
    for begin, eind, dikte in (((0.50, 0.52), (0.16, 0.24), 0.030),
                               ((0.50, 0.44), (0.86, 0.18), 0.028),
                               ((0.50, 0.34), (0.34, 0.06), 0.022),
                               ((0.51, 0.36), (0.70, 0.08), 0.020)):
        p.line([begin, eind], c, dikte)
    for begin, eind in (((0.30, 0.32), (0.20, 0.12)), ((0.70, 0.28), (0.82, 0.10))):
        p.line([begin, eind], c, 0.014)


@silhouette("signpost")
def _signpost(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.46, 1.0), (0.46, 0.12), (0.54, 0.12), (0.54, 1.0)], c)
    _vlak(p, [(0.50, 0.20), (0.94, 0.20), (0.98, 0.28), (0.94, 0.36), (0.50, 0.36)], c)
    _vlak(p, [(0.50, 0.44), (0.14, 0.44), (0.08, 0.52), (0.14, 0.60), (0.50, 0.60)], c)


# ---------------------------------------------------------------------------
#  Figuren
#
#  Op de schaal waarop deze in beeld komen is een gezicht toch niet te zien.
#  Wat je wél leest is de houding: een gebogen rug, een uitgestoken arm, een
#  wapperende mantel. Daar zit dus het werk.
# ---------------------------------------------------------------------------


@silhouette("traveller")
def _traveller(p: Pen, c: RGB) -> None:
    p.circle(0.46, 0.10, 0.085, c, outline=None)                              # hoofd
    _vlak(p, [(0.30, 0.94), (0.34, 0.24), (0.60, 0.22), (0.68, 0.96)], c)     # mantel
    p.line([(0.72, 0.06), (0.74, 1.0)], c, 0.026)                             # staf
    _vlak(p, [(0.56, 0.30), (0.74, 0.26), (0.74, 0.34), (0.56, 0.38)], c)     # arm


@silhouette("woman")
def _woman(p: Pen, c: RGB) -> None:
    p.circle(0.50, 0.10, 0.082, c, outline=None)
    _vlak(p, [(0.40, 0.19), (0.60, 0.19), (0.72, 1.0), (0.28, 1.0)], c)       # lange rok
    _vlak(p, [(0.30, 0.28), (0.40, 0.24), (0.42, 0.52), (0.34, 0.52)], c)     # armen
    _vlak(p, [(0.60, 0.24), (0.70, 0.28), (0.66, 0.52), (0.58, 0.52)], c)


@silhouette("man")
def _man(p: Pen, c: RGB) -> None:
    p.circle(0.50, 0.10, 0.085, c, outline=None)
    _vlak(p, [(0.38, 0.19), (0.62, 0.19), (0.60, 0.56), (0.40, 0.56)], c)     # romp
    _vlak(p, [(0.40, 0.54), (0.48, 0.54), (0.46, 1.0), (0.36, 1.0)], c)       # benen
    _vlak(p, [(0.52, 0.54), (0.60, 0.54), (0.64, 1.0), (0.54, 1.0)], c)
    p.line([(0.40, 0.24), (0.30, 0.52)], c, 0.030)                            # armen
    p.line([(0.60, 0.24), (0.70, 0.52)], c, 0.030)


@silhouette("child")
def _child(p: Pen, c: RGB) -> None:
    p.circle(0.50, 0.16, 0.105, c, outline=None)                              # groter hoofd
    _vlak(p, [(0.40, 0.28), (0.60, 0.28), (0.62, 0.66), (0.38, 0.66)], c)
    _vlak(p, [(0.40, 0.64), (0.48, 0.64), (0.47, 1.0), (0.38, 1.0)], c)
    _vlak(p, [(0.52, 0.64), (0.60, 0.64), (0.62, 1.0), (0.53, 1.0)], c)
    p.line([(0.41, 0.34), (0.32, 0.58)], c, 0.026)
    p.line([(0.59, 0.34), (0.68, 0.58)], c, 0.026)


@silhouette("rider")
def _rider(p: Pen, c: RGB) -> None:
    # Eén doorlopende paardenvorm: romp, hals en kop in dezelfde omtrek, met
    # de ruiter erbovenop. Losse blokken lezen als een tafel.
    _vlak(p, [(0.14, 0.66), (0.20, 0.54), (0.60, 0.52), (0.68, 0.44),
              (0.80, 0.30), (0.92, 0.28), (0.99, 0.34), (0.88, 0.42),
              (0.80, 0.52), (0.76, 0.68), (0.70, 0.76), (0.22, 0.78),
              (0.14, 0.70)], c)
    _vlak(p, [(0.80, 0.34), (0.86, 0.22), (0.90, 0.30)], c)                   # oor
    for x, kort in ((0.24, 0.0), (0.34, 0.03), (0.60, 0.0), (0.70, 0.03)):    # benen
        _vlak(p, [(x, 0.74), (x + 0.055, 0.74), (x + 0.045, 1.0 - kort),
                  (x - 0.005, 1.0 - kort)], c)
    _vlak(p, [(0.16, 0.62), (0.04, 0.42), (0.10, 0.38), (0.20, 0.60)], c)     # staart
    p.circle(0.44, 0.24, 0.070, c, outline=None)                              # ruiter
    _vlak(p, [(0.36, 0.31), (0.53, 0.30), (0.58, 0.56), (0.34, 0.58)], c)     # mantel
    p.line([(0.52, 0.38), (0.70, 0.46)], c, 0.026)                            # arm aan teugel


@silhouette("horse")
def _horse(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.18, 0.44), (0.74, 0.42), (0.78, 0.60), (0.16, 0.62)], c)
    _vlak(p, [(0.70, 0.46), (0.86, 0.18), (0.94, 0.22), (0.80, 0.50)], c)
    _vlak(p, [(0.84, 0.14), (0.99, 0.12), (0.98, 0.26), (0.84, 0.26)], c)
    for x in (0.22, 0.34, 0.60, 0.72):
        _vlak(p, [(x, 0.58), (x + 0.06, 0.58), (x + 0.05, 1.0), (x - 0.01, 1.0)], c)
    _vlak(p, [(0.14, 0.44), (0.04, 0.24), (0.10, 0.22), (0.19, 0.42)], c)


@silhouette("wolf")
def _wolf(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.20, 0.52), (0.72, 0.50), (0.74, 0.70), (0.18, 0.72)], c)
    _vlak(p, [(0.68, 0.54), (0.84, 0.36), (0.98, 0.44), (0.80, 0.60)], c)     # kop
    _vlak(p, [(0.78, 0.40), (0.82, 0.26), (0.88, 0.38)], c)                   # oren
    _vlak(p, [(0.86, 0.38), (0.90, 0.26), (0.94, 0.40)], c)
    for x in (0.24, 0.34, 0.58, 0.68):
        _vlak(p, [(x, 0.68), (x + 0.05, 0.68), (x + 0.04, 0.96), (x - 0.01, 0.96)], c)
    _vlak(p, [(0.16, 0.54), (0.02, 0.38), (0.06, 0.32), (0.20, 0.50)], c)     # staart


@silhouette("bear")
def _bear(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.18, 0.40), (0.72, 0.38), (0.78, 0.78), (0.16, 0.80)], c)
    p.circle(0.78, 0.32, 0.15, c, outline=None)
    p.circle(0.70, 0.19, 0.055, c, outline=None)
    p.circle(0.88, 0.20, 0.055, c, outline=None)
    _vlak(p, [(0.88, 0.32), (0.99, 0.34), (0.98, 0.42), (0.88, 0.42)], c)     # snuit
    for x in (0.22, 0.58):
        _vlak(p, [(x, 0.74), (x + 0.13, 0.74), (x + 0.12, 1.0), (x - 0.01, 1.0)], c)


@silhouette("deer")
def _deer(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.22, 0.50), (0.68, 0.48), (0.72, 0.66), (0.20, 0.68)], c)
    _vlak(p, [(0.64, 0.52), (0.76, 0.28), (0.84, 0.30), (0.74, 0.56)], c)
    _vlak(p, [(0.74, 0.24), (0.90, 0.22), (0.89, 0.34), (0.74, 0.34)], c)
    for begin, eind in (((0.78, 0.24), (0.68, 0.04)), ((0.84, 0.24), (0.94, 0.04)),
                        ((0.73, 0.16), (0.62, 0.12)), ((0.89, 0.16), (0.99, 0.12))):
        p.line([begin, eind], c, 0.020)                                       # gewei
    for x in (0.26, 0.36, 0.56, 0.64):
        _vlak(p, [(x, 0.64), (x + 0.04, 0.64), (x + 0.035, 1.0), (x - 0.005, 1.0)], c)


@silhouette("fox")
def _fox(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.24, 0.56), (0.70, 0.54), (0.72, 0.72), (0.22, 0.74)], c)
    _vlak(p, [(0.66, 0.58), (0.80, 0.44), (0.96, 0.54), (0.78, 0.64)], c)
    _vlak(p, [(0.74, 0.48), (0.78, 0.32), (0.84, 0.46)], c)
    _vlak(p, [(0.82, 0.46), (0.86, 0.32), (0.90, 0.48)], c)
    for x in (0.28, 0.36, 0.58, 0.65):
        _vlak(p, [(x, 0.70), (x + 0.04, 0.70), (x + 0.035, 0.94), (x - 0.005, 0.94)], c)
    _vlak(p, [(0.22, 0.58), (0.02, 0.44), (0.02, 0.62), (0.24, 0.70)], c)     # pluimstaart


@silhouette("raven")
def _raven(p: Pen, c: RGB) -> None:
    # Zittende raaf in profiel: lijf, kop en snavel in één omtrek, met de
    # vleugel als inkeping in het lijf in plaats van een los stuk.
    _vlak(p, [(0.18, 0.62), (0.26, 0.44), (0.46, 0.34), (0.60, 0.30),
              (0.66, 0.20), (0.76, 0.16), (0.86, 0.20), (0.99, 0.26),
              (0.86, 0.30), (0.78, 0.34), (0.74, 0.44), (0.62, 0.56),
              (0.44, 0.68), (0.24, 0.72)], c)
    _vlak(p, [(0.20, 0.62), (0.02, 0.76), (0.06, 0.82), (0.30, 0.70)], c)     # staart
    _vlak(p, [(0.34, 0.48), (0.56, 0.42), (0.52, 0.60), (0.32, 0.64)], c)     # vleugel
    for x in (0.42, 0.52):
        p.line([(x, 0.68), (x - 0.01, 0.84)], c, 0.020)
        p.line([(x - 0.04, 0.84), (x + 0.03, 0.84)], c, 0.016)


@silhouette("dragon")
def _dragon(p: Pen, c: RGB) -> None:
    # Zijaanzicht, stijgend: staart linksonder, romp in het midden, hals die
    # naar rechtsboven kromt. De vleugel staat links achter de romp, weg van
    # de kop; overlappen ze elkaar dan wordt het één blob.
    _vlak(p, [
        (0.03, 0.97), (0.10, 0.86), (0.20, 0.80), (0.32, 0.78),   # staart
        (0.44, 0.76), (0.54, 0.70), (0.60, 0.60),                 # romp
        (0.64, 0.48), (0.70, 0.38), (0.78, 0.31),                 # hals
        (0.86, 0.28), (0.93, 0.30), (0.99, 0.35),                 # kop
        (0.92, 0.39), (0.84, 0.38), (0.78, 0.42),                 # kaak terug
        (0.72, 0.50), (0.68, 0.62), (0.60, 0.74),
        (0.48, 0.84), (0.32, 0.90), (0.16, 0.95),
    ], c)
    _vlak(p, [(0.84, 0.29), (0.83, 0.15), (0.92, 0.26)], c)       # horens
    _vlak(p, [(0.91, 0.28), (0.94, 0.16), (0.98, 0.30)], c)
    _vlak(p, [(0.99, 0.35), (0.99, 0.41), (0.90, 0.40)], c)       # kaak

    # vleugel: membraan met drie punten, achter de romp omhoog
    _vlak(p, [(0.52, 0.72), (0.40, 0.44), (0.24, 0.16), (0.34, 0.20),
              (0.30, 0.06), (0.42, 0.22), (0.46, 0.10), (0.50, 0.30),
              (0.58, 0.24), (0.58, 0.46), (0.60, 0.64)], c)

    for x, y in ((0.34, 0.80), (0.52, 0.74)):                     # poten
        _vlak(p, [(x, y), (x + 0.07, y - 0.02), (x + 0.10, y + 0.19),
                  (x + 0.03, y + 0.21)], c)
    for x, y in ((0.16, 0.85), (0.26, 0.81), (0.38, 0.78)):       # rugkam
        _vlak(p, [(x, y), (x + 0.035, y - 0.11), (x + 0.065, y - 0.01)], c)


@silhouette("giant")
def _giant(p: Pen, c: RGB) -> None:
    p.circle(0.50, 0.12, 0.115, c, outline=None)
    _vlak(p, [(0.30, 0.22), (0.70, 0.22), (0.66, 0.62), (0.34, 0.62)], c)     # brede romp
    _vlak(p, [(0.34, 0.60), (0.48, 0.60), (0.46, 1.0), (0.30, 1.0)], c)
    _vlak(p, [(0.52, 0.60), (0.66, 0.60), (0.70, 1.0), (0.54, 1.0)], c)
    p.line([(0.32, 0.28), (0.14, 0.62)], c, 0.052)
    p.line([(0.68, 0.28), (0.86, 0.62)], c, 0.052)


@silhouette("monk")
def _monk(p: Pen, c: RGB) -> None:
    _vlak(p, [(0.34, 0.22), (0.50, 0.06), (0.66, 0.22), (0.62, 0.34), (0.38, 0.34)], c)
    _vlak(p, [(0.36, 0.30), (0.64, 0.30), (0.74, 1.0), (0.26, 1.0)], c)       # pij
    _vlak(p, [(0.40, 0.44), (0.60, 0.44), (0.58, 0.56), (0.42, 0.56)], c)


# ---------------------------------------------------------------------------
#  Renderen
# ---------------------------------------------------------------------------

WERKMAAT = 480          # vaste tekenmaat; het resultaat wordt daarna geschaald
_CACHE: dict[tuple[str, int, RGB], Image.Image] = {}


def available_silhouettes() -> list[str]:
    return sorted(SILHOUETTES)


def render_silhouette(naam: str, hoogte: int, kleur: RGB) -> Image.Image:
    """Tekent een silhouet van deze hoogte, in één kleur.

    De vorm wordt op een vaste maat getekend en daarna bijgesneden tot wat
    er werkelijk staat. De breedte volgt dus uit de vorm zelf; niets wordt
    uitgerekt om in een vakje te passen.
    """
    if naam not in SILHOUETTES:
        raise KeyError(
            f"Onbekend silhouet {naam!r}. Beschikbaar: {', '.join(available_silhouettes())}"
        )

    sleutel = (naam, hoogte, tuple(kleur))
    if sleutel in _CACHE:
        return _CACHE[sleutel]

    pen = Pen(WERKMAAT * SUPERSAMPLE)
    SILHOUETTES[naam](pen, tuple(kleur))
    vorm = pen.img.resize((WERKMAAT, WERKMAAT), Image.LANCZOS)

    kader = vorm.getbbox()
    if kader is None:                       # niets getekend; lege tegel
        return Image.new("RGBA", (1, hoogte), (0, 0, 0, 0))
    vorm = vorm.crop(kader)

    breedte = max(1, round(vorm.width * hoogte / vorm.height))
    tegel = vorm.resize((breedte, hoogte), Image.LANCZOS)

    _CACHE[sleutel] = tegel
    return tegel
