// Small pure helpers shared across components.

export function msToFrames(ms: number, fps: number): number {
  return Math.round((ms / 1000) * fps);
}

export interface WordTiming {
  word: string;
  startMs: number;
  endMs: number;
}

/**
 * Distribute a segment's [startMs, endMs) window across its words,
 * proportionally to each word's length. This is an approximation of
 * word-level timing (edge-tts boundaries are not persisted per word),
 * tuned to feel smooth rather than exact.
 */
export function distributeWords(
  text: string,
  startMs: number,
  endMs: number
): WordTiming[] {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  // +2 softens the difference between very short and long words so the
  // highlight never darts across several tiny words in one frame.
  const weights = words.map((w) => w.length + 2);
  const total = weights.reduce((a, b) => a + b, 0);
  const span = Math.max(0, endMs - startMs);
  let acc = startMs;
  return words.map((word, i) => {
    const dur = (weights[i] / total) * span;
    const wStart = acc;
    acc += dur;
    return { word, startMs: wStart, endMs: acc };
  });
}

/** A contiguous run of segments that all display the same figure image. */
export interface FigureShot {
  image: string | null;
  attribution: string | null;
  startFrame: number;
  endFrame: number;
}

export function computeFigureShots(
  segments: { startMs: number; endMs: number; image: string | null; attribution: string | null }[],
  fps: number
): FigureShot[] {
  const shots: FigureShot[] = [];
  for (const seg of segments) {
    const startFrame = msToFrames(seg.startMs, fps);
    const endFrame = msToFrames(seg.endMs, fps);
    const last = shots[shots.length - 1];
    if (last && last.image === seg.image) {
      last.endFrame = endFrame;
      if (!last.attribution && seg.attribution) last.attribution = seg.attribution;
    } else {
      shots.push({
        image: seg.image,
        attribution: seg.attribution,
        startFrame,
        endFrame,
      });
    }
  }
  return shots;
}
