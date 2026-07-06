import React from "react";
import { Img } from "remotion";
import type { Theme } from "../theme";

interface Props {
  /** fully-resolved image URL (staticFile), or null for a "discussion" motif */
  src: string | null;
  attribution: string | null;
  theme: Theme;
  fontFamily: string;
  opacity: number;
  scale: number;
}

// The figure occupies an upper band so it never collides with the subtitles.
const BAND_TOP = 116;
const BAND_HEIGHT = 600;

/**
 * The centered figure panel: rounded corners, soft violet glow (layered
 * box-shadow, no hard border), image contained on a slightly-lighter panel,
 * attribution in muted small caps beneath. When there is no figure to show
 * (discussion-only segment) it renders a subtle glowing accent orb instead of
 * an empty panel, so the frame still feels intentional.
 */
export const FigureCard: React.FC<Props> = ({
  src,
  attribution,
  theme,
  fontFamily,
  opacity,
  scale,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: BAND_TOP,
        left: 0,
        right: 0,
        height: BAND_HEIGHT,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      {src ? (
        <>
          <div
            style={{
              position: "relative",
              width: 1120,
              height: 512,
              borderRadius: 24,
              background: theme.panel,
              boxShadow: [
                "0 0 0 1px rgba(255,255,255,0.04)",
                "0 30px 80px -20px rgba(0,0,0,0.7)",
                `0 0 130px -30px ${theme.accent}`,
              ].join(", "),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            <Img
              src={src}
              style={{ maxWidth: "92%", maxHeight: "88%", objectFit: "contain", borderRadius: 8 }}
            />
          </div>
          {attribution ? (
            <div
              style={{
                fontFamily,
                fontSize: 20,
                letterSpacing: 1.2,
                color: theme.textFaint,
                maxWidth: 1120,
                textAlign: "center",
              }}
            >
              {attribution}
            </div>
          ) : null}
        </>
      ) : (
        // Discussion-only motif: a soft accent orb, no fake figure.
        <div
          style={{
            width: 300,
            height: 300,
            borderRadius: 999,
            background: `radial-gradient(circle at 50% 40%, ${theme.accent}55 0%, ${theme.accent}18 45%, transparent 70%)`,
            filter: "blur(2px)",
          }}
        />
      )}
    </div>
  );
};
