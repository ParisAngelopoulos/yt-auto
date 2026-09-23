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
from .db import Store
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


# Wie het script mag schrijven, en wat de terugval is als dat niet lukt.
# 'auto' is de standaard: hij pakt het beste wat beschikbaar is en eindigt
# altijd bij de ingebouwde verteller, zodat de knop nooit niets doet.
SCRIPT_CHAIN = {
    "auto":     ("claude", "ollama", "local"),
    "claude":   ("claude", "local"),
    "ollama":   ("ollama", "local"),
    "local":    ("local",),
    "template": ("template",),
}


def script_chain(cfg: Config) -> tuple[str, ...]:
    provider = str(cfg.script.get("provider", "auto"))
    return SCRIPT_CHAIN.get(provider, ("local",))


def resolve_script_provider(cfg: Config) -> str:
    """Wie het script straks werkelijk schrijft, zonder er een te laten schrijven.

    Gebruikt door 'ytauto check' en de bedieningspagina: die moeten kunnen
    zeggen of er iets afgeschreven gaat worden voordat je op de knop drukt.
    """
    for provider in script_chain(cfg):
        if provider == "claude":
            if not cfg.secrets.anthropic_api_key:
                continue
            try:
                import anthropic  # noqa: F401
            except ImportError:
                continue
            return "claude"
        if provider == "ollama":
            from .scripting.ollama_writer import is_available

            if not is_available(cfg):
                continue
            return "ollama"
        return provider
    return "local"


# Wat een schrijver kost. 'auto' zonder sleutel komt dus op niets uit.
PAID_PROVIDERS = {"claude"}


def _write_with(cfg: Config, provider: str, store: Store,
                hint: str | None) -> Blueprint:
    """Laat één schrijver het proberen. Kan hij niet, dan volgt de volgende."""
    if provider == "claude":
        from .scripting.claude_writer import write_blueprint as claude_write

        made = [row["title"] for row in store.all_episodes()]
        return claude_write(cfg, already_made=made, hint=hint)

    if provider == "ollama":
        from .scripting.ollama_writer import write_blueprint as ollama_write

        made = [row["title"] for row in store.all_episodes()]
        return ollama_write(cfg, already_made=made, hint=hint)

    verhalen = cfg.channel.get("format", "kids") == "folklore"

    if provider == "template":
        # De oude, kale terugval: alleen wat met de hand in de config staat.
        if verhalen:
            from .scripting.tale_writer import write_blueprint as tale_write

            return tale_write(cfg, taken=store.taken_keys())
        from .scripting.template_writer import write_blueprint as template_write

        return template_write(cfg, pick_next(cfg, store, enforce_rate_limit=False))

    if not verhalen:
        from .scripting.template_writer import write_blueprint as template_write

        return template_write(cfg, pick_next(cfg, store, enforce_rate_limit=False))

    # De drie verhalen uit config/tales.yaml zijn met de hand geschreven en
    # dus beter dan wat de generator maakt. Die gaan voor; is de bank op, dan
    # schrijft de verteller er zelf een, en die raakt nooit op.
    from .scripting.tale_writer import NoTalesLeft
    from .scripting.tale_writer import write_blueprint as tale_write

    try:
        return tale_write(cfg, taken=store.taken_keys())
    except NoTalesLeft:
        from .scripting.local_writer import write_blueprint as local_write

        return local_write(cfg, taken=store.taken_keys(), hint=hint)


def make_script(cfg: Config, hint: str | None = None, store: Store | None = None) -> Episode:
    """Bedenkt en schrijft een aflevering.

    Er is altijd een schrijver beschikbaar. Staat er een sleutel, dan schrijft
    Claude; draait er een lokaal model, dan doet dat het; en anders de
    ingebouwde verteller. Die laatste kost niets en raakt niet op.
    """
    store = store or Store()
    blueprint: Blueprint | None = None
    keten = script_chain(cfg)

    if cfg.script.get("provider", "auto") == "auto":
        # Bij 'auto' is het geen nieuws dat er geen sleutel staat: dan is dit
        # gewoon de gratis weg. Begin dus stil bij de eerste die er echt is,
        # zodat alleen een schrijver die het lát afweten een melding geeft.
        beschikbaar = resolve_script_provider(cfg)
        if beschikbaar in keten:
            keten = keten[keten.index(beschikbaar):]

    for index, provider in enumerate(keten):
        try:
            blueprint = _write_with(cfg, provider, store, hint)
            break
        except Exception as exc:                                # noqa: BLE001
            # Wat er ook misgaat bij een betaalde of externe schrijver — geen
            # sleutel, geen tegoed, geen netwerk, onbruikbare JSON — de
            # volgende in de rij mag het proberen. De laatste is de
            # ingebouwde verteller; gaat die stuk, dan hoor je het wel.
            if index == len(keten) - 1:
                raise
            print(f"  {provider} niet beschikbaar ({exc}); volgende schrijver.")

    if blueprint is None:                                       # pragma: no cover
        raise ValueError("Geen enkele scriptschrijver leverde iets op.")

    report = check_blueprint(cfg, blueprint)
    if not report.ok:
        raise ValueError("Script afgekeurd door de veiligheidscontrole:\n" + report.summary())

    workdir = OUT_DIR / blueprint.slug
    workdir.mkdir(parents=True, exist_ok=True)

    # De database is de bron; het bestand ernaast is er alleen om even in te
    # kunnen kijken. Wie out/ opruimt raakt dus niets kwijt.
    store.save_blueprint(blueprint)
    blueprint.save(workdir / "blueprint.json")

    set_current(blueprint.key)
    return Episode(blueprint=blueprint, workdir=workdir)


# ---------------------------------------------------------------------------
#  Shorts
# ---------------------------------------------------------------------------


def shorts_config(cfg: Config) -> Config:
    """Dezelfde config, maar staand en met een strakker tempo.

    De rest van de pipeline hoeft niets van Shorts te weten: hij leest de
    afmetingen uit `video`, en die worden hier vervangen door wat er in de
    `shorts`-sectie staat.
    """
    import copy

    raw = copy.deepcopy(cfg.raw)
    shorts = raw.get("shorts", {})
    raw["video"].update({
        "width": int(shorts.get("width", 1080)),
        "height": int(shorts.get("height", 1920)),
        "crossfade_seconds": float(shorts.get("crossfade_seconds", 0.35)),
        "lead_in": float(shorts.get("lead_in", 0.15)),
        "tail": float(shorts.get("tail", 0.25)),
    })
    return Config(raw=raw, curriculum=cfg.curriculum, secrets=cfg.secrets)


def make_short(cfg: Config, hint: str | None = None,
               store: Store | None = None) -> tuple[Config, Episode]:
    """Schrijft een Short en geeft de config terug waarmee hij gerenderd wordt.

    Alleen de ingebouwde verteller maakt Shorts. Claude en Ollama schrijven
    lange verhalen; die in een minuut persen levert een samenvatting op, en
    een samenvatting is geen Short.
    """
    from .scripting.local_writer import write_short

    if cfg.channel.get("format", "kids") != "folklore":
        raise ValueError(
            "Shorts bestaan alleen voor de volksverhalen-vorm. "
            "Zet channel.format op 'folklore' in config/channel.yaml."
        )

    store = store or Store()
    staand = shorts_config(cfg)
    blueprint = write_short(staand, taken=store.taken_keys(), hint=hint)

    report = check_blueprint(staand, blueprint)
    if not report.ok:
        raise ValueError("Short afgekeurd door de veiligheidscontrole:\n" + report.summary())

    workdir = OUT_DIR / blueprint.slug
    workdir.mkdir(parents=True, exist_ok=True)
    store.save_blueprint(blueprint)
    blueprint.save(workdir / "blueprint.json")

    set_current(blueprint.key)
    return staand, Episode(blueprint=blueprint, workdir=workdir)


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


def adopt_loose_scripts(store: Store | None = None) -> list[str]:
    """Neemt scripts die nog los op schijf staan alsnog op in de database.

    Draait bij het opstarten. Wie de studio al gebruikte voordat de database
    er was, raakt zo niets kwijt.
    """
    return (store or Store()).import_json_files(OUT_DIR)


def set_current(key: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT.write_text(json.dumps({
        "key": key,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }), encoding="utf-8")


def load_current(cfg: Config, store: Store | None = None) -> Episode | None:
    """De aflevering waar je nu aan werkt, uit de database."""
    if not CURRENT.exists():
        return None
    key = json.loads(CURRENT.read_text(encoding="utf-8")).get("key")
    if not key:
        return None

    blueprint = (store or Store()).load_blueprint(key)
    if blueprint is None:
        return None
    return Episode(blueprint=blueprint, workdir=OUT_DIR / blueprint.slug)


def open_episode(key: str, store: Store | None = None) -> Episode | None:
    """Haalt een oudere aflevering uit het archief en maakt hem de huidige."""
    blueprint = (store or Store()).load_blueprint(key)
    if blueprint is None:
        return None
    workdir = OUT_DIR / blueprint.slug
    workdir.mkdir(parents=True, exist_ok=True)
    set_current(key)
    return Episode(blueprint=blueprint, workdir=workdir)


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
