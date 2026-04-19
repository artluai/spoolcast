# Transition + camera rules

How to pick entrance transitions, reveal directions, pause values, and
per-beat camera moves per chunk. Evaluated top-down; first matching rule
wins.

## Hard constraint: transition variety

**Do NOT use the same reveal type more than ~30% of the time.** A 44-chunk
video with 10 chalkboards in a row reads as one repeated style and bores
the viewer. Chalkboard in particular is expensive visual attention — use
it sparingly, not for every chapter boundary.

Target mix across the full video:
- **~60% cut** (continuity-driven, unavoidable)
- **~10-15% chalkboard** (reserved for biggest narrative shifts only)
- **~25-30% paint** (split between auto and center-out by content)

If chalkboard count exceeds ~5-6 chunks in a 40+ chunk video, downgrade
the weaker chapter boundaries to paint.

## Transition types

| Type | Script | Feel | Used for |
|---|---|---|---|
| **cut** | (none) | hard instant | continues-from-prev, proof, callbacks |
| **paint-auto** | `scripts/stroke_reveal.py --strategy auto` | organic parallel draw-on | complex/busy scenes |
| **paint-center-out** | `scripts/stroke_reveal.py --strategy center-out` | radial emergence from image center | single/centered subjects |
| **paint-sequential** | `scripts/stroke_reveal.py --strategy auto --stagger 0.85` | strokes drawn one-at-a-time | occasional dramatic reveal (reserve) |
| **chalkboard** | `scripts/chalkboard_wipe.py` | diagonal back-and-forth eraser | BIGGEST narrative shifts only |

Directional paint modes (`lr`/`rl`/`tb`/`bt`) are **banned**. They look
mechanical on our content — the parallelism dilutes the directional bias,
and forcing it makes the reveal read as a sweep.

## Entrance-picking rule (evaluated top-down)

1. **`continues-from-prev`** → **cut**. Same visual world.
2. **`image_source == proof`** → **cut**. Style-clash IS the transition.
3. **`callback-to-*`** → **cut**. Returning to known scene.
4. **Chapter boundary + BIGGEST narrative shift** → **chalkboard**.
   Biggest shifts are manually selected, not automatic. Ask: does this
   feel like the video is changing register/topic in a major way? Limit
   to ~5-6 across the whole video. See "Picking which chapters" below.
5. **Chapter boundary, lesser shift** → **paint** (auto or center-out
   by content, per rule 6).
6. **Standalone non-chapter-boundary** → **paint**.
   Subtype by image content:
   - **Single central subject** (portrait, one character, one object) →
     **paint-center-out**
   - **Complex busy scene** with many equal-weight elements → **paint-auto**
   - **Only use paint-sequential** for a single specific dramatic reveal
     moment, not as a default.

## Picking which chapters get chalkboard

Not all chapter boundaries are equal. Chalkboard is reserved for the
~5-6 most significant chapter boundaries. To qualify, a chunk must
satisfy **BOTH**:

**(1) Narrative significance** — at least one of:
- **Video opener** — the very first chunk
- **Core-concept introduction** — where the main thesis/subject is
  first named
- **Major register shift** — story → methodology, methodology →
  findings, findings → takeaways
- **Big pivot moments** — narrative turns (e.g. "we studied X → here's
  what we found")

**(2) Image-content veto (CRITICAL)** — image must be a single subject
or clear composition with breathing room. Chaos / many-equal-elements
images (ad walls, crowds, icon grids, dense scenes) **NEVER get
chalkboard**, even if they qualify on narrative significance. The
chalkboard reveal pattern needs negative space to read; on dense
content it just looks like a sweep through visual noise.

If (1) passes but (2) fails → use **paint-auto** instead.

Every other chapter boundary: paint (center-out for single-subject
chapters, auto for busy ones).

## Exit rule

- `image_source == "proof"` → **cut** out.
- Last chunk of whole video → **paint** out (closing flourish).
- Next chunk is proof → **cut** out.
- Next chunk is in a different scene (chapter boundary) → **paint** out.
- Else → **cut** out.

Exits are NEVER chalkboard — the eraser shape running in reverse reads
wrong. Use the same pre-gen frames as entrance (played reverse) for
paint-style exits.

## Pause rule (between beats within a chunk)

| pause_after | Seconds |
|---|---|
| `none` | 0.0 |
| `short` (default) | 0.3 |
| `medium` | 0.5 |
| `long` | 0.8 |

Previously medium=0.8 and long=1.5 — both felt dead on 7-12s chunks.
These values keep the breath without stalling.

## Camera rules (per-beat movements)

Default: no per-beat camera moves — the subtle 1.0→1.08 push-in carries
short chunks just fine.

**Continues-from-prev / callback exception (CRITICAL)**: chunks with
`continuity == continues-from-prev` or `continuity == callback-to-*`
must NOT have the default subtle push-in. They hold steady at zoom 1.0.

Why: the default push-in goes 1.0 → 1.08 over the chunk's duration. On
a cut between two visually-similar/continuing chunks, each independent
push-in causes the camera to "rewind" from 1.08 back to 1.0 at every
cut, which reads as a jarring tiny zoom-out. Holding steady on
continues-from-prev keeps cuts seamless.

Implemented in `Composition.tsx` `computeCamera()`: continues /
callback chunks return `{zoom: 1.0}` when no per-beat camera is set.
Standalone chunks still get the subtle push-in.

Add per-beat camera moves when **either** of these triggers:

- **Chunk duration ≥ 8 seconds** — the image needs to feel alive over
  that long, even without a specific detail to zoom to.
- **Narration explicitly names a detail** in a specific zone of the
  image (e.g. "the metrics on the laptop screen" → tight on
  upper-middle).

When adding moves:

- **Zoom vocabulary**: prefer `wide` (1.0) → `medium` (1.35). Use
  `tight` (1.9) only when the image has real content at that zone
  that the narration points to. Avoid `close` (2.8) unless narration
  dwells on one micro-detail.
- **Structure**: wide establishing → one or two focused beats → wide
  pull-back. C2's pattern is the template: 02C wide, 02D tight on
  the named detail, 02E wide again.
- **Transitions**: `transition_s = 1.0` for most pans; `0` for hard
  cuts between camera states (rare).
- **Zones available**: center, left-third, right-third, top-third,
  bottom-third, upper-middle, lower-middle, top-left, top-right,
  bottom-left, bottom-right, left, right, top, bottom.

**DO NOT auto-apply a generic camera template** (like wide → upper-middle
medium → wide) to every long chunk. The target zone must match the
image's actual focal content. A blanket `upper-middle medium` works
only when the image has real content there. For images with content
elsewhere, the zoom looks like it's panning to nothing.

If you can't pick a specific zone based on the image content, do NOT
add camera moves. The default subtle push-in is safer than a wrong
target.

## Reveal direction (chalkboard only)

Chalkboard runs on `random` — script picks one of 4 diagonals per seed.
No manual direction needed. For deterministic replay, pass `--seed`;
otherwise time-seeded variation per preprocess run.

Paint runs use `strategy` (not direction): `auto` or `center-out`. Do
not assign directional strategies.

## Final pilot mix (validated)

Across 44 chunks:
- 28 cut (64%)
- 5 chalkboard (11%) — C1, C5, C18, C29, C38
- 4 paint-auto (9%) — C6, C8, C36, (one more if expanded)
- 7 paint-center-out (16%) — C11, C13, C20, C21, C26, C42, C44

This is the target distribution. If a new session ends up with 10+
chalkboards, rebalance before rendering.

## When in doubt

Default to **paint-auto** + no per-beat camera. Only deviate when a
specific rule above triggers.
