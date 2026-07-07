"""Stage 2 — script_gen: PDF -> two-host dialogue script (Gemini, JSON)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from common import Context, log, read_json, write_json
from config import Config
from models import PaperMeta, Script

LANG_NAME = {"ko": "Korean", "en": "English"}
INLINE_LIMIT = 18 * 1024 * 1024  # bytes; above this use the Files API

# Gemini can return transient 5xx / 429 under load ("high demand"). Retry these
# ourselves with exponential backoff — the SDK's own retry does not always cover 503.
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5


def _generate_content_with_retry(client, **kwargs):
    from google.genai import errors

    for attempt in range(_MAX_RETRIES):
        try:
            return client.models.generate_content(**kwargs)
        except errors.APIError as exc:
            status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if status not in _RETRY_STATUS or attempt == _MAX_RETRIES - 1:
                raise
            delay = min(2 ** attempt, 30)
            log("script", f"Gemini {status} (attempt {attempt + 1}/{_MAX_RETRIES}); "
                          f"retrying in {delay}s")
            time.sleep(delay)


def _figures_block(available: dict) -> str:
    """Tell the model exactly which figures exist so it references real ones."""
    if not available:
        return ('This paper has no detected figures — set "figure" to null on '
                "every line.")
    lines = ["Figures available in this paper (reference ONLY these numbers in "
             'the "figure" field, when a line explains that figure):']
    for num in sorted(available):
        cap = available[num]
        lines.append(f"- Figure {num}" + (f": {cap}" if cap else ""))
    lines.append('When a line does not discuss a specific figure, set "figure" '
                 "to null. Do NOT reference any figure number not listed above.")
    return "\n".join(lines)


def build_prompt(cfg: Config, meta: PaperMeta, words: int, available: dict) -> str:
    lang = LANG_NAME[cfg.language]
    minutes = max(1, round(words / 150))
    return f"""You are the writers' room for a short, high-quality explainer video about \
the attached academic paper. Produce a natural, two-host conversation in {lang}.

Hosts:
- Host A ("speaker": "A") is a sharp, curious non-expert. A asks the questions a \
smart viewer would ask, reacts, and keeps things grounded.
- Host B ("speaker": "B") is the expert who explains clearly, using plain-language \
analogies rather than jargon.

Style (NotebookLM-like):
- Open with a short hook that makes the viewer care.
- Explain the core idea in plain language with an analogy or two.
- Be honest about limitations or caveats.
- End with a brief, satisfying wrap-up.

Hard requirements:
- Total spoken length ~{words} words (about {minutes} minute(s)). Do not pad.
- Alternate speakers naturally; A and B should each speak multiple times.
- Write natural spoken {lang}. NO markdown, NO stage directions, NO "Host A:" \
prefixes inside the "text" field — just the spoken words.
- Figures: reference them so viewers see the paper's own visuals. {_figures_block(available)}
- "title" is a compelling video title. "summary" is 2-3 sentences for the video \
description. "keywords" are 5-8 search tags.

Paper title (for reference): {meta.title}
Return ONLY JSON matching the provided schema."""


def _generate(cfg: Config, prompt: str, pdf: Path, extra: str = "") -> str:
    from google import genai  # lazy
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (or run with --mock)")
    client = genai.Client(api_key=api_key)

    pdf_bytes = pdf.read_bytes()
    if len(pdf_bytes) <= INLINE_LIMIT:
        pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    else:
        log("script", f"PDF is {len(pdf_bytes)//(1024*1024)}MB — using Files API")
        uploaded = client.files.upload(file=str(pdf))
        for _ in range(30):
            if getattr(uploaded.state, "name", "") == "ACTIVE":
                break
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
        pdf_part = uploaded

    resp = _generate_content_with_retry(
        client,
        model=cfg.gemini_model,
        contents=[pdf_part, prompt + ("\n\n" + extra if extra else "")],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Script,
            temperature=0.75,
        ),
    )
    return resp.text or ""


def _generate_one(cfg: Config, sub: Context, words: int, available: dict) -> Script:
    """Generate + validate a single paper's script (caller persists it)."""
    meta = PaperMeta.model_validate(read_json(sub.metadata))
    prompt = build_prompt(cfg, meta, words, available)
    log("script", f"calling Gemini ({cfg.gemini_model}) in {cfg.language} for '{meta.title}'")

    raw = _generate(cfg, prompt, sub.pdf)
    try:
        script = Script.model_validate_json(raw)
    except Exception as first_err:  # noqa: BLE001 - retry once with a repair prompt
        log("script", f"invalid JSON ({first_err}); retrying once with repair prompt")
        repair = (
            "Your previous output did not validate. Return ONLY valid JSON that "
            "matches the schema exactly: keys title (string), summary (string), "
            "keywords (array of strings), segments (array of {speaker:'A'|'B', "
            "text:string, figure:int|null}). No prose, no code fences."
        )
        raw = _generate(cfg, prompt, sub.pdf, extra=repair)
        script = Script.model_validate_json(raw)

    word_count = sum(len(s.text.split()) for s in script.segments)
    log("script", f"ok: {len(script.segments)} segments, ~{word_count} words")
    return script


def _ensure_figures_referenced(script: Script, available: dict) -> None:
    """Guarantee the video shows the paper's figures.

    If the model already tagged at least one *real* figure, trust it. Otherwise
    (the common failure that leaves videos figure-less) auto-attach the detected
    figures, spread across the explainer (Host B) lines in figure order.
    """
    nums = sorted(available)
    if not nums:
        return
    tagged = {s.figure for s in script.segments if s.figure}
    if tagged & set(nums):
        # Drop any hallucinated numbers the model invented that don't exist.
        for s in script.segments:
            if s.figure is not None and s.figure not in available:
                s.figure = None
        return

    # Prefer explainer lines; fall back to all lines if B never speaks.
    targets = [i for i, s in enumerate(script.segments) if s.speaker == "B"] \
        or list(range(len(script.segments)))
    if not targets:
        return
    for k, num in enumerate(nums):
        script.segments[targets[(k * len(targets)) // len(nums)]].figure = num
    log("script", f"no real figure referenced — auto-attached figures {nums}")


def _compose_digest(cfg: Config, ctx: Context, scripts) -> dict:
    """Deterministically build the digest title/summary/keywords from per-paper scripts."""
    if len(scripts) == 1:
        s = scripts[0]
        digest = {"title": s.title, "summary": s.summary, "keywords": list(s.keywords)}
    else:
        title = f"{cfg.digest_title} — {len(scripts)} papers"
        lines = [f"In this digest we cover {len(scripts)} recent papers:", ""]
        for i, s in enumerate(scripts, start=1):
            lines.append(f"{i}. {s.title} — {s.summary.strip()}")
        # De-duplicated union of per-paper keywords, order preserved.
        seen, keywords = set(), []
        for s in scripts:
            for kw in s.keywords:
                k = kw.strip()
                if k and k.lower() not in seen:
                    seen.add(k.lower())
                    keywords.append(k)
        digest = {"title": title, "summary": "\n".join(lines), "keywords": keywords}
    write_json(ctx.digest, digest)
    return digest


def run(ctx: Context) -> dict:
    cfg = ctx.config
    subs = ctx.paper_contexts()
    # Single-paper runs keep the fuller target length; digests use the shorter
    # per-paper budget so a ~10-paper video stays watchable.
    if len(subs) <= 1:
        words = cfg.target_duration_min * 150
    else:
        words = int(cfg.digest_duration_min_per_paper * 150)

    import figures  # local import avoids any import-order surprises

    mock_scripts = None
    if ctx.mock:
        from mock_data import MOCK_PAPERS

        mock_scripts = MOCK_PAPERS
        log("script", f"MOCK: using {len(subs)} built-in dialogue script(s)")

    scripts = []
    for i, sub in enumerate(subs):
        available = figures.available_figures(sub.pdf)
        log("script", f"paper {i}: figures detected in PDF: "
                      f"{sorted(available) or 'none'}")
        if mock_scripts is not None:
            script = Script.model_validate(mock_scripts[i]["script"])
        else:
            script = _generate_one(cfg, sub, words, available)
        # Detection-driven guarantee: real figures make it into the video even
        # when the model forgets to reference them.
        _ensure_figures_referenced(script, available)
        write_json(sub.script, script.model_dump())
        scripts.append(script)

    digest = _compose_digest(cfg, ctx, scripts)
    log("script", f"digest: '{digest['title']}' from {len(scripts)} paper(s)")
    return digest
