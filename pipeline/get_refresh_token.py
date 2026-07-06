#!/usr/bin/env python3
"""One-time helper: run the OAuth consent flow and print a YouTube refresh token.

Prerequisites (see SETUP.md):
  - A Google Cloud project with the YouTube Data API v3 enabled.
  - An OAuth client of type "Desktop app".

Usage:
  export YOUTUBE_CLIENT_ID=...        # from the OAuth client
  export YOUTUBE_CLIENT_SECRET=...
  python pipeline/get_refresh_token.py

A browser window opens for consent; on success the refresh token is printed.
Copy it into the YOUTUBE_REFRESH_TOKEN GitHub secret (and/or your local env).
"""
from __future__ import annotations

import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET first.", file=sys.stderr)
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh token is returned.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        print("No refresh token returned. Revoke prior access and retry.", file=sys.stderr)
        return 1

    print("\n=== YOUTUBE_REFRESH_TOKEN ===")
    print(creds.refresh_token)
    print("=============================")
    print("Store this as the YOUTUBE_REFRESH_TOKEN secret. Keep it private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
