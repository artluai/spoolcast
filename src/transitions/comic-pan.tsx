/**
 * comicPan — "viewer's eye moving across a comic strip"
 *
 * The outgoing panel slides out in one direction while the incoming panel
 * slides in from the opposite direction. Slight easing on the horizontal axis,
 * no vertical motion — mimics reading left-to-right across adjacent panels.
 *
 * Use for inter-chunk transitions within an act where the two chunks share
 * the same narrative thread (continues-thread / continues-from-prev). Not for
 * topic shifts, not for act boundaries.
 */

import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import {linearTiming, springTiming} from "@remotion/transitions";
import React from "react";

type ComicPanProps = {
  // Direction the incoming panel enters from.
  direction: "from-right" | "from-left";
  // 0-1; how much the outgoing panel drifts out of frame. Lower = only the
  // incoming panel slides across a held outgoing background; higher = both move.
  outgoingDrift: number;
};

const ComicPanPresentation: React.FC<
  TransitionPresentationComponentProps<ComicPanProps>
> = ({presentationProgress, presentationDirection, children, passedProps}) => {
  const {direction, outgoingDrift} = passedProps;
  const sign = direction === "from-right" ? 1 : -1;

  const isEntering = presentationDirection === "entering";
  // Entering: incoming slides from +100% (or -100%) → 0
  // Exiting: outgoing drifts toward -sign * outgoingDrift * 100%
  const translateXPct = isEntering
    ? (1 - presentationProgress) * 100 * sign
    : -presentationProgress * outgoingDrift * 100 * sign;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transform: `translateX(${translateXPct}%)`,
        willChange: "transform",
      }}
    >
      {children}
    </div>
  );
};

type ComicPanOptions = Partial<ComicPanProps> & {
  durationFrames?: number;
};

export const comicPan = (
  options: ComicPanOptions = {},
): TransitionPresentation<ComicPanProps> => ({
  component: ComicPanPresentation,
  props: {
    direction: options.direction ?? "from-right",
    outgoingDrift: options.outgoingDrift ?? 0.25,
  },
});

/**
 * Default timing — gentle spring. ~0.5s at 30fps.
 */
comicPan.timing = (options: {durationInFrames?: number} = {}) =>
  springTiming({
    durationInFrames: options.durationInFrames ?? 15,
    config: {damping: 200, stiffness: 180, mass: 0.7},
  });

/**
 * Linear variant — for when the spring feel is wrong (e.g. saga montage
 * where consistent cadence is the point).
 */
comicPan.linear = (options: {durationInFrames?: number} = {}) =>
  linearTiming({durationInFrames: options.durationInFrames ?? 15});
