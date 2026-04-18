import "./index.css";
import React from "react";
import {Composition} from "remotion";
import {
  MyComposition,
  TEMPLATE_DURATION_IN_FRAMES,
  TEMPLATE_FPS,
} from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="session-to-video-template"
      component={MyComposition}
      durationInFrames={TEMPLATE_DURATION_IN_FRAMES}
      fps={TEMPLATE_FPS}
      width={1920}
      height={1080}
    />
  );
};
