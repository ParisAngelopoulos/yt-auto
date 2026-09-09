"""SQLite-boekhouding: wat is al gemaakt, wat is al gepubliceerd, hoe vaak.

Voorkomt twee dingen die een kanaal om zeep helpen:
  1. dezelfde aflevering twee keer uploaden;
  2. te veel uploaden in korte tijd (spam-signaal richting YouTube).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from .config import ROOT

DB_PATH = ROOT / "state" / "episodes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    key           TEXT PRIMARY KEY,   -- "colors:balloons"
    lesson_id     TEXT NOT NULL,
    theme_id      TEXT NOT NULL,
    title         TEXT NOT NULL,
    status        TEXT NOT NULL,      -- planned | produced | uploaded | failed
    video_id      TEXT,
    duration_s    REAL,
    error         TEXT,
    created_at    TEXT NOT NULL,
    published_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_episodes_status    ON episodes(status);
CREATE INDEX IF NOT EXISTS idx_episodes_published ON episodes(published_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


class Store:
    """Dunne wrapper rond de database. Elke methode opent en sluit zijn eigen verbinding."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH

    # ---------- lezen ----------

    def taken_keys(self) -> set[str]:
        """Afleveringen die al af zijn of onderweg. Mislukte mogen opnieuw."""
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key FROM episodes WHERE status != 'failed'"
            ).fetchall()
        return {row["key"] for row in rows}

    def last_touched_per_lesson(self) -> dict[str, str]:
        """Wanneer elke les voor het laatst aan bod kwam.

        Ook nog niet gepubliceerde afleveringen tellen mee: anders zou de
        planner vier keer achter elkaar dezelfde les kiezen zolang er nog
        niets online staat.
        """
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT lesson_id, MAX(COALESCE(published_at, created_at)) AS last "
                "FROM episodes WHERE status != 'failed' GROUP BY lesson_id"
            ).fetchall()
        return {row["lesson_id"]: row["last"] for row in rows}

    def published_since(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM episodes "
                "WHERE published_at IS NOT NULL AND published_at >= ?",
                (cutoff,),
            ).fetchone()
        return int(row["n"])

    def hours_since_last_publish(self) -> float | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT MAX(published_at) AS last FROM episodes "
                "WHERE published_at IS NOT NULL"
            ).fetchone()
        if not row or not row["last"]:
            return None
        last = datetime.fromisoformat(row["last"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last).total_seconds() / 3600.0

    def all_episodes(self) -> list[sqlite3.Row]:
        with connect(self.db_path) as conn:
            return conn.execute(
                "SELECT * FROM episodes ORDER BY created_at DESC"
            ).fetchall()

    # ---------- schrijven ----------

    def mark_planned(self, key: str, lesson_id: str, theme_id: str, title: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (key, lesson_id, theme_id, title, status, created_at) "
                "VALUES (?, ?, ?, ?, 'planned', ?) "
                "ON CONFLICT(key) DO UPDATE SET status='planned', error=NULL, title=excluded.title",
                (key, lesson_id, theme_id, title, _now()),
            )

    def mark_produced(self, key: str, duration_s: float) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET status='produced', duration_s=? WHERE key=?",
                (duration_s, key),
            )

    def mark_uploaded(self, key: str, video_id: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET status='uploaded', video_id=?, published_at=? WHERE key=?",
                (video_id, _now(), key),
            )

    def mark_failed(self, key: str, error: str) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE episodes SET status='failed', error=? WHERE key=?",
                (error[:1000], key),
            )
