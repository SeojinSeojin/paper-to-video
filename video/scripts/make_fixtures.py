#!/usr/bin/env python3
"""Generate self-contained Remotion fixtures (no API keys, no pipeline needed).

Writes into video/public/fixtures/:
  - images/figure-1.png, images/figure-2.png   (fake but realistic academic figures)
  - audio/final.mp3                             (silent narration of the right length)
  - timeline.json                               (the single source of truth)

Run:  python video/scripts/make_fixtures.py
Requires: Pillow, ffmpeg on PATH.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "public" / "fixtures"
IMG_DIR = FIX / "images"
AUDIO_DIR = FIX / "audio"

INK = (28, 30, 38)
GRID = (210, 213, 222)
ACCENT = (124, 108, 255)
TEAL = (78, 200, 200)
PAPER = (250, 250, 252)


def font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def figure_line_chart(path: Path) -> None:
    """A two-curve line chart: 'quadratic vs learned-sparse' cost."""
    W, H = 1200, 800
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    left, top, right, bottom = 130, 120, W - 70, H - 110

    d.text((left, 54), "Figure 1: Compute cost vs. sequence length", font=font(30), fill=INK)
    # axes
    d.line([(left, top), (left, bottom)], fill=INK, width=3)
    d.line([(left, bottom), (right, bottom)], fill=INK, width=3)
    # gridlines
    for i in range(1, 6):
        y = bottom - i * (bottom - top) / 6
        d.line([(left, y), (right, y)], fill=GRID, width=1)
    # quadratic (dense)
    pts_q = []
    for i in range(0, 101):
        x = left + i / 100 * (right - left)
        y = bottom - (i / 100) ** 2 * (bottom - top) * 0.95
        pts_q.append((x, y))
    d.line(pts_q, fill=INK, width=4)
    # near-linear (sparse)
    pts_l = []
    for i in range(0, 101):
        x = left + i / 100 * (right - left)
        y = bottom - (i / 100) * (bottom - top) * 0.42
        pts_l.append((x, y))
    d.line(pts_l, fill=ACCENT, width=4)
    # labels
    d.text((right - 250, top + 10), "dense O(n^2)", font=font(24), fill=INK)
    d.text((right - 250, bottom - 120), "sparse ~O(n)", font=font(24), fill=ACCENT)
    d.text((W // 2 - 120, bottom + 40), "sequence length", font=font(24), fill=INK)
    im.save(path)


def figure_sparsity(path: Path) -> None:
    """A sparsity heatmap: which tokens attend to which."""
    W, H = 1200, 800
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.text((130, 54), "Figure 2: Learned sparse attention mask", font=font(30), fill=INK)
    n = 16
    cell = 40
    ox, oy = 160, 140
    for r in range(n):
        for c in range(n):
            # local band + a few learned global columns
            on = abs(r - c) <= 2 or c in (0, 5, 11)
            if on:
                inten = 1.0 - min(abs(r - c), 3) / 4
                col = tuple(int(PAPER[k] + (ACCENT[k] - PAPER[k]) * inten) for k in range(3))
            else:
                col = (238, 239, 244)
            x0, y0 = ox + c * cell, oy + r * cell
            d.rectangle([x0, y0, x0 + cell - 2, y0 + cell - 2], fill=col)
    d.text((ox, oy + n * cell + 24), "rows = query token   cols = key token", font=font(24), fill=INK)
    im.save(path)


# A two-paper digest so the fixture exercises the multi-paper render path.
PAPERS = [
    {
        "meta": {
            "title": "Efficient Transformers via Learned Sparse Attention",
            "authors": ["A. Rivera", "K. Sato", "L. Meyer", "P. Osei"],
            "year": "2024",
            "arxivId": "2401.01234",
            "url": "https://arxiv.org/abs/2401.01234",
        },
        "attrib": "Rivera et al., 2024 (arXiv:2401.01234)",
        "segments": [
            ("A", "So this paper claims transformers can be made dramatically faster. Is that actually true?", None),
            ("B", "Mostly, yes. The trick is to attend to a learned subset of tokens instead of all of them.", 1),
            ("A", "So instead of every word looking at every other word, the model picks a few important ones?", 1),
            ("B", "Exactly. Figure two shows the sparsity pattern the model discovers on its own.", 2),
            ("A", "And that grid is what saves all the computation? Great tradeoff.", 2),
        ],
    },
    {
        "meta": {
            "title": "Retrieval-Augmented Generation for Long Documents",
            "authors": ["M. Chen", "R. Kumar", "S. Ito"],
            "year": "2024",
            "arxivId": "2402.05678",
            "url": "https://arxiv.org/abs/2402.05678",
        },
        "attrib": "Chen et al., 2024 (arXiv:2402.05678)",
        "segments": [
            ("A", "Why do language models get worse on really long documents?", None),
            ("B", "They lose track of the middle. Figure one shows accuracy falling as the document grows.", 1),
            ("A", "So how does retrieval fix that?", 1),
            ("B", "A small retriever picks the most relevant passages first, as figure two illustrates.", 2),
            ("A", "And only those go into the model, so the answers stay grounded.", 2),
        ],
    },
]

INTRO_MS = 3000
OUTRO_MS = 3000
GAP_MS = 350
PAPER_GAP_MS = 900
WPS = 2.6  # words per second, rough speaking rate for fixture timing


def build_timeline() -> tuple:
    segments = []
    papers = []
    t = 0
    gi = 0
    for pi, paper in enumerate(PAPERS):
        papers.append(paper["meta"])
        last_paper = pi == len(PAPERS) - 1
        for si, (spk, text, fig) in enumerate(paper["segments"]):
            words = len(text.split())
            dur = int(words / WPS * 1000) + 500
            image = f"images/p{pi:02d}-figure-{fig}.png" if fig else None
            attribution = f"Figure {fig} — {paper['attrib']}" if fig else None
            segments.append(
                {
                    "index": gi,
                    "paperIndex": pi,
                    "speaker": spk,
                    "text": text,
                    "startMs": t,
                    "endMs": t + dur,
                    "figure": fig,
                    "image": image,
                    "attribution": attribution,
                }
            )
            gi += 1
            last_seg = si == len(paper["segments"]) - 1
            if last_seg and last_paper:
                t += dur
            elif last_seg:
                t += dur + PAPER_GAP_MS
            else:
                t += dur + GAP_MS
    narration_ms = segments[-1]["endMs"]
    total_ms = INTRO_MS + narration_ms + OUTRO_MS
    return {
        "language": "en",
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "papers": papers,
        "digestTitle": "Paper Digest — 2 papers",
        "channelName": "paper2video",
        "accent": "#7C6CFF",
        "background": "#0E0E12",
        "intro": {"durationMs": INTRO_MS},
        "outro": {"durationMs": OUTRO_MS},
        "segments": segments,
        "audio": "audio/final.mp3",
        "totalMs": total_ms,
    }, narration_ms


def make_silence(path: Path, ms: int) -> None:
    seconds = max(0.5, ms / 1000)
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{seconds:.3f}", "-q:a", "9", "-acodec", "libmp3lame", str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    # Two papers reuse the same two chart images under per-paper namespaced names
    # (p00-figure-1.png, ...) to mirror the pipeline's real output layout.
    figure_line_chart(IMG_DIR / "figure-1.png")
    figure_sparsity(IMG_DIR / "figure-2.png")
    for pi in range(len(PAPERS)):
        for fig in (1, 2):
            (IMG_DIR / f"p{pi:02d}-figure-{fig}.png").write_bytes(
                (IMG_DIR / f"figure-{fig}.png").read_bytes()
            )
    timeline, narration_ms = build_timeline()
    make_silence(AUDIO_DIR / "final.mp3", narration_ms)
    (FIX / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2))
    print(f"Fixtures written to {FIX}")
    print(f"  narration {narration_ms} ms, total {timeline['totalMs']} ms, {len(timeline['segments'])} segments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
