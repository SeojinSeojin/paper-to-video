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


def build_prompt(cfg: Config, meta: PaperMeta) -> str:
    words = cfg.target_duration_min * 150
    lang = LANG_NAME[cfg.language]
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
- Total spoken length ~{words} words (about {cfg.target_duration_min} minutes). Do not pad.
- Alternate speakers naturally; A and B should each speak multiple times.
- Write natural spoken {lang}. NO markdown, NO stage directions, NO "Host A:" \
prefixes inside the "text" field — just the spoken words.
- For "figure": when a line specifically discusses a figure that exists in the \
paper, set it to that figure's number (an integer like 1, 2, 3). Otherwise null. \
Do not invent figures that are not in the paper.
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

    resp = client.models.generate_content(
        model=cfg.gemini_model,
        contents=[pdf_part, prompt + ("\n\n" + extra if extra else "")],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Script,
            temperature=0.75,
        ),
    )
    return resp.text or ""


def run(ctx: Context) -> Script:
    cfg = ctx.config

    if ctx.mock:
        from mock_data import MOCK_SCRIPT

        log("script", "MOCK: using built-in dialogue script")
        script = Script.model_validate(MOCK_SCRIPT)
        write_json(ctx.script, script.model_dump())
        return script

    meta = PaperMeta.model_validate(read_json(ctx.metadata))
    prompt = build_prompt(cfg, meta)
    log("script", f"calling Gemini ({cfg.gemini_model}) in {cfg.language}")

    raw = _generate(cfg, prompt, ctx.pdf)
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
        raw = _generate(cfg, prompt, ctx.pdf, extra=repair)
        script = Script.model_validate_json(raw)

    word_count = sum(len(s.text.split()) for s in script.segments)
    log("script", f"ok: {len(script.segments)} segments, ~{word_count} words")
    write_json(ctx.script, script.model_dump())
    return script
