"""Vinden en aanroepen van ffmpeg.

Waarom dit bestaat: ffmpeg zelf installeren was de grootste drempel om te
beginnen. Daarom wordt er een kant-en-klare ffmpeg meegeïnstalleerd via pip.
Staat er al een op het systeem, dan krijgt die voorrang: die is meestal
nieuwer en kleiner.

Die meegeleverde versie bevat geen ffprobe. De duur van een bestand wordt
daarom uit ffmpeg zelf gehaald wanneer ffprobe ontbreekt.
"""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    pass


@functools.lru_cache(maxsize=1)
def ffmpeg_bin() -> str:
    """Pad naar ffmpeg. Systeemversie eerst, anders de meegeleverde."""
    systeem = shutil.which("ffmpeg")
    if systeem:
        return systeem
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:                                    # noqa: BLE001
        raise MediaError(
            "Geen ffmpeg gevonden. Installeer hem met "
            "'pip install imageio-ffmpeg', of via brew, apt of winget."
        ) from exc


@functools.lru_cache(maxsize=1)
def ffprobe_bin() -> str | None:
    """Pad naar ffprobe, of None. De meegeleverde ffmpeg heeft er geen."""
    return shutil.which("ffprobe")


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Roept ffmpeg aan met de juiste binary voorop."""
    return subprocess.run([ffmpeg_bin(), *args], capture_output=True, **kwargs)


_TIME = re.compile(r"time=(\d+):(\d\d):(\d\d(?:\.\d+)?)")
_DURATION = re.compile(r"Duration: (\d+):(\d\d):(\d\d(?:\.\d+)?)")


def _to_seconds(match) -> float:
    uren, minuten, seconden = match
    return int(uren) * 3600 + int(minuten) * 60 + float(seconden)


def duration(path: Path | str) -> float:
    """Lengte van een audio- of videobestand in seconden."""
    path = str(path)

    probe = ffprobe_bin()
    if probe:
        result = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True,
        )
        waarde = result.stdout.strip()
        if result.returncode == 0 and waarde not in ("", "N/A"):
            return float(waarde)

    # Zonder ffprobe: ffmpeg meldt de duur al in de kop van zijn uitvoer.
    # Dat is meteen klaar, ook bij een video van tien minuten.
    kop = subprocess.run([ffmpeg_bin(), "-i", path], capture_output=True, text=True)
    treffer = _DURATION.search(kop.stderr)
    if treffer and "N/A" not in treffer.group(0):
        return _to_seconds(treffer.groups())

    # Staat de duur niet in de kop (komt voor bij sommige streams), dan het
    # bestand één keer doordraaien en de laatste tijdstempel aflezen.
    result = subprocess.run(
        [ffmpeg_bin(), "-i", path, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    treffers = _TIME.findall(result.stderr)
    if not treffers:
        raise MediaError(f"Kon de lengte van {path} niet bepalen.")
    return _to_seconds(treffers[-1])


def describe() -> str:
    """Korte omschrijving voor 'ytauto check'."""
    binary = ffmpeg_bin()
    herkomst = "systeem" if shutil.which("ffmpeg") else "meegeleverd via pip"
    probe = "met ffprobe" if ffprobe_bin() else "zonder ffprobe (niet nodig)"
    return f"{binary} ({herkomst}, {probe})"
