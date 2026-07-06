"""Stage 6 — upload: push the MP4 to YouTube (Data API v3, OAuth refresh token).

Privacy is ALWAYS 'private' in CI. videos.insert costs ~1600 quota units against
a default daily quota of 10,000. Unverified OAuth apps may have uploads locked to
private regardless — see SETUP.md.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from common import Context, log, read_json
from config import Config
from models import PaperMeta, Script

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
MAX_TAGS_CHARS = 460


def build_description(cfg: Config, script: Script, meta: PaperMeta) -> str:
    lines = [script.summary.strip(), ""]
    lines.append(f"Paper: {meta.title}")
    if meta.authors:
        authors = ", ".join(meta.authors[:8]) + (" et al." if len(meta.authors) > 8 else "")
        lines.append(f"Authors: {authors}")
    if meta.arxiv_id:
        lines.append(f"arXiv: https://arxiv.org/abs/{meta.arxiv_id}")
    elif meta.source_url:
        lines.append(f"Source: {meta.source_url}")
    lines.append("")
    lines.append("Figures from the original paper, © original authors.")
    lines.append(f"Generated automatically by {cfg.channel_name}.")
    return "\n".join(lines)


def clamp_tags(keywords) -> list:
    tags, total = [], 0
    for kw in keywords:
        kw = kw.strip()[:100]
        if not kw:
            continue
        if total + len(kw) + 1 > MAX_TAGS_CHARS:
            break
        tags.append(kw)
        total += len(kw) + 1
    return tags


def run(ctx: Context) -> dict:
    cfg = ctx.config
    script = Script.model_validate(read_json(ctx.script))
    meta = PaperMeta.model_validate(read_json(ctx.metadata))
    privacy = "private" if os.environ.get("CI") else cfg.upload_privacy

    title = script.title[:100]
    description = build_description(cfg, script, meta)[:4900]
    tags = clamp_tags(script.keywords)

    if ctx.mock:
        log("upload", f"MOCK: would upload '{title}' as {privacy}")
        log("upload", f"MOCK: tags={tags}")
        return {"video_id": "MOCK_VIDEO_ID", "url": "https://youtu.be/MOCK_VIDEO_ID", "mock": True}

    if not ctx.out_mp4.exists():
        raise FileNotFoundError(f"{ctx.out_mp4} not found — run the render stage first")

    from google.oauth2.credentials import Credentials  # lazy
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "Missing YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN"
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": cfg.upload_category_id,
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(ctx.out_mp4), chunksize=-1, resumable=True, mimetype="video/mp4")
    log("upload", f"uploading '{title}' as {privacy} ...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log("upload", f"progress {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    log("upload", f"done: {url} (privacy={privacy})")
    return {"video_id": video_id, "url": url, "privacy": privacy}
