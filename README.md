# paper2video

Turn an academic paper (arXiv URL) into a ~5-minute, two-host conversational
explainer video and upload it to YouTube — entirely on **GitHub Actions**, using
only **free-tier** services.

Open a GitHub issue with an arXiv link, add the `video-request` label, and a bot
does the rest: downloads the PDF, writes a NotebookLM-style two-speaker script
with Gemini, pulls the figures, narrates it with edge-tts, renders a polished
1920×1080 video with Remotion, and posts back a (private) YouTube link.

## Pipeline

```
issue (arXiv URL)
   │
   ▼
ingest ──► script_gen ──► figures ──► tts ──► render ──► upload
(PDF +     (Gemini →     (PyMuPDF    (edge-   (Remotion   (YouTube
 metadata)  dialogue      figures +   tts +    1920×1080)  private)
            JSON)         fallbacks)  timeline)
```

`timeline.json` (from the tts stage) is the single source of truth the Remotion
renderer consumes.

## What it looks like

Dark base (`#0E0E12`) with a single violet accent (`#7C6CFF`): a persistent
paper title bar, a centered figure card with a soft glow, two colored speaker
identities, and subtitles with an approximate word-level highlight. Cross-faded
figure transitions, a title intro, and an attribution outro. Fonts (Inter /
Pretendard) are bundled and loaded offline so CI renders without a network.

## Repository layout

```
pipeline/        Python 3.11 stages + run.py orchestrator (+ --mock mode)
video/           Remotion (TypeScript) composition, components, fonts, fixtures
.github/         issue-triggered workflow + request parser
video.config.yaml  language, voices, theme, model, privacy
state/processed.json  dedupe ledger
.claude/agents/  remotion-designer · pipeline-engineer · doc-researcher
DECISIONS.md     every non-obvious choice, with rationale
SETUP.md         step-by-step setup & run (start here)
```

## Quickstart

```bash
# 1) Preview the design — no API keys needed
cd video && npm install && npx remotion render PaperVideo out/fixture.mp4

# 2) Run the whole pipeline offline with mock data
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
python pipeline/run.py --stage all --mock      # -> pipeline/work/out.mp4
```

For real runs (Gemini + YouTube keys) and the GitHub automation, see
**[SETUP.md](SETUP.md)**.

## Configuration

Edit `video.config.yaml`: default `language` (`ko`/`en`), edge-tts `voices` per
language, `theme` colors, `gemini_model`, and `upload_privacy` (CI always uploads
**private** regardless). An issue body may override language with a `lang: en`
line.

## Notes & limitations

- Figure-number mapping is heuristic; unmatched figures degrade to a typographic
  keyword card. See `DECISIONS.md`.
- Uploads are always **private**; flip visibility manually in YouTube Studio.
  Unverified OAuth apps may enforce this anyway.
- Free-tier limits apply (Gemini RPM/RPD, YouTube ~6 uploads/day).

Built to run autonomously — see `DECISIONS.md` for the choices made along the way.
