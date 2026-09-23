"""De afdaling als video: één doorlopende beweging, frame voor frame.

Anders dan de rest van de pipeline worden hier geen losse beelden aan elkaar
geplakt. Het hele beeld bestaat al — één hoge kolom — en wat er gebeurt is
dat de camera erdoorheen zakt. Elk beeldje wordt uitgesneden, voorzien van
de dieptemeter, en rechtstreeks naar ffmpeg gestuurd. Dat is eenvoudiger dan
het met filters proberen, en het maakt alles wat per beeldje verandert
mogelijk zonder dat er een nieuw stuk montage bij komt.

De camera volgt de verteller: op het moment dat een mijlpaal wordt genoemd,
staat die mijlpaal in beeld. Daartussen versnelt hij. Zo hoeft niemand de
timing met de hand goed te zetten, en klopt het altijd, ook als de stem
sneller of langzamer blijkt te lezen dan gedacht.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw

from ..audio.music import SAMPLE_RATE, bed_for, write_wav
from ..config import Config
from ..media import ffmpeg_bin
from ..render.descent import Column, build_column
from ..render.story_scene import load_font
from ..tts import synthesize
from .assemble import decode_audio

Progress = Callable[[str, float], None]

GAP = 0.28              # stilte tussen twee regels
HOOK_HOLD = 2.2         # hoe lang de openingsvraag blijft staan
FOCUS = 0.55            # waar in beeld een mijlpaal staat als hij genoemd wordt


def _noop(message: str, fraction: float) -> None:
    pass


@dataclass
class Line:
    """Eén gesproken regel met zijn plek op de tijdlijn."""

    text: str
    start: float
    duration: float
    row: float | None = None        # waar de camera dan moet staan, of None

    @property
    def middle(self) -> float:
        return self.start + self.duration / 2


def build_lines(cfg: Config, journey: dict, column: Column, workdir: Path,
                progress: Progress = _noop) -> list[Line]:
    """Spreekt alles in en zet het op de tijdlijn."""
    stem_dir = workdir / "voice"
    stem_dir.mkdir(parents=True, exist_ok=True)

    teksten = [(journey["hook"], None)]
    teksten += [(steen["say"], float(steen["depth"])) for steen in journey["milestones"]]
    if journey.get("closing"):
        teksten.append((journey["closing"], float(journey["total"])))

    lijnen: list[Line] = []
    loopt = 0.35
    for index, (tekst, diepte) in enumerate(teksten):
        mp3 = stem_dir / f"{index:03d}.mp3"
        duur = synthesize(cfg, tekst, mp3, cache_dir=workdir.parent / "voice-cache")
        lijnen.append(Line(text=tekst, start=loopt, duration=duur,
                           row=None if diepte is None else column.row(diepte)))
        loopt += duur + GAP
        progress(f"stem {index + 1}/{len(teksten)}", 0.05 + 0.35 * (index + 1) / len(teksten))

    # De openingsvraag krijgt lucht: hem meteen laten vallen is zonde van de
    # enige seconde waarin iemand besluit of hij blijft kijken.
    if len(lijnen) > 1:
        verschuiving = max(0.0, HOOK_HOLD - (lijnen[1].start - lijnen[0].start))
        for lijn in lijnen[1:]:
            lijn.start += verschuiving
    return lijnen


def camera_path(lijnen: list[Line], column: Column, height: int,
                total_seconds: float, fps: int) -> np.ndarray:
    """Waar de camera op elk beeldje staat.

    Tussen twee mijlpalen wordt zacht versneld en weer afgeremd. Dat 'even
    inhouden' is wat je de mijlpaal laat zien; zou hij met vaste snelheid
    doorzakken, dan schiet elk wezen voorbij op het moment dat het genoemd
    wordt.
    """
    max_y = column.image.height - height
    ankers = [(0.0, 0.0)]
    for lijn in lijnen:
        if lijn.row is not None:
            ankers.append((lijn.middle, min(max_y, max(0.0, lijn.row - height * FOCUS))))
    ankers.append((total_seconds, float(max_y)))

    frames = int(round(total_seconds * fps))
    pad = np.empty(frames, dtype=np.float64)
    for index in range(frames):
        t = index / fps
        vorige = ankers[0]
        for anker in ankers[1:]:
            if t <= anker[0]:
                spanne = max(1e-6, anker[0] - vorige[0])
                deel = min(1.0, max(0.0, (t - vorige[0]) / spanne))
                zacht = deel * deel * (3 - 2 * deel)         # zacht aan, zacht uit
                pad[index] = vorige[1] + (anker[1] - vorige[1]) * zacht
                break
            vorige = anker
        else:
            pad[index] = ankers[-1][1]
    return np.clip(pad, 0, max_y)


def _rounded(meters: float, total: float | None = None) -> str:
    """Afgerond genoeg om leesbaar te zijn, exact waar het ertoe doet.

    Onderweg mag de teller afronden — niemand leest vier cijfers die tien
    keer per seconde veranderen. Maar op het diepste punt staat het echte
    getal ook als label in beeld, en twee verschillende getallen naast
    elkaar is een fout, geen afronding.
    """
    if total is not None and meters >= total * 0.995:
        return f"{int(round(total)):,}".replace(",", ".")
    stap = 1 if meters < 100 else 10 if meters < 1000 else 50
    waarde = int(round(meters / stap) * stap)
    return f"{waarde:,}".replace(",", ".")


def build_audio(cfg: Config, lijnen: list[Line], workdir: Path,
                total: float, seed: int = 0) -> Path:
    """Stem op de tijdlijn, met een laag muziekbed eronder."""
    monsters = int((total + 0.5) * SAMPLE_RATE)
    stem = np.zeros(monsters, dtype=np.float32)

    for index, lijn in enumerate(lijnen):
        pad = workdir / "voice" / f"{index:03d}.mp3"
        if not pad.exists():
            continue
        golf = decode_audio(pad)
        begin = int(lijn.start * SAMPLE_RATE)
        eind = min(monsters, begin + len(golf))
        if eind > begin:
            stem[begin:eind] += golf[:eind - begin]

    bron = cfg.music.get("source", "synth")
    if bron == "none":
        mix = stem
    else:
        bed = bed_for(cfg.music.get("mood", "folklore"), total + 0.5, seed)
        niveau = 10 ** (float(cfg.music.get("volume_db", -28)) / 20)
        mix = stem + bed[:monsters] * niveau

    piek = float(np.max(np.abs(mix))) or 1.0
    doel = workdir / "mix.wav"
    write_wav(doel, (mix / piek * 0.92).astype(np.float32))
    return doel


def render(cfg: Config, journey: dict, workdir: Path, seed: int = 0,
           progress: Progress = _noop) -> Path:
    """Maakt de complete video en geeft het pad terug."""
    width, height = cfg.resolution
    fps = cfg.fps
    workdir.mkdir(parents=True, exist_ok=True)

    progress("de kolom tekenen", 0.02)
    column = build_column(width, journey, seed=seed)
    totaal_m = float(journey["total"])

    lijnen = build_lines(cfg, journey, column, workdir, progress=progress)
    totaal = lijnen[-1].start + lijnen[-1].duration + 1.1

    progress("geluid", 0.42)
    audio = build_audio(cfg, lijnen, workdir, totaal, seed=seed)
    pad = camera_path(lijnen, column, height, totaal, fps)

    kolom = np.asarray(column.image.convert("RGB"))
    teller_font = load_font(int(width * 0.105), "IBMPlexSans", 700)
    eenheid_font = load_font(int(width * 0.040), "IBMPlexSans", 500)
    haak_font = load_font(int(width * 0.082), "IBMPlexSans", 700)

    # Een donkere sluier bovenin. Zonder deze loopt een label dat langs de
    # bovenrand schuift dwars door de dieptemeter heen; met sluier zakt het
    # er netjes achter weg.
    scrim_h = int(height * 0.19)
    scrim = Image.new("RGBA", (width, scrim_h), (0, 0, 0, 0))
    sluier = ImageDraw.Draw(scrim)
    for rij in range(scrim_h):
        deel = 1.0 - rij / scrim_h
        sluier.line([(0, rij), (width, rij)], fill=(2, 14, 26, int(205 * deel ** 1.4)))

    uit = workdir / "video.mp4"
    opdracht = [
        ffmpeg_bin(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
        "-r", str(fps), "-i", "-",
        "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-af", f"loudnorm=I={float(cfg.safety.get('loudness_lufs', -14))}:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", str(cfg.video.get("encoder_preset", "veryfast")),
        "-crf", str(int(cfg.video.get("crf", 21))), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(uit),
    ]
    proces = subprocess.Popen(opdracht, stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    haak_einde = lijnen[0].start + lijnen[0].duration + 0.7
    try:
        for index, y in enumerate(pad):
            boven = int(y)
            beeld = Image.fromarray(kolom[boven:boven + height])
            d = ImageDraw.Draw(beeld, "RGBA")

            # De teller leest op dezelfde lijn waar een mijlpaal staat als hij
            # genoemd wordt. Zo zegt het getal precies wat de verteller zegt,
            # en haalt hij aan het eind ook werkelijk het diepste punt.
            diepte = column.depth_at(boven + height * FOCUS)
            if diepte > 0.4:
                band = beeld.crop((0, 0, width, scrim_h)).convert("RGBA")
                band.alpha_composite(scrim)
                beeld.paste(band.convert("RGB"), (0, 0))
                d = ImageDraw.Draw(beeld, "RGBA")
                d.text((width / 2, height * 0.085), _rounded(diepte, totaal_m), font=teller_font,
                       anchor="mm", fill=(244, 251, 255, 240))
                d.text((width / 2, height * 0.133), journey.get("unit", "m"),
                       font=eenheid_font, anchor="mm", fill=(170, 210, 234, 215))

            t = index / fps
            if t < haak_einde:
                vervaag = min(1.0, (haak_einde - t) / 0.6)
                _hook(d, journey["hook"], haak_font, width, height, vervaag)

            proces.stdin.write(beeld.tobytes())
            if index % 45 == 0:
                progress("beeld", 0.45 + 0.5 * index / len(pad))
    finally:
        proces.stdin.close()
        fout = proces.stderr.read().decode("utf-8", "replace")
        proces.wait()

    if proces.returncode != 0:
        raise RuntimeError(f"ffmpeg mislukt:\n{fout[-2000:]}")

    progress("klaar", 1.0)
    return uit


def _hook(d: ImageDraw.ImageDraw, tekst: str, font, width: int, height: int,
          alpha: float) -> None:
    """De openingsvraag, over het wateroppervlak."""
    regels, regel = [], ""
    for woord in tekst.split():
        kandidaat = f"{regel} {woord}".strip()
        if regel and d.textlength(kandidaat, font=font) > width * 0.84:
            regels.append(regel)
            regel = woord
        else:
            regel = kandidaat
    regels.append(regel)

    hoogte = int(width * 0.105)
    begin = height * 0.40 - (len(regels) - 1) * hoogte / 2
    for nummer, tekstregel in enumerate(regels):
        d.text((width / 2, begin + nummer * hoogte), tekstregel, font=font, anchor="mm",
               fill=(255, 255, 255, int(255 * alpha)),
               stroke_width=max(3, width // 170),
               stroke_fill=(0, 26, 44, int(215 * alpha)))
