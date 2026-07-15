"""Stage 1 — ingest: one or more arXiv/PDF URLs -> per-paper paper.pdf + metadata.json.

Each paper lands in its own sub-workdir (workdir/papers/NN); `papers.json` records
them in order so later stages can iterate. A single-URL run is just N == 1.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

import requests

from common import Context, log, write_json
from models import PaperMeta

ARXIV_API = "http://export.arxiv.org/api/query?id_list={id}"
ARXIV_SEARCH_API = "http://export.arxiv.org/api/query?search_query=ti:%22{title}%22&max_results=1"
ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+)", re.IGNORECASE)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#&\"]+", re.IGNORECASE)
S2_DOI_API = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,externalIds,openAccessPdf"
UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}?email=seojin.kim.ko@gmail.com"
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


def _arxiv_id_by_title(title: str) -> Optional[str]:
    """Search arXiv for a paper by exact-ish title -> its id (best match), or None."""
    from urllib.parse import quote

    try:
        resp = requests.get(
            ARXIV_SEARCH_API.format(title=quote(title)),
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = ET.fromstring(resp.text).find("a:entry", ns)
        if entry is None:
            return None
        got = re.sub(r"\s+", " ", entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        # Guard against loose matches: require the titles to line up closely.
        if got.lower()[:60] != re.sub(r"\s+", " ", title).lower()[:60]:
            return None
        raw = (entry.findtext("a:id", default="", namespaces=ns) or "").rsplit("/", 1)[-1]
        return re.sub(r"v\d+$", "", raw) or None
    except (requests.RequestException, ET.ParseError):
        return None


def resolve_open_access(url: str, title: Optional[str] = None) -> Optional[tuple[str, Optional[str]]]:
    """A publisher URL is walled — find a free copy instead.

    Returns (pdf_url, arxiv_id) where arxiv_id may be None (non-arXiv OA PDF), or
    None if nothing free could be located. Tries, in order: Semantic Scholar by DOI
    (best signal — gives the arXiv id), Unpaywall by DOI, then arXiv title search.
    """
    doi_m = DOI_RE.search(url)
    doi = doi_m.group(0).rstrip(".") if doi_m else None

    if doi:
        try:
            r = requests.get(S2_DOI_API.format(doi=doi), headers={"User-Agent": USER_AGENT}, timeout=30)
            if r.ok:
                data = r.json()
                arxiv_id = (data.get("externalIds") or {}).get("ArXiv")
                if arxiv_id:
                    return arxiv_pdf_url(arxiv_id), arxiv_id
                oa = (data.get("openAccessPdf") or {}).get("url")
                if oa:
                    return oa, None
                title = title or data.get("title")
        except (requests.RequestException, ValueError):
            pass

        try:
            r = requests.get(UNPAYWALL_API.format(doi=doi), headers={"User-Agent": USER_AGENT}, timeout=30)
            if r.ok:
                loc = r.json().get("best_oa_location") or {}
                pdf = loc.get("url_for_pdf") or loc.get("url")
                if pdf:
                    return pdf, None
        except (requests.RequestException, ValueError):
            pass

    # Last resort: no DOI (e.g. IEEE stamp.jsp?arnumber=…). The publisher's own
    # landing HTML still carries the title in a <meta name="citation_title">.
    if not title:
        title = _title_from_landing(url)

    if title:
        arxiv_id = _arxiv_id_by_title(title)
        if arxiv_id:
            return arxiv_pdf_url(arxiv_id), arxiv_id

    return None


def _title_from_landing(url: str) -> Optional[str]:
    # IEEE stamp.jsp is only the PDF iframe; its abstract page holds the real title.
    m = re.search(r"ieeexplore\.ieee\.org/stamp/stamp\.jsp.*?arnumber=(\d+)", url, re.IGNORECASE)
    if m:
        url = f"https://ieeexplore.ieee.org/document/{m.group(1)}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if not r.ok:
            return None
        m = re.search(
            r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)', r.text, re.IGNORECASE
        ) or re.search(r"<title[^>]*>([^<]+)</title>", r.text, re.IGNORECASE)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
    except requests.RequestException:
        return None


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


# Publisher hosts that sit behind an interactive bot challenge (Cloudflare et al.):
# a plain HTTP client can't get the PDF, so we resolve an open-access copy instead.
_BLOCKED_HOSTS = ("dl.acm.org", "ieeexplore.ieee.org", "link.springer.com", "www.sciencedirect.com")


class WalledURL(ValueError):
    """The URL is behind a bot wall / didn't return a PDF — try open-access resolution."""


def download(url: str, dest: Path) -> None:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120, stream=True)
    if resp.status_code == 403 or resp.headers.get("cf-mitigated") == "challenge":
        raise WalledURL(f"Blocked ({resp.status_code}) downloading {url}")
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            fh.write(chunk)
    if dest.stat().st_size < 1024:
        raise ValueError(f"Downloaded PDF from {url} is suspiciously small")
    # Publisher landing/challenge pages return 200 with HTML, not a PDF. A file that
    # isn't a real PDF only blows up stages later (Gemini: "document has no pages"),
    # so reject it here where the message is actionable.
    with dest.open("rb") as fh:
        head = fh.read(1024)
    ctype = resp.headers.get("Content-Type", "")
    if not head.lstrip().startswith(b"%PDF") or "html" in ctype.lower():
        dest.unlink(missing_ok=True)
        raise WalledURL(f"{url} did not return a PDF (got Content-Type '{ctype}')")


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


def _ingest_one(sub: Context, url: str) -> PaperMeta:
    """Download a single paper's PDF + metadata into its sub-workdir."""
    sub.ensure_dirs()
    arxiv_id = extract_arxiv_id(url)
    if arxiv_id:
        log("ingest", f"arXiv id {arxiv_id}: fetching metadata")
        meta = fetch_arxiv_metadata(arxiv_id)
        log("ingest", f"downloading PDF for {arxiv_id}")
        download(arxiv_pdf_url(arxiv_id), sub.pdf)
    else:
        log("ingest", f"non-arXiv PDF: downloading {url}")
        try:
            download(url, sub.pdf)
        except WalledURL as e:
            # Publisher wall — look for a free copy (usually the arXiv preprint).
            log("ingest", f"{e}; resolving open-access copy")
            resolved = resolve_open_access(url)
            if not resolved:
                raise WalledURL(
                    f"{url} is behind a bot wall and no open-access copy was found. "
                    "Supply an arXiv or author-hosted PDF URL instead."
                ) from e
            pdf_url, resolved_arxiv = resolved
            log("ingest", f"open-access copy: {pdf_url}")
            if resolved_arxiv:
                meta = fetch_arxiv_metadata(resolved_arxiv)
                download(arxiv_pdf_url(resolved_arxiv), sub.pdf)
                write_json(sub.metadata, meta.model_dump())
                log("ingest", f"done: '{meta.title}' ({sub.pdf.stat().st_size} bytes)")
                return meta
            download(pdf_url, sub.pdf)
        title = title_from_pdf(sub.pdf)
        meta = PaperMeta(
            title=title,
            authors=[],
            year="",
            arxiv_id=None,
            source_url=url,
            metadata_confidence="low",
        )
        log("ingest", f"best-effort title: '{title}'")

    write_json(sub.metadata, meta.model_dump())
    log("ingest", f"done: '{meta.title}' ({sub.pdf.stat().st_size} bytes)")
    return meta


def run(ctx: Context, urls: Optional[List[str]]) -> List[PaperMeta]:
    ctx.ensure_dirs()
    metas: List[PaperMeta] = []
    manifest: List[dict] = []

    if ctx.mock:
        from mock_data import MOCK_PAPERS, build_mock_pdf

        log("ingest", f"MOCK: building {len(MOCK_PAPERS)} fixture paper(s)")
        for i, paper in enumerate(MOCK_PAPERS):
            sub = ctx.for_paper(i)
            sub.ensure_dirs()
            pdf_spec = paper["pdf"]
            build_mock_pdf(
                sub.pdf,
                title=pdf_spec["title"],
                body=pdf_spec["body"],
                figures=pdf_spec["figures"],
            )
            meta = PaperMeta(**paper["metadata"])
            write_json(sub.metadata, meta.model_dump())
            metas.append(meta)
            manifest.append({"index": i, "url": meta.source_url, "dir": f"papers/{i:02d}"})
            log("ingest", f"MOCK paper {i}: '{meta.title}' ({sub.pdf.stat().st_size} bytes)")
        write_json(ctx.papers_manifest, manifest)
        return metas

    urls = [u for u in (urls or []) if u and u.strip()]
    if not urls:
        raise ValueError("ingest requires --urls (or use --mock)")

    log("ingest", f"ingesting {len(urls)} paper(s)")
    for i, url in enumerate(urls):
        sub = ctx.for_paper(i)
        meta = _ingest_one(sub, url.strip())
        metas.append(meta)
        manifest.append({"index": i, "url": url.strip(), "dir": f"papers/{i:02d}"})

    write_json(ctx.papers_manifest, manifest)
    log("ingest", f"done: {len(metas)} paper(s) ingested")
    return metas
