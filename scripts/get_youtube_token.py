#!/usr/bin/env python3
"""Haalt eenmalig een YouTube refresh token op.

Dit doe je één keer, op je eigen computer. Daarna kan de pipeline zonder
jou uploaden.

Vooraf, in de Google Cloud Console (console.cloud.google.com):

  1. Maak een project.
  2. Zet 'YouTube Data API v3' aan bij APIs & Services > Library.
  3. Vul het OAuth consent screen in. Kies User Type 'External'.
  4. Zet de publishing status op 'In production' en niet op 'Testing'.
     Dit is de belangrijkste stap. Bij 'Testing' verloopt het refresh
     token na zeven dagen en staat je automatisering elke week stil.
     Google vraagt pas om verificatie als je app door anderen gebruikt
     wordt; voor je eigen kanaal is dat niet nodig.
  5. Maak bij Credentials een OAuth client ID van het type 'Desktop app'.
  6. Download het JSON-bestand en zet het in de projectmap neer als
     client_secret.json.

Draai dan:  python scripts/get_youtube_token.py

Google waarschuwt tijdens het inloggen dat de app niet geverifieerd is.
Dat klopt: het is jouw eigen app. Klik op 'Geavanceerd' en daarna op
'Ga naar ... (onveilig)'.
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

    print("\n  Gelukt.\n")
    print("Zet deze drie regels in je .env bestand, of plak ze in de")
    print("bedieningspagina onder 'Sleutels instellen':\n")
    print(f"YOUTUBE_CLIENT_ID={installed.get('client_id', '')}")
    print(f"YOUTUBE_CLIENT_SECRET={installed.get('client_secret', '')}")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print("\nGebruik je GitHub Actions? Zet ze daar als repository secrets.")
    print("\nLet op: staat je app in de Google Cloud Console op 'Testing',")
    print("dan verloopt dit token over zeven dagen. Zet hem op 'In production'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
