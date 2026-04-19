# Preprocessor Rules

## Purpose

This file defines the scene preprocessor: the deterministic step between scene generation and video render.

The preprocessor takes one generated full-frame illustration and produces a numbered PNG sequence that reveals the illustration over time.

The preprocessor exists so the renderer never has to improvise reveal animation.

## What The Preprocessor Is

The preprocessor is:
- deterministic — same input produces identical output every run
- local — runs on the user's machine, consumes no AI tokens
- script-based — driven by the session config and the scene manifest
- frame-producing — output is a folder of numbered PNGs

The preprocessor is not:
- a renderer
- an AI step
- a source of creative decisions
- allowed to alter the final frame

## Canonical Input

Inputs to the preprocessor:
- a generated scene PNG from `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/<chunk-id>.png`
- reveal parameters from the session config: `reveal_style`, `reveal_duration_seconds`, `scene_fps`
- the chunk id

## Canonical Output

Output folder per chunk:

- `../spoolcast-content/sessions/<session-id>/frames/<chunk-id>/`

Contents:
- `frame_0001.png`, `frame_0002.png`, ..., `frame_NNNN.png`
- `frames.json` — metadata file

Frame count rule:
- `frameCount == round(reveal_duration_seconds * scene_fps)`

Final-frame rule:
- the last frame in the sequence must equal the input scene PNG, pixel for pixel
- if it does not, the reveal is wrong and the sequence is invalid

`frames.json` must contain:

```json
{
  "chunk_id": "C1",
  "scene_src": "../source/generated-assets/scenes/C1.png",
  "reveal_style": "fade",
  "reveal_duration_seconds": 1.5,
  "scene_fps": 30,
  "frame_count": 45,
  "input_hash": "sha256:...",
  "created_at": "2026-04-19T00:00:00Z"
}
```

## Supported Reveal Styles

### `fade` (default, v1)
- frame N opacity = min(1, N / frameCount)
- underlying composition: fully opaque input image composited over a neutral background at a ramped alpha
- simplest and safest reveal; ships first

### `paint`
- soft-edged progressive wipe from one side
- no visible edge artifacts
- direction is fixed per session (default: left to right); not per chunk

### `edge-skeleton` (v2, stretch)
- detect edges on the input image (OpenCV or equivalent)
- reveal edges in stroke order over the first 60% of duration
- then reveal color fill under the edges over the remaining 40%
- intended to feel like hand-drawing, but optional

Unapproved reveal styles must not ship. Any new style requires a spec entry in this file before code references it.

## Determinism Rule

Same (input image bytes, reveal_style, reveal_duration_seconds, scene_fps) must produce identical output frames every run.

The preprocessor must not:
- use random seeds
- depend on wall-clock time
- depend on hostname, user, or any environmental state

If you need any randomness (e.g. paint edge jitter), derive it from the input image hash.

## Caching Rule

The preprocessor should not regenerate frames that are already valid.

- Compute `input_hash` from the input scene PNG bytes.
- If `frames.json` exists with matching `input_hash` and matching reveal params, skip regen.
- If any param differs, regenerate from scratch (delete the old folder first).
- A `--force` flag may skip the cache.

## Remotion Rule

The renderer must play the frame sequence produced by the preprocessor.

The renderer must not:
- generate reveal animation inline
- apply additional fade/opacity/transition effects on top of the frame sequence
- change the reveal timing
- swap out any frame with an alternate image

If a different reveal is needed, update the session config and rerun the preprocessor. Do not solve it in the renderer.

## Stale Output Rule

If the source scene image changes, the preprocessor must regenerate the frame folder.

Before regenerating:
- identify the old frame folder
- delete it or overwrite it completely
- do not leave a mixed folder with some old frames and some new frames

## Validation Rules

A preprocessor run is invalid if:

- `frames.json` is missing
- the number of frame files does not match `frame_count` in `frames.json`
- the `input_hash` in `frames.json` does not match the current scene PNG
- the final frame does not equal the input scene PNG
- the reveal style is not in the allowed list
- the frame file names are not strictly sequential (`frame_0001.png` through `frame_NNNN.png`)
