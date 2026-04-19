# Session Config Spec

## Purpose

This file defines the per-session configuration file that controls how a session is generated and rendered.

The session config is one of two per-session sources of truth:
- the shot list = structure, narration, timing
- the session config = style, provider, reveal behavior, budget

## Canonical Location

Every session must have a session config at:

- `../spoolcast-content/sessions/<session-id>/session.json`

## Required Fields

- `session_id` — string, must match the folder name
- `ai_budget` — integer, max number of image generations allowed for the session
- `preferred_model` — string, the kie.ai model name used by default for scene generation

## Optional Fields

- `style_reference` — string. Either a descriptive style prompt or a URL/local path to a reference image.
- `default_style_prompt` — string. Fallback style prompt used when `style_reference` is not set.
- `reveal_style` — string enum. Default: `fade`. Allowed values defined in `PREPROCESSOR_RULES.md`.
- `reveal_duration_seconds` — number. Default: `1.5`.
- `scene_fps` — integer. Default: `30`.
- `resolution` — string. Default: `2K`. Allowed: `1K`, `2K`, `4K`.
- `aspect_ratio` — string. Default: `16:9`.
- `output_format` — string. Default: `png`.
- `notes` — string. Human notes, not read by any pipeline.

## Style Anchor Rule

The session config controls per-session style consistency.

- The first scene generation in the session establishes the visual style anchor.
- The anchor is recorded in the session's scene manifest.
- Every subsequent scene generation must pass the anchor reference back in as `image_input` (see `ASSET_RULES.md` — Kie Provider Spec).
- If `style_reference` is an image URL, use it directly as the anchor for the first generation.
- If `style_reference` is a prompt string, the first generated scene becomes the anchor image.
- If neither `style_reference` nor `default_style_prompt` is set, scene generation must fail loudly instead of silently picking a style.

## Model Selection Rule

`preferred_model` sets the default. Any scene may override via its own prompt metadata, but the override should be explicit in the generation request, not silent.

Known working models are listed in `ASSET_RULES.md` — Kie Provider Spec.

## Budget Rule

`ai_budget` is the hard ceiling on image generations for the session.

- Count every successful generation against the budget.
- Do not count failures or cache hits.
- When the budget is exhausted, the pipeline must stop and require explicit config change before continuing.

## Example

```json
{
  "session_id": "example-session-001",
  "ai_budget": 40,
  "preferred_model": "nano-banana-2",
  "style_reference": "loose hand-drawn marker illustration, muted earth tones, single recurring character in soft ink outlines, warm paper texture background",
  "default_style_prompt": "loose hand-drawn marker illustration",
  "reveal_style": "fade",
  "reveal_duration_seconds": 1.5,
  "scene_fps": 30,
  "resolution": "2K",
  "aspect_ratio": "16:9",
  "output_format": "png",
  "notes": "first reference case for illustrated pipeline"
}
```

## Validation Rules

A session is invalid if:

- `session.json` is missing
- `session_id` does not match the folder name
- `ai_budget` is missing or not a positive integer
- `preferred_model` is missing
- neither `style_reference` nor `default_style_prompt` is set
- `reveal_style` is set to a value not allowed by `PREPROCESSOR_RULES.md`
