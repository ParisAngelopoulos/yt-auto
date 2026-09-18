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


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run([ffmpeg_bin(), "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mislukt:\n{result.stderr[-2000:]}")


def _encoder_args(cfg: Config) -> list[str]:
    return [
        "-c:v", "libx264",
        "-preset", str(cfg.video.get("encoder_preset", "medium")),
        "-crf", str(int(cfg.video.get("crf", 20))),
        "-pix_fmt", "yuv420p",
        "-r", str(cfg.fps),
        "-an",
    ]


def plan_segments(holds: list[float], fade: float) -> list[tuple[str, int, float]]:
    """Deelt de tijdlijn op in stukken die los gecodeerd kunnen worden.

    Een beeld staat eerst stil ('hold') en vloeit daarna over in het volgende
    ('xfade'). Het eerste en het laatste beeld staan langer stil, omdat daar
    maar aan één kant een overgang zit.

    Wat eruit komt is per stuk: wat het is, welke scene het betreft, en hoe
    lang het duurt. De optelsom is precies sum(holds) + fade, net als
    voorheen, zodat beeld en geluid gelijk blijven lopen.
    """
    aantal = len(holds)
    if aantal == 1:
        return [("hold", 0, holds[0] + fade)]

    stukken: list[tuple[str, int, float]] = []
    for index, hold in enumerate(holds):
        stil = hold if index in (0, aantal - 1) else hold - fade
        stukken.append(("hold", index, max(stil, 1 / 30)))
        if index < aantal - 1:
            stukken.append(("xfade", index, fade))
    return stukken


def _frame_counts(stukken: list[tuple[str, int, float]], fps: int) -> list[int]:
    """Zet seconden om in hele beeldjes zonder dat de afrondingen oplopen.

    Per stuk afronden zou bij zestig scenes een seconde kunnen schelen, en
    dan loopt het beeld uit de pas met de stem. Daarom wordt de grens van
    elk stuk afgerond, niet de lengte.
    """
    aantallen: list[int] = []
    verstreken = 0.0
    vorige = 0
    for _, _, seconden in stukken:
        verstreken += seconden
        grens = round(verstreken * fps)
        aantallen.append(max(1, grens - vorige))
        vorige = grens
    return aantallen


def build_video(
    cfg: Config,
    timeline: Timeline,
    audio_path: Path,
    out_path: Path,
    workdir: Path,
    progress: Progress = _noop,
) -> Path:
    """Vloeit de PNG's aan elkaar en encodeert samen met het audiospoor.

    Dit gebeurt in stukjes en niet in één aanroep. Eén ffmpeg-opdracht met
    alle beelden tegelijk vraagt geheugen naar rato van het aantal scenes:
    elk beeld is een eigen invoer die vanaf seconde nul staat te decoderen
    terwijl de eerste overgang nog bezig is. Bij een verhaal van acht
    minuten (ruim zestig beelden) liep dat op tot dertien gigabyte en werd
    ffmpeg door het systeem afgeschoten, halverwege het encoderen.

    Nu wordt elk stuk apart gecodeerd — nooit meer dan twee beelden tegelijk
    in het geheugen — en worden de stukken daarna aan elkaar geplakt zonder
    opnieuw te coderen. Het resultaat is beeld voor beeld hetzelfde; alleen
    het geheugengebruik hangt niet meer af van de lengte van het verhaal.
    """
    fps = cfg.fps
    fade = float(cfg.video.get("crossfade_seconds", 0.6))
    frames_dir = workdir / "frames"
    deel_dir = workdir / "segments"
    if deel_dir.exists():
        shutil.rmtree(deel_dir)
    deel_dir.mkdir(parents=True)

    stukken = plan_segments(list(timeline.holds), fade)
    beeldjes = _frame_counts(stukken, fps)
    encoder = _encoder_args(cfg)
    filters = f"fps={fps},format=yuv420p,setsar=1"

    delen: list[Path] = []
    for nummer, ((soort, index, seconden), aantal) in enumerate(zip(stukken, beeldjes)):
        doel = deel_dir / f"{nummer:04d}.mp4"
        eerste = frames_dir / f"{timeline.scenes[index].id}.png"
        ruim = (aantal + 2) / fps          # iets langer invoeren dan we afnemen

        if soort == "hold":
            _run_ffmpeg([
                "-loop", "1", "-t", f"{ruim:.3f}", "-i", str(eerste),
                "-vf", filters, "-frames:v", str(aantal), *encoder, str(doel),
            ])
        else:
            tweede = frames_dir / f"{timeline.scenes[index + 1].id}.png"
            _run_ffmpeg([
                "-loop", "1", "-t", f"{ruim:.3f}", "-i", str(eerste),
                "-loop", "1", "-t", f"{ruim:.3f}", "-i", str(tweede),
                "-filter_complex",
                f"[0:v]{filters}[a];[1:v]{filters}[b];"
                f"[a][b]xfade=transition=fade:duration={seconden:.3f}:offset=0[v]",
                "-map", "[v]", "-frames:v", str(aantal), *encoder, str(doel),
            ])

        delen.append(doel)
        progress("encoderen", 0.75 + 0.2 * (nummer + 1) / len(stukken))

    lijst = deel_dir / "delen.txt"
    lijst.write_text("".join(f"file '{deel.name}'\n" for deel in delen), encoding="utf-8")

    # Alle stukken hebben dezelfde encoder-instellingen, dus aan elkaar
    # plakken kan zonder opnieuw te coderen. Dat is bijna gratis.
    beeldspoor = deel_dir / "beeld.mp4"
    _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lijst),
                 "-c", "copy", str(beeldspoor)])

    progress("geluid eronder", 0.97)
    loudness = float(cfg.safety.get("loudness_lufs", -14))
    _run_ffmpeg([
        "-i", str(beeldspoor), "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a",
        "-af", f"loudnorm=I={loudness}:TP=-1.5:LRA=11",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(out_path),
    ])

    shutil.rmtree(deel_dir, ignore_errors=True)
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
