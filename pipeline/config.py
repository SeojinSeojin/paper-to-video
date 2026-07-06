"""Load video.config.yaml and resolve per-run settings (language, voices, theme)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "video.config.yaml"
VIDEO_DIR = ROOT / "video"


@dataclass
class Config:
    raw: dict
    language: str
    voice_a: str
    voice_b: str
    accent: str
    background: str
    channel_name: str
    gemini_model: str
    upload_privacy: str
    upload_category_id: str
    segment_gap_ms: int
    intro_ms: int
    outro_ms: int
    target_duration_min: int

    @property
    def voices(self) -> dict:
        return {"A": self.voice_a, "B": self.voice_b}


def load_config(language: Optional[str] = None) -> Config:
    """Load config, applying an optional language override (from CLI or issue)."""
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    lang = (language or data.get("language") or "ko").strip().lower()
    if lang not in ("ko", "en"):
        raise ValueError(f"Unsupported language '{lang}' (expected 'ko' or 'en')")

    voices = data.get("voices", {}).get(lang)
    if not voices:
        raise ValueError(f"No voices configured for language '{lang}' in video.config.yaml")

    theme = data.get("theme", {})
    return Config(
        raw=data,
        language=lang,
        voice_a=voices["hostA"],
        voice_b=voices["hostB"],
        accent=theme.get("accent", "#7C6CFF"),
        background=theme.get("background", "#0E0E12"),
        channel_name=data.get("channel_name", "paper2video"),
        gemini_model=os.environ.get("GEMINI_MODEL", data.get("gemini_model", "gemini-2.5-flash")),
        # CI always forces private; env can pin it too. Config value is the default.
        upload_privacy=os.environ.get("UPLOAD_PRIVACY", data.get("upload_privacy", "private")),
        upload_category_id=str(data.get("upload_category_id", "27")),
        segment_gap_ms=int(data.get("segment_gap_ms", 350)),
        intro_ms=int(data.get("intro_ms", 3000)),
        outro_ms=int(data.get("outro_ms", 3000)),
        target_duration_min=int(data.get("target_duration_min", 5)),
    )
