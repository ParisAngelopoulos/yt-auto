"""Lokale bedieningspagina.

Draait op je eigen machine, praat rechtstreeks met de pipeline. Bewust
gebouwd op de standaardbibliotheek: geen Flask, geen build-stap, geen
extra dingen die stuk kunnen. Starten met:  python -m ytauto.ui

Knop 1 laat een aflevering bedenken en schrijven, zodat je hem kunt lezen.
Knop 2 zet datzelfde script om in een complete video.
"""

from __future__ import annotations

import json
import threading
import traceback
import webbrowser
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..config import ROOT, SECRET_KEYS, Config, Secrets, load_config, write_secrets
from ..pipeline import (PAID_PROVIDERS, Episode, adopt_loose_scripts, load_current,
                        make_script, make_video, open_episode, publish,
                        resolve_script_provider)
from ..db import Store
from ..tts import voice_status

PANEL = Path(__file__).parent / "panel.html"
FONT_DIR = ROOT / "assets" / "fonts"


# ---------------------------------------------------------------------------
#  Achtergrondtaak
# ---------------------------------------------------------------------------


@dataclass
class Job:
    """Eén lopende taak. Er draait er nooit meer dan één tegelijk."""

    kind: str = ""
    running: bool = False
    fraction: float = 0.0
    message: str = ""
    error: str = ""
    result: dict = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def note(self, message: str, fraction: float | None = None) -> None:
        self.message = message
        if fraction is not None:
            self.fraction = max(0.0, min(1.0, fraction))
        if not self.log or self.log[-1] != message:
            self.log.append(message)
            del self.log[:-40]


JOB = Job()
JOB_LOCK = threading.Lock()

# Laatste uitslag per dienst. Een sleutel die ingevuld is, is nog niet
# hetzelfde als een sleutel die werkt; de pagina moet dat verschil tonen.
LAST_TEST: dict[str, dict] = {}


def run_in_background(kind: str, work) -> bool:
    """Start een taak, of weiger als er al één loopt."""
    with JOB_LOCK:
        if JOB.running:
            return False
        JOB.kind = kind
        JOB.running = True
        JOB.fraction = 0.0
        JOB.error = ""
        JOB.result = {}
        JOB.log = []
        JOB.note(f"{kind} gestart", 0.01)

    def wrapper() -> None:
        try:
            JOB.result = work(JOB) or {}
            JOB.note("klaar", 1.0)
        except Exception as exc:                                # noqa: BLE001
            JOB.error = str(exc)
            JOB.note(f"mislukt: {exc}", JOB.fraction)
            traceback.print_exc()
        finally:
            JOB.running = False

    threading.Thread(target=wrapper, daemon=True).start()
    return True


# ---------------------------------------------------------------------------
#  Gegevens voor de pagina
# ---------------------------------------------------------------------------


def episode_payload(episode: Episode | None) -> dict | None:
    if episode is None:
        return None
    bp = episode.blueprint
    return {
        "key": bp.key,
        "idea": bp.idea,
        "title": bp.title,
        "description": bp.description,
        "tags": bp.tags,
        "lesson_kind": bp.lesson_kind,
        "source": bp.source,
        "items": [asdict(i) for i in bp.items],
        "beats": [asdict(b) for b in bp.beats],
        "word_count": bp.word_count,
        "estimated_minutes": round(bp.estimated_duration / 60, 1),
        "has_video": episode.has_video,
        "video_size_mb": (round(episode.video_path.stat().st_size / 1e6, 1)
                          if episode.has_video else 0),
    }


def test_all_keys(cfg: Config) -> dict:
    """Controleert elke ingevulde sleutel bij de dienst zelf.

    Anthropic en ElevenLabs kosten hier niets: het zijn opvragingen zonder
    tokens. Beter dat je het hier hoort dan halverwege een video.
    """
    resultaat: dict[str, dict] = {}

    if cfg.secrets.anthropic_api_key:
        from ..scripting.claude_writer import check_credentials

        resultaat["anthropic"] = check_credentials(cfg)

    if cfg.secrets.elevenlabs_api_key:
        from ..tts.elevenlabs import check_credentials as eleven_check

        info = eleven_check(cfg)
        if info["ok"]:
            info["detail"] = (f"{info['remaining']:,} tekens over "
                              f"({info['tier']})").replace(",", ".")
        resultaat["elevenlabs"] = info

    if cfg.secrets.can_upload():
        from ..youtube.upload import check_credentials as yt_check

        info = yt_check(cfg)
        if info.get("ok"):
            info["detail"] = f"kanaal: {info['channel']}"
        resultaat["youtube"] = info

    LAST_TEST.clear()
    LAST_TEST.update(resultaat)
    return resultaat


def library_payload(store: Store, search: str = "") -> dict:
    """Het archief: alles wat er ooit geschreven is.

    Het script staat in de database en blijft dus altijd. De gerenderde
    video staat in out/ en kan weg zijn; daarom wordt per aflevering
    gekeken of het bestand er nog is. 'Klaar' beweren terwijl er niets meer
    staat, is misleidend.
    """
    from ..pipeline import OUT_DIR

    def heeft_video(slug: str) -> bool:
        pad = OUT_DIR / slug / "video.mp4"
        return pad.exists() and pad.stat().st_size > 10_000

    rijen = store.library(limit=200, search=search)
    return {
        "stats": store.stats(),
        "episodes": [{
            "key": r["key"],
            "title": r["title"],
            "idea": r["idea"],
            "kind": r["lesson_kind"],
            "source": r["source"],
            "status": r["status"],
            "has_video": heeft_video(r["slug"]),
            "beats": r["beats"],
            "words": r["word_count"],
            "minutes": round((r["duration_s"] or r["estimated_seconds"] or 0) / 60, 1),
            "video_id": r["video_id"],
            "created_at": (r["created_at"] or "")[:10],
        } for r in rijen],
    }


def status_payload(cfg: Config) -> dict:
    secrets = cfg.secrets
    store = Store()
    schrijver = resolve_script_provider(cfg)
    stem = voice_status(cfg)
    return {
        # Wat er straks werkelijk gebeurt als je op de knop drukt, en of daar
        # iets voor afgeschreven wordt. Dat hoort op de pagina te staan
        # voordat je klikt, niet in de rekening erna.
        "writer": schrijver,
        "voice": stem,
        "free": schrijver not in PAID_PROVIDERS and stem["free"],
        "channel": cfg.channel["name"],
        "language": cfg.channel["language"],
        "target_minutes": cfg.video["target_duration_minutes"],
        "script_provider": cfg.script.get("provider", "claude"),
        "keys": {
            "anthropic": bool(secrets.anthropic_api_key),
            "elevenlabs": bool(secrets.elevenlabs_api_key),
            "youtube": secrets.can_upload(),
        },
        "voice_provider": stem["provider"],
        "key_tests": {naam: bool(info.get("ok")) for naam, info in LAST_TEST.items()},
        "published_this_week": store.published_since(7),
        "max_per_week": cfg.publish.get("max_per_week", 4),
        "episode": episode_payload(load_current(cfg)),
        "job": {
            "kind": JOB.kind, "running": JOB.running, "fraction": JOB.fraction,
            "message": JOB.message, "error": JOB.error, "log": JOB.log[-12:],
            "result": JOB.result,
        },
    }


# ---------------------------------------------------------------------------
#  HTTP
# ---------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    cfg: Config

    def log_message(self, fmt: str, *args) -> None:       # stil in de terminal
        pass

    # -- helpers --

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_json({"error": "niet gevonden"}, 404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "none")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # -- routes --

    def do_GET(self) -> None:                             # noqa: N802
        route = urlparse(self.path).path

        if route in ("/", "/index.html"):
            self._send_file(PANEL, "text/html; charset=utf-8")
        elif route.startswith("/fonts/"):
            # De lettertypes komen uit de projectmap, niet van internet: de
            # studio moet er ook goed uitzien zonder verbinding. Alleen de
            # bestandsnaam wordt gebruikt, zodat ../ nergens heen leidt.
            naam = Path(route).name
            if naam.endswith(".ttf") and (FONT_DIR / naam).is_file():
                self._send_file(FONT_DIR / naam, "font/ttf")
            else:
                self._send_json({"error": "onbekend lettertype"}, 404)

        elif route == "/api/status":
            self._send_json(status_payload(self.cfg))
        elif route == "/api/library":
            zoek = parse_qs(urlparse(self.path).query).get("search", [""])[0]
            self._send_json(library_payload(Store(), zoek))
        elif route == "/api/video.mp4":
            episode = load_current(self.cfg)
            if episode and episode.has_video:
                self._send_file(episode.video_path, "video/mp4")
            else:
                self._send_json({"error": "nog geen video"}, 404)
        elif route == "/api/thumbnail.jpg":
            episode = load_current(self.cfg)
            if episode and episode.thumbnail_path.exists():
                self._send_file(episode.thumbnail_path, "image/jpeg")
            else:
                self._send_json({"error": "nog geen thumbnail"}, 404)
        else:
            self._send_json({"error": "onbekend pad"}, 404)

    def do_POST(self) -> None:                            # noqa: N802
        route = urlparse(self.path).path
        body = self._read_body()

        if route == "/api/script":
            hint = (body.get("hint") or "").strip() or None

            def work(job: Job) -> dict:
                job.note("de aflevering wordt bedacht en geschreven", 0.3)
                episode = make_script(self.cfg, hint=hint)
                job.note(f"script klaar: {episode.blueprint.title}", 1.0)
                return {"key": episode.blueprint.key}

            started = run_in_background("script", work)

        elif route == "/api/video":
            episode = load_current(self.cfg)
            if episode is None:
                self._send_json({"error": "Maak eerst een script."}, 400)
                return

            def work(job: Job) -> dict:
                def progress(message: str, fraction: float) -> None:
                    job.note(message, fraction)

                make_video(self.cfg, episode, progress=progress)
                return {"key": episode.blueprint.key}

            started = run_in_background("video", work)

        elif route == "/api/open":
            episode = open_episode(str(body.get("key", "")))
            if episode is None:
                self._send_json({"error": "Die aflevering staat niet in het archief."}, 404)
            else:
                self._send_json({"key": episode.blueprint.key,
                                 "title": episode.blueprint.title})
            return

        elif route == "/api/keys":
            # De server luistert alleen op 127.0.0.1, dus dit blijft binnen
            # je eigen machine. Waarden worden nooit teruggestuurd naar de
            # pagina; alleen of ze werken.
            opgeslagen = write_secrets({k: str(body.get(k, "")) for k in SECRET_KEYS})
            self.cfg.secrets = Secrets.from_env()
            self._send_json({"saved": opgeslagen, "results": test_all_keys(self.cfg)})
            return

        elif route == "/api/publish":
            episode = load_current(self.cfg)
            if episode is None or not episode.has_video:
                self._send_json({"error": "Maak eerst een video."}, 400)
                return

            def work(job: Job) -> dict:
                job.note("uploaden naar YouTube", 0.4)
                video_id = publish(self.cfg, episode)
                return {"video_id": video_id, "url": f"https://youtu.be/{video_id}"}

            started = run_in_background("publiceren", work)

        else:
            self._send_json({"error": "onbekend pad"}, 404)
            return

        if not started:
            self._send_json({"error": f"Er loopt al een taak ({JOB.kind})."}, 409)
        else:
            self._send_json({"started": True})


def serve(port: int = 8765, open_browser: bool = True) -> None:
    Handler.cfg = load_config()

    opgenomen = adopt_loose_scripts()
    if opgenomen:
        print(f"  {len(opgenomen)} losse script(s) opgenomen in de database.")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"

    print(f"\n  Bedieningspagina staat klaar op {url}")
    print("  Stoppen met Ctrl+C\n")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Gestopt.")
    finally:
        server.server_close()
