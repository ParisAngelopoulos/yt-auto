"""Orkestratie: van niets naar een gepubliceerde video.

Drie stappen die los van elkaar aan te roepen zijn, want dat is precies wat
de bedieningspagina nodig heeft: eerst het script laten schrijven en lezen,
daarna pas de video laten maken.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import ROOT, Config
from .planner import NothingToDo, check_rate_limit, pick_next
from .render.thumbnail import build_thumbnail
from .safety import SafetyReport, check_blueprint, check_frames
from .scripting.blueprint import Blueprint
from .state import Store
from .video.assemble import assemble, probe_duration

OUT_DIR = ROOT / "out"
CURRENT = OUT_DIR / "current.json"

Progress = Callable[[str, float], None]


def _noop(message: str, fraction: float) -> None:
    pass


@dataclass
class Episode:
    """Een aflevering met alles wat erbij hoort, op schijf."""

    blueprint: Blueprint
    workdir: Path

    @property
    def video_path(self) -> Path:
        return self.workdir / "video.mp4"

    @property
    def thumbnail_path(self) -> Path:
        return self.workdir / "thumbnail.jpg"

    @property
    def has_video(self) -> bool:
        return self.video_path.exists() and self.video_path.stat().st_size > 10_000


# ---------------------------------------------------------------------------
#  Stap 1: script
# ---------------------------------------------------------------------------


def make_script(cfg: Config, hint: str | None = None, store: Store | None = None) -> Episode:
    """Laat Claude een aflevering bedenken en schrijven.

    Zonder API-sleutel valt dit terug op het sjabloon uit curriculum.yaml,
    zodat de knop altijd iets oplevert.
    """
    store = store or Store()
    provider = cfg.script.get("provider", "claude")

    blueprint: Blueprint | None = None
    if provider == "claude":
        from .scripting.claude_writer import WriterUnavailable, write_blueprint

        made = [row["title"] for row in store.all_episodes()]
        try:
            blueprint = write_blueprint(cfg, already_made=made, hint=hint)
        except WriterUnavailable as exc:
            print(f"  Claude niet beschikbaar ({exc}); sjabloon wordt gebruikt.")

    if blueprint is None:
        from .scripting.template_writer import write_blueprint as template_write

        plan = pick_next(cfg, store, enforce_rate_limit=False)
        blueprint = template_write(cfg, plan)

    report = check_blueprint(cfg, blueprint)
    if not report.ok:
        raise ValueError("Script afgekeurd door de veiligheidscontrole:\n" + report.summary())

    workdir = OUT_DIR / blueprint.slug
    workdir.mkdir(parents=True, exist_ok=True)
    blueprint.save(workdir / "blueprint.json")

    theme = blueprint.items[0].draw if blueprint.items else ""
    store.mark_planned(blueprint.key, blueprint.lesson_kind, theme, blueprint.title)
    set_current(blueprint.slug)
    return Episode(blueprint=blueprint, workdir=workdir)


# ---------------------------------------------------------------------------
#  Stap 2: video
# ---------------------------------------------------------------------------


def episode_seed(key: str) -> int:
    """Vaste seed per aflevering.

    Bewust niet hash(): die is per proces anders, waardoor dezelfde
    aflevering twee keer renderen een ander resultaat gaf.
    """
    import hashlib

    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100_000


def make_video(cfg: Config, episode: Episode, progress: Progress = _noop) -> Episode:
    seed = episode_seed(episode.blueprint.key)
    video, planned = assemble(cfg, episode.blueprint, episode.workdir,
                              seed=seed, progress=progress)

    frame_report = check_frames(cfg, episode.workdir / "frames")
    if not frame_report.ok:
        raise ValueError("Beeld afgekeurd:\n" + frame_report.summary())

    build_thumbnail(episode.blueprint, episode.thumbnail_path)

    Store().mark_produced(episode.blueprint.key, probe_duration(video))
    return episode


# ---------------------------------------------------------------------------
#  Stap 3: publiceren
# ---------------------------------------------------------------------------


def publish(cfg: Config, episode: Episode, store: Store | None = None) -> str:
    from .youtube.upload import upload_video

    store = store or Store()
    check_rate_limit(cfg, store)

    if not episode.has_video:
        raise ValueError("Er is nog geen video om te publiceren.")

    video_id = upload_video(cfg, episode.blueprint, episode.video_path,
                            episode.thumbnail_path)
    store.mark_uploaded(episode.blueprint.key, video_id)
    return video_id


# ---------------------------------------------------------------------------
#  Huidige aflevering
# ---------------------------------------------------------------------------


def set_current(slug: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT.write_text(json.dumps({
        "slug": slug,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }), encoding="utf-8")


def load_current(cfg: Config) -> Episode | None:
    if not CURRENT.exists():
        return None
    slug = json.loads(CURRENT.read_text(encoding="utf-8")).get("slug")
    if not slug:
        return None
    workdir = OUT_DIR / slug
    path = workdir / "blueprint.json"
    if not path.exists():
        return None
    return Episode(blueprint=Blueprint.load(path), workdir=workdir)


def run_once(cfg: Config, progress: Progress = _noop, do_publish: bool = True) -> dict:
    """Volautomatisch: bedenk, schrijf, maak en publiceer. Voor de planner."""
    store = Store()
    try:
        check_rate_limit(cfg, store)
    except NothingToDo as exc:
        return {"status": "skipped", "reason": str(exc)}

    episode = make_script(cfg, store=store)
    progress("script klaar", 0.05)
    make_video(cfg, episode, progress=progress)

    result = {
        "status": "produced",
        "key": episode.blueprint.key,
        "title": episode.blueprint.title,
        "video": str(episode.video_path),
        "duration": probe_duration(episode.video_path),
    }
    if do_publish:
        result["video_id"] = publish(cfg, episode, store=store)
        result["status"] = "published"
    return result
