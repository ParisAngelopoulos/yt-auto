"""Laadt config/channel.yaml + config/curriculum.yaml en de secrets uit de omgeving."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimale .env-lader zodat lokaal draaien geen extra dependency nodig heeft."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class Secrets:
    """Alles wat niet in git hoort. Komt uit .env of uit GitHub Actions secrets."""

    elevenlabs_api_key: str = ""
    anthropic_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    @classmethod
    def from_env(cls) -> "Secrets":
        _load_dotenv(ROOT / ".env")
        return cls(
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
            youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
            youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
        )

    def can_upload(self) -> bool:
        return bool(
            self.youtube_client_id
            and self.youtube_client_secret
            and self.youtube_refresh_token
        )


ENV_PATH = ROOT / ".env"

# Alles wat de studio aan geheimen kent. De volgorde bepaalt hoe .env
# eruitziet als hij nieuw wordt aangemaakt.
SECRET_KEYS = (
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
)


def write_secrets(values: dict[str, str], path: Path | None = None) -> list[str]:
    """Werkt .env bij en laat de rest van het bestand met rust.

    Alleen sleutels uit SECRET_KEYS worden geschreven; anders zou een
    aanroep van buitenaf willekeurige omgevingsvariabelen kunnen zetten.
    Lege waarden worden overgeslagen, zodat een leeg veld in het formulier
    een bestaande sleutel niet wist.
    """
    path = path or ENV_PATH
    schoon = {
        key: value.strip()
        for key, value in values.items()
        if key in SECRET_KEYS and value and value.strip()
    }
    if not schoon:
        return []

    regels = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    nog_te_doen = dict(schoon)

    for index, regel in enumerate(regels):
        naam = regel.split("=", 1)[0].strip()
        if naam in nog_te_doen:
            regels[index] = f"{naam}={nog_te_doen.pop(naam)}"
    for naam, waarde in nog_te_doen.items():
        regels.append(f"{naam}={waarde}")

    path.write_text("\n".join(regels) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)          # geheimen zijn niet leesbaar voor anderen
    except OSError:
        pass

    # De lopende sessie moet de nieuwe waarden meteen kennen.
    for naam, waarde in schoon.items():
        os.environ[naam] = waarde

    return sorted(schoon)


@dataclass
class Config:
    raw: dict[str, Any]
    curriculum: dict[str, Any]
    secrets: Secrets = field(default_factory=Secrets.from_env)

    # -- handige accessors, zodat de rest van de code geen dict-gegraaf doet --
    @property
    def channel(self) -> dict[str, Any]:
        return self.raw["channel"]

    @property
    def video(self) -> dict[str, Any]:
        return self.raw["video"]

    @property
    def tts(self) -> dict[str, Any]:
        return self.raw["tts"]

    @property
    def script(self) -> dict[str, Any]:
        return self.raw["script"]

    @property
    def music(self) -> dict[str, Any]:
        return self.raw["music"]

    @property
    def publish(self) -> dict[str, Any]:
        return self.raw["publish"]

    @property
    def safety(self) -> dict[str, Any]:
        return self.raw["safety"]

    @property
    def lessons(self) -> list[dict[str, Any]]:
        return self.curriculum["lessons"]

    @property
    def resolution(self) -> tuple[int, int]:
        return int(self.video["width"]), int(self.video["height"])

    @property
    def fps(self) -> int:
        return int(self.video["fps"])


def load_config(
    channel_path: Path | None = None,
    curriculum_path: Path | None = None,
) -> Config:
    channel_path = channel_path or ROOT / "config" / "channel.yaml"
    curriculum_path = curriculum_path or ROOT / "config" / "curriculum.yaml"

    raw = yaml.safe_load(channel_path.read_text(encoding="utf-8"))
    curriculum = yaml.safe_load(curriculum_path.read_text(encoding="utf-8"))

    missing = {"channel", "video", "tts", "script", "music", "publish", "safety"} - raw.keys()
    if missing:
        raise ValueError(f"channel.yaml mist secties: {sorted(missing)}")
    if not curriculum.get("lessons"):
        raise ValueError("curriculum.yaml bevat geen lessen")

    return Config(raw=raw, curriculum=curriculum)
