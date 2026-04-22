/**
 * Spoolcast transitions library.
 *
 * Custom presentations wrapping and extending @remotion/transitions, tailored
 * to the comic-book / strip vibe for illustrated explainer videos.
 *
 * Each entry exports:
 *   - a `presentation` factory (config -> Presentation component + helpers)
 *   - a sensible default `timing` spec
 *   - TS types for config
 *
 * Usage inside a <TransitionSeries>:
 *
 *   import {comicPan, pageFlip, CUT} from "./transitions";
 *   ...
 *   <TransitionSeries.Transition
 *     presentation={comicPan({direction: "from-right"})}
 *     timing={comicPan.timing()}
 *   />
 *
 * When to use which (the editorial rule, from STORY.md § Transitions):
 *   - comicPan: inter-chunk, within an act, same-thread (continues-thread /
 *     continues-from-prev). Mimics the viewer's eye moving across panels.
 *   - pageFlip: act boundaries only (act-boundary chunks, and their preceding
 *     bumper). The bigger the transition, the stronger the signal; pageFlip
 *     is the strongest and is reserved for chapter changes.
 *   - CUT: use inside reveal-groups, for proof inserts, and for the hard-cut
 *     between the cold-open thesis landing and Act 1's opener (so the reset
 *     feels like a deliberate page, not a soft blend).
 *
 * All transitions honor the existing stroke-reveal frame sequences — they
 * only affect the inter-chunk hand-off, not the within-chunk reveal.
 */

export {comicPan} from "./comic-pan";
export {pageFlip} from "./page-flip";
export {panelSplit} from "./panel-split";
export {CUT} from "./cut";
