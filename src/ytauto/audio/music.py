"""Zacht muziekbedje, ter plekke gesynthetiseerd.

Waarom zelf maken en geen bestaande muziek: kindercontent wordt streng
gescand op Content ID. Zelfs 'royalty free' bibliotheken leveren regelmatig
claims op, en één claim op een kanaal met tientallen video's kost meer tijd
dan dit hele bestand. Wat hier uitkomt is van jou, altijd.

Het klinkt als een speeldoosje: zachte belletjes over een rustig akkoord.
Bewust simpel, want de muziek moet onder de stem blijven, niet erbovenuit.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100

# C-majeur pentatoniek: er bestaat geen combinatie van deze tonen die vals
# klinkt, dus willekeurige melodieën blijven altijd luisterbaar.
PENTATONIC = [261.63, 293.66, 329.63, 392.00, 440.00,
              523.25, 587.33, 659.25, 783.99, 880.00]

# I - V - vi - IV, het rustigste akkoordenschema dat er is.
PROGRESSION = [
    (130.81, 164.81, 196.00),   # C
    (196.00, 246.94, 293.66),   # G
    (220.00, 261.63, 329.63),   # Am
    (174.61, 220.00, 261.63),   # F
]

BAR_SECONDS = 2.4

# ---------------------------------------------------------------------------
#  Volksverhalen
#
#  Onder een sage hoort geen speeldoosje. Wat wel werkt is een lage
#  aangehouden toon met daarboven losse noten in een oude toonsoort, ver uit
#  elkaar. Dorisch klinkt plechtig zonder verdrietig te worden, en dat is
#  precies het register van een verteller.
# ---------------------------------------------------------------------------

DRONE = (73.42, 110.00)                 # D en A: een kwint als bodem
DORIAN = [146.83, 164.81, 174.61, 196.00, 220.00, 246.94, 261.63,
          293.66, 329.63, 349.23, 392.00]
STORY_BAR = 4.8                         # trager dan bij de kindervideo's


def _drone(duration: float, freqs: tuple[float, ...] = DRONE,
           amp: float = 0.16) -> np.ndarray:
    """Aangehouden lage toon met lichte zweving.

    Twee stemmen die minimaal uit elkaar liggen gaan langzaam in en uit
    fase. Dat geeft een trage golf die klinkt als iets levends in plaats
    van een synthesizer die een knop vasthoudt.
    """
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    out = np.zeros(n, dtype=np.float32)
    for i, freq in enumerate(freqs):
        for zweving in (1.0, 1.0032):
            out += np.sin(2 * np.pi * freq * zweving * t).astype(np.float32)
        out += 0.22 * np.sin(2 * np.pi * freq * 2 * t).astype(np.float32)
    trilling = 1.0 + 0.06 * np.sin(2 * np.pi * 0.06 * t)
    return (out / (len(freqs) * 2.4) * amp * trilling).astype(np.float32)


def _pluck(freq: float, duration: float, amp: float = 0.30) -> np.ndarray:
    """Aangeslagen snaar: harder in de aanzet, met een langere nagalm dan
    een belletje en meer boventonen, zoals een harp of een luit."""
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    decay = np.exp(-2.1 * t / max(duration, 0.01))
    golf = (
        np.sin(2 * np.pi * freq * t)
        + 0.45 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.22 * np.sin(2 * np.pi * freq * 3 * t)
        + 0.10 * np.sin(2 * np.pi * freq * 5 * t)
    )
    attack = np.minimum(1.0, t * 320)
    return (golf * decay * attack * amp).astype(np.float32)


def synth_story_bed(duration: float, seed: int = 0) -> np.ndarray:
    """Muziekbed voor een volksverhaal."""
    rng = random.Random(seed)
    total = int(duration * SAMPLE_RATE)
    track = np.zeros(total + SAMPLE_RATE, dtype=np.float32)

    _mix_in(track, 0, _drone(duration + 1.0))

    positie = int(1.5 * SAMPLE_RATE)
    vorige = len(DORIAN) // 2
    while positie < total:
        # Kleine stappen door de toonladder: grote sprongen klinken als een
        # melodie die iets wil, en dat leidt af van de verteller.
        vorige = max(0, min(len(DORIAN) - 1, vorige + rng.choice([-2, -1, -1, 1, 1, 2])))
        _mix_in(track, positie, _pluck(DORIAN[vorige], STORY_BAR * 0.9,
                                       amp=rng.uniform(0.16, 0.30)))
        if rng.random() < 0.30:                    # af en toe een tweede stem
            lager = max(0, vorige - rng.choice([3, 4]))
            _mix_in(track, positie + int(0.28 * SAMPLE_RATE),
                    _pluck(DORIAN[lager] / 2, STORY_BAR, amp=0.12))
        positie += int(STORY_BAR * rng.uniform(0.8, 1.5) * SAMPLE_RATE)

    track = track[:total]
    piek = float(np.max(np.abs(track))) or 1.0
    track = track / piek * 0.72

    fade = int(4.0 * SAMPLE_RATE)
    if total > fade * 2:
        track[:fade] *= np.linspace(0, 1, fade)
        track[-fade:] *= np.linspace(1, 0, fade)
    return track


def _bell(freq: float, duration: float, amp: float = 0.5) -> np.ndarray:
    """Eén belletje: grondtoon met twee boventonen en een snelle uitdemping."""
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    decay = np.exp(-3.2 * t / max(duration, 0.01))
    wave_data = (
        np.sin(2 * np.pi * freq * t)
        + 0.32 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.11 * np.sin(2 * np.pi * freq * 3 * t)
    )
    attack = np.minimum(1.0, t * 220)          # klikvrije inzet
    return (wave_data * decay * attack * amp).astype(np.float32)


def _pad(freqs: tuple[float, ...], duration: float, amp: float = 0.10) -> np.ndarray:
    """Warm akkoord eronder, met een langzame in- en uitloop."""
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False)
    out = np.zeros(n, dtype=np.float32)
    for i, freq in enumerate(freqs):
        detune = 1.0 + (i - 1) * 0.0015        # minieme zweving: klinkt levend
        out += np.sin(2 * np.pi * freq * detune * t).astype(np.float32)
    envelope = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.4
    return out / len(freqs) * envelope * amp


def _mix_in(track: np.ndarray, start: int, chunk: np.ndarray) -> None:
    """Telt een fragment bij het spoor op en kapt netjes af aan het einde.

    Zonder deze afkapping klapt de synthesizer eruit zodra een noot voorbij
    het einde van het spoor begint: een negatieve slicelengte levert dan
    bijna de hele array op in plaats van niets.
    """
    if start >= len(track):
        return
    begin = max(0, start)
    einde = min(len(track), start + len(chunk))
    if einde <= begin:
        return
    track[begin:einde] += chunk[begin - start:einde - start]


def synth_bed(duration: float, seed: int = 0) -> np.ndarray:
    """Bouwt een muziekbed van precies deze lengte."""
    rng = random.Random(seed)
    total = int(duration * SAMPLE_RATE)
    track = np.zeros(total + SAMPLE_RATE, dtype=np.float32)

    bar = 0
    position = 0
    while position < total:
        chord = PROGRESSION[bar % len(PROGRESSION)]
        _mix_in(track, position, _pad(chord, BAR_SECONDS))

        # Vier tellen per maat; niet elke tel krijgt een noot, dat geeft lucht.
        for beat in range(4):
            if rng.random() < 0.34:
                continue
            note = rng.choice(PENTATONIC)
            if beat == 0:
                note = rng.choice(PENTATONIC[:5])   # maat begint laag
            start = position + int(beat * BAR_SECONDS / 4 * SAMPLE_RATE)
            _mix_in(track, start, _bell(note, BAR_SECONDS / 2, amp=rng.uniform(0.28, 0.46)))

        position += int(BAR_SECONDS * SAMPLE_RATE)
        bar += 1

    track = track[:total]

    peak = float(np.max(np.abs(track))) or 1.0
    track = track / peak * 0.75

    fade = int(2.5 * SAMPLE_RATE)
    if total > fade * 2:
        track[:fade] *= np.linspace(0, 1, fade)
        track[-fade:] *= np.linspace(1, 0, fade)

    return track


def write_wav(path: Path, samples: np.ndarray) -> None:
    """Schrijft mono 16-bit wav."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())


def build_music(path: Path, duration: float, seed: int = 0,
                mood: str = "kids") -> Path:
    write_wav(path, bed_for(mood, duration, seed))
    return path


def bed_for(mood: str, duration: float, seed: int = 0) -> np.ndarray:
    """Kiest het muziekbed dat bij de niche hoort."""
    return synth_story_bed(duration, seed) if mood == "folklore" else synth_bed(duration, seed)


def pick_library_track(library: Path) -> Path | None:
    """Kiest een eigen bestand uit assets/music, als je die zelf aanlevert."""
    if not library.exists():
        return None
    tracks = sorted(p for p in library.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a"))
    return tracks[0] if tracks else None
