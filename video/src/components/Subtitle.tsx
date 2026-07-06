import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { Segment } from "../types";
import { speakerColor, type Theme } from "../theme";
import { distributeWords } from "../util";
import { SpeakerIndicator } from "./SpeakerIndicator";

interface Props {
  segment: Segment;
  speakerName: string;
  theme: Theme;
  fontFamily: string;
  /** frame (relative to the narration sequence) where this segment starts */
  segStartFrame: number;
}

/**
 * Bottom subtitle block: speaker indicator + the current segment's text with an
 * approximate word-level highlight. Words ahead of the playhead are muted; the
 * current/spoken words are bright, easing in so the highlight glides.
 */
export const Subtitle: React.FC<Props> = ({
  segment,
  speakerName,
  theme,
  fontFamily,
  segStartFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const nowMs = ((frame - segStartFrame) / fps) * 1000 + segment.startMs;
  const words = distributeWords(segment.text, segment.startMs, segment.endMs);
  const color = speakerColor(theme, segment.speaker);

  // Gentle entrance for the whole block on segment change.
  const enter = interpolate(frame - segStartFrame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 96,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 26,
        padding: "0 7%",
        opacity: enter,
        transform: `translateY(${interpolate(enter, [0, 1], [14, 0])}px)`,
      }}
    >
      <SpeakerIndicator
        speaker={segment.speaker}
        name={speakerName}
        theme={theme}
        fontFamily={fontFamily}
        active
        enterAtFrame={segStartFrame}
      />
      <div
        style={{
          fontFamily,
          fontWeight: 600,
          fontSize: 48,
          lineHeight: 1.42,
          textAlign: "center",
          maxWidth: 1500,
          textWrap: "balance",
        }}
      >
        {words.map((w, i) => {
          // Progress of the playhead through this word, eased for smoothness.
          const p = interpolate(nowMs, [w.startMs - 60, w.startMs + 60], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const spoken = nowMs >= w.endMs - 40;
          const opacity = spoken ? 1 : interpolate(p, [0, 1], [0.34, 1]);
          const glow = p > 0.15 && !spoken;
          return (
            <span
              key={i}
              style={{
                color: opacity >= 0.99 ? theme.textPrimary : theme.textMuted,
                opacity,
                textShadow: glow ? `0 0 22px ${color}55` : "none",
                transition: "none",
              }}
            >
              {w.word}
              {i < words.length - 1 ? " " : ""}
            </span>
          );
        })}
      </div>
    </div>
  );
};
