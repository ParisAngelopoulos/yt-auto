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


def build_music(path: Path, duration: float, seed: int = 0) -> Path:
    write_wav(path, synth_bed(duration, seed))
    return path


def pick_library_track(library: Path) -> Path | None:
    """Kiest een eigen bestand uit assets/music, als je die zelf aanlevert."""
    if not library.exists():
        return None
    tracks = sorted(p for p in library.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a"))
    return tracks[0] if tracks else None
