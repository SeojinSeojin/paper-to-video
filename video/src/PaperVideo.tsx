import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { PaperMeta, PaperVideoProps, Segment } from "./types";
import { buildTheme, fontFamilyFor, type Theme } from "./theme";
import { computeFigureShots, msToFrames } from "./util";
import { ensureFonts } from "./fonts";
import { TitleBar } from "./components/TitleBar";
import { FigureCard } from "./components/FigureCard";
import { Subtitle } from "./components/Subtitle";
import { Intro } from "./components/Intro";
import { Outro } from "./components/Outro";

function speakerName(seg: Segment, language: string): string {
  // Host A asks, Host B explains. Names kept short and language-appropriate.
  if (language === "ko") return seg.speaker === "A" ? "진행자" : "설명자";
  return seg.speaker === "A" ? "Host" : "Guest";
}

/** Persistent top bar that follows the current paper across a digest. */
const PaperTitleBar: React.FC<{
  segments: Segment[];
  papers: PaperMeta[];
  theme: Theme;
  fontFamily: string;
}> = ({ segments, papers, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Most-recent segment that has started decides which paper we're on (mirrors
  // FigureStage), so the title holds through the small silences between lines.
  let idx = 0;
  for (let i = 0; i < segments.length; i += 1) {
    if (frame >= msToFrames(segments[i].startMs, fps)) idx = segments[i].paperIndex;
    else break;
  }
  const paper = papers[idx] ?? papers[0];
  if (!paper) return null;
  const counter = papers.length > 1 ? `${idx + 1} / ${papers.length}` : null;
  return (
    <TitleBar
      title={paper.title}
      arxivId={paper.arxivId}
      counter={counter}
      theme={theme}
      fontFamily={fontFamily}
    />
  );
};

/** Cross-fading figure stage spanning the whole narration. */
const FigureStage: React.FC<{
  segments: Segment[];
  dataDir: string;
  theme: Theme;
  fontFamily: string;
}> = ({ segments, dataDir, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const T = Math.round(0.5 * fps); // ~500ms cross-fade
  const shots = computeFigureShots(segments, fps);
  if (shots.length === 0) return null;

  // Pick the most-recent shot that has started. During the small silence gaps
  // between segments this keeps the current figure on screen instead of
  // jumping ahead to a later one.
  let idx = 0;
  for (let i = 0; i < shots.length; i += 1) {
    if (frame >= shots[i].startFrame) idx = i;
    else break;
  }
  const cur = shots[idx];
  const prev = idx > 0 ? shots[idx - 1] : null;

  const resolve = (img: string | null) => (img ? staticFile(`${dataDir}/${img}`) : null);
  const tin = interpolate(frame, [cur.startFrame, cur.startFrame + T], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const curScale = interpolate(frame, [cur.startFrame, cur.startFrame + T], [1.0, 1.03], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {prev && tin < 1 ? (
        <FigureCard
          src={resolve(prev.image)}
          attribution={prev.attribution}
          theme={theme}
          fontFamily={fontFamily}
          opacity={1 - tin}
          scale={1.03}
        />
      ) : null}
      <FigureCard
        src={resolve(cur.image)}
        attribution={cur.attribution}
        theme={theme}
        fontFamily={fontFamily}
        opacity={tin}
        scale={curScale}
      />
    </AbsoluteFill>
  );
};

export const PaperVideo: React.FC<PaperVideoProps> = ({ dataDir, timeline }) => {
  ensureFonts();
  const { fps } = useVideoConfig();

  if (!timeline) {
    return (
      <AbsoluteFill
        style={{ background: "#0E0E12", color: "#fff", alignItems: "center", justifyContent: "center" }}
      >
        timeline.json not loaded
      </AbsoluteFill>
    );
  }

  const theme = buildTheme(timeline);
  const fontFamily = fontFamilyFor(timeline.language);

  const introFrames = Math.max(1, msToFrames(timeline.intro.durationMs, fps));
  const outroFrames = Math.max(1, msToFrames(timeline.outro.durationMs, fps));
  const narrationEndMs = timeline.segments.reduce((m, s) => Math.max(m, s.endMs), 0);
  const narrationFrames = Math.max(1, msToFrames(narrationEndMs, fps));
  const audioSrc = staticFile(`${dataDir}/${timeline.audio}`);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1200px 700px at 50% -10%, ${theme.bgGradientTop} 0%, ${theme.bg} 60%)`,
      }}
    >
      {/* faint accent vignette for depth */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(900px 500px at 50% 120%, ${theme.accent}14 0%, transparent 60%)`,
        }}
      />

      <Sequence durationInFrames={introFrames} name="Intro">
        <Intro papers={timeline.papers} digestTitle={timeline.digestTitle} channelName={timeline.channelName} theme={theme} fontFamily={fontFamily} />
      </Sequence>

      <Sequence from={introFrames} durationInFrames={narrationFrames} name="Narration">
        <Audio src={audioSrc} />
        <PaperTitleBar segments={timeline.segments} papers={timeline.papers} theme={theme} fontFamily={fontFamily} />
        <FigureStage segments={timeline.segments} dataDir={dataDir} theme={theme} fontFamily={fontFamily} />
        {timeline.segments.map((seg) => {
          const start = msToFrames(seg.startMs, fps);
          const len = Math.max(1, msToFrames(seg.endMs, fps) - start);
          return (
            <Sequence key={seg.index} from={start} durationInFrames={len} name={`Seg ${seg.index}`}>
              <Subtitle
                segment={seg}
                speakerName={speakerName(seg, timeline.language)}
                theme={theme}
                fontFamily={fontFamily}
                segStartFrame={0}
              />
            </Sequence>
          );
        })}
      </Sequence>

      <Sequence from={introFrames + narrationFrames} durationInFrames={outroFrames} name="Outro">
        <Outro papers={timeline.papers} digestTitle={timeline.digestTitle} channelName={timeline.channelName} theme={theme} fontFamily={fontFamily} />
      </Sequence>
    </AbsoluteFill>
  );
};
