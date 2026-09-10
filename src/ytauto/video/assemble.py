"""Zet een blueprint om in een afgemonteerde mp4.

De opbouw in drie stappen:
  1. per scene een PNG renderen en de zin laten inspreken;
  2. één audiospoor bouwen waarin elke zin op zijn eigen tijdstip staat,
     met het muziekbed eronder;
  3. ffmpeg de beelden aan elkaar laten vloeien en het geheel encoderen.

De tijdlijn wordt in stap 2 exact vastgelegd. Stap 3 volgt die tijdlijn,
zodat beeld en geluid niet uit elkaar kunnen lopen bij een lange video.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from ..audio.music import SAMPLE_RATE, bed_for, pick_library_track, write_wav
from ..config import ROOT, Config
from ..media import duration as media_duration
from ..media import ffmpeg_bin
from ..render.frame import render_frame
from ..script_builder import Scene
from ..scripting.blueprint import Blueprint, to_scenes
from ..tts import synthesize

LEAD_IN = 0.35        # stilte voor de zin begint
TAIL = 0.45           # stilte na de zin, voor de overgang

Progress = Callable[[str, float], None]


def _noop(message: str, fraction: float) -> None:
    pass


@dataclass
class Timeline:
    scenes: list[Scene]
    starts: list[float]        # startmoment van elke scene op de tijdlijn
    holds: list[float]         # hoe lang elke scene in beeld blijft
    total: float


# ---------------------------------------------------------------------------
#  Stap 1: beeld en stem
# ---------------------------------------------------------------------------


def prepare_assets(
    cfg: Config,
    blueprint: Blueprint,
    workdir: Path,
    seed: int = 0,
    progress: Progress = _noop,
) -> Timeline:
    scenes = to_scenes(blueprint, seed=seed)
    frames_dir = workdir / "frames"
    voice_dir = workdir / "voice"
    frames_dir.mkdir(parents=True, exist_ok=True)
    voice_dir.mkdir(parents=True, exist_ok=True)

    resolution = cfg.resolution
    holds: list[float] = []

    for index, scene in enumerate(scenes):
        png = frames_dir / f"{scene.id}.png"
        if not png.exists():
            render_frame(scene.visual, resolution, seed=seed + index).save(png, optimize=False)

        mp3 = voice_dir / f"{scene.id}.mp3"
        spoken = synthesize(cfg, scene.narration, mp3, cache_dir=workdir.parent / "voice-cache")
        scene.audio_path = str(mp3)
        scene.duration = spoken

        hold = max(scene.min_duration, LEAD_IN + spoken + TAIL) + scene.pause_after
        hold = max(hold, float(cfg.safety.get("min_scene_seconds", 2.5)))
        holds.append(hold)

        progress(f"scene {index + 1}/{len(scenes)}", (index + 1) / len(scenes) * 0.55)

    starts, running = [], 0.0
    for hold in holds:
        starts.append(running)
        running += hold

    return Timeline(scenes=scenes, starts=starts, holds=holds, total=running)


# ---------------------------------------------------------------------------
#  Stap 2: audiospoor
# ---------------------------------------------------------------------------


def decode_audio(path: Path) -> np.ndarray:
    """Leest een audiobestand als mono float32 op 44,1 kHz."""
    result = subprocess.run(
        [ffmpeg_bin(), "-v", "error", "-i", str(path), "-f", "f32le",
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(result.stdout, dtype="<f4").copy()


def build_audio_track(
    cfg: Config,
    timeline: Timeline,
    out_path: Path,
    seed: int = 0,
    progress: Progress = _noop,
) -> Path:
    total_samples = int((timeline.total + 1.0) * SAMPLE_RATE)
    voice = np.zeros(total_samples, dtype=np.float32)

    for index, (scene, start) in enumerate(zip(timeline.scenes, timeline.starts)):
        if not scene.audio_path:
            continue
        samples = decode_audio(Path(scene.audio_path))
        offset = int((start + LEAD_IN) * SAMPLE_RATE)
        end = min(total_samples, offset + len(samples))
        if end > offset:
            voice[offset:end] += samples[:end - offset]
        progress("audio", 0.55 + (index + 1) / len(timeline.scenes) * 0.15)

    # Stem eerst op een vaste piek zetten, daarna pas de muziek eronder.
    peak = float(np.max(np.abs(voice))) or 1.0
    voice = voice / peak * 0.82

    source = cfg.music.get("source", "synth")
    if source != "none":
        gain = 10 ** (float(cfg.music.get("volume_db", -26)) / 20.0)
        bed = _music_bed(cfg, timeline.total + 1.0, seed, source)
        length = min(len(bed), total_samples)
        voice[:length] += bed[:length] * gain

    write_wav(out_path, np.clip(voice, -1.0, 1.0))
    return out_path


def _music_bed(cfg: Config, duration: float, seed: int, source: str) -> np.ndarray:
    if source == "library":
        track = pick_library_track(ROOT / "assets" / "music")
        if track:
            bed = decode_audio(track)
            needed = int(duration * SAMPLE_RATE)
            if len(bed) < needed:                      # herhalen tot het past
                bed = np.tile(bed, int(needed / max(1, len(bed))) + 1)
            return bed[:needed]
    return bed_for(cfg.music.get("mood", "kids"), duration, seed)


# ---------------------------------------------------------------------------
#  Stap 3: monteren
# ---------------------------------------------------------------------------


def build_video(
    cfg: Config,
    timeline: Timeline,
    audio_path: Path,
    out_path: Path,
    workdir: Path,
    progress: Progress = _noop,
) -> Path:
    """Vloeit de PNG's aan elkaar en encodeert samen met het audiospoor.

    Elk beeld is een eigen ffmpeg-input die net iets langer loopt dan hij in
    beeld staat; dat overschot is precies het materiaal waar de xfade
    doorheen vloeit. De offsets lopen op met de vaste schermtijd, dus de
    tijdlijn blijft gelijk aan die van het audiospoor.
    """
    fps = cfg.fps
    fade = float(cfg.video.get("crossfade_seconds", 0.6))
    preset = cfg.video.get("encoder_preset", "medium")
    crf = int(cfg.video.get("crf", 20))
    frames_dir = workdir / "frames"

    inputs: list[str] = []
    chain: list[str] = []
    for index, (scene, hold) in enumerate(zip(timeline.scenes, timeline.holds)):
        png = frames_dir / f"{scene.id}.png"
        inputs += ["-loop", "1", "-t", f"{hold + fade:.3f}", "-i", str(png)]
        chain.append(f"[{index}:v]fps={fps},format=yuv420p,setsar=1[v{index}]")

    label = "v0"
    offset = 0.0
    for index in range(1, len(timeline.scenes)):
        offset += timeline.holds[index - 1]
        chain.append(
            f"[{label}][v{index}]xfade=transition=fade:"
            f"duration={fade:.3f}:offset={offset:.3f}[x{index}]"
        )
        label = f"x{index}"

    loudness = float(cfg.safety.get("loudness_lufs", -14))
    command = (
        [ffmpeg_bin(), "-y"] + inputs
        + ["-i", str(audio_path),
           "-filter_complex", ";".join(chain),
           "-map", f"[{label}]", "-map", f"{len(timeline.scenes)}:a",
           "-af", f"loudnorm=I={loudness}:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
           "-r", str(fps), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart",
           str(out_path)]
    )

    progress("encoderen", 0.75)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mislukt:\n{result.stderr[-2000:]}")

    progress("klaar", 1.0)
    return out_path


# ---------------------------------------------------------------------------
#  Alles achter elkaar
# ---------------------------------------------------------------------------


def assemble(
    cfg: Config,
    blueprint: Blueprint,
    workdir: Path,
    seed: int = 0,
    progress: Progress = _noop,
) -> tuple[Path, float]:
    workdir.mkdir(parents=True, exist_ok=True)

    timeline = prepare_assets(cfg, blueprint, workdir, seed=seed, progress=progress)
    audio = build_audio_track(cfg, timeline, workdir / "mix.wav", seed=seed, progress=progress)
    video = build_video(cfg, timeline, audio, workdir / "video.mp4", workdir, progress=progress)

    return video, timeline.total


def probe_duration(path: Path) -> float:
    return media_duration(path)
