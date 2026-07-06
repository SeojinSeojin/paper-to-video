#!/usr/bin/env python3
"""Parse a video request into `url` and `lang` GitHub Actions step outputs.

For workflow_dispatch: read INPUT_URL / INPUT_LANG.
For issues: extract the first URL (preferring arXiv, then .pdf) and an optional
`lang: ko|en` line from ISSUE_BODY.

Writes `url=...` and `lang=...` to stdout (redirect into $GITHUB_OUTPUT).
Exits non-zero if no URL is found.
"""
from __future__ import annotations

import os
import re
import sys

URL_RE = re.compile(r"https?://[^\s<>)\]}\"']+")
LANG_RE = re.compile(r"lang\s*:\s*(ko|en)\b", re.IGNORECASE)


def pick_url(body: str) -> str:
    urls = [u.strip().rstrip(".,);") for u in URL_RE.findall(body)]
    urls = [u for u in urls if u]
    for u in urls:
        if "arxiv.org" in u.lower():
            return u
    for u in urls:
        if u.lower().endswith(".pdf"):
            return u
    return urls[0] if urls else ""


def main() -> int:
    event = os.environ.get("EVENT_NAME", "")
    if event == "workflow_dispatch":
        url = (os.environ.get("INPUT_URL") or "").strip()
        lang = (os.environ.get("INPUT_LANG") or "").strip().lower()
    else:
        body = os.environ.get("ISSUE_BODY") or ""
        url = pick_url(body)
        m = LANG_RE.search(body)
        lang = m.group(1).lower() if m else ""

    if lang not in ("ko", "en", ""):
        lang = ""
    if not url:
        print("No URL found in the request body.", file=sys.stderr)
        return 1

    print(f"url={url}")
    print(f"lang={lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
