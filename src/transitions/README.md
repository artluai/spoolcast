# Spoolcast transitions library

Custom presentations wrapping `@remotion/transitions`, tuned to the illustrated comic-strip vibe.

## Available

| Name | Use for | Default duration |
|---|---|---|
| `comicPan` | Inter-chunk within an act, same-thread (`continues-thread` / `continues-from-prev`). Panel-pan like a viewer's eye crossing to the next panel. | 15 frames (~0.5s) |
| `pageFlip` | Act boundaries only. Outgoing panel rotates on Y-axis like a physical page turn. Reserved — biggest transition in the library. | 24 frames (~0.8s) |
| `panelSplit` | Adjacent chunks that benefit from being on screen together (setup/payoff pair, adjacent evidence). Holds both panels visible mid-transition. | 24 frames |
| `CUT` | Reveal-groups, proof inserts, cold-open → Act-1 handoff. Zero-frame hard cut. | 1 frame |

## Editorial rules (from STORY.md § Transitions)

- **Match transition size to boundary size.** `continues-thread` → `comicPan`. `topic-shift` → `comicPan` with higher `outgoingDrift`. `act-boundary` → `pageFlip`. Reveal-group internals → `CUT`.
- **Don't over-use `pageFlip`.** If every transition is a page-flip, none of them signal anything. Chapter changes only.
- **`comicPan` direction should match reading flow.** Default `from-right` reads L→R. Use `from-left` only for deliberate callbacks (viewer's eye moving BACK to an earlier panel).
- **`CUT` beats a soft transition for deadpan punchlines.** If the next beat is a deadpan reveal, any soft transition dilutes it.

## Usage

```tsx
import {TransitionSeries} from "@remotion/transitions";
import {comicPan, pageFlip, CUT} from "./transitions";

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={90}>
    <Chunk1 />
  </TransitionSeries.Sequence>

  <TransitionSeries.Transition
    presentation={comicPan()}
    timing={comicPan.timing()}
  />

  <TransitionSeries.Sequence durationInFrames={75}>
    <Chunk2 />
  </TransitionSeries.Sequence>

  <TransitionSeries.Transition
    presentation={pageFlip()}
    timing={pageFlip.timing()}
  />

  <TransitionSeries.Sequence durationInFrames={60}>
    <ActBumper />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

## Adding a new transition

1. Create `src/transitions/<name>.tsx`.
2. Export a factory `<name>(options): TransitionPresentation<Props>` and a `<name>.timing()` helper.
3. Re-export from `src/transitions/index.ts`.
4. Document: when to use (the editorial rule), default timing, and what other transitions it substitutes for.
5. Never publish a transition that breaks the editorial rule — if `pageFlip` could theoretically fire between every chunk, that's a pipeline concern not a library concern, and it should be guarded elsewhere (e.g. in `Composition.tsx`'s transition selector).
