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
  papers: PaperMeta[];
  digestTitle: string;
  channelName: string;
  theme: Theme;
  fontFamily: string;
}

/** Opening title card. For one paper: title + authors. For a digest: the digest
 * title, a "N papers" eyebrow, and the list of paper titles — all fading in. */
export const Intro: React.FC<Props> = ({ papers, digestTitle, channelName, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 24 });
  const single = papers.length === 1 ? papers[0] : null;
  const authors = single
    ? single.authors.slice(0, 6).join(", ") + (single.authors.length > 6 ? " et al." : "")
    : "";
  const eyebrow = single ? channelName : `${channelName}  ·  ${papers.length} papers`;
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
            fontWeight: 600,
            fontSize: 22,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: theme.accent,
            marginBottom: 34,
          }}
        >
          {eyebrow}
        </div>
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
          {single ? single.title : digestTitle}
        </div>
        {single && authors ? (
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
            {single.year ? `  ·  ${single.year}` : ""}
          </div>
        ) : null}
        {!single ? (
          <div
            style={{
              fontFamily,
              fontWeight: 500,
              fontSize: 26,
              lineHeight: 1.5,
              marginTop: 36,
              color: theme.textMuted,
              textAlign: "left",
              maxWidth: 1200,
              marginLeft: "auto",
              marginRight: "auto",
            }}
          >
            {papers.slice(0, 6).map((p, i) => (
              <div key={i} style={{ marginBottom: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                <span style={{ color: theme.accent, marginRight: 14 }}>{i + 1}</span>
                {p.title}
              </div>
            ))}
            {papers.length > 6 ? (
              <div style={{ color: theme.textFaint }}>+ {papers.length - 6} more</div>
            ) : null}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
