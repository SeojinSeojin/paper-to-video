// Offline font loading via the FontFace API. CI has no network, so we never
// use webfonts — the .woff2 files are bundled in public/fonts and loaded from
// there. delayRender blocks the render until the faces are ready so text never
// renders in a fallback face.

import { staticFile, delayRender, continueRender } from "remotion";

interface FaceSpec {
  family: string;
  weight: string;
  file: string;
}

const FACES: FaceSpec[] = [
  { family: "Inter", weight: "400", file: "fonts/Inter-Regular.woff2" },
  { family: "Inter", weight: "600", file: "fonts/Inter-SemiBold.woff2" },
  { family: "Inter", weight: "700", file: "fonts/Inter-Bold.woff2" },
  { family: "Pretendard", weight: "400", file: "fonts/Pretendard-Regular.woff2" },
  { family: "Pretendard", weight: "600", file: "fonts/Pretendard-SemiBold.woff2" },
  { family: "Pretendard", weight: "700", file: "fonts/Pretendard-Bold.woff2" },
];

let started = false;

/** Idempotently load all bundled fonts. Safe to call from a component body. */
export function ensureFonts(): void {
  if (started || typeof document === "undefined") return;
  started = true;
  const handle = delayRender("Loading bundled fonts");
  Promise.all(
    FACES.map(async (f) => {
      const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {
        weight: f.weight,
        style: "normal",
        display: "block",
      });
      await face.load();
      (document.fonts as FontFaceSet).add(face);
    })
  )
    .then(() => continueRender(handle))
    .catch((err) => {
      // Never hang the render on a font problem — log and continue.
      // eslint-disable-next-line no-console
      console.error("Font load failed:", err);
      continueRender(handle);
    });
}
