"""Stage 4 — tts: synthesize speech per segment and build timeline.json.

Real mode uses edge-tts; --mock produces silence sized by word count so the
whole chain runs offline. Both paths share the concatenation + timeline logic,
so the output shape is identical.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from pydub import AudioSegment

from common import Context, log, read_json, write_json
from config import Config
from models import PaperMeta, Script, Timeline

MOCK_WPS = 2.6  # words/sec used to fake segment durations in --mock


def _synth_real(text: str, voice: str, dest: Path) -> AudioSegment:
    async def _save() -> None:
        import edge_tts  # lazy

        await edge_tts.Communicate(text, voice).save(str(dest))

    asyncio.run(_save())
    return AudioSegment.from_file(dest)


def _synth_mock(text: str, dest: Path) -> AudioSegment:
    words = max(1, len(text.split()))
    dur = int(words / MOCK_WPS * 1000) + 500
    seg = AudioSegment.silent(duration=dur)
    seg.export(dest, format="mp3")
    return seg


def _synth_segment(ctx: Context, cfg: Config, sub: Context, seg, dest: Path) -> AudioSegment:
    if not seg.text.strip():
        # Defensive: never hand edge-tts an empty string.
        audio = AudioSegment.silent(duration=400)
        audio.export(dest, format="mp3")
    elif ctx.mock:
        audio = _synth_mock(seg.text, dest)
    else:
        audio = _synth_real(seg.text, cfg.voices[seg.speaker], dest)
    return audio


def run(ctx: Context) -> Timeline:
    cfg: Config = ctx.config
    ctx.audio_dir.mkdir(parents=True, exist_ok=True)

    subs = ctx.paper_contexts()
    digest = read_json(ctx.digest) if ctx.digest.exists() else {"title": ""}

    final = AudioSegment.silent(duration=0)
    seg_gap = AudioSegment.silent(duration=cfg.segment_gap_ms)
    paper_gap = AudioSegment.silent(duration=cfg.paper_gap_ms)
    segments: list = []
    papers: list = []
    cursor = 0
    global_index = 0

    total_lines = 0
    for i, sub in enumerate(subs):
        meta = PaperMeta.model_validate(read_json(sub.metadata))
        script = Script.model_validate(read_json(sub.script))
        figures = read_json(sub.figures_json).get("figures", {}) if sub.figures_json.exists() else {}
        papers.append(
            {
                "title": meta.title,
                "authors": meta.authors,
                "year": meta.year,
                "arxivId": meta.arxiv_id,
                "url": meta.source_url,
            }
        )
        log("tts", f"paper {i}: synthesizing {len(script.segments)} segments "
                   f"({'mock' if ctx.mock else cfg.language})")

        last_paper = i == len(subs) - 1
        for j, seg in enumerate(script.segments):
            dest = sub.audio_dir / f"seg-{j:02d}.mp3"
            audio = _synth_segment(ctx, cfg, sub, seg, dest)
            dur = len(audio)

            start_ms = cursor
            end_ms = cursor + dur
            fig_entry = figures.get(str(seg.figure)) if seg.figure else None
            image: Optional[str] = None
            attribution: Optional[str] = None
            if fig_entry and fig_entry.get("image"):
                # Namespace per paper so "figure-1.png" from different papers
                # don't collide when copied into the shared render images dir.
                image = f"images/p{i:02d}-{fig_entry['image']}"
                attribution = fig_entry.get("attribution")

            segments.append(
                {
                    "index": global_index,
                    "paperIndex": i,
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "startMs": start_ms,
                    "endMs": end_ms,
                    "figure": seg.figure,
                    "image": image,
                    "attribution": attribution,
                }
            )
            final += audio
            global_index += 1
            total_lines += 1

            last_seg = j == len(script.segments) - 1
            if last_seg and last_paper:
                cursor = end_ms
            elif last_seg:
                final += paper_gap
                cursor = end_ms + cfg.paper_gap_ms
            else:
                final += seg_gap
                cursor = end_ms + cfg.segment_gap_ms

    final_path = ctx.audio_dir / "final.mp3"
    final.export(final_path, format="mp3", bitrate="192k")
    narration_ms = cursor
    total_ms = cfg.intro_ms + narration_ms + cfg.outro_ms

    timeline = Timeline(
        language=cfg.language,  # type: ignore[arg-type]
        fps=30,
        width=1920,
        height=1080,
        papers=papers,  # type: ignore[arg-type]
        digestTitle=digest.get("title") or (papers[0]["title"] if papers else ""),
        channelName=cfg.channel_name,
        accent=cfg.accent,
        background=cfg.background,
        intro={"durationMs": cfg.intro_ms},
        outro={"durationMs": cfg.outro_ms},
        segments=segments,  # type: ignore[arg-type]
        audio="audio/final.mp3",
        totalMs=total_ms,
    )
    write_json(ctx.timeline, timeline.model_dump())
    log(
        "tts",
        f"done: {len(papers)} paper(s), {total_lines} lines, narration {narration_ms}ms, "
        f"total {total_ms}ms, audio {final_path.stat().st_size} bytes",
    )
    return timeline
