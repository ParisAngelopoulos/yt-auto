"""Controles die het kanaal beschermen.

Wat gecontroleerd wordt hangt af van de niche. Bij kindercontent is de lat
het hoogst: zo'n kanaal valt onder COPPA en onder een apart pakket
kwaliteitsregels. Bij volksverhalen gelden andere grenzen — een wolf die
iemand opeet hoort in een sage thuis en is daar geen probleem — maar wat
YouTube ongeschikt vindt voor adverteerders is dat nog steeds wel.

Deze controles draaien voor elke publicatie en kosten niets; één geweigerde
video kost een dag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageStat

from .config import Config
from .scripting.blueprint import Blueprint

# Woorden die in deze niche nooit door de verteller horen te komen. De lijst
# is met opzet ruim: liever een terechte afkeuring te veel dan een video die
# een driejarige aan het schrikken maakt.
FORBIDDEN = {
    "scary", "scared", "afraid", "fear", "monster", "ghost", "blood", "die",
    "dead", "death", "kill", "gun", "knife", "weapon", "fight", "hurt",
    "pain", "cry", "crying", "sad", "angry", "hate", "stupid", "dumb",
    "ugly", "fat", "shut up", "alone", "lost", "danger", "dangerous",
    "poison", "sick", "hospital", "police", "jail", "war", "bomb",
}

# YouTube staat bij Made for Kids geen oproepen tot interactie toe:
# reacties, likes en abonneren zijn op zulke video's uitgeschakeld.
CALLS_TO_ACTION = {
    "subscribe", "like this video", "click", "comment below", "hit the bell",
    "link in the description", "follow us", "share this video",
}

# ---------------------------------------------------------------------------
#  Volksverhalen
# ---------------------------------------------------------------------------

# In een sage mag gevochten en gestorven worden. Wat niet kan is expliciet
# beschreven geweld: dat kost je de advertentiegeschiktheid, ook als het
# verhaal zelf eeuwenoud is.
GRAPHIC = {
    "disembowel", "disembowelled", "dismember", "dismembered", "mutilate",
    "mutilated", "gore", "gory", "entrails", "decapitate", "decapitated",
    "torture", "tortured", "flayed", "impaled", "butchered",
}

# Zelfdoding hoort niet beschreven te worden, hoe oud het verhaal ook is.
SELF_HARM = {"suicide", "hang himself", "hang herself", "kill himself",
             "kill herself", "took her own life", "took his own life"}

# Merken en bestaande figuren leveren claims op.
BRANDS = {
    "disney", "pixar", "peppa", "paw patrol", "cocomelon", "bluey",
    "mickey", "elsa", "frozen", "spiderman", "spider-man", "baby shark",
    "pokemon", "minecraft", "roblox", "barbie", "lego",
}


@dataclass
class SafetyReport:
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def summary(self) -> str:
        if self.ok and not self.warnings:
            return "Alle controles doorstaan."
        lines = [f"BLOKKEREND: {i}" for i in self.issues]
        lines += [f"let op: {w}" for w in self.warnings]
        return "\n".join(lines)


def _find(text: str, needles: set[str]) -> list[str]:
    lowered = f" {text.lower()} "
    hits = []
    for needle in needles:
        pattern = r"\b" + re.escape(needle) + r"\b"
        if re.search(pattern, lowered):
            hits.append(needle)
    return sorted(hits)


def check_text(text: str, format: str = "kids") -> SafetyReport:
    """Controleert gesproken tekst tegen de regels van deze niche."""
    report = SafetyReport()

    for brand in _find(text, BRANDS):
        report.issues.append(f"merknaam of bestaand figuur: {brand!r}")

    if format == "folklore":
        for woord in _find(text, GRAPHIC):
            report.issues.append(f"te expliciet geweld voor adverteerders: {woord!r}")
        for zin in _find(text, SELF_HARM):
            report.issues.append(f"beschrijving van zelfdoding: {zin!r}")
        return report

    for word in _find(text, FORBIDDEN):
        report.issues.append(f"verboden woord in de tekst: {word!r}")
    for phrase in _find(text, CALLS_TO_ACTION):
        report.issues.append(f"oproep tot actie, niet toegestaan bij Made for Kids: {phrase!r}")
    return report


def check_blueprint(cfg: Config, bp: Blueprint) -> SafetyReport:
    """Controleert het script voordat er ook maar iets gerenderd wordt."""
    vorm = bp.format
    report = check_text(bp.transcript(), vorm)
    report.issues += check_text(
        f"{bp.title} {bp.description} {' '.join(bp.tags)}", vorm).issues

    made_for_kids = bool(cfg.publish.get("made_for_kids", True))
    if vorm == "kids" and not made_for_kids:
        report.issues.append(
            "publish.made_for_kids staat uit. Voor een kinderkanaal is dat "
            "verplicht onder COPPA."
        )
    if vorm == "folklore":
        if made_for_kids:
            report.issues.append(
                "publish.made_for_kids staat aan, maar dit kanaal maakt geen "
                "kindercontent. Onterecht als kindervideo aanmerken schakelt "
                "reacties en advertenties uit en klopt niet."
            )
        if not bp.lesson_kind.strip():
            report.warnings.append(
                "geen traditie vermeld; noem waar het verhaal vandaan komt"
            )
        if not any(b.mode == "source" for b in bp.beats):
            report.warnings.append(
                "geen bronvermelding aan het eind; dat hoort bij een hervertelling"
            )

    minutes = bp.estimated_duration / 60
    if bp.shorts:
        # YouTube laat Shorts tot drie minuten toe; onder de twintig seconden
        # is het geen verhaal meer maar een losse zin.
        if minutes < 0.33:
            report.issues.append(f"Short is maar {minutes * 60:.0f} seconden; te kort")
        if minutes > 3:
            report.issues.append(
                f"Short is {minutes * 60:.0f} seconden; YouTube telt boven de drie "
                "minuten niet meer als Short"
            )
    else:
        if minutes < 1.5:
            report.issues.append(f"script is maar {minutes:.1f} minuten; te kort om te publiceren")
        if minutes > 20:
            report.warnings.append(f"script is {minutes:.0f} minuten, dat is lang voor deze leeftijd")

    if vorm == "kids" and len(bp.items) < 3:
        report.warnings.append(f"maar {len(bp.items)} items; drie is het minimum voor een zoekronde")

    if len(bp.title) > 100:
        report.issues.append(f"titel is {len(bp.title)} tekens; YouTube staat maximaal 100 toe")
    if len(bp.description) > 4900:
        report.issues.append("beschrijving is te lang voor YouTube (maximaal 5000 tekens)")

    return report


def check_frames(cfg: Config, frames_dir: Path) -> SafetyReport:
    """Kijkt of het beeld nergens hard flitst.

    Snelle wisselingen tussen licht en donker kunnen bij gevoelige kijkers
    een aanval uitlokken. Omdat alle scenes dezelfde achtergrond delen zou
    dit nooit mogen gebeuren, maar bij een aangepast script kan het wel.
    """
    report = SafetyReport()
    limit = float(cfg.safety.get("max_luminance_delta", 0.35))

    frames = sorted(frames_dir.glob("*.png"))
    previous = None
    for path in frames:
        with Image.open(path) as image:
            small = image.convert("L").resize((32, 18))
            luminance = ImageStat.Stat(small).mean[0] / 255.0
        if previous is not None and abs(luminance - previous) > limit:
            report.issues.append(
                f"te grote helderheidssprong bij {path.name} "
                f"({previous:.2f} -> {luminance:.2f}, grens {limit})"
            )
        previous = luminance

    return report
