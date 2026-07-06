import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import type { Theme } from "../theme";

interface Props {
  title: string;
  arxivId: string | null;
  theme: Theme;
  fontFamily: string;
}

/** Small, low-contrast persistent bar at the very top of the frame. */
export const TitleBar: React.FC<Props> = ({ title, arxivId, theme, fontFamily }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 92,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 7%",
        opacity,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          minWidth: 0,
        }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: 3,
            background: theme.accent,
            boxShadow: `0 0 12px ${theme.accent}`,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily,
            fontWeight: 600,
            fontSize: 24,
            color: theme.textMuted,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            maxWidth: 1200,
          }}
        >
          {title}
        </span>
      </div>
      {arxivId ? (
        <span
          style={{
            fontFamily,
            fontWeight: 500,
            fontSize: 20,
            letterSpacing: 1.5,
            textTransform: "uppercase",
            color: theme.textFaint,
            flexShrink: 0,
          }}
        >
          arXiv:{arxivId}
        </span>
      ) : null}
    </div>
  );
};
