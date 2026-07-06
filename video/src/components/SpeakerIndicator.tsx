import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Speaker } from "../types";
import { speakerColor, type Theme } from "../theme";

interface Props {
  speaker: Speaker;
  name: string;
  theme: Theme;
  fontFamily: string;
  /** true when this speaker is currently talking */
  active: boolean;
  /** frame at which the current segment started, for the entrance spring */
  enterAtFrame: number;
}

/** Avatar dot + speaker name. The active speaker brightens and lifts subtly. */
export const SpeakerIndicator: React.FC<Props> = ({
  speaker,
  name,
  theme,
  fontFamily,
  active,
  enterAtFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const color = speakerColor(theme, speaker);

  const enter = spring({
    frame: frame - enterAtFrame,
    fps,
    config: { damping: 200 },
    durationInFrames: 12,
  });

  const dim = active ? 1 : 0.45;
  const dotScale = active ? 1 + 0.06 * Math.sin((frame / fps) * 2.2) : 1;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: interpolate(enter, [0, 1], [0, dim]),
        transform: `translateY(${interpolate(enter, [0, 1], [8, 0])}px)`,
      }}
    >
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: 999,
          background: color,
          transform: `scale(${dotScale})`,
          boxShadow: active
            ? `0 0 18px ${color}, 0 0 4px ${color}`
            : "none",
        }}
      />
      <span
        style={{
          fontFamily,
          fontWeight: 600,
          fontSize: 34,
          letterSpacing: 0.2,
          color: active ? theme.textPrimary : theme.textMuted,
        }}
      >
        {name}
      </span>
    </div>
  );
};
