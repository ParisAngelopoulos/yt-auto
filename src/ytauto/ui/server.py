"""Lokale bedieningspagina.

Draait op je eigen machine, praat rechtstreeks met de pipeline. Bewust
gebouwd op de standaardbibliotheek: geen Flask, geen build-stap, geen
extra dingen die stuk kunnen. Starten met:  python -m ytauto.ui

Knop 1 laat Claude een aflevering bedenken en schrijven, zodat je hem kunt
lezen. Knop 2 zet datzelfde script om in een complete video.
"""

from __future__ import annotations

import json
import threading
import traceback
import webbrowser
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ..config import Config, load_config
from ..pipeline import Episode, load_current, make_script, make_video, publish
from ..state import Store

PANEL = Path(__file__).parent / "panel.html"


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


def status_payload(cfg: Config) -> dict:
    secrets = cfg.secrets
    store = Store()
    return {
        "channel": cfg.channel["name"],
        "language": cfg.channel["language"],
        "target_minutes": cfg.video["target_duration_minutes"],
        "script_provider": cfg.script.get("provider", "claude"),
        "keys": {
            "anthropic": bool(secrets.anthropic_api_key),
            "elevenlabs": bool(secrets.elevenlabs_api_key),
            "youtube": secrets.can_upload(),
        },
        "voice_provider": cfg.tts.get("provider", "elevenlabs"),
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
        elif route == "/api/status":
            self._send_json(status_payload(self.cfg))
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
                job.note("Claude bedenkt en schrijft de aflevering", 0.3)
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
