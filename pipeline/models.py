"""Pydantic schemas shared across pipeline stages.

`Script` doubles as the Gemini `response_schema`, so its field names/shape are
the contract for structured output. `Timeline` is validated before rendering and
its serialised shape MUST match video/src/types.ts.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Script (Gemini output)
# --------------------------------------------------------------------------- #
class ScriptSegment(BaseModel):
    speaker: Literal["A", "B"] = Field(description="A asks/reacts, B explains")
    text: str = Field(description="Spoken line, no markdown or stage directions")
    figure: Optional[int] = Field(
        default=None, description="Figure number to show during this line, or null"
    )

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class Script(BaseModel):
    title: str = Field(description="Video title")
    summary: str = Field(description="2-3 sentence summary for the YouTube description")
    keywords: List[str] = Field(description="Search keywords / tags")
    segments: List[ScriptSegment]

    @field_validator("segments")
    @classmethod
    def _non_empty(cls, v: List[ScriptSegment]) -> List[ScriptSegment]:
        if not v:
            raise ValueError("script must contain at least one segment")
        return v


# --------------------------------------------------------------------------- #
# Paper metadata (ingest output)
# --------------------------------------------------------------------------- #
class PaperMeta(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    year: str = ""
    arxiv_id: Optional[str] = None
    source_url: str = ""
    metadata_confidence: Literal["high", "low"] = "high"

    def first_author_last(self) -> str:
        if not self.authors:
            return "Unknown"
        # "Ashish Vaswani" -> "Vaswani"; "Vaswani, A." -> "Vaswani"
        name = self.authors[0].strip()
        if "," in name:
            return name.split(",")[0].strip()
        return name.split()[-1] if name.split() else name


# --------------------------------------------------------------------------- #
# Timeline (tts output; consumed by Remotion) — mirrors video/src/types.ts
# --------------------------------------------------------------------------- #
class TimelineSegment(BaseModel):
    index: int
    # Which paper (0-based) in `Timeline.papers` this line belongs to.
    paperIndex: int = 0
    speaker: Literal["A", "B"]
    text: str
    startMs: int
    endMs: int
    figure: Optional[int] = None
    image: Optional[str] = None
    attribution: Optional[str] = None


class TimelinePaper(BaseModel):
    title: str
    authors: List[str]
    year: str
    arxivId: Optional[str] = None
    url: str = ""


class Timeline(BaseModel):
    language: Literal["ko", "en"]
    fps: int = 30
    width: int = 1920
    height: int = 1080
    # One entry per paper in the digest (a single-paper run has one).
    papers: List[TimelinePaper]
    # Title shown on the intro/outro cards (the paper title, or the digest title).
    digestTitle: str
    channelName: str
    accent: str
    background: str
    intro: dict
    outro: dict
    segments: List[TimelineSegment]
    audio: str
    totalMs: int
