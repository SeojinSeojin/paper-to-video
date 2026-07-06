#!/usr/bin/env python3
"""paper2video orchestrator.

Run the whole pipeline or a single stage:

  python pipeline/run.py --stage all --url https://arxiv.org/abs/2401.01234
  python pipeline/run.py --stage all --mock            # offline, no API keys
  python pipeline/run.py --stage render --workdir pipeline/work

Stages: ingest | script | figures | tts | render | upload | all | check
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Allow running as a script (python pipeline/run.py) or module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import Context, RENDER_PUBLIC_DIR, VIDEO_DIR, ROOT, log, read_json, write_json  # noqa: E402
from config import load_config  # noqa: E402

STATE_PATH = ROOT / "state" / "processed.json"
ALL_STAGES = ["ingest", "script", "figures", "tts", "render", "upload"]


# --------------------------------------------------------------------------- #
# processed-state helpers
# --------------------------------------------------------------------------- #
def _load_state() -> list:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("processed", [])
        except Exception:  # noqa: BLE001
            return []
    return []


def _norm(url: str) -> str:
    from ingest import extract_arxiv_id

    aid = extract_arxiv_id(url or "")
    return f"arxiv:{aid}" if aid else (url or "").strip().rstrip("/")


def is_processed(url: str) -> bool:
    key = _norm(url)
    return any(_norm(r.get("url", "")) == key for r in _load_state())


def mark_processed(url: str, result: dict, title: str) -> None:
    state = _load_state()
    state.append(
        {
            "url": url,
            "key": _norm(url),
            "video_id": result.get("video_id"),
            "video_url": result.get("url"),
            "title": title,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(STATE_PATH, state)


# --------------------------------------------------------------------------- #
# render stage (shells out to Remotion)
# --------------------------------------------------------------------------- #
def stage_render(ctx: Context) -> None:
    if not ctx.timeline.exists():
        raise FileNotFoundError(f"{ctx.timeline} missing — run the tts stage first")

    dest = RENDER_PUBLIC_DIR
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "images").mkdir(parents=True, exist_ok=True)
    (dest / "audio").mkdir(parents=True, exist_ok=True)

    shutil.copy(ctx.timeline, dest / "timeline.json")
    final_audio = ctx.audio_dir / "final.mp3"
    if not final_audio.exists():
        raise FileNotFoundError(f"{final_audio} missing — run the tts stage first")
    shutil.copy(final_audio, dest / "audio" / "final.mp3")
    for png in sorted(ctx.figures_dir.glob("*.png")):
        shutil.copy(png, dest / "images" / png.name)

    props = json.dumps({"dataDir": "render"})
    out = ctx.out_mp4.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "remotion", "render", "PaperVideo", str(out), f"--props={props}"]
    log("render", f"running: {' '.join(cmd)} (cwd={VIDEO_DIR})")
    subprocess.run(cmd, cwd=str(VIDEO_DIR), check=True)
    log("render", f"done: {out} ({out.stat().st_size} bytes)")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(description="paper2video pipeline")
    p.add_argument("--stage", required=True,
                   choices=ALL_STAGES + ["all", "check"])
    p.add_argument("--url", default=None, help="arXiv or PDF URL")
    p.add_argument("--workdir", default=str(ROOT / "pipeline" / "work"))
    p.add_argument("--lang", default=None, help="override language (ko|en)")
    p.add_argument("--mock", action="store_true", help="offline mode using fixtures")
    p.add_argument("--skip-upload", action="store_true", help="for --stage all: skip upload")
    args = p.parse_args()

    cfg = load_config(language=args.lang)
    ctx = Context(workdir=Path(args.workdir), config=cfg, mock=args.mock)
    ctx.ensure_dirs()

    # 'check' is a lightweight helper for the workflow's dedupe guard.
    if args.stage == "check":
        if not args.url:
            print("check requires --url", file=sys.stderr)
            return 2
        print("PROCESSED" if is_processed(args.url) else "NEW")
        return 0

    import ingest, script_gen, figures, tts, upload  # noqa: E402

    stages = ALL_STAGES if args.stage == "all" else [args.stage]
    if args.skip_upload and "upload" in stages:
        stages = [s for s in stages if s != "upload"]

    result = {}
    for stage in stages:
        if stage == "ingest":
            ingest.run(ctx, args.url)
        elif stage == "script":
            script_gen.run(ctx)
        elif stage == "figures":
            figures.run(ctx)
        elif stage == "tts":
            tts.run(ctx)
        elif stage == "render":
            stage_render(ctx)
        elif stage == "upload":
            result = upload.run(ctx)
            if not ctx.mock and result.get("video_id"):
                meta = read_json(ctx.metadata)
                src = args.url or meta.get("source_url", "")
                mark_processed(src, result, meta.get("title", ""))
            # Emit a parseable line for the GitHub Actions workflow.
            if result.get("url"):
                print(f"RESULT_VIDEO_URL={result['url']}", flush=True)
            write_json(ctx.workdir / "result.json", result)

    log("run", f"completed stages: {', '.join(stages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
