"""Shared context, paths, and logging for the pipeline stages."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import Config, ROOT, VIDEO_DIR


def log(stage: str, msg: str) -> None:
    """Progress line. GitHub Actions echoes these into issue comments."""
    print(f"[{stage}] {msg}", flush=True)


def die(stage: str, msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"[{stage}] ERROR: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class Context:
    workdir: Path
    config: Config
    mock: bool

    @property
    def pdf(self) -> Path:
        return self.workdir / "paper.pdf"

    @property
    def metadata(self) -> Path:
        return self.workdir / "metadata.json"

    @property
    def script(self) -> Path:
        return self.workdir / "script.json"

    @property
    def figures_dir(self) -> Path:
        return self.workdir / "figures"

    @property
    def figures_json(self) -> Path:
        return self.workdir / "figures.json"

    @property
    def audio_dir(self) -> Path:
        return self.workdir / "audio"

    @property
    def timeline(self) -> Path:
        return self.workdir / "timeline.json"

    @property
    def out_mp4(self) -> Path:
        return self.workdir / "out.mp4"

    def ensure_dirs(self) -> None:
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)


# Directory holding built-in mock fixtures for --mock runs.
MOCK_DIR = Path(__file__).resolve().parent / "mock"
RENDER_PUBLIC_DIR = VIDEO_DIR / "public" / "render"

__all__ = [
    "log", "die", "read_json", "write_json", "Context",
    "ROOT", "VIDEO_DIR", "MOCK_DIR", "RENDER_PUBLIC_DIR",
]
