# Fixtures location

The runnable fixtures live in **`video/public/fixtures/`**, not here.

Remotion's `staticFile()` can only resolve assets under `public/`, and the
composition loads `timeline.json`, the narration audio, and the figure images
via `staticFile()`. Keeping the fixtures under `public/` is what lets

```bash
npx remotion studio          # preview in the browser
npx remotion render          # render out/fixture.mp4
```

work with **no API keys and no network**.

Regenerate them with:

```bash
python video/scripts/make_fixtures.py
```

See `DECISIONS.md` (entry: "Fixtures live under public/") for the rationale.
