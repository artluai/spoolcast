/**
 * CUT — instant hard cut, zero-frame transition.
 *
 * Use for reveal-groups (where the group's cadence itself is the rhythm),
 * proof inserts (the style-clash is the transition signal), and the
 * cold-open → Act-1 boundary (so the handoff reads as a deliberate page
 * break rather than a soft blend).
 *
 * This is a thin re-export of `@remotion/transitions`' `none()` presentation
 * plus a zero-frame linear timing. Exists in the library so the callsite
 * reads consistently with the other named transitions.
 */

import {linearTiming, TransitionSeries} from "@remotion/transitions";
import {none} from "@remotion/transitions/none";

export const CUT = {
  presentation: none(),
  timing: () => linearTiming({durationInFrames: 1}),
};

// Re-export so consumers don't need a second import for the series container.
export {TransitionSeries};
