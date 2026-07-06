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

## Pipeline (see also each module)
- (filled in during Phase 2)

## Upload
- (filled in during Phase 2)
