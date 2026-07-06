# paper2video — Setup & Run Guide

Everything you need to preview the design, run the pipeline locally, and wire up
the GitHub Actions automation. Copy-paste friendly.

> Legend: ✅ = verified during the build · ⚠️ `UNVERIFIED (needs secrets)` =
> implemented but not run against the live API (needs your keys).

---

## 1. Local prerequisites

- **Node** ≥ 18 (18 and 20 both work). **Python** 3.11+. **ffmpeg** on PATH.
- macOS (Homebrew/MacPorts) or Linux.

```bash
# Python 3.11 venv (adjust the interpreter path to your system)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements.txt

# ffmpeg (pick one)
brew install ffmpeg          # macOS Homebrew
# sudo apt-get install -y ffmpeg   # Debian/Ubuntu

# Remotion / Node deps
cd video && npm install && cd ..
```

Verify: `ffmpeg -version`, `python -c "import fitz, pydub, pydantic"`, `node -v`.

---

## 2. Preview the design (no API keys needed) ✅

The composition is driven by committed fixtures under `video/public/fixtures/`.

```bash
cd video

# Interactive studio in the browser (scrub the timeline, tweak, hot-reload):
npx remotion studio

# Render the fixture to an MP4 (1920x1080, ~50s):
npx remotion render PaperVideo out/fixture.mp4
open out/fixture.mp4      # macOS ('xdg-open' on Linux)
```

Regenerate fixtures (e.g. after editing the sample script) with:

```bash
python video/scripts/make_fixtures.py
```

You can also render the whole pipeline offline with mock data (see §7).

---

## 3. Gemini API key (script generation)

1. Go to **Google AI Studio** → <https://aistudio.google.com/apikey> → *Create API key*.
2. Export it locally, and/or add it as a GitHub secret (see §5):

```bash
export GEMINI_API_KEY="your-key"
# optional: override the model (default gemini-2.5-flash)
export GEMINI_MODEL="gemini-2.5-flash"
```

Free tier is rate-limited (requests-per-minute/day). One paper = one request
(plus at most one repair retry).

---

## 4. YouTube OAuth (upload) ⚠️ `UNVERIFIED (needs secrets)`

You need three values: **client id**, **client secret**, **refresh token**.

**a. Create the project + credentials**

1. <https://console.cloud.google.com/> → create/select a project.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen** → *External* → add your Google
   account as a **Test user** (required while the app is unverified).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** →
   application type **Desktop app**. Copy the **Client ID** and **Client secret**.

**b. Get a refresh token (one-time, local)**

```bash
source .venv/bin/activate
export YOUTUBE_CLIENT_ID="....apps.googleusercontent.com"
export YOUTUBE_CLIENT_SECRET="...."
python pipeline/get_refresh_token.py
```

A browser opens for consent (log in with the Test user account, accept the
warning for the unverified app). The script prints your **refresh token**.

**c. Where each value goes**

| Value                    | Env var / GitHub secret     |
| ------------------------ | --------------------------- |
| Client ID                | `YOUTUBE_CLIENT_ID`         |
| Client secret            | `YOUTUBE_CLIENT_SECRET`     |
| Refresh token            | `YOUTUBE_REFRESH_TOKEN`     |

> **Known caveat:** unverified OAuth apps may have uploads locked to
> **private** and cannot be made public via the API. That is fine here —
> paper2video always uploads as private by design; you flip visibility manually
> in YouTube Studio. To lift the restriction you would submit the app for
> Google verification.

---

## 5. GitHub setup

**a. Repository secrets** (*Settings → Secrets and variables → Actions → New
repository secret*):

- `GEMINI_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

**b. Create the label**

```bash
gh label create video-request --description "Generate a paper2video" --color 7C6CFF
```
(or *Issues → Labels → New label*, name exactly `video-request`).

**c. Workflow permissions** — the workflow declares `issues: write` and
`contents: write`. Ensure *Settings → Actions → General → Workflow permissions*
is set to **Read and write permissions** so it can comment, close issues, and
commit `state/processed.json`.

---

## 6. First real run

**Option A — open an issue** (recommended):

- Title: anything, e.g. `Video: Attention Is All You Need`
- Body:
  ```
  https://arxiv.org/abs/1706.03762
  lang: en
  ```
- Add the **`video-request`** label. The workflow starts, comments progress, and
  on success posts the (private) YouTube link and closes the issue.

**Option B — manual dispatch:** *Actions → Generate paper video → Run workflow* →
fill in `url` (and optional `lang`).

---

## 7. Local full run

**Offline, no keys (mock)** ✅ — produces `pipeline/work/out.mp4`:

```bash
source .venv/bin/activate
python pipeline/run.py --stage all --mock
```

**Real run with your keys:**

```bash
source .venv/bin/activate
export GEMINI_API_KEY=... YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... YOUTUBE_REFRESH_TOKEN=...

# whole pipeline (ingest → script → figures → tts → render → upload):
python pipeline/run.py --stage all --url "https://arxiv.org/abs/1706.03762" --lang en

# or render locally without uploading:
python pipeline/run.py --stage all --url "https://arxiv.org/abs/1706.03762" --skip-upload

# or one stage at a time (artifacts persist in pipeline/work/):
python pipeline/run.py --stage ingest  --url "https://arxiv.org/abs/1706.03762"
python pipeline/run.py --stage script
python pipeline/run.py --stage figures
python pipeline/run.py --stage tts
python pipeline/run.py --stage render
python pipeline/run.py --stage upload
```

Artifacts land in `pipeline/work/` (`paper.pdf`, `script.json`, `figures/`,
`timeline.json`, `audio/final.mp3`, `out.mp4`).

---

## 8. Troubleshooting (the 5 most likely failure modes)

1. **YouTube quota exceeded (403 `quotaExceeded`).** `videos.insert` costs ~1600
   units of a default 10,000/day quota → ~6 uploads/day. Wait for the daily
   reset (midnight Pacific) or request more quota in the Cloud Console.

2. **Gemini rate limit / empty output (429 or validation error).** Free tier has
   per-minute/day caps. The pipeline already retries invalid JSON once; if it
   still fails, wait a minute and re-run `--stage script`, or set a paid
   `GEMINI_MODEL`. Very large PDFs (>18MB) switch to the Files API automatically.

3. **Figure extraction misses / shows a keyword card.** Mapping "Figure N" →
   image is heuristic (embedded image → region render → typographic fallback).
   A fallback card is expected behavior, not a crash. To debug, inspect
   `pipeline/work/figures.json` (`source: embedded|region|fallback`) and the PNGs
   in `pipeline/work/figures/`.

4. **Fonts / Chrome fail to render in CI.** Remotion needs a headless Chrome and
   its shared libs; the workflow installs them (`libnss3`, `libgbm1`, …). Fonts
   are bundled offline in `video/public/fonts/` (no network). If a render fails
   to launch the browser locally, run `cd video && npx remotion browser ensure`.

5. **edge-tts network error (`NoAudioReceived` / timeouts).** edge-tts calls a
   Microsoft endpoint. Transient failures: re-run `--stage tts`. If a voice name
   is rejected, confirm it in `video.config.yaml` against the current Edge voice
   list (`edge-tts --list-voices`). Corporate networks sometimes block it.

---

### What is verified vs. not

- ✅ Offline fixture render, mocked end-to-end pipeline (real figure extraction +
  real Remotion render), real edge-tts synthesis + real timeline build, workflow
  lint (actionlint clean) and issue-parser.
- ⚠️ `UNVERIFIED (needs secrets)`: Gemini script generation against the live API,
  and the YouTube upload. Both code paths are complete. Verify with the exact
  commands in §7 (real run) once your secrets are set.
