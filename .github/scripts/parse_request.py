#!/usr/bin/env python3
"""Parse a video request into `urls`, `url`, `count` and `lang` step outputs.

For workflow_dispatch: read INPUT_URL (may hold several space/newline/comma
separated URLs) / INPUT_LANG.
For issues: extract every URL from ISSUE_BODY (arXiv/PDF first, then the rest)
and an optional `lang: ko|en` line.

Writes to stdout (redirect into $GITHUB_OUTPUT):
  urls=<space-joined list, capped at MAX_URLS>   # for `run.py --urls`
  url=<first url>                                 # for comment display
  count=<number of urls>
  lang=<ko|en|"">
Exits non-zero if no URL is found.
"""
from __future__ import annotations

import os
import re
import sys

URL_RE = re.compile(r"https?://[^\s<>)\]}\"']+")
LANG_RE = re.compile(r"lang\s*:\s*(ko|en)\b", re.IGNORECASE)
MAX_URLS = 10


def _rank(u: str) -> int:
    lu = u.lower()
    if "arxiv.org" in lu:
        return 0
    if lu.endswith(".pdf"):
        return 1
    return 2


def extract_urls(text: str) -> list:
    """All URLs in `text`: arXiv first, then PDFs, then the rest. De-duped, capped."""
    raw = [u.strip().rstrip(".,);") for u in URL_RE.findall(text or "")]
    seen, urls = set(), []
    for u in raw:
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    urls.sort(key=_rank)  # stable: preserves original order within a rank
    return urls[:MAX_URLS]


def main() -> int:
    event = os.environ.get("EVENT_NAME", "")
    if event == "workflow_dispatch":
        urls = extract_urls(os.environ.get("INPUT_URL") or "")
        lang = (os.environ.get("INPUT_LANG") or "").strip().lower()
    else:
        body = os.environ.get("ISSUE_BODY") or ""
        urls = extract_urls(body)
        m = LANG_RE.search(body)
        lang = m.group(1).lower() if m else ""

    if lang not in ("ko", "en", ""):
        lang = ""
    if not urls:
        print("No URL found in the request body.", file=sys.stderr)
        return 1

    print(f"urls={' '.join(urls)}")
    print(f"url={urls[0]}")
    print(f"count={len(urls)}")
    print(f"lang={lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
