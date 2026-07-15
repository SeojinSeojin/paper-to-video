"""Optional stock-image fallback: when a figure can't be extracted from the PDF,
search a free image service for an *illustrative* background instead of showing a
bare keyword card.

Never used to replace a real figure — only invoked from the fallback path, and
only when PIXABAY_API_KEY is set. Any failure returns None so the caller degrades
to the typographic keyword card. The image is clearly labelled as illustrative
(not from the paper) by the caller, so it can't be mistaken for the source figure.
"""
from __future__ import annotations

import io
import os
import re
from typing import List, Optional

from common import log

PIXABAY_URL = "https://pixabay.com/api/"
_TIMEOUT = 12
_MIN_PX = 120


def _query(keywords: List[str], limit: int = 3) -> str:
    """Build a search query. Pixabay indexes English, so prefer ASCII terms
    (technical jargon in a Korean script is usually left in English)."""
    ascii_kw = [k for k in keywords if re.search(r"[A-Za-z]", k)]
    picked = (ascii_kw or keywords)[:limit]
    return " ".join(picked).strip()


def search_image(keywords: List[str]) -> Optional[bytes]:
    """Return normalized PNG bytes for the best free stock match, or None.

    Returns None (silently, apart from a log line) when no API key is set, the
    request fails, or nothing suitable is found — the caller falls back to a card.
    """
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        return None
    query = _query(keywords)
    if not query:
        return None

    import requests

    try:
        resp = requests.get(
            PIXABAY_URL,
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "safesearch": "true",
                "orientation": "horizontal",
                "per_page": 3,
                "min_width": 1200,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits") or []
    except Exception as exc:  # noqa: BLE001 - stock search must never break figures
        log("figures", f"stock search failed for '{query}': {exc}")
        return None

    if not hits:
        log("figures", f"stock search: no match for '{query}'")
        return None

    url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
    if not url:
        return None
    try:
        img = requests.get(url, timeout=_TIMEOUT)
        img.raise_for_status()
        data = _normalize(img.content)
    except Exception as exc:  # noqa: BLE001
        log("figures", f"stock download failed for '{query}': {exc}")
        return None

    if data:
        log("figures", f"stock match for '{query}'")
    return data


def _normalize(data: Optional[bytes]) -> Optional[bytes]:
    if not data:
        return None
    from PIL import Image

    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    if im.width < _MIN_PX or im.height < _MIN_PX:
        return None
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()
