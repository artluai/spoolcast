import "./index.css";
import React from "react";
import {Composition} from "remotion";
import {
  SpoolcastComposition,
  SPOOLCAST_DURATION_IN_FRAMES,
  SPOOLCAST_FPS,
  SPOOLCAST_WIDTH,
  SPOOLCAST_HEIGHT,
} from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="spoolcast-pilot"
      component={SpoolcastComposition}
      durationInFrames={SPOOLCAST_DURATION_IN_FRAMES}
      fps={SPOOLCAST_FPS}
      width={SPOOLCAST_WIDTH}
      height={SPOOLCAST_HEIGHT}
    />
  );
};
