import React from "react";
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from "remotion";

export type SceneRunProps = {
  /**
   * Path to the frames folder, relative to Remotion's configured publicDir.
   * Example: "frames/C1". The frames folder must contain
   * `frame_0001.png` ... `frame_NNNN.png`, produced by the preprocessor.
   */
  framesDir: string;
  /**
   * Total number of reveal frames (e.g. 45 for 1.5s at 30fps).
   * After this many frames elapse, the component holds the final frame.
   */
  frameCount: number;
  /**
   * Optional background color shown before the first frame loads.
   * Should roughly match the preprocessor's neutral background.
   */
  backgroundColor?: string;
};

/**
 * SceneRun — plays a preprocessor-produced numbered PNG sequence.
 *
 * While the composition frame is within [0, frameCount - 1], displays the
 * corresponding reveal frame (1-indexed: frame 0 -> frame_0001.png).
 * After that, holds frame_NNNN.png for the rest of the chunk's duration.
 *
 * Per RENDER_RULES.md and PREPROCESSOR_RULES.md: the renderer must not
 * apply any fade, scale, or effect on top of these frames. Play as-is.
 *
 * Remotion resolves `framesDir` via `staticFile()`, so the caller must
 * configure `publicDir` to point at the location where per-chunk frame
 * folders live. For spoolcast, that is typically a session-specific
 * content directory, passed via the render CLI:
 *
 *     npx remotion render ... --public-dir=../spoolcast-content/sessions/<id>
 */
export const SceneRun: React.FC<SceneRunProps> = ({
  framesDir,
  frameCount,
  backgroundColor = "#fcfaf5",
}) => {
  const frame = useCurrentFrame();
  // frame 0 of the composition maps to frame_0001.png
  const oneIndexed = Math.min(frame + 1, frameCount);
  const padded = String(oneIndexed).padStart(4, "0");
  const src = staticFile(`${framesDir}/frame_${padded}.png`);

  return (
    <AbsoluteFill style={{backgroundColor}}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          display: "block",
        }}
      />
    </AbsoluteFill>
  );
};
