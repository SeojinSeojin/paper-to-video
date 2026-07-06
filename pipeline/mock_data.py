"""Built-in fixtures for --mock runs: a fake paper (PDF + metadata) and script.

The mock PDF embeds the two committed fixture figures with real "Figure N"
captions, so the *real* figures.py extraction logic runs against it during the
mocked end-to-end chain (only ingest/script/tts/upload are stubbed).
"""
from __future__ import annotations

from pathlib import Path

from config import VIDEO_DIR

FIXTURE_IMAGES = VIDEO_DIR / "public" / "fixtures" / "images"

MOCK_METADATA = {
    "title": "Efficient Transformers via Learned Sparse Attention",
    "authors": ["A. Rivera", "K. Sato", "L. Meyer", "P. Osei"],
    "year": "2024",
    "arxiv_id": "2401.01234",
    "source_url": "https://arxiv.org/abs/2401.01234",
    "metadata_confidence": "high",
}

MOCK_SCRIPT = {
    "title": "Making Transformers Fast: Learned Sparse Attention, Explained",
    "summary": (
        "A two-host walkthrough of a paper that replaces dense attention with a "
        "learned sparse pattern, cutting cost from quadratic to near-linear with "
        "little accuracy loss. We cover the intuition, the figures, and the caveats."
    ),
    "keywords": ["transformers", "sparse attention", "efficiency", "deep learning", "NLP"],
    "segments": [
        {"speaker": "A", "text": "So this paper claims transformers can be made dramatically faster. Is that actually true?", "figure": None},
        {"speaker": "B", "text": "Mostly, yes. The trick is to attend to a learned subset of tokens instead of all of them.", "figure": 1},
        {"speaker": "A", "text": "So instead of every word looking at every other word, the model picks a few important ones?", "figure": 1},
        {"speaker": "B", "text": "Exactly. Figure two shows the sparsity pattern the model discovers on its own during training.", "figure": 2},
        {"speaker": "A", "text": "And that grid is what saves all the computation?", "figure": 2},
        {"speaker": "B", "text": "Right. The cost drops from quadratic to almost linear, with barely any accuracy loss.", "figure": None},
        {"speaker": "A", "text": "That is a genuinely great tradeoff. Thanks for breaking it down so clearly.", "figure": None},
    ],
}


def build_mock_pdf(dest: Path) -> None:
    """Create a small PDF with the two fixture figures and captions."""
    import fitz  # lazy: only needed when actually building the mock

    doc = fitz.open()
    body = (
        "Efficient Transformers via Learned Sparse Attention\n\n"
        "A. Rivera, K. Sato, L. Meyer, P. Osei\n\n"
        "Abstract. We study whether the quadratic cost of self-attention can be "
        "avoided by learning, rather than fixing, which tokens attend to which. "
        "Our method reduces attention cost from O(n^2) to near O(n)."
    )
    figures = [
        (FIXTURE_IMAGES / "figure-1.png", "Figure 1: Compute cost vs. sequence length."),
        (FIXTURE_IMAGES / "figure-2.png", "Figure 2: Learned sparse attention mask."),
    ]
    for i, (img, caption) in enumerate(figures):
        page = doc.new_page(width=595, height=842)  # A4 in points
        if i == 0:
            page.insert_text((72, 90), body, fontsize=12)
            top = 260
        else:
            top = 150
        rect = fitz.Rect(120, top, 475, top + 300)
        if img.exists():
            page.insert_image(rect, filename=str(img))
        page.insert_text((120, top + 320), caption, fontsize=11)
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dest))
    doc.close()
