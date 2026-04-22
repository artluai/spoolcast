/**
 * panelSplit — two panels share the frame during handoff.
 *
 * The incoming panel enters as a growing vertical strip while the outgoing
 * panel narrows to the opposite side. Mid-transition, both panels coexist
 * on screen like a two-panel comic page — then the outgoing panel collapses
 * and the incoming panel expands to fill the frame.
 *
 * Use when two adjacent chunks are part of the same micro-moment and the
 * viewer benefits from seeing both in frame simultaneously (e.g. a setup/
 * payoff pair, or adjacent evidence beats).
 */

import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import {linearTiming} from "@remotion/transitions";
import React from "react";

type PanelSplitProps = {
  incomingFrom: "right" | "left";
  // How long the split holds both panels visible. 0 = no hold, just a wipe.
  // 1 = full duration is the split hold. Default 0.4 = first 40% enters, middle
  // 20% holds, last 40% collapses.
  splitHoldFraction: number;
};

const PanelSplitPresentation: React.FC<
  TransitionPresentationComponentProps<PanelSplitProps>
> = ({presentationProgress, presentationDirection, children, passedProps}) => {
  const {incomingFrom, splitHoldFraction} = passedProps;

  // Three-phase progress: enter (0 -> enterEnd), hold (enterEnd -> holdEnd), exit (holdEnd -> 1)
  const enterEnd = (1 - splitHoldFraction) / 2;
  const holdEnd = enterEnd + splitHoldFraction;

  let incomingWidthPct: number;
  if (presentationProgress <= enterEnd) {
    incomingWidthPct = (presentationProgress / enterEnd) * 50;
  } else if (presentationProgress <= holdEnd) {
    incomingWidthPct = 50;
  } else {
    const exitProgress = (presentationProgress - holdEnd) / (1 - holdEnd);
    incomingWidthPct = 50 + exitProgress * 50;
  }

  const isEntering = presentationDirection === "entering";
  const pctForThisSide = isEntering ? incomingWidthPct : 100 - incomingWidthPct;
  const side = isEntering ? incomingFrom : (incomingFrom === "right" ? "left" : "right");

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        [side]: 0,
        width: `${pctForThisSide}%`,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          height: "100%",
          width: `${100 / (pctForThisSide / 100)}%`,
          [side === "right" ? "right" : "left"]: 0,
        }}
      >
        {children}
      </div>
    </div>
  );
};

type PanelSplitOptions = Partial<PanelSplitProps> & {
  durationInFrames?: number;
};

export const panelSplit = (
  options: PanelSplitOptions = {},
): TransitionPresentation<PanelSplitProps> => ({
  component: PanelSplitPresentation,
  props: {
    incomingFrom: options.incomingFrom ?? "right",
    splitHoldFraction: options.splitHoldFraction ?? 0.4,
  },
});

panelSplit.timing = (options: {durationInFrames?: number} = {}) =>
  linearTiming({durationInFrames: options.durationInFrames ?? 24});
