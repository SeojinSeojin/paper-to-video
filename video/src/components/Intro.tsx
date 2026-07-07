import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { PaperMeta } from "../types";
import type { Theme } from "../theme";

interface Props {
  paper: PaperMeta;
  theme: Theme;
  fontFamily: string;
}

/** Opening title card: paper title + authors, fading and lifting in. */
export const Intro: React.FC<Props> = ({ paper, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 24 });
  const authors = paper.authors.slice(0, 6).join(", ") + (paper.authors.length > 6 ? " et al." : "");
  const out = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        padding: "0 12%",
        opacity: out,
      }}
    >
      <div
        style={{
          transform: `translateY(${interpolate(enter, [0, 1], [26, 0])}px)`,
          opacity: enter,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily,
            fontWeight: 700,
            fontSize: 74,
            lineHeight: 1.18,
            letterSpacing: -0.5,
            color: theme.textPrimary,
            textWrap: "balance",
            maxWidth: 1400,
          }}
        >
          {paper.title}
        </div>
        {authors ? (
          <div
            style={{
              fontFamily,
              fontWeight: 500,
              fontSize: 30,
              marginTop: 34,
              color: theme.textMuted,
            }}
          >
            {authors}
            {paper.year ? `  ·  ${paper.year}` : ""}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
