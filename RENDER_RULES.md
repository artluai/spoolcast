# Render Rules

## Purpose

This file defines how preview-data generation and Remotion rendering should behave.

## Preview Rule

The preview should act like a rough cut.

It should not act like:
- a debug export
- a diagnostics page
- a review board converted directly into a video

## Runtime Requirements

Current known-good setup:
- Node 22

Known issue:
- Node 24 caused repeated Rspack / Remotion native-binding failures on this machine

If render/build fails with Rspack native-binding errors:

1. switch to Node 22
2. remove `node_modules`
3. reinstall dependencies
4. retry render

## Canonical Render Inputs

The renderer should read:
- the current generated preview-data file
- the current scene manifest
- the current preprocessor frame folders
- the current audio metadata

It must not read:
- stale review-board HTML
- stale deleted preview-data files
- removed legacy columns
- raw scene PNGs directly (reveal is the preprocessor's job — see `PREPROCESSOR_RULES.md`)

## Required Render Behavior

The preview should:
- play each chunk's preprocessor frame sequence synced to its narration audio
- hold the final frame for the remainder of the chunk after the reveal completes
- advance to the next chunk's frame sequence on chunk change
- use full session audio correctly
- remove debug text from frame
- reflect the current shot list and session config exactly

## Preview-Data Schema

Generated preview-data for each session must contain:
- `sessionId`
- `fps`
- `chunks` — ordered array of chunk objects

Each chunk object must contain:
- `chunkId`
- `beats` — array of shot ids that fall under this chunk
- `framesDir` — path to the preprocessor output folder for this chunk
- `frameCount`
- `revealDurationSeconds`
- `chunkDurationSeconds` — total time this chunk occupies in the timeline
- `startFrame` — global frame index at which this chunk begins
- `endFrame` — global frame index at which this chunk ends
- `narrationAudioSrc` — path to the audio used for this chunk
- `narrationStartSeconds` — offset into `narrationAudioSrc`
- `narrationEndSeconds`

Optional per-chunk fields:
- `cameraMotion` — optional light motion applied on top of the frame playback (see Motion Mapping below)
- `holdFrameIndex` — which frame to hold after reveal completes (default: last frame)

## Chunk Timeline Rule

The chunk is the unit of timeline scheduling.

- frames within a chunk come from the preprocessor, nothing else
- chunk boundaries align with chunk changes in the shot list
- adjacent chunks using the same illustration should be represented as one chunk in the shot list first, not stitched at render time

## Reveal Rule

The reveal animation is owned entirely by the preprocessor.

The renderer must:
- play the PNG sequence as-is
- hold the final frame after the sequence completes
- not re-time the sequence
- not apply fade, scale, or blur on top

If a different reveal is needed, update the session config and rerun the preprocessor.

## Background Rules

The illustrated scene is the only visual layer.

If the session switches to the alternate stock/sourced mode (see `ASSET_RULES.md`):
- backgrounds are still the only visual layer
- vertical source media must be rendered as full-height backgrounds
- adjacent beats that share a background should be grouped into one chunk upstream, not stitched at render time

## Removed Columns Rule

The render pipeline must not read, preserve, or recreate data from removed legacy columns.

If a legacy shot list still contains those columns:
- delete them upstream first
- then regenerate preview data
- then rerender

## Shot-List To Render Mapping

### `Shot`
Used for:
- debug identification
- review labeling

### `Chunk`
Used for:
- grouping beats into illustration units
- driving the render timeline

### `Duration`
Used for:
- frame allocation inside a chunk

### `Script / Narration`
Used for:
- narration audio alignment
- debug only when explicitly enabled

### `Movement`
Used for:
- optional per-chunk camera motion on top of the frame playback

### `Camera`
Used for:
- optional per-chunk camera behavior

Note: prior visual-intent fields (`Tone Job`, `Background Visual`, `Asset To Find`, `Priority`) are primarily used by the scene generation stage, not the render stage.

## Motion Mapping

Camera motion is optional and applied on top of the preprocessor frame playback.

Default:
- `Static` or `Hold` — no camera motion

Allowed on top of frame playback:
- `Slow push in` — gentle scale-in across the chunk
- `Slow push out` — gentle scale-out across the chunk
- `Gentle pan left` — slow horizontal translation left across the chunk
- `Gentle pan right` — slow horizontal translation right across the chunk

Not allowed by default:
- impact shake
- micro zoom on impact
- arbitrary camera pops
- decorative transitions between chunks
- reveal effects overlaid on frame playback

## Audio Contract

The render pipeline must know:
- where audio lives
- whether timing is chunk-level or session-level
- start and end offsets for playback

If audio is session-level:
- attach it once at session scope with mapped offsets per chunk
- do not accidentally play only the first chunk

If audio is chunk-level:
- each chunk must define its own audio segment explicitly

## Visual Effect Rules

Do not apply global visual effects by default that darken or stylize the whole frame unnecessarily.

Disallowed by default:
- global gradient overlays
- decorative darkening layers that are not explicitly needed
- any effect applied on top of preprocessor frames

## Overlay Placement Schema

The one-visual-layer rule allows a carve-out for explicitly-specified overlays (see `WORKFLOW_RULES.md` Overlay carve-out). This section defines the schema.

### Per-overlay fields (read by renderer, specified in shot list)

Every overlay entry must specify ALL of the following — no defaults, no improvisation:

- `source` — path or URL to the overlay image (PNG with clean alpha preferred, SVG acceptable if rasterized at render time)
- `timing_start_s` — number of seconds into the chunk when the overlay appears. `0.0` for chunk-start.
- `timing_end_s` — number of seconds into the chunk when the overlay disappears. Must be `> timing_start_s`.
- `x` — horizontal position in 0.0-1.0 coordinates (0 = left edge, 1 = right edge) OR absolute pixels. Convention: use normalized coords.
- `y` — vertical position, same convention.
- `anchor` — which point of the overlay image is placed at (x, y). One of: `top-left`, `top-right`, `center`, `bottom-left`, `bottom-right`. Default convention: `center`.
- `width` — target width in normalized coords (0.0-1.0 fraction of canvas width) OR absolute pixels. Convention: use normalized.
- `height` — optional. If omitted, height is computed from source aspect ratio. Specify only when forcing a non-native aspect.
- `entry_transition` — one of: `cut`, `fade-in`, `pop-in`, `slide-in-left`, `slide-in-right`, `slide-in-top`, `slide-in-bottom`. Default `fade-in` over 0.2s.
- `exit_transition` — same vocabulary as entry. Default `fade-out` over 0.2s.

### Renderer behavior

On each frame, the renderer:
- iterates overlays for the current chunk
- for each overlay, checks if the current chunk-relative time is within `[timing_start_s, timing_end_s]` (including transition time)
- composites the overlay at the specified position / size / anchor with the specified entry/exit transition state
- does NOT compute its own positions, sizes, timings, or transitions

If an overlay entry is missing any required field, the renderer must fail loudly (not silently substitute defaults).

### Caps

To preserve the "overlays are rare" principle:
- Hard cap: 3 concurrent overlays on screen at any moment. Anything over 3 requires a rule-conflict flag.
- Soft cap per video: ~5-10 overlay insertions total. More than that should be redesigned as full-frame scenes, not overlay-stacked.

## Preview-Data Rules

Preview-data generation must:
- read from the current shot list
- read from the current session config
- read from the current scene manifest
- read from the current preprocessor frame folders
- export only the layers allowed by the current system

Current rule:
- preview data must contain one-chunk-per-entry with frame sequence references
- no foreground layer entries

## Render Commands

Typical local render flow:

1. go to repo root
2. confirm Node 22
3. confirm scene manifest and frame folders exist for every chunk
4. regenerate preview data if upstream changed
5. run the render from the repo root

The exact render command can vary, but it must:
- use the current composition entry
- write output into the content root `renders/` directory

## Render Regeneration Rule

When any of these change:
- shot list (including `Chunk` values)
- session config
- scene illustrations
- preprocessor frame folders
- preview-data generation logic
- composition logic

Then the video must be rerendered.

Do not trust an older MP4 if any upstream layer has changed.

Before rerender:
- overwrite or remove the prior MP4 if it shares the same output path

## Validation Rules

The render fails if:
- it shows deleted elements
- it uses stale preview data
- a chunk plays a frame folder whose scene does not match the current scene manifest
- any chunk's frame count does not match its preview-data entry
- reveal timing is modified inside the renderer
- reused illustrations play with fresh reveal when they should hold
- audio plays incorrectly across the planned duration
- motion is arbitrary or visually distracting

## Long-Running Render Rule

When starting a render:
- start it
- let it run
- avoid noisy polling unless explicitly requested

For reliability:
- prefer stable direct terminal renders over fragile detached launch patterns
