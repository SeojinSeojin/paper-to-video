"""Stage 1 — ingest: arXiv/PDF URL -> paper.pdf + metadata.json."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from common import Context, log, write_json
from models import PaperMeta

ARXIV_API = "http://export.arxiv.org/api/query?id_list={id}"
ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+)", re.IGNORECASE)
USER_AGENT = "paper2video/1.0 (+https://github.com/paper2video)"


def extract_arxiv_id(url: str) -> Optional[str]:
    m = ARXIV_ID_RE.search(url)
    if not m:
        return None
    raw = m.group(1)
    raw = re.sub(r"\.pdf$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"v\d+$", "", raw)  # drop version suffix
    return raw


def arxiv_pdf_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def fetch_arxiv_metadata(arxiv_id: str) -> PaperMeta:
    resp = requests.get(ARXIV_API.format(id=arxiv_id), headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    entry = root.find("a:entry", ns)
    if entry is None:
        raise ValueError(f"arXiv API returned no entry for {arxiv_id}")
    title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
    title = re.sub(r"\s+", " ", title)
    authors = [
        (a.findtext("a:name", default="", namespaces=ns) or "").strip()
        for a in entry.findall("a:author", ns)
    ]
    authors = [a for a in authors if a]
    published = entry.findtext("a:published", default="", namespaces=ns) or ""
    year = published[:4] if published else ""
    return PaperMeta(
        title=title or f"arXiv:{arxiv_id}",
        authors=authors,
        year=year,
        arxiv_id=arxiv_id,
        source_url=f"https://arxiv.org/abs/{arxiv_id}",
        metadata_confidence="high",
    )


def download(url: str, dest: Path) -> None:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120, stream=True)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            fh.write(chunk)
    if dest.stat().st_size < 1024:
        raise ValueError(f"Downloaded PDF from {url} is suspiciously small")


def title_from_pdf(pdf: Path) -> str:
    import fitz  # lazy

    with fitz.open(pdf) as doc:
        if doc.page_count == 0:
            return "Untitled paper"
        text = doc[0].get_text().strip()
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 8 and not line.lower().startswith(("arxiv", "http")):
            return re.sub(r"\s+", " ", line)[:200]
    return "Untitled paper"


def run(ctx: Context, url: Optional[str]) -> PaperMeta:
    ctx.ensure_dirs()

    if ctx.mock:
        from mock_data import MOCK_METADATA, build_mock_pdf

        log("ingest", "MOCK: building fixture paper.pdf + metadata.json")
        build_mock_pdf(ctx.pdf)
        meta = PaperMeta(**MOCK_METADATA)
        write_json(ctx.metadata, meta.model_dump())
        log("ingest", f"MOCK: '{meta.title}' ({ctx.pdf.stat().st_size} bytes)")
        return meta

    if not url:
        raise ValueError("ingest requires --url (or use --mock)")

    arxiv_id = extract_arxiv_id(url)
    if arxiv_id:
        log("ingest", f"arXiv id {arxiv_id}: fetching metadata")
        meta = fetch_arxiv_metadata(arxiv_id)
        log("ingest", f"downloading PDF for {arxiv_id}")
        download(arxiv_pdf_url(arxiv_id), ctx.pdf)
    else:
        log("ingest", f"non-arXiv PDF: downloading {url}")
        download(url, ctx.pdf)
        title = title_from_pdf(ctx.pdf)
        meta = PaperMeta(
            title=title,
            authors=[],
            year="",
            arxiv_id=None,
            source_url=url,
            metadata_confidence="low",
        )
        log("ingest", f"best-effort title: '{title}'")

    write_json(ctx.metadata, meta.model_dump())
    log("ingest", f"done: '{meta.title}' ({ctx.pdf.stat().st_size} bytes)")
    return meta
