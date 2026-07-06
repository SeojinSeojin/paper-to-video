import React from "react";
import { Composition, staticFile } from "remotion";
import { PaperVideo } from "./PaperVideo";
import type { PaperVideoProps, Timeline } from "./types";

// Fallback metadata used only if timeline.json cannot be loaded (should not
// happen in practice — calculateMetadata always loads it).
const FALLBACK = { fps: 30, width: 1920, height: 1080, durationInFrames: 300 };

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="PaperVideo"
      component={PaperVideo}
      durationInFrames={FALLBACK.durationInFrames}
      fps={FALLBACK.fps}
      width={FALLBACK.width}
      height={FALLBACK.height}
      defaultProps={{ dataDir: "fixtures", timeline: null } as PaperVideoProps}
      calculateMetadata={async ({ props }) => {
        // Load the single source of truth for this render and inject it into
        // props so the composition never has to fetch again.
        const res = await fetch(staticFile(`${props.dataDir}/timeline.json`));
        if (!res.ok) {
          throw new Error(
            `Could not load ${props.dataDir}/timeline.json (status ${res.status})`
          );
        }
        const timeline = (await res.json()) as Timeline;
        const fps = timeline.fps ?? FALLBACK.fps;
        return {
          durationInFrames: Math.max(1, Math.ceil((timeline.totalMs / 1000) * fps)),
          fps,
          width: timeline.width ?? FALLBACK.width,
          height: timeline.height ?? FALLBACK.height,
          props: { ...props, timeline },
        };
      }}
    />
  );
};
