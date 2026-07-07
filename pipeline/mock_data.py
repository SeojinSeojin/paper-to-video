"""Built-in fixtures for --mock runs: fake papers (PDF + metadata) and scripts.

Each mock PDF embeds the two committed fixture figures with real "Figure N"
captions, so the *real* figures.py extraction logic runs against it during the
mocked end-to-end chain (only ingest/script/tts/upload are stubbed).

`MOCK_PAPERS` holds several papers so the multi-paper digest path is exercised
offline. The first entry doubles as the single-paper fixture.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from config import VIDEO_DIR

FIXTURE_IMAGES = VIDEO_DIR / "public" / "fixtures" / "images"


# Each paper: metadata + script + the inputs used to build its mock PDF.
MOCK_PAPERS = [
    {
        "metadata": {
            "title": "Efficient Transformers via Learned Sparse Attention",
            "authors": ["A. Rivera", "K. Sato", "L. Meyer", "P. Osei"],
            "year": "2024",
            "arxiv_id": "2401.01234",
            "source_url": "https://arxiv.org/abs/2401.01234",
            "metadata_confidence": "high",
        },
        "pdf": {
            "title": "Efficient Transformers via Learned Sparse Attention",
            "body": (
                "Efficient Transformers via Learned Sparse Attention\n\n"
                "A. Rivera, K. Sato, L. Meyer, P. Osei\n\n"
                "Abstract. We study whether the quadratic cost of self-attention can be "
                "avoided by learning, rather than fixing, which tokens attend to which. "
                "Our method reduces attention cost from O(n^2) to near O(n)."
            ),
            "figures": [
                ("figure-1.png", "Figure 1: Compute cost vs. sequence length."),
                ("figure-2.png", "Figure 2: Learned sparse attention mask."),
            ],
        },
        "script": {
            "title": "Making Transformers Fast: Learned Sparse Attention, Explained",
            "summary": (
                "A two-host walkthrough of a paper that replaces dense attention with a "
                "learned sparse pattern, cutting cost from quadratic to near-linear with "
                "little accuracy loss."
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
        },
    },
    {
        "metadata": {
            "title": "Retrieval-Augmented Generation for Long Documents",
            "authors": ["M. Chen", "R. Kumar", "S. Ito"],
            "year": "2024",
            "arxiv_id": "2402.05678",
            "source_url": "https://arxiv.org/abs/2402.05678",
            "metadata_confidence": "high",
        },
        "pdf": {
            "title": "Retrieval-Augmented Generation for Long Documents",
            "body": (
                "Retrieval-Augmented Generation for Long Documents\n\n"
                "M. Chen, R. Kumar, S. Ito\n\n"
                "Abstract. Language models forget the middle of long inputs. We pair a "
                "lightweight retriever with the generator so only the most relevant "
                "passages enter the context window, improving factuality at lower cost."
            ),
            "figures": [
                ("figure-1.png", "Figure 1: Accuracy vs. document length."),
                ("figure-2.png", "Figure 2: Retriever attention over passages."),
            ],
        },
        "script": {
            "title": "Helping LLMs Read Long Documents: Retrieval-Augmented Generation",
            "summary": (
                "A short explainer on pairing a retriever with a generator so a language "
                "model attends only to the passages that matter, keeping long documents "
                "accurate without blowing up the context window."
            ),
            "keywords": ["retrieval", "RAG", "long context", "language models", "factuality"],
            "segments": [
                {"speaker": "A", "text": "Why do language models get worse on really long documents?", "figure": None},
                {"speaker": "B", "text": "They lose track of the middle. Figure one shows accuracy falling as the document grows.", "figure": 1},
                {"speaker": "A", "text": "So how does retrieval fix that?", "figure": 1},
                {"speaker": "B", "text": "A small retriever picks the most relevant passages first, as figure two illustrates.", "figure": 2},
                {"speaker": "A", "text": "And only those passages go into the model?", "figure": 2},
                {"speaker": "B", "text": "Right, so the context stays small and the answers stay grounded.", "figure": None},
            ],
        },
    },
]

# Backwards-compatible single-paper aliases.
MOCK_METADATA = MOCK_PAPERS[0]["metadata"]
MOCK_SCRIPT = MOCK_PAPERS[0]["script"]


def build_mock_pdf(dest: Path, title: str = None, body: str = None,
                   figures: List[Tuple[str, str]] = None) -> None:
    """Create a small PDF with the given figures and captions.

    Defaults to the first mock paper so existing single-paper callers keep working.
    `figures` is a list of (image filename under FIXTURE_IMAGES, caption).
    """
    import fitz  # lazy: only needed when actually building the mock

    spec = MOCK_PAPERS[0]["pdf"]
    body = body if body is not None else spec["body"]
    figures = figures if figures is not None else spec["figures"]

    doc = fitz.open()
    for i, (img_name, caption) in enumerate(figures):
        page = doc.new_page(width=595, height=842)  # A4 in points
        if i == 0:
            page.insert_text((72, 90), body, fontsize=12)
            top = 260
        else:
            top = 150
        rect = fitz.Rect(120, top, 475, top + 300)
        img = FIXTURE_IMAGES / img_name
        if img.exists():
            page.insert_image(rect, filename=str(img))
        page.insert_text((120, top + 320), caption, fontsize=11)
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dest))
    doc.close()
