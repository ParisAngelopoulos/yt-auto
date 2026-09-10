"""Opdrachtregel voor de pipeline.

    ytauto setup      sleutels invoeren en meteen testen
    ytauto panel      bedieningspagina openen (twee knoppen)
    ytauto script     laat Claude een aflevering schrijven
    ytauto video      maak de video van het laatste script
    ytauto publish    zet die video op YouTube
    ytauto run        alles achter elkaar, zonder tussenkomst
    ytauto status     wat is er gemaakt en wat staat er klaar
    ytauto check      controleer de sleutels en de omgeving
"""

from __future__ import annotations

import argparse
import sys

from .config import load_config, write_secrets
from .pipeline import load_current, make_script, make_video, publish, run_once
from .state import Store


def _progress(message: str, fraction: float) -> None:
    bar = "#" * int(fraction * 28)
    sys.stdout.write(f"\r  [{bar:<28}] {fraction * 100:3.0f}%  {message[:44]:<44}")
    sys.stdout.flush()
    if fraction >= 1.0:
        print()


def cmd_panel(args) -> int:
    from .ui.server import serve

    serve(port=args.port, open_browser=not args.no_browser)
    return 0


def cmd_script(args) -> int:
    cfg = load_config()
    episode = make_script(cfg, hint=args.hint)
    bp = episode.blueprint
    print(f"\n  {bp.title}")
    print(f"  {bp.idea}")
    print(f"  {len(bp.beats)} scenes, {bp.word_count} woorden, "
          f"ongeveer {bp.estimated_duration / 60:.1f} minuten\n")
    print(bp.transcript())
    print(f"\n  Opgeslagen in {episode.workdir / 'blueprint.json'}")
    return 0


def cmd_video(args) -> int:
    cfg = load_config()
    episode = load_current(cfg)
    if episode is None:
        print("Geen script gevonden. Draai eerst: ytauto script")
        return 1
    print(f"  {episode.blueprint.title}")
    make_video(cfg, episode, progress=_progress)
    print(f"  Klaar: {episode.video_path}")
    return 0


def cmd_publish(args) -> int:
    cfg = load_config()
    episode = load_current(cfg)
    if episode is None or not episode.has_video:
        print("Geen video gevonden. Draai eerst: ytauto video")
        return 1
    video_id = publish(cfg, episode)
    print(f"  https://youtu.be/{video_id}")
    return 0


def cmd_run(args) -> int:
    cfg = load_config()
    result = run_once(cfg, progress=_progress, do_publish=not args.no_publish)
    print(f"\n  {result['status']}: {result.get('title', '')}")
    if result.get("reason"):
        print(f"  {result['reason']}")
    if result.get("video_id"):
        print(f"  https://youtu.be/{result['video_id']}")
    return 0


def cmd_setup(args) -> int:
    """Vraagt de sleutels, slaat ze op en test ze meteen."""
    from getpass import getpass

    from .config import Secrets
    from .ui.server import test_all_keys

    cfg = load_config()
    huidig = cfg.secrets

    print("\n  Sleutels instellen. Enter overslaan laat een bestaande sleutel staan.\n")
    vragen = [
        ("ANTHROPIC_API_KEY", "Claude (schrijft de scripts)",
         "console.anthropic.com/settings/keys", bool(huidig.anthropic_api_key)),
        ("ELEVENLABS_API_KEY", "ElevenLabs (spreekt in)",
         "elevenlabs.io -> Settings -> API Keys", bool(huidig.elevenlabs_api_key)),
        ("YOUTUBE_CLIENT_ID", "YouTube client id",
         "python scripts/get_youtube_token.py", bool(huidig.youtube_client_id)),
        ("YOUTUBE_CLIENT_SECRET", "YouTube client secret", "", bool(huidig.youtube_client_secret)),
        ("YOUTUBE_REFRESH_TOKEN", "YouTube refresh token", "", bool(huidig.youtube_refresh_token)),
    ]

    ingevoerd: dict[str, str] = {}
    for naam, omschrijving, bron, aanwezig in vragen:
        status = "al ingesteld" if aanwezig else "nog leeg"
        print(f"  {omschrijving}  [{status}]")
        if bron:
            print(f"    {bron}")
        waarde = getpass("    waarde: ").strip()
        if waarde:
            ingevoerd[naam] = waarde
        print()

    opgeslagen = write_secrets(ingevoerd)
    if opgeslagen:
        print(f"  Opgeslagen in .env: {', '.join(opgeslagen)}\n")
    else:
        print("  Niets gewijzigd. Bestaande sleutels worden nu getest.\n")

    cfg.secrets = Secrets.from_env()
    for naam, info in test_all_keys(cfg).items():
        if info.get("ok"):
            extra = info.get("detail") or info.get("warning") or ""
            print(f"  {naam:12} werkt {('- ' + extra) if extra else ''}")
        else:
            print(f"  {naam:12} FOUT: {info['reason']}")
    print()
    return 0


def cmd_status(args) -> int:
    cfg = load_config()
    store = Store()
    rows = store.all_episodes()
    print(f"  Kanaal: {cfg.channel['name']}")
    print(f"  Deze week gepubliceerd: {store.published_since(7)}/"
          f"{cfg.publish.get('max_per_week', 4)}")
    print(f"  Afleveringen in de boekhouding: {len(rows)}\n")
    for row in rows[:20]:
        marker = {"uploaded": "online", "produced": "klaar", "planned": "script",
                  "failed": "MISLUKT"}.get(row["status"], row["status"])
        print(f"  {marker:8} {row['title'][:64]}")
    return 0


def cmd_check(args) -> int:
    cfg = load_config()
    secrets = cfg.secrets
    print(f"  Kanaal      : {cfg.channel['name']} ({cfg.channel['language']})")
    print(f"  Scripts     : {cfg.script.get('provider')} / {cfg.script.get('model')}")
    print(f"  Stem        : {cfg.tts.get('provider')}")
    print(f"  Anthropic   : {'gevonden' if secrets.anthropic_api_key else 'ONTBREEKT'}")
    print(f"  ElevenLabs  : {'gevonden' if secrets.elevenlabs_api_key else 'ONTBREEKT'}")
    print(f"  YouTube     : {'compleet' if secrets.can_upload() else 'ONTBREEKT'}")

    if secrets.elevenlabs_api_key:
        from .tts.elevenlabs import check_credentials

        info = check_credentials(cfg)
        if info["ok"]:
            print(f"  ElevenLabs tegoed: {info['remaining']:,} van "
                  f"{info['limit']:,} tekens ({info['tier']})")
        else:
            print(f"  ElevenLabs: {info['reason']}")

    if secrets.can_upload():
        from .youtube.upload import check_credentials as yt_check

        info = yt_check(cfg)
        print(f"  YouTube-kanaal: {info.get('channel') or info.get('reason')}")

    from .media import MediaError, describe

    try:
        print(f"  ffmpeg      : {describe()}")
    except MediaError as exc:
        print(f"  ffmpeg      : ONTBREEKT — {exc}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ytauto", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command")

    panel = subparsers.add_parser("panel", help="bedieningspagina openen")
    panel.add_argument("--port", type=int, default=8765)
    panel.add_argument("--no-browser", action="store_true")
    panel.set_defaults(func=cmd_panel)

    script = subparsers.add_parser("script", help="laat Claude een aflevering schrijven")
    script.add_argument("--hint", help="optionele wens voor het onderwerp")
    script.set_defaults(func=cmd_script)

    subparsers.add_parser("video", help="maak de video").set_defaults(func=cmd_video)
    subparsers.add_parser("publish", help="publiceer op YouTube").set_defaults(func=cmd_publish)

    run = subparsers.add_parser("run", help="alles achter elkaar")
    run.add_argument("--no-publish", action="store_true", help="wel maken, niet uploaden")
    run.set_defaults(func=cmd_run)

    subparsers.add_parser("setup", help="sleutels invoeren en testen").set_defaults(func=cmd_setup)
    subparsers.add_parser("status", help="wat is er gemaakt").set_defaults(func=cmd_status)
    subparsers.add_parser("check", help="controleer sleutels en omgeving").set_defaults(func=cmd_check)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
