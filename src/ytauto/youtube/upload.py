"""Uploadt een afgemonteerde video naar YouTube.

Er wordt bewust met een refresh token gewerkt en niet met de browser-flow:
de pipeline moet 's nachts kunnen draaien zonder dat er iemand op een knop
klikt. Het token haal je één keer op met scripts/get_youtube_token.py.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..config import Config
from ..scripting.blueprint import Blueprint

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_ATTEMPTS = 4


class UploadError(RuntimeError):
    pass


def build_client(cfg: Config):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:                                  # pragma: no cover
        raise UploadError(
            "Google-packages ontbreken. Draai: pip install -r requirements.txt"
        ) from exc

    secrets = cfg.secrets
    if not secrets.can_upload():
        raise UploadError(
            "YouTube-gegevens ontbreken. Nodig zijn YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET en YOUTUBE_REFRESH_TOKEN. Draai "
            "scripts/get_youtube_token.py om ze op te halen."
        )

    credentials = Credentials(
        token=None,
        refresh_token=secrets.youtube_refresh_token,
        client_id=secrets.youtube_client_id,
        client_secret=secrets.youtube_client_secret,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def build_body(cfg: Config, bp: Blueprint) -> dict:
    publish = cfg.publish
    description = bp.description.strip()

    return {
        "snippet": {
            "title": bp.title[:100],
            "description": description[:4900],
            "tags": [t[:30] for t in bp.tags][:15],
            "categoryId": str(publish.get("category_id", "27")),
            "defaultLanguage": cfg.channel.get("language", "en"),
            "defaultAudioLanguage": cfg.channel.get("language", "en"),
        },
        "status": {
            "privacyStatus": publish.get("privacy_status", "public"),
            # Verplicht voor kindercontent. YouTube schakelt hiermee zelf
            # reacties, meldingen en gepersonaliseerde advertenties uit.
            "selfDeclaredMadeForKids": bool(publish.get("made_for_kids", True)),
            "embeddable": True,
            "license": "youtube",
        },
    }


def upload_video(
    cfg: Config,
    bp: Blueprint,
    video_path: Path,
    thumbnail_path: Path | None = None,
) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    youtube = build_client(cfg)
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(
        part="snippet,status", body=build_body(cfg, bp), media_body=media,
    )

    response = None
    attempt = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"  uploaden: {int(status.progress() * 100)}%")
        except HttpError as exc:
            if exc.resp.status in (500, 502, 503, 504) and attempt < MAX_ATTEMPTS:
                attempt += 1
                time.sleep(2 ** attempt)
                continue
            raise UploadError(f"YouTube weigerde de upload: {exc}") from exc

    video_id = response["id"]
    print(f"  gepubliceerd: https://youtu.be/{video_id}")

    if thumbnail_path and thumbnail_path.exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
        except HttpError as exc:
            # Een eigen thumbnail vereist een geverifieerd kanaal. Zonder die
            # verificatie mislukt alleen deze stap; de video staat er wel.
            print(f"  thumbnail niet geplaatst ({exc.resp.status}). "
                  "Kanaal moet daarvoor geverifieerd zijn.")

    return video_id


def check_credentials(cfg: Config) -> dict:
    """Kijkt of het kanaal bereikbaar is. Voor de bedieningspagina."""
    if not cfg.secrets.can_upload():
        return {"ok": False, "reason": "Geen YouTube-gegevens in .env"}
    try:
        youtube = build_client(cfg)
        response = youtube.channels().list(part="snippet", mine=True).execute()
    except Exception as exc:                                    # noqa: BLE001
        melding = str(exc)
        if "invalid_grant" in melding:
            return {"ok": False, "reason": "Het refresh token is verlopen. "
                                           "Draai scripts/get_youtube_token.py opnieuw."}
        if "invalid_client" in melding:
            return {"ok": False, "reason": "Client id of secret klopt niet."}
        if "accessNotConfigured" in melding or "has not been used" in melding:
            return {"ok": False, "reason": "YouTube Data API v3 staat nog uit "
                                           "in je Google Cloud-project."}
        return {"ok": False, "reason": melding.splitlines()[0][:180]}

    items = response.get("items", [])
    if not items:
        return {"ok": False, "reason": "Geen kanaal gevonden bij dit account"}
    return {"ok": True, "channel": items[0]["snippet"]["title"]}
