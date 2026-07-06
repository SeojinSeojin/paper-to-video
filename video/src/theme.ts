// Central design tokens. Colors default here but can be overridden per-render
// by values coming from timeline.json (which the pipeline forwards from
// video.config.yaml). Keep this the single place that defines the look.

import type { Language, Timeline } from "./types";

export const DEFAULT_ACCENT = "#7C6CFF"; // violet
export const DEFAULT_BG = "#0E0E12"; // near-black, slightly blue

export interface Theme {
  accent: string; // primary accent (Speaker A + highlights + glow)
  speakerB: string; // cool teal that pairs with the accent (Speaker B)
  bg: string; // base background
  bgGradientTop: string; // subtle depth gradient
  bgGradientBottom: string;
  panel: string; // figure panel fill (slightly lighter than bg)
  textPrimary: string;
  textMuted: string;
  textFaint: string;
}

export function buildTheme(timeline?: Timeline | null): Theme {
  const accent = timeline?.accent || DEFAULT_ACCENT;
  const bg = timeline?.background || DEFAULT_BG;
  return {
    accent,
    speakerB: "#4EC8C8",
    bg,
    bgGradientTop: "#141420",
    bgGradientBottom: bg,
    panel: "#191922",
    textPrimary: "#F4F5FA",
    textMuted: "#9AA0B4",
    textFaint: "#5C6076",
  };
}

export function fontFamilyFor(language: Language): string {
  return language === "ko"
    ? "'Pretendard', 'Noto Sans KR', sans-serif"
    : "'Inter', sans-serif";
}

export function speakerColor(theme: Theme, speaker: "A" | "B"): string {
  return speaker === "A" ? theme.accent : theme.speakerB;
}
