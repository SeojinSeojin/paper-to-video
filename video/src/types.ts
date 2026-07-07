// Shared types for the paper2video Remotion project.
// The shape here MUST match what pipeline/tts.py writes to timeline.json.

export type Speaker = "A" | "B";
export type Language = "ko" | "en";

export interface PaperMeta {
  title: string;
  authors: string[];
  year: string;
  arxivId: string | null;
  url: string;
}

export interface Segment {
  index: number;
  /** which paper (0-based) in Timeline.papers this line belongs to */
  paperIndex: number;
  speaker: Speaker;
  text: string;
  /** milliseconds relative to the start of the narration audio (0 = first word) */
  startMs: number;
  endMs: number;
  /** figure number the script asked to show, or null */
  figure: number | null;
  /** image path relative to dataDir (e.g. "images/figure-3.png"), or null */
  image: string | null;
  /** attribution line rendered under the figure, or null */
  attribution: string | null;
}

export interface Timeline {
  language: Language;
  fps: number;
  width: number;
  height: number;
  /** one entry per paper in the digest (single-paper runs have one) */
  papers: PaperMeta[];
  /** title shown on the intro/outro cards (paper title, or the digest title) */
  digestTitle: string;
  channelName: string;
  /** theme colors, forwarded from video.config.yaml by the pipeline */
  accent: string;
  background: string;
  intro: { durationMs: number };
  outro: { durationMs: number };
  segments: Segment[];
  /** narration audio path relative to dataDir (e.g. "audio/final.mp3") */
  audio: string;
  /** total video duration incl. intro + narration + outro */
  totalMs: number;
}

// A type alias (not an interface) so it is assignable to
// Record<string, unknown>, which Remotion's <Composition> requires.
export type PaperVideoProps = {
  /** directory under video/public that holds timeline.json, audio and images */
  dataDir: string;
  /** injected by calculateMetadata after loading timeline.json */
  timeline: Timeline | null;
};
