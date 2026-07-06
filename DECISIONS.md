# Decisions

Autonomous build decisions for **paper2video**, with rationale. Newest first
within each area. "UNVERIFIED" marks anything that needs the owner's secrets.

## Environment
- **Git repo scope**: `arxiv-yt/` was initialised as its own git repository so
  `.github/workflows/` sits at the repo root (required for GitHub Actions) and
  commits stay isolated from the surrounding home-directory git repo.
- **Python**: local toolchain is Python 3.9 by default, but 3.11 is available at
  `/opt/local/bin/python3.11`. The project targets 3.11+ and the venv + CI use
  3.11. Code avoids gratuitously new syntax so it still imports on 3.9.
- **Node**: 18.20.4 (fine for Remotion 4). **ffmpeg**: 8.0 present.

## Video / Remotion
- **Remotion v4**, pinned as `^4.0.0` in `video/package.json` so `npm install`
  resolves the current stable release. Verified: a fixture render produces a
  valid 1920×1080 H.264 + AAC MP4.
- **Dynamic duration** via `<Composition calculateMetadata>` — it fetches
  `timeline.json` (single source of truth) and returns `durationInFrames`,
  `fps`, `width`, `height`, and the loaded timeline injected back into props.
  Ref: https://www.remotion.dev/docs/dynamic-metadata
- **Fixtures live under `video/public/fixtures/`** (not a top-level
  `video/fixtures/`). Reason: `staticFile()` only serves assets from `public/`,
  and the composition loads timeline/audio/images via `staticFile()`. This is
  what makes `npx remotion studio` / `render` work offline with no keys. A
  pointer stub is left at `video/fixtures/README.md`.
- **Render data staging**: the pipeline copies a run's artifacts into
  `video/public/render/` and renders with input props `{ "dataDir": "render" }`.
  Fixtures use `{ "dataDir": "fixtures" }` (the default). `public/render/` is
  gitignored.
- **Offline fonts**: bundled `.woff2` in `public/fonts/` (Inter for EN,
  Pretendard for KO), loaded via the FontFace API with `delayRender` /
  `continueRender`. No network webfonts — CI renders offline. Inter is the
  latin subset; Pretendard includes Korean glyphs.
- **Word-level highlight** is an approximation: each segment's duration is
  distributed across its words proportionally to word length (`util.ts`
  `distributeWords`), softened by a +2 constant so it never darts across short
  words. edge-tts word boundaries are not persisted per word (kept simple).
- **Speaker names**: Host (A) / Guest (B) in English, 진행자 / 설명자 in Korean.
  A asks, B explains, per the brief.

## Pipeline
- **Mock mode scope**: `--mock` stubs only the stages with external
  dependencies — ingest (no download), script_gen (no Gemini), tts (no edge-tts
  network), upload (no YouTube). **figures and render always run for real**, so
  the mocked chain genuinely exercises PyMuPDF extraction and the Remotion
  render. Verified: `run.py --stage all --mock` produces a real MP4, and figures
  were extracted as `source: "embedded"` from the mock PDF.
- **Mock PDF**: `mock_data.build_mock_pdf` embeds the two committed fixture
  figures with real "Figure N" captions (via PyMuPDF), so extraction has
  something authentic to find offline.
- **Heavy deps are lazy-imported** (`google.genai`, `edge_tts`,
  `googleapiclient`, `PIL` in places) so `--mock` runs without them / without
  keys. They are still listed in `requirements.txt` for real runs.
- **Gemini**: model `gemini-2.5-flash` (configurable via `gemini_model` /
  `GEMINI_MODEL`), new `google-genai` SDK (`from google import genai`), PDF sent
  inline as `types.Part.from_bytes` when ≤18MB else via the Files API. Structured
  output uses `response_mime_type="application/json"` + `response_schema=Script`
  (a pydantic model). One repair retry on invalid JSON. UNVERIFIED (needs
  GEMINI_API_KEY) — code path is complete but not run against the live API.
- **Figure extraction heuristic**: find each referenced figure's "Figure N"
  caption, then (1) prefer a large embedded image above it, (2) else render the
  page region above the caption (handles vector figures), (3) else a typographic
  keyword card (Pillow). Fallback cards carry **no** arXiv attribution to avoid
  over-claiming that a synthetic card is the paper's figure.
- **TTS**: edge-tts per segment; exact duration measured by loading the saved
  mp3 with pydub (no reliance on WordBoundary events). 350ms silence between
  segments; concatenated to `audio/final.mp3`. Verified with real
  en-US-AvaNeural / ko-KR-SunHiNeural synthesis and a real timeline build.
- **Render staging**: `run.py` copies `timeline.json` + `audio/final.mp3` +
  `figures/*.png` into `video/public/render/{,audio,images}` and runs
  `npx remotion render PaperVideo <out> --props={"dataDir":"render"}`.
- **State/dedupe**: `state/processed.json` is a JSON list; entries keyed by
  normalized URL (`arxiv:<id>` when possible). `run.py --stage check --url ...`
  prints NEW/PROCESSED for the workflow's guard. Marked only after a real upload.

## Upload
- YouTube Data API v3 `videos.insert`, OAuth **refresh-token** flow built from
  `YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN` env (google-auth `Credentials`).
  Resumable `MediaFileUpload`. Cost ~1600 units / default 10,000 daily quota.
  Scope `youtube.upload`. privacyStatus **always `private`** under CI
  (`os.environ["CI"]`). `get_refresh_token.py` does the one-time local consent
  (`run_local_server`, access_type=offline, prompt=consent). UNVERIFIED (needs
  YouTube OAuth secrets).
- Description = summary + paper title/authors + arXiv link + "Figures from the
  original paper, © original authors". Tags from keywords, clamped to ~460 chars.
