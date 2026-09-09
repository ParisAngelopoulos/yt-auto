#!/usr/bin/env python3
"""Haalt eenmalig een YouTube refresh token op.

Dit doe je één keer, op je eigen computer. Daarna kan de pipeline zonder
jou uploaden.

Vooraf, in de Google Cloud Console:
  1. Maak een project en zet 'YouTube Data API v3' aan.
  2. Maak OAuth-gegevens van het type 'Desktop app'.
  3. Download het JSON-bestand en zet het naast dit script neer als
     client_secret.json.
  4. Voeg bij het OAuth-toestemmingsscherm je eigen Google-account toe als
     testgebruiker.

Draai dan:  python scripts/get_youtube_token.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def main() -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Ontbrekende package. Draai eerst: pip install -r requirements.txt")
        return 1

    secret = ROOT / "client_secret.json"
    if not secret.exists():
        print(f"Zet je OAuth-bestand neer als {secret}")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
    # offline + consent samen zorgen dat Google echt een refresh token geeft
    # en niet alleen een access token van een uur.
    credentials = flow.run_local_server(
        port=0, access_type="offline", prompt="consent",
    )

    data = json.loads(secret.read_text())
    installed = data.get("installed") or data.get("web") or {}

    print("\nZet deze drie regels in je .env bestand:\n")
    print(f"YOUTUBE_CLIENT_ID={installed.get('client_id', '')}")
    print(f"YOUTUBE_CLIENT_SECRET={installed.get('client_secret', '')}")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print("\nGebruik je GitHub Actions? Zet ze daar als repository secrets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
