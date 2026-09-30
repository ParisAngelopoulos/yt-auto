"""Opdrachtregel voor de pipeline.

    ytauto setup      sleutels invoeren en meteen testen
    ytauto panel      bedieningspagina openen (twee knoppen)
    ytauto script     laat een aflevering schrijven
    ytauto short      maak een Short: staand beeld, rond de minuut
    ytauto descent    maak een afdaling: doorlopende beweging
    ytauto video      maak de video van het laatste script
    ytauto publish    zet die video op YouTube
    ytauto run        alles achter elkaar, zonder tussenkomst
    ytauto library    alles wat er ooit geschreven is
    ytauto open KEY   een oudere aflevering terughalen
    ytauto find TEXT  zoek in alle gesproken tekst
    ytauto sql "..."  een eigen SELECT op de database
    ytauto export     alles als JSON wegschrijven
    ytauto status     wat is er gemaakt en wat staat er klaar
    ytauto voice      de gratis stem bekijken en testen
    ytauto check      controleer de sleutels en de omgeving
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config, write_secrets
from .pipeline import (adopt_loose_scripts, load_current, make_script, make_video,
                       open_episode, publish, run_once)
from .db import Store


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


def cmd_short(args) -> int:
    """Schrijft en maakt een Short in één keer: staand, rond de minuut."""
    from .pipeline import make_short

    cfg = load_config()
    staand, episode = make_short(cfg, hint=args.hint)
    bp = episode.blueprint
    print(f"\n  {bp.title}")
    print(f"  {len(bp.beats)} beats, {bp.word_count} woorden, "
          f"ongeveer {bp.estimated_duration:.0f} seconden\n")
    print(bp.transcript())

    if args.script_only:
        print(f"\n  Opgeslagen. Video maken met: ytauto video")
        return 0

    print()
    make_video(staand, episode, progress=_progress)
    print(f"  Klaar: {episode.video_path}")
    return 0


def cmd_descent(args) -> int:
    """Een afdaling: doorlopende beweging, geen diashow."""
    from .pipeline import load_journeys, make_descent

    cfg = load_config()
    if args.list:
        for reis in load_journeys():
            print(f"  {reis['key']:12} {reis['title']}")
        return 0

    video = make_descent(cfg, key=args.key or "", progress=_progress,
                         preview_seconds=args.preview or 0.0)
    print(f"  Klaar: {video}")
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

    print("\n  Sleutels instellen. Enter overslaan laat een bestaande sleutel staan.")
    print("  Alles is optioneel: zonder sleutels draait de studio gratis.\n")
    vragen = [
        ("ANTHROPIC_API_KEY", "Claude (schrijft de scripts; zonder sleutel doet de verteller het)",
         "console.anthropic.com/settings/keys", bool(huidig.anthropic_api_key)),
        ("ELEVENLABS_API_KEY", "ElevenLabs (spreekt in; zonder sleutel doet Piper het)",
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


def cmd_library(args) -> int:
    """Alles wat er ooit geschreven is, uit de database."""
    store = Store()
    adopt_loose_scripts(store)
    rijen = store.library(limit=args.limit, search=args.search or "")

    if not rijen:
        print("  Nog niets geschreven. Draai: ytauto script")
        return 0

    merk = {"uploaded": "online", "produced": "klaar ", "planned": "script",
            "failed": "MISLUK"}
    print()
    for rij in rijen:
        minuten = (rij["duration_s"] or rij["estimated_seconds"] or 0) / 60
        print(f"  {merk.get(rij['status'], rij['status']):6}  {minuten:4.1f}m  "
              f"{rij['beats']:3} sc  {rij['title'][:56]}")
        print(f"          {rij['key']}")

    s = store.stats()
    print(f"\n  {s['afleveringen']} afleveringen, {s['zinnen']} zinnen, "
          f"{s['woorden']} woorden, {s['online']} online\n")
    return 0


def cmd_open(args) -> int:
    episode = open_episode(args.key)
    if episode is None:
        print(f"  Geen aflevering met sleutel {args.key!r}. Kijk met: ytauto library")
        return 1
    print(f"\n  {episode.blueprint.title}\n")
    print(episode.blueprint.transcript())
    print(f"\n  Staat nu klaar. Video maken met: ytauto video")
    return 0


def cmd_find(args) -> int:
    """Zoekt in alle gesproken tekst van alle afleveringen."""
    rijen = Store().search_lines(args.text, limit=args.limit)
    if not rijen:
        print(f"  Niets gevonden voor {args.text!r}.")
        return 0
    print()
    for rij in rijen:
        print(f"  {rij['title'][:44]:46} [{rij['mode']:13}] {rij['narration']}")
    print(f"\n  {len(rijen)} regels\n")
    return 0


def cmd_sql(args) -> int:
    """Een eigen SELECT op de database."""
    try:
        rijen = Store().query(args.query)
    except Exception as exc:                                    # noqa: BLE001
        print(f"  {exc}")
        return 1
    if not rijen:
        print("  Geen rijen.")
        return 0

    kolommen = rijen[0].keys()
    breedtes = [max(len(k), max(len(str(r[k])) for r in rijen)) for k in kolommen]
    print()
    print("  " + "  ".join(k.ljust(b) for k, b in zip(kolommen, breedtes)))
    print("  " + "  ".join("-" * b for b in breedtes))
    for rij in rijen:
        print("  " + "  ".join(str(rij[k]).ljust(b) for k, b in zip(kolommen, breedtes)))
    print(f"\n  {len(rijen)} rijen\n")
    return 0


def cmd_export(args) -> int:
    doel = Path(args.path)
    aantal = Store().export_all(doel)
    print(f"  {aantal} afleveringen weggeschreven naar {doel}")
    return 0


def cmd_check(args) -> int:
    from .pipeline import PAID_PROVIDERS, resolve_script_provider, script_chain
    from .tts import voice_status

    cfg = load_config()
    secrets = cfg.secrets

    schrijver = resolve_script_provider(cfg)
    stem = voice_status(cfg)
    gratis = schrijver not in PAID_PROVIDERS and stem["free"]

    ingesteld = cfg.script.get("provider", "auto")
    keten = "" if schrijver == ingesteld else \
        f"  (ingesteld: {ingesteld} — {' -> '.join(script_chain(cfg))})"

    print(f"  Kanaal      : {cfg.channel['name']} ({cfg.channel['language']})")
    print(f"  Scripts     : {schrijver}{keten}")
    print(f"  Stem        : {stem['label']}"
          f"{' — ' + stem['detail'] if stem.get('detail') else ''}")
    if stem.get("reason"):
        print(f"                {stem['reason']}")
    print(f"  Kosten      : {'niets — alles draait lokaal' if gratis else 'er wordt een betaalde dienst gebruikt'}")
    print()
    print(f"  Anthropic   : {'gevonden' if secrets.anthropic_api_key else 'niet ingesteld (optioneel)'}")
    print(f"  ElevenLabs  : {'gevonden' if secrets.elevenlabs_api_key else 'niet ingesteld (optioneel)'}")
    print(f"  YouTube     : {'compleet' if secrets.can_upload() else 'ONTBREEKT — publiceren kan nog niet'}")

    from .scripting.ollama_writer import check_credentials as ollama_check

    info = ollama_check(cfg)
    print(f"  Ollama      : {info.get('detail') or info['reason']}")

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

    from .scripting.local_writer import available

    bank = available()
    print(f"  Verteller   : {len(bank['traditions'])} tradities x "
          f"{len(bank['patterns'])} verhaalvormen, altijd beschikbaar")
    return 0


def cmd_voice(args) -> int:
    """De gratis stem: staat hij klaar, en hoe klinkt hij."""
    from .tts import piper, voice_status

    cfg = load_config()
    stem = voice_status(cfg)
    print(f"\n  Stem in gebruik: {stem['label']}")
    if stem.get("detail"):
        print(f"  {stem['detail']}")
    if stem.get("reason"):
        print(f"  {stem['reason']}")

    if args.download or args.test:
        if stem["provider"] != "piper":
            print("  Dit werkt alleen met de gratis stem (tts.provider: piper).")
            return 1
        naam = piper.model_name(cfg)
        try:
            piper.ensure_model(naam)
        except piper.PiperUnavailable as exc:
            print(f"  {exc}")
            return 1

    if args.test:
        from .pipeline import OUT_DIR
        from .tts import synthesize

        doel = OUT_DIR / "stemtest.mp3"
        zin = ("There was once a ferryman who knew the river better than he "
               "knew his own hands.")
        seconden = synthesize(cfg, zin, doel, cache_dir=OUT_DIR / "voice-cache")
        print(f"  Proefzin ingesproken: {doel} ({seconden:.1f} seconden)")
        return 0

    print("\n  Andere stemmen (zet de naam bij tts.voice_model in channel.yaml):")
    for naam, omschrijving in piper.SUGGESTED.items():
        merk = "*" if naam == piper.model_name(cfg) else " "
        print(f"   {merk} {naam:38} {omschrijving}")
    print("\n  Alles beluisteren: https://rhasspy.github.io/piper-samples\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ytauto", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command")

    panel = subparsers.add_parser("panel", help="bedieningspagina openen")
    panel.add_argument("--port", type=int, default=8765)
    panel.add_argument("--no-browser", action="store_true")
    panel.set_defaults(func=cmd_panel)

    script = subparsers.add_parser("script", help="laat een aflevering schrijven")
    script.add_argument("--hint", help="optionele wens voor het onderwerp")
    script.set_defaults(func=cmd_script)

    short = subparsers.add_parser("short", help="maak een Short (staand, ~1 minuut)")
    short.add_argument("--hint", help="optionele wens voor het onderwerp")
    short.add_argument("--script-only", action="store_true",
                       help="alleen schrijven, nog niet renderen")
    short.set_defaults(func=cmd_short)

    descent = subparsers.add_parser("descent", help="maak een afdaling (staand, doorlopend)")
    descent.add_argument("--key", help="welke reis uit config/journeys.yaml")
    descent.add_argument("--list", action="store_true", help="toon de beschikbare reizen")
    descent.add_argument("--preview", type=float, nargs="?", const=20.0, metavar="SEC",
                         help="stille proefversie van zoveel seconden (standaard 20)")
    descent.set_defaults(func=cmd_descent)

    subparsers.add_parser("video", help="maak de video").set_defaults(func=cmd_video)
    subparsers.add_parser("publish", help="publiceer op YouTube").set_defaults(func=cmd_publish)

    run = subparsers.add_parser("run", help="alles achter elkaar")
    run.add_argument("--no-publish", action="store_true", help="wel maken, niet uploaden")
    run.set_defaults(func=cmd_run)

    subparsers.add_parser("setup", help="sleutels invoeren en testen").set_defaults(func=cmd_setup)

    library = subparsers.add_parser("library", help="alles wat er geschreven is")
    library.add_argument("--limit", type=int, default=50)
    library.add_argument("--search", help="zoek in titel en idee")
    library.set_defaults(func=cmd_library)

    openen = subparsers.add_parser("open", help="een oudere aflevering terughalen")
    openen.add_argument("key", help="de sleutel uit 'ytauto library'")
    openen.set_defaults(func=cmd_open)

    find = subparsers.add_parser("find", help="zoek in alle gesproken tekst")
    find.add_argument("text")
    find.add_argument("--limit", type=int, default=40)
    find.set_defaults(func=cmd_find)

    sql = subparsers.add_parser("sql", help="een eigen SELECT op de database")
    sql.add_argument("query")
    sql.set_defaults(func=cmd_sql)

    export = subparsers.add_parser("export", help="alles als JSON wegschrijven")
    export.add_argument("path", nargs="?", default="export.json")
    export.set_defaults(func=cmd_export)
    voice = subparsers.add_parser("voice", help="de gratis stem bekijken en testen")
    voice.add_argument("--download", action="store_true", help="stemmodel nu ophalen")
    voice.add_argument("--test", action="store_true", help="een proefzin inspreken")
    voice.set_defaults(func=cmd_voice)

    subparsers.add_parser("status", help="wat is er gemaakt").set_defaults(func=cmd_status)
    subparsers.add_parser("check", help="controleer sleutels en omgeving").set_defaults(func=cmd_check)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
