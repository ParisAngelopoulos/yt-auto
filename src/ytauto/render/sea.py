"""Wat je onderweg naar beneden tegenkomt.

Eigen register, los van de silhouetten voor volksverhalen: een walvis hoort
niet op een bergkam te kunnen belanden omdat iemand zich vertypt.

Vlakke vormen in één kleur, net als de rest van dit project. Welke kleur
hangt af van de diepte: bovenin is er licht van boven en zie je een donker
silhouet, beneden is het enige licht dat van jezelf en wordt alles wat je
tegenkomt juist lichter dan het water. Dat verloop zit in `creature_color`.
"""

from __future__ import annotations

from typing import Callable

from PIL import Image

from .objects import SUPERSAMPLE, Pen
from .palette import RGB

WERKMAAT = 512

SeaFn = Callable[[Pen, RGB], None]
SEA: dict[str, SeaFn] = {}
_CACHE: dict[tuple, Image.Image] = {}


def sea(naam: str):
    def registreer(fn: SeaFn) -> SeaFn:
        SEA[naam] = fn
        return fn
    return registreer


def _vlak(p: Pen, punten, kleur: RGB) -> None:
    p.polygon(punten, kleur, outline=None)


# ---------------------------------------------------------------------------
#  Mensen en machines
# ---------------------------------------------------------------------------


@sea("diver")
def _diver(p: Pen, c: RGB) -> None:
    # De duiker is de kijker zelf, dus hij moet meteen als mens lezen. Daarom
    # smalle ledematen en een klein hoofd: een dikke romp met een grote bol
    # erop wordt een raket. Zijaanzicht, licht omlaag, hoofd linksboven.
    p.circle(0.215, 0.315, 0.050, c, outline=None)                  # hoofd
    _vlak(p, [(0.155, 0.300), (0.215, 0.285), (0.215, 0.345), (0.155, 0.335)], c)  # masker
    _vlak(p, [(0.245, 0.300), (0.60, 0.44), (0.585, 0.505), (0.235, 0.365)], c)    # romp
    _vlak(p, [(0.275, 0.268), (0.50, 0.365), (0.475, 0.425), (0.255, 0.330)], c)   # fles
    p.line([(0.29, 0.345), (0.235, 0.46), (0.30, 0.55)], c, 0.030)  # arm naar voren
    p.line([(0.34, 0.375), (0.40, 0.50), (0.50, 0.55)], c, 0.028)   # tweede arm
    p.line([(0.585, 0.475), (0.73, 0.545), (0.85, 0.585)], c, 0.040)  # benen
    _vlak(p, [(0.82, 0.555), (0.99, 0.585), (0.975, 0.665), (0.80, 0.615)], c)     # vinnen
    _vlak(p, [(0.80, 0.520), (0.955, 0.545), (0.945, 0.605), (0.785, 0.580)], c)


@sea("submersible")
def _submersible(p: Pen, c: RGB) -> None:
    p.circle(0.46, 0.50, 0.20, c, outline=None)                     # drukbol
    _vlak(p, [(0.26, 0.62), (0.70, 0.62), (0.74, 0.74), (0.22, 0.74)], c)   # frame
    _vlak(p, [(0.62, 0.36), (0.84, 0.30), (0.86, 0.40), (0.64, 0.46)], c)   # arm
    for x in (0.30, 0.42):                                          # lampen
        _vlak(p, [(x, 0.30), (x + 0.07, 0.30), (x + 0.07, 0.38), (x, 0.38)], c)
    _vlak(p, [(0.18, 0.72), (0.80, 0.72), (0.80, 0.78), (0.18, 0.78)], c)   # skids


@sea("wreck")
def _wreck(p: Pen, c: RGB) -> None:
    # Gekanteld op de bodem, gebroken mast. De scheve lijn maakt hem meteen
    # herkenbaar als iets dat gezonken is en niet als een varend schip.
    _vlak(p, [(0.08, 0.76), (0.86, 0.56), (0.92, 0.66), (0.80, 0.82),
              (0.20, 0.90)], c)                                     # romp
    _vlak(p, [(0.30, 0.72), (0.34, 0.34), (0.40, 0.34), (0.38, 0.73)], c)   # mast
    _vlak(p, [(0.34, 0.40), (0.60, 0.46), (0.34, 0.50)], c)         # restant ra
    _vlak(p, [(0.56, 0.62), (0.68, 0.59), (0.68, 0.52), (0.56, 0.55)], c)   # opbouw


# ---------------------------------------------------------------------------
#  Dieren
# ---------------------------------------------------------------------------


@sea("whale")
def _whale(p: Pen, c: RGB) -> None:
    # Blauwe vinvis, zijaanzicht naar links: lange gestroomlijnde romp die
    # naar achteren versmalt, en een brede staartvin.
    _vlak(p, [
        (0.04, 0.50), (0.12, 0.44), (0.28, 0.40), (0.48, 0.39),
        (0.66, 0.41), (0.80, 0.45), (0.86, 0.48),
        (0.80, 0.54), (0.66, 0.58), (0.46, 0.61), (0.26, 0.60),
        (0.12, 0.56),
    ], c)
    _vlak(p, [(0.86, 0.48), (0.99, 0.36), (0.97, 0.50), (0.99, 0.64)], c)   # fluke
    _vlak(p, [(0.34, 0.58), (0.46, 0.60), (0.40, 0.72), (0.32, 0.66)], c)   # borstvin
    _vlak(p, [(0.66, 0.41), (0.72, 0.33), (0.74, 0.42)], c)                 # rugvin


@sea("sperm_whale")
def _sperm_whale(p: Pen, c: RGB) -> None:
    # Potvis: de blokkige kop is het hele kenmerk, dus die krijgt een derde
    # van de lengte en een rechte voorkant.
    _vlak(p, [
        (0.05, 0.38), (0.34, 0.36), (0.58, 0.40), (0.76, 0.45), (0.84, 0.49),
        (0.76, 0.55), (0.58, 0.59), (0.34, 0.60), (0.06, 0.58), (0.04, 0.48),
    ], c)
    _vlak(p, [(0.84, 0.49), (0.99, 0.38), (0.96, 0.50), (0.99, 0.62)], c)
    _vlak(p, [(0.30, 0.58), (0.42, 0.59), (0.36, 0.70), (0.28, 0.65)], c)
    for x in (0.62, 0.68, 0.74):                                            # bultenrij
        _vlak(p, [(x, 0.41), (x + 0.04, 0.37), (x + 0.05, 0.42)], c)


@sea("shark")
def _shark(p: Pen, c: RGB) -> None:
    _vlak(p, [
        (0.04, 0.50), (0.14, 0.44), (0.32, 0.41), (0.54, 0.42),
        (0.74, 0.46), (0.84, 0.49),
        (0.74, 0.55), (0.54, 0.59), (0.32, 0.59), (0.14, 0.55),
    ], c)
    _vlak(p, [(0.36, 0.42), (0.44, 0.24), (0.54, 0.42)], c)                 # rugvin
    _vlak(p, [(0.84, 0.49), (0.97, 0.30), (0.94, 0.50), (0.99, 0.66)], c)   # staart
    _vlak(p, [(0.30, 0.57), (0.40, 0.58), (0.32, 0.72), (0.26, 0.62)], c)   # borstvin


@sea("jellyfish")
def _jellyfish(p: Pen, c: RGB) -> None:
    # Een koepel met een golvende rand, niet een veelhoek: de ronding is wat
    # hem van een paraplu onderscheidt. De tentakels hangen en slingeren
    # zacht; scherpe zigzag leest als draad.
    _vlak(p, [(0.20, 0.40), (0.23, 0.31), (0.30, 0.24), (0.40, 0.20),
              (0.50, 0.19), (0.60, 0.20), (0.70, 0.24), (0.77, 0.31),
              (0.80, 0.40), (0.74, 0.44), (0.68, 0.40), (0.61, 0.45),
              (0.54, 0.41), (0.46, 0.41), (0.39, 0.45), (0.32, 0.40),
              (0.26, 0.44)], c)
    for x in (0.42, 0.50, 0.58):                                    # mondarmen
        _vlak(p, [(x - 0.035, 0.42), (x + 0.035, 0.42), (x + 0.02, 0.60), (x - 0.02, 0.60)], c)
    for x, zwaai in ((0.27, -0.045), (0.36, 0.030), (0.50, -0.020),
                     (0.64, 0.035), (0.74, -0.040)):
        p.line([(x, 0.42), (x + zwaai, 0.58), (x + zwaai * 0.2, 0.74),
                (x + zwaai * 1.3, 0.88), (x + zwaai * 0.4, 0.99)], c, 0.013)


@sea("squid")
def _squid(p: Pen, c: RGB) -> None:
    # Reuzeninktvis met de punt naar boven: mantel, korte armen, en twee
    # lange vangarmen die verder doorlopen dan de rest.
    _vlak(p, [(0.42, 0.06), (0.58, 0.06), (0.64, 0.30), (0.62, 0.44),
              (0.38, 0.44), (0.36, 0.30)], c)                       # mantel
    _vlak(p, [(0.36, 0.14), (0.24, 0.06), (0.34, 0.22)], c)         # vinnen
    _vlak(p, [(0.64, 0.14), (0.76, 0.06), (0.66, 0.22)], c)
    for x, zwaai in ((0.40, -0.06), (0.46, -0.02), (0.54, 0.02), (0.60, 0.06)):
        p.line([(x, 0.44), (x + zwaai, 0.60), (x - zwaai * 0.5, 0.74)], c, 0.018)
    for x, zwaai in ((0.44, -0.10), (0.56, 0.10)):                  # vangarmen
        p.line([(x, 0.44), (x + zwaai, 0.66), (x - zwaai, 0.84), (x + zwaai * 1.4, 0.99)],
               c, 0.014)


@sea("anglerfish")
def _anglerfish(p: Pen, c: RGB) -> None:
    # Grote kop, kleine staart, en de hengel met lampje: dat lampje maakt
    # hem in één oogopslag herkenbaar, ook op honderd pixels.
    _vlak(p, [(0.14, 0.52), (0.22, 0.38), (0.40, 0.32), (0.58, 0.36),
              (0.70, 0.46), (0.72, 0.58), (0.60, 0.68), (0.40, 0.72),
              (0.22, 0.66)], c)                                     # lijf
    _vlak(p, [(0.72, 0.50), (0.90, 0.40), (0.86, 0.52), (0.90, 0.66)], c)   # staart
    for x in (0.18, 0.24, 0.30, 0.36):                              # tanden onder
        _vlak(p, [(x, 0.60), (x + 0.03, 0.60), (x + 0.015, 0.68)], c)
    for x in (0.20, 0.26, 0.32):                                    # tanden boven
        _vlak(p, [(x, 0.50), (x + 0.03, 0.50), (x + 0.015, 0.42)], c)
    p.line([(0.34, 0.33), (0.30, 0.18), (0.40, 0.10)], c, 0.018)    # hengel
    p.circle(0.43, 0.08, 0.055, c, outline=None)                    # lampje


@sea("tube_worms")
def _tube_worms(p: Pen, c: RGB) -> None:
    """Kokerwormen bij een warmwaterbron: het enige leven op die diepte.

    Dikke, licht gebogen kokers met een volle pluim erop. Dunne stokjes met
    een bolletje lezen als spelden, en dat is het tegenovergestelde van wat
    je wilt: dit moet er levend uitzien.
    """
    for x, hoogte, buiging in ((0.16, 0.46, 0.03), (0.29, 0.22, -0.02),
                               (0.43, 0.50, 0.02), (0.56, 0.30, -0.03),
                               (0.70, 0.40, 0.025), (0.84, 0.26, -0.02)):
        _vlak(p, [(x - 0.035, 0.99), (x + 0.035, 0.99),
                  (x + buiging + 0.026, hoogte + 0.04),
                  (x + buiging - 0.026, hoogte + 0.04)], c)         # koker
        # pluim: een paar tongen die uitwaaieren
        top = x + buiging
        for spreid in (-0.045, -0.015, 0.015, 0.045):
            _vlak(p, [(top - 0.020, hoogte + 0.06),
                      (top + 0.020, hoogte + 0.06),
                      (top + spreid + 0.013, hoogte - 0.055),
                      (top + spreid - 0.013, hoogte - 0.045)], c)


# ---------------------------------------------------------------------------
#  Tekenen
# ---------------------------------------------------------------------------


def available_sea() -> list[str]:
    return sorted(SEA)


def creature_color(meters: float) -> RGB:
    """Van donker silhouet bovenin naar zwak oplichtend beneden.

    Boven is het licht van boven en is alles wat ertussen zwemt donker. Onder
    de duizend meter komt er geen licht meer van boven; wat je dan ziet is
    wat je zelf beschijnt, en dat is lichter dan het water eromheen.
    """
    if meters <= 400:
        return (8, 22, 34)
    if meters >= 900:
        return (150, 172, 188)
    # Tussen 400 en 900 meter is het water al donker maar nog niet zwart;
    # daar is een figuur nog nét een silhouet. Die omslag mag daarom kort
    # zijn: rekt hij langer, dan valt alles ertussenin weg in het water.
    deel = (meters - 400) / (900 - 400)
    zacht = deel * deel * (3 - 2 * deel)                  # rustige overgang
    return tuple(int(8 + (150 - 8) * zacht) if i == 0 else
                 int((22, 34)[i - 1] + ((172, 188)[i - 1] - (22, 34)[i - 1]) * zacht)
                 for i in range(3))


def render_creature(naam: str, hoogte: int, kleur: RGB) -> Image.Image:
    """Tekent één wezen op deze hoogte, bijgesneden tot wat er werkelijk staat."""
    if naam not in SEA:
        raise KeyError(f"Onbekend zeewezen {naam!r}. Beschikbaar: {', '.join(available_sea())}")

    sleutel = (naam, hoogte, tuple(kleur))
    if sleutel in _CACHE:
        return _CACHE[sleutel]

    pen = Pen(WERKMAAT * SUPERSAMPLE)
    SEA[naam](pen, tuple(kleur))
    vorm = pen.img.resize((WERKMAAT, WERKMAAT), Image.LANCZOS)

    kader = vorm.getbbox()
    if kader is None:                                            # pragma: no cover
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    vorm = vorm.crop(kader)

    schaal = hoogte / vorm.height
    doel = vorm.resize((max(1, round(vorm.width * schaal)), max(1, hoogte)), Image.LANCZOS)
    _CACHE[sleutel] = doel
    return doel
