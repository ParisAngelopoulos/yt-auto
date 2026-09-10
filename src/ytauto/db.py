"""Opslag: één SQLite-bestand met alles wat de studio maakt.

Waarom SQLite en geen Postgres of MySQL: dit is echte SQL, maar zonder
server die moet draaien. Het is één bestand (state/episodes.db) dat je kunt
kopiëren, back-uppen en met elk SQL-programma kunt openen. Voor een studio
die op je eigen laptop draait is dat precies goed.

Wat erin gaat:

    episodes       één rij per aflevering: titel, idee, beschrijving, status
    episode_items  wat er geleerd wordt, in volgorde
    episode_beats  elke gesproken zin, in volgorde
    episode_tags   de YouTube-zoektermen

De scripts stonden eerst alleen als losse JSON-bestanden in out/. Die map
staat in .gitignore, dus wie hem opruimde was zijn scripts kwijt. Nu staat
alles hier, en out/ bevat alleen nog gerenderde bestanden die je opnieuw
kunt maken.

Elke aflevering bewaart daarnaast zijn eigen JSON in de kolom raw_json.
Dat is dubbelop met de tabellen hierboven, en dat is bewust: de tabellen
zijn om in te zoeken, de JSON is de garantie dat je een aflevering altijd
exact terugkrijgt, ook als het schema later verandert.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import ROOT
from .scripting.blueprint import Beat, Blueprint, Item, StoryScene

DB_PATH = ROOT / "state" / "episodes.db"

# Elke stap wordt één keer uitgevoerd; PRAGMA user_version houdt bij hoe ver
# een bestand is. Zo migreert een bestaande database vanzelf mee.
MIGRATIONS: list[str] = [
    # 1 — de oorspronkelijke boekhouding
    """
    CREATE TABLE IF NOT EXISTS episodes (
        key           TEXT PRIMARY KEY,
        lesson_id     TEXT NOT NULL,
        theme_id      TEXT NOT NULL,
        title         TEXT NOT NULL,
        status        TEXT NOT NULL,
        video_id      TEXT,
        duration_s    REAL,
        error         TEXT,
        created_at    TEXT NOT NULL,
        published_at  TEXT
    );
    """,
    # 2 — het script erbij, in doorzoekbare tabellen
    """
    ALTER TABLE episodes RENAME TO episodes_v1;

    CREATE TABLE episodes (
        key               TEXT PRIMARY KEY,
        slug              TEXT NOT NULL,
        title             TEXT NOT NULL,
        idea              TEXT NOT NULL DEFAULT '',
        description       TEXT NOT NULL DEFAULT '',
        lesson_kind       TEXT NOT NULL DEFAULT '',
        backdrop_top      TEXT NOT NULL DEFAULT '',
        backdrop_bottom   TEXT NOT NULL DEFAULT '',
        source            TEXT NOT NULL DEFAULT '',
        word_count        INTEGER NOT NULL DEFAULT 0,
        estimated_seconds REAL    NOT NULL DEFAULT 0,
        status            TEXT NOT NULL,
        video_id          TEXT,
        duration_s        REAL,
        error             TEXT,
        raw_json          TEXT,
        created_at        TEXT NOT NULL,
        produced_at       TEXT,
        published_at      TEXT
    );

    CREATE TABLE episode_items (
        episode_key TEXT NOT NULL REFERENCES episodes(key) ON DELETE CASCADE,
        position    INTEGER NOT NULL,
        word        TEXT NOT NULL,
        draw        TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        count       INTEGER,
        PRIMARY KEY (episode_key, position)
    );

    CREATE TABLE episode_beats (
        episode_key TEXT NOT NULL REFERENCES episodes(key) ON DELETE CASCADE,
        position    INTEGER NOT NULL,
        mode        TEXT NOT NULL,
        narration   TEXT NOT NULL,
        item_index  INTEGER,
        title       TEXT,
        subtitle    TEXT,
        PRIMARY KEY (episode_key, position)
    );

    CREATE TABLE episode_tags (
        episode_key TEXT NOT NULL REFERENCES episodes(key) ON DELETE CASCADE,
        position    INTEGER NOT NULL,
        tag         TEXT NOT NULL,
        PRIMARY KEY (episode_key, position)
    );

    INSERT INTO episodes (key, slug, title, lesson_kind, status, video_id,
                          duration_s, error, created_at, published_at)
        SELECT key,
               REPLACE(REPLACE(LOWER(key), ':', '-'), '_', '-'),
               title, lesson_id, status, video_id, duration_s, error,
               created_at, published_at
        FROM episodes_v1;

    DROP TABLE episodes_v1;

    CREATE INDEX idx_episodes_status    ON episodes(status);
    CREATE INDEX idx_episodes_published ON episodes(published_at);
    CREATE INDEX idx_episodes_kind      ON episodes(lesson_kind);
    CREATE INDEX idx_beats_narration    ON episode_beats(narration);
    """,
    # 3 — volksverhalen: de vorm, de plekken en waar elke beat speelt
    """
    ALTER TABLE episodes ADD COLUMN format TEXT NOT NULL DEFAULT 'kids';
    ALTER TABLE episodes ADD COLUMN scenes_json TEXT;
    ALTER TABLE episode_beats ADD COLUMN scene_index INTEGER;
    CREATE INDEX idx_episodes_format ON episodes(format);
    """,
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migrate(conn: sqlite3.Connection) -> int:
    """Brengt een database bij tot de nieuwste versie. Geeft terug hoeveel stappen."""
    versie = conn.execute("PRAGMA user_version").fetchone()[0]
    gedaan = 0
    for nummer, stap in enumerate(MIGRATIONS, start=1):
        if versie >= nummer:
            continue
        conn.executescript(stap)
        conn.execute(f"PRAGMA user_version = {nummer}")
        gedaan += 1
    return gedaan


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


class Store:
    """Alles wat de studio met de database doet.

    Elke methode opent en sluit zijn eigen verbinding. Dat is voor deze
    hoeveelheid werk ruim snel genoeg en scheelt gedoe met verbindingen die
    tussen threads gedeeld worden — de bedieningspagina draait taken in de
    achtergrond.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH

    # ── het script bewaren ──────────────────────────────────────────

    def save_blueprint(self, bp: Blueprint) -> None:
        """Schrijft een aflevering met script, items en zoektermen weg.

        Bestaat de aflevering al, dan wordt het script vervangen. De status
        en wat er al gepubliceerd is blijven staan: die horen bij de
        aflevering, niet bij deze versie van de tekst.
        """
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    key, slug, title, idea, description, lesson_kind,
                    backdrop_top, backdrop_bottom, source, word_count,
                    estimated_seconds, status, raw_json, created_at,
                    format, scenes_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?, 'planned', ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    slug=excluded.slug, title=excluded.title, idea=excluded.idea,
                    description=excluded.description, lesson_kind=excluded.lesson_kind,
                    backdrop_top=excluded.backdrop_top,
                    backdrop_bottom=excluded.backdrop_bottom,
                    source=excluded.source, word_count=excluded.word_count,
                    estimated_seconds=excluded.estimated_seconds,
                    raw_json=excluded.raw_json, error=NULL,
                    format=excluded.format, scenes_json=excluded.scenes_json
                """,
                (bp.key, bp.slug, bp.title, bp.idea, bp.description, bp.lesson_kind,
                 bp.backdrop_top, bp.backdrop_bottom, bp.source, bp.word_count,
                 bp.estimated_duration, bp.to_json(), _now(),
                 bp.format, json.dumps([asdict(sc) for sc in bp.scenes])),
            )

            for tabel in ("episode_items", "episode_beats", "episode_tags"):
                conn.execute(f"DELETE FROM {tabel} WHERE episode_key = ?", (bp.key,))

            conn.executemany(
                "INSERT INTO episode_items (episode_key, position, word, draw, label, color, count)"
                " VALUES (?,?,?,?,?,?,?)",
                [(bp.key, i, it.word, it.draw, it.label, it.color, it.count)
                 for i, it in enumerate(bp.items)],
            )
            conn.executemany(
                "INSERT INTO episode_beats (episode_key, position, mode, narration,"
                " item_index, title, subtitle, scene_index) VALUES (?,?,?,?,?,?,?,?)",
                [(bp.key, i, b.mode, b.narration, b.item, b.title, b.subtitle, b.scene)
                 for i, b in enumerate(bp.beats)],
            )
            conn.executemany(
                "INSERT INTO episode_tags (episode_key, position, tag) VALUES (?,?,?)",
                [(bp.key, i, t) for i, t in enumerate(bp.tags)],
            )

    def load_blueprint(self, key: str) -> Blueprint | None:
        """Haalt een aflevering compleet terug.

        Eerst uit raw_json, want dat is de exacte kopie. Ontbreekt die,
        bijvoorbeeld bij een rij uit de oude boekhouding, dan wordt de
        aflevering uit de tabellen opgebouwd.
        """
        with connect(self.db_path) as conn:
            rij = conn.execute("SELECT * FROM episodes WHERE key = ?", (key,)).fetchone()
            if rij is None:
                return None

            if rij["raw_json"]:
                return Blueprint.from_dict(json.loads(rij["raw_json"]))

            items = conn.execute(
                "SELECT * FROM episode_items WHERE episode_key = ? ORDER BY position", (key,)
            ).fetchall()
            beats = conn.execute(
                "SELECT * FROM episode_beats WHERE episode_key = ? ORDER BY position", (key,)
            ).fetchall()
            tags = conn.execute(
                "SELECT tag FROM episode_tags WHERE episode_key = ? ORDER BY position", (key,)
            ).fetchall()

        if not beats:
            return None

        return Blueprint(
            idea=rij["idea"], title=rij["title"], description=rij["description"],
            tags=[t["tag"] for t in tags], lesson_kind=rij["lesson_kind"],
            backdrop_top=rij["backdrop_top"] or "#DCEEFB",
            backdrop_bottom=rij["backdrop_bottom"] or "#F6E4C8",
            items=[Item(word=i["word"], draw=i["draw"], label=i["label"],
                        color=i["color"], count=i["count"]) for i in items],
            beats=[Beat(mode=b["mode"], narration=b["narration"], item=b["item_index"],
                        title=b["title"], subtitle=b["subtitle"],
                        scene=b["scene_index"]) for b in beats],
            source=rij["source"], key=rij["key"],
            format=rij["format"] or "kids",
            scenes=[StoryScene(**sc) for sc in json.loads(rij["scenes_json"] or "[]")],
        )

    # ── overzicht en zoeken ─────────────────────────────────────────

    def library(self, limit: int = 100, search: str = "") -> list[sqlite3.Row]:
        """Alle afleveringen, nieuwste eerst. search kijkt in titel en idee."""
        vraag = """
            SELECT key, slug, title, idea, lesson_kind, source, status,
                   word_count, estimated_seconds, duration_s, video_id,
                   created_at, published_at,
                   (SELECT COUNT(*) FROM episode_beats b WHERE b.episode_key = e.key) AS beats
            FROM episodes e
        """
        parameters: list[Any] = []
        if search.strip():
            vraag += " WHERE title LIKE ? OR idea LIKE ?"
            naald = f"%{search.strip()}%"
            parameters += [naald, naald]
        vraag += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(limit)

        with connect(self.db_path) as conn:
            return conn.execute(vraag, parameters).fetchall()

    def search_lines(self, text: str, limit: int = 50) -> list[sqlite3.Row]:
        """Zoekt in alle gesproken tekst van alle afleveringen."""
        with connect(self.db_path) as conn:
            return conn.execute(
                """
                SELECT b.episode_key, e.title, b.position, b.mode, b.narration
                FROM episode_beats b JOIN episodes e ON e.key = b.episode_key
                WHERE b.narration LIKE ?
                ORDER BY e.created_at DESC, b.position
                LIMIT ?
                """,
                (f"%{text}%", limit),
            ).fetchall()

    def keys_with_script(self) -> set[str]:
        """Afleveringen die daadwerkelijk tekst hebben.

        Een rij kan wel bestaan zonder script: rijen uit de oude boekhouding
        kennen alleen een titel en een status.
        """
        with connect(self.db_path) as conn:
            rijen = conn.execute("SELECT DISTINCT episode_key FROM episode_beats").fetchall()
        return {r["episode_key"] for r in rijen}

    def stats(self) -> dict[str, Any]:
        with connect(self.db_path) as conn:
            rij = conn.execute(
                """
                SELECT COUNT(*) AS afleveringen,
                       COALESCE(SUM(word_count), 0) AS woorden,
                       COALESCE(SUM(CASE WHEN status='uploaded' THEN 1 ELSE 0 END), 0) AS online,
                       COALESCE(SUM(duration_s), 0) AS seconden
                FROM episodes
                """
            ).fetchone()
            zinnen = conn.execute("SELECT COUNT(*) FROM episode_beats").fetchone()[0]
        return {**dict(rij), "zinnen": zinnen}

    # ── boekhouding ─────────────────────────────────────────────────

    def taken_keys(self) -> set[str]:
        """Afleveringen die al af zijn of onderweg. Mislukte mogen opnieuw."""
        with connect(self.db_path) as conn:
            rijen = conn.execute("SELECT key FROM episodes WHERE status != 'failed'").fetchall()
        return {r["key"] for r in rijen}

    def last_touched_per_lesson(self) -> dict[str, str]:
        """Wanneer elke les voor het laatst aan bod kwam.

        Ook nog niet gepubliceerde afleveringen tellen mee: anders zou de
        planner steeds dezelfde les kiezen zolang er nog niets online staat.
        """
        with connect(self.db_path) as conn:
            rijen = conn.execute(
                "SELECT lesson_kind, MAX(COALESCE(published_at, created_at)) AS last "
                "FROM episodes WHERE status != 'failed' GROUP BY lesson_kind"
            ).fetchall()
        return {r["lesson_kind"]: r["last"] for r in rijen}

    def published_since(self, days: int) -> int:
        grens = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with connect(self.db_path) as conn:
            return int(conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE published_at IS NOT NULL "
                "AND published_at >= ?", (grens,),
            ).fetchone()[0])

    def hours_since_last_publish(self) -> float | None:
        with connect(self.db_path) as conn:
            rij = conn.execute(
                "SELECT MAX(published_at) AS last FROM episodes WHERE published_at IS NOT NULL"
            ).fetchone()
        if not rij or not rij["last"]:
            return None
        laatst = datetime.fromisoformat(rij["last"])
        if laatst.tzinfo is None:
            laatst = laatst.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - laatst).total_seconds() / 3600.0

    def all_episodes(self) -> list[sqlite3.Row]:
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM episodes ORDER BY created_at DESC").fetchall()

    def mark_planned(self, key: str, lesson_id: str, theme_id: str, title: str) -> None:
        """Alleen nog voor afleveringen zonder script, zoals in tests."""
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (key, slug, title, lesson_kind, status, created_at) "
                "VALUES (?, ?, ?, ?, 'planned', ?) "
                "ON CONFLICT(key) DO UPDATE SET status='planned', error=NULL, "
                "title=excluded.title",
                (key, key.replace(":", "-"), title, lesson_id, _now()),
            )

    def mark_produced(self, key: str, duration_s: float) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET status='produced', duration_s=?, produced_at=? WHERE key=?",
                (duration_s, _now(), key),
            )

    def mark_uploaded(self, key: str, video_id: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET status='uploaded', video_id=?, published_at=? WHERE key=?",
                (video_id, _now(), key),
            )

    def mark_failed(self, key: str, error: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute("UPDATE episodes SET status='failed', error=? WHERE key=?",
                         (error[:1000], key))

    # ── binnenhalen en uitvoeren ────────────────────────────────────

    def import_json_files(self, out_dir: Path) -> list[str]:
        """Neemt losse blueprint.json-bestanden alsnog op in de database.

        Draait bij het opstarten van de studio. Zo raakt niemand die al
        afleveringen had gemaakt die alsnog kwijt.
        """
        if not out_dir.exists():
            return []

        # Kijken naar wie er al tekst heeft, niet naar wie er al een rij
        # heeft: rijen uit de oude boekhouding bestaan wel maar zijn leeg,
        # en juist die moeten hun script alsnog krijgen.
        bestaand = self.keys_with_script()
        opgenomen: list[str] = []
        for pad in sorted(out_dir.glob("*/blueprint.json")):
            try:
                bp = Blueprint.load(pad)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue                       # onleesbaar bestand overslaan
            if bp.key in bestaand:
                continue
            self.save_blueprint(bp)
            if (pad.parent / "video.mp4").exists():
                self.mark_produced(bp.key, 0.0)
            opgenomen.append(bp.key)
        return opgenomen

    def export_all(self, path: Path) -> int:
        """Schrijft alle afleveringen als één JSON-bestand weg."""
        afleveringen = []
        for rij in self.all_episodes():
            bp = self.load_blueprint(rij["key"])
            if bp is None:
                continue
            afleveringen.append({
                **asdict(bp),
                "status": rij["status"],
                "video_id": rij["video_id"],
                "created_at": rij["created_at"],
                "published_at": rij["published_at"],
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(afleveringen, indent=2, ensure_ascii=False), encoding="utf-8")
        return len(afleveringen)

    def query(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        """Voert een eigen SELECT uit. Alleen lezen."""
        eerste = sql.strip().split(None, 1)[0].lower() if sql.strip() else ""
        if eerste not in ("select", "with", "pragma", "explain"):
            raise ValueError("Alleen SELECT-vragen zijn toegestaan.")
        with connect(self.db_path) as conn:
            return conn.execute(sql, parameters).fetchall()
