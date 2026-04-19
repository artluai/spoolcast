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
- current generated preview-data file
- current local media
- current audio metadata

It must not read:
- stale review-board HTML
- stale deleted preview-data files
- removed legacy columns

## Required Render Behavior

The preview should:
- use real video backgrounds when available
- use image backgrounds when video is not available
- use full scene/chapter audio correctly
- remove debug text from frame
- reflect the current shot list exactly

## Preview-Data Schema

Generated preview-data for each beat must contain:
- `shot`
- `chapter`
- `durationSeconds`
- `durationFrames`
- `script`
- `beat`
- `background`
- `movement`
- `camera`
- `toneJob`

Required `background` child fields:
- `kind` (`image` or `video`)
- `src`
- `aspectRatio`
- `isVertical`
- `previewSrc` (optional)

Optional audio fields:
- `audioSrc`
- `audioStartSeconds`
- `audioEndSeconds`

## Background Run Schema

Adjacent beats using the same background should be grouped into one run.

Each background run must contain:
- `runId`
- `backgroundSrc`
- `startBeatIndex`
- `endBeatIndex`
- `startFrame`
- `endFrame`
- `cameraMode`

The run is the unit of background playback and background motion.

## Background Rules

Backgrounds are the only visual layer.

If adjacent beats use the same background:
- treat them as one continuous background run
- do not restart the media
- do not restart the camera move

One reused background run should feel like one shot.

If the source media is vertical:
- render it as a full-height background
- do not turn it into a floating element

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
- run grouping
- review labeling

### `Duration`
Used for:
- frame allocation

### `Script / Narration`
Used for:
- optional subtitle or timing alignment logic
- debug only when explicitly enabled

### `Background Visual`
Used for:
- actual image/video source selection

### `Movement`
Used for:
- shot-level change intent

### `Camera`
Used for:
- actual background transform behavior

### `Tone Job`
Used for:
- sanity-checking asset choice, not direct transform logic

## Motion Mapping

Approved mappings:

- `Static` or `Hold`
  - no camera movement

- `Slow push` or `Slow push in`
  - gentle scale-in across the whole beat or run

- `Slow push out`
  - gentle scale-out across the whole beat or run

- `Gentle pan left`
  - slow horizontal translation left across the whole beat or run

- `Gentle pan right`
  - slow horizontal translation right across the whole beat or run

- `Lateral pan`
  - wider gentle horizontal move across the whole beat or run

- `Continuous run move`
  - one continuous transform across the full grouped run

- `Cut`
  - no interpolation between prior and next beat

Not allowed by default:
- impact shake
- micro zoom on impact
- arbitrary camera pops
- repeated reset motion on reused backgrounds
- decorative transitions between every beat

## Audio Contract

The render pipeline must know:
- where audio lives
- whether timing is beat-level or chapter-level
- start and end offsets for playback

If audio is chapter-level:
- attach it once at chapter scope
- do not accidentally play only the first beat

If audio is beat-level:
- each beat must define its own audio segment explicitly

## Visual Effect Rules

Do not apply global visual effects by default that darken or stylize the whole frame unnecessarily.

Disallowed by default:
- global gradient overlays
- decorative darkening layers that are not explicitly needed

## Preview-Data Rules

Preview-data generation must:
- read from the current shot list
- read from current validated asset data
- export only the layers allowed by the current system

Current rule:
- preview data must contain background-only beats

## Render Commands

Typical local render flow:

1. go to repo root
2. confirm Node 22
3. regenerate preview data if upstream changed
4. run the render from the repo root

The exact render command can vary, but it must:
- use the current composition entry
- write output into the content root `renders/` directory

## Render Regeneration Rule

When any of these change:
- shot list
- asset resolution
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
- reused backgrounds reset when they should be continuous
- audio plays incorrectly across the planned duration
- motion is arbitrary or visually distracting

## Long-Running Render Rule

When starting a render:
- start it
- let it run
- avoid noisy polling unless explicitly requested

For reliability:
- prefer stable direct terminal renders over fragile detached launch patterns
