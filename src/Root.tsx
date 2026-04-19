import "./index.css";
import React from "react";
import {Composition} from "remotion";
import {
  SpoolcastComposition,
  SPOOLCAST_DURATION_IN_FRAMES,
  SPOOLCAST_FPS,
} from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="spoolcast-pilot"
      component={SpoolcastComposition}
      durationInFrames={SPOOLCAST_DURATION_IN_FRAMES}
      fps={SPOOLCAST_FPS}
      width={1920}
      height={1080}
    />
  );
};
