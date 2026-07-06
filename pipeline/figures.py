"""Stage 3 — figures: extract figures from the PDF, map to figure numbers.

Strategy per referenced figure number:
  1) find its "Figure N" caption in the PDF text,
  2) prefer a large embedded image sitting just above that caption,
  3) else render the page region above the caption (handles vector figures),
  4) else fall back to a typographic keyword card.
Mapping is heuristic and imperfect by nature — every path degrades gracefully.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from common import Context, log, read_json, write_json
from config import Config
from models import PaperMeta, Script

CAPTION_RE = re.compile(r"\b(?:figure|fig\.?)\s*(\d+)", re.IGNORECASE)
MIN_IMG_PX = 120          # ignore logos/icons smaller than this
RENDER_DPI = 150
MAX_REGION_PT = 430       # cap the height of a rendered figure region (points)

STOPWORDS = set(
    "the a an of to and or in on for with that this these those is are was were be by as at "
    "it its into from we our their they you your can will not but if then than so such more most "
    "using use used via when where which who what how about over under between within figure shows "
    "show model models paper method methods result results".split()
)


@dataclass
class Caption:
    number: int
    page: int
    y0: float
    y1: float


def _find_captions(doc) -> Dict[int, Caption]:
    """First caption seen for each figure number wins."""
    found: Dict[int, Caption] = {}
    for pno in range(doc.page_count):
        for b in doc[pno].get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            m = CAPTION_RE.search(text.strip())
            if not m:
                continue
            num = int(m.group(1))
            if num not in found:
                found[num] = Caption(number=num, page=pno, y0=y0, y1=y1)
    return found


def _embedded_image_above(doc, cap: Caption) -> Optional[bytes]:
    """Largest embedded image whose bottom is at/above the caption top."""
    page = doc[cap.page]
    best = None
    best_area = 0.0
    try:
        infos = page.get_image_info(xrefs=True)
    except TypeError:
        infos = page.get_image_info()
    for info in infos:
        bbox = info.get("bbox")
        xref = info.get("xref", 0)
        if not bbox or not xref:
            continue
        bx0, by0, bx1, by1 = bbox
        w, h = bx1 - bx0, by1 - by0
        if w < MIN_IMG_PX or h < MIN_IMG_PX:
            continue
        if by1 > cap.y0 + 24:  # must sit above the caption
            continue
        area = w * h
        if area > best_area:
            best_area = area
            best = xref
    if best is None:
        return None
    try:
        extracted = doc.extract_image(best)
    except Exception:  # noqa: BLE001
        return None
    return _normalize_png(extracted.get("image"))


def _normalize_png(data: Optional[bytes]) -> Optional[bytes]:
    if not data:
        return None
    from PIL import Image

    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    if im.width < MIN_IMG_PX or im.height < MIN_IMG_PX:
        return None
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def _render_region_above(doc, cap: Caption) -> Optional[bytes]:
    """Rasterise the page area above the caption (works for vector figures)."""
    import fitz

    page = doc[cap.page]
    top = max(page.rect.y0 + 40, cap.y0 - MAX_REGION_PT)
    if cap.y0 - top < 80:
        return None
    clip = fitz.Rect(page.rect.x0 + 24, top, page.rect.x1 - 24, cap.y0 - 4)
    pix = page.get_pixmap(dpi=RENDER_DPI, clip=clip)
    if pix.width < MIN_IMG_PX or pix.height < MIN_IMG_PX:
        return None
    return pix.tobytes("png")


def _segment_keywords(script: Script, number: int, limit: int = 4) -> List[str]:
    texts = [s.text for s in script.segments if s.figure == number]
    words: List[str] = []
    for t in texts:
        for w in re.findall(r"[A-Za-z가-힣][A-Za-z0-9가-힣\-]{2,}", t):
            lw = w.lower()
            if lw in STOPWORDS or w in words:
                continue
            words.append(w)
    words.sort(key=len, reverse=True)
    result = words[:limit]
    if len(result) < 2:
        result = (result + script.keywords)[:limit]
    return result


def _fallback_card(cfg: Config, number: int, keywords: List[str], dest: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 800
    bg = _hex(cfg.background)
    accent = _hex(cfg.accent)
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)

    def font(sz: int):
        try:
            return ImageFont.load_default(size=sz)
        except TypeError:
            return ImageFont.load_default()

    d.text((80, 90), f"FIGURE {number}", font=font(30), fill=accent)
    d.line([(80, 150), (300, 150)], fill=accent, width=4)
    y = 230
    for kw in keywords[:4]:
        d.ellipse([80, y + 12, 104, y + 36], fill=accent)
        d.text((130, y), kw, font=font(44), fill=(240, 241, 250))
        y += 96
    d.text((80, H - 90), "figure unavailable — key concepts", font=font(24), fill=(120, 124, 140))
    im.save(dest)


def _hex(s: str):
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def _attribution(meta: PaperMeta, number: int) -> str:
    who = meta.first_author_last()
    year = meta.year or "n.d."
    base = f"Figure {number} — {who} et al., {year}"
    if meta.arxiv_id:
        base += f" (arXiv:{meta.arxiv_id})"
    return base


def run(ctx: Context) -> dict:
    import fitz

    cfg = ctx.config
    ctx.figures_dir.mkdir(parents=True, exist_ok=True)
    meta = PaperMeta.model_validate(read_json(ctx.metadata))
    script = Script.model_validate(read_json(ctx.script))

    referenced = sorted({s.figure for s in script.segments if s.figure})
    log("figures", f"script references figures: {referenced or 'none'}")

    figures: Dict[str, dict] = {}
    if not referenced:
        write_json(ctx.figures_json, {"figures": {}})
        return {"figures": {}}

    with fitz.open(ctx.pdf) as doc:
        captions = _find_captions(doc)
        for num in referenced:
            dest = ctx.figures_dir / f"figure-{num}.png"
            data: Optional[bytes] = None
            source = "fallback"
            cap = captions.get(num)
            if cap is not None:
                data = _embedded_image_above(doc, cap)
                if data:
                    source = "embedded"
                else:
                    data = _render_region_above(doc, cap)
                    if data:
                        source = "region"

            if data:
                dest.write_bytes(data)
                figures[str(num)] = {
                    "image": f"figure-{num}.png",
                    "attribution": _attribution(meta, num),
                    "source": source,
                }
                log("figures", f"figure {num}: {source} -> {dest.name}")
            else:
                kws = _segment_keywords(script, num)
                _fallback_card(cfg, num, kws, dest)
                figures[str(num)] = {
                    "image": f"figure-{num}.png",
                    # No arXiv attribution on a synthetic card (avoid over-claiming).
                    "attribution": None,
                    "source": "fallback",
                }
                log("figures", f"figure {num}: fallback card ({', '.join(kws) or 'n/a'})")

    result = {"figures": figures}
    write_json(ctx.figures_json, result)
    return result
