/**
 * pageFlip — the chapter-turn transition.
 *
 * The outgoing panel rotates on the Y axis like a physical page turning,
 * revealing the incoming panel. Combined with a subtle paper-shadow pass
 * (optional) to sell the physicality.
 *
 * Use at act boundaries ONLY — the biggest transition in the video, reserved
 * for "we are moving to a new chapter." Overusing it flattens its signal.
 */

import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import {springTiming} from "@remotion/transitions";
import React from "react";

type PageFlipProps = {
  // Which way the page flips: "forward" = right edge lifts first (reading
  // direction); "backward" = left edge lifts first (rare, for flashbacks).
  direction: "forward" | "backward";
  // Subtle shadow band drawn across the flipping page during the arc.
  showShadow: boolean;
};

const PageFlipPresentation: React.FC<
  TransitionPresentationComponentProps<PageFlipProps>
> = ({presentationProgress, presentationDirection, children, passedProps}) => {
  const {direction, showShadow} = passedProps;
  const isEntering = presentationDirection === "entering";

  // The outgoing page rotates from 0° → -180° (forward) or +180° (backward).
  // The incoming page sits still; the outgoing page flipping off-axis reveals it.
  const sign = direction === "forward" ? -1 : 1;

  if (isEntering) {
    // Incoming: static, sits underneath the flipping outgoing page.
    return (
      <div style={{position: "absolute", inset: 0}}>{children}</div>
    );
  }

  // Exiting: rotate around the spine (opposite edge from where it lifts).
  const rotationDeg = presentationProgress * 180 * sign;
  const transformOrigin = direction === "forward" ? "left center" : "right center";
  const opacity = presentationProgress < 0.5 ? 1 : 0; // hide after midpoint

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transform: `perspective(2000px) rotateY(${rotationDeg}deg)`,
        transformOrigin,
        backfaceVisibility: "hidden",
        opacity,
        willChange: "transform",
      }}
    >
      {children}
      {showShadow ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(${
              direction === "forward" ? "90deg" : "270deg"
            }, rgba(0,0,0,${presentationProgress * 0.25}) 0%, transparent 60%)`,
            pointerEvents: "none",
          }}
        />
      ) : null}
    </div>
  );
};

type PageFlipOptions = Partial<PageFlipProps> & {
  durationInFrames?: number;
};

export const pageFlip = (
  options: PageFlipOptions = {},
): TransitionPresentation<PageFlipProps> => ({
  component: PageFlipPresentation,
  props: {
    direction: options.direction ?? "forward",
    showShadow: options.showShadow ?? true,
  },
});

/**
 * Default timing — slower spring, ~0.8s at 30fps. Page flips should feel
 * weighty; snap looks cheap.
 */
pageFlip.timing = (options: {durationInFrames?: number} = {}) =>
  springTiming({
    durationInFrames: options.durationInFrames ?? 24,
    config: {damping: 140, stiffness: 100, mass: 1.1},
  });
