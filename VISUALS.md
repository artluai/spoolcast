# Visuals

Everything on-screen and how it animates: asset generation, preprocessor, transitions.

## Table of Contents

- [Part 1 — Assets (generation, sourcing, overlays)](#part-1--assets-generation-sourcing-overlays)
  - [Purpose](#purpose)
  - [Global Asset Rule](#global-asset-rule)
  - [Primary Visual Pipeline: AI-Illustrated Scenes](#primary-visual-pipeline-ai-illustrated-scenes)
    - [Model](#model)
    - [Per-Chunk Generation Rule](#per-chunk-generation-rule)
    - [Style Anchor Rule](#style-anchor-rule)
    - [Multi-element anchors ("character sheet" style)](#multi-element-anchors-character-sheet-style)
    - [Prompt Assembly Rule](#prompt-assembly-rule)
    - [Scene Output Contract](#scene-output-contract)
  - [Asset Validity Rule](#asset-validity-rule)
  - [Canonical Asset Output Locations](#canonical-asset-output-locations)
  - [Scene Manifest Contract](#scene-manifest-contract)
  - [Kie Provider Spec](#kie-provider-spec)
    - [Calling kie from new scripts (rule)](#calling-kie-from-new-scripts-rule)
    - [Gotchas (learned the hard way — don't relearn these)](#gotchas-learned-the-hard-way--dont-relearn-these)
    - [Recovery procedure](#recovery-procedure-when-generation-completes-on-kieai-but-local-script-was-killed-before-downloading)
  - [Reuse Rules](#reuse-rules)
  - [AI Budget Rule](#ai-budget-rule)
  - [Transparency Rule](#transparency-rule)
  - [Asset Failure Rules](#asset-failure-rules)
  - [Validation Checklist](#validation-checklist)
  - [Narration-Text Audit Rule](#narration-text-audit-rule)
  - [Overlay Sourcing (Logos, Badges, Contextual Markers)](#overlay-sourcing-logos-badges-contextual-markers)
    - [Required source qualities](#required-source-qualities)
    - [Sourcing order for brand logos](#sourcing-order-for-brand-logos)
    - [Sourcing for non-logo overlays](#sourcing-for-non-logo-overlays)
    - [Manifest entries](#manifest-entries)
  - [Punchline Chunk Carve-Out (Style-Anchor Override)](#punchline-chunk-carve-out-style-anchor-override)
  - [Alternate Mode: Stock / Sourced Assets](#alternate-mode-stock--sourced-assets)
    - [Sourcing Order](#sourcing-order)
    - [Fetch Pipeline](#fetch-pipeline)
    - [Fetch Rules](#fetch-rules)
    - [Thumbnail Rules](#thumbnail-rules)
    - [Provenance Rules](#provenance-rules)
    - [Alternate-Mode Manifest](#alternate-mode-manifest)
- [Part 2 — Preprocessor (reveal animation)](#part-2--preprocessor-reveal-animation)
  - [Preprocessor Purpose](#preprocessor-purpose)
  - [What The Preprocessor Is](#what-the-preprocessor-is)
  - [Canonical Input](#canonical-input)
  - [Canonical Output](#canonical-output)
  - [Supported Reveal Styles](#supported-reveal-styles)
  - [Determinism Rule](#determinism-rule)
  - [Caching Rule](#caching-rule)
  - [Remotion Rule](#remotion-rule)
  - [Stale Output Rule](#stale-output-rule)
  - [Validation Rules](#validation-rules)
- [Part 3 — Transitions](#part-3--transitions)
  - [Hard constraint: transition variety](#hard-constraint-transition-variety)
  - [Transition types](#transition-types)
  - [Entrance-picking rule (evaluated top-down)](#entrance-picking-rule-evaluated-top-down)
  - [Picking which chapters get chalkboard](#picking-which-chapters-get-chalkboard)
  - [Exit rule](#exit-rule)
  - [Pause rule (between beats within a chunk)](#pause-rule-between-beats-within-a-chunk)
  - [Camera rules (per-beat movements)](#camera-rules-per-beat-movements)
  - [Reveal direction (chalkboard only)](#reveal-direction-chalkboard-only)
  - [Final pilot mix (validated)](#final-pilot-mix-validated)
  - [When in doubt](#when-in-doubt)

## Part 1 — Assets (generation, sourcing, overlays)

### Asset Rules

#### Purpose

This file defines how agents and apps should generate, source, validate, reuse, fetch, manifest, and budget visual assets.

#### Global Asset Rule

The primary visual system uses one AI-generated illustration per narration chunk.

That means:
- generate illustrations per chunk, not per beat
- do not build a workflow that depends on a second visual layer
- create contrast by moving to the next illustration on the next chunk
- reuse a prior chunk's illustration explicitly when narrative calls for it

A second mode — stock and sourced assets — is supported but is not the default. See "Alternate Mode: Stock / Sourced Assets" below.

#### Primary Visual Pipeline: AI-Illustrated Scenes

##### Model

The primary provider is kie.ai. See the Kie Provider Spec section below.

##### Per-Chunk Generation Rule

For each unique `Chunk` value in the shot list:
- compose a prompt from the chunk's narration and beat descriptions
- merge the session's style anchor (prompt or reference image)
- submit a scene generation job
- on success, download the result into `source/generated-assets/scenes/<chunk-id>.png`
- write or update the scene manifest

Do not generate more than one illustration per chunk unless the prior generation is being replaced.

##### Style Anchor Rule

Every session has one locked visual style.

- The style anchor is established on the first successful scene generation.
- The anchor is recorded in the scene manifest (anchor type, source, task id if applicable).
- Every subsequent scene generation in the session must pass the anchor reference back in through `input.image_input` so character and style stay consistent across chunks.

##### Multi-element anchors ("character sheet" style)

When a session needs visual continuity on **multiple recurring elements** (e.g. two characters, a landmark object, a specific location), the anchor itself should be constructed to include those elements — a single rich "character sheet" image rather than multiple separate named anchors.

Why one richer anchor instead of N smaller ones:
- kie.ai's `image_input` is an array, but passing multiple style references confuses compositional tendencies. One comprehensive image biases the model more cleanly than a set.
- Keeps the manifest simple: one `style_anchor` field, not a keyed set.
- Every chunk's image-ref flow stays identical to the single-element case.

How to build a multi-element anchor:
1. Before locking the anchor, list the elements that must stay visually consistent across the session (main character, any secondary characters, key props, any recurring location).
2. Generate an anchor that shows all those elements together in a neutral composition — like a character sheet with the main character on the left, secondary character on the right, a representative prop in front. Style locked by the session's `default_style_prompt`.
3. Subsequent scene generations style-reference this comprehensive anchor. The model picks up the relevant element(s) based on what the scene's `beat_description` actually calls for.

For sessions with only one recurring element (the current default case), the anchor can be a single-character composition. The multi-element approach is an upgrade, not a requirement.

If `session.json` has `style_reference` set to an image URL or local path:
- use it directly as the anchor for the first generation.

If `style_reference` is a descriptive prompt:
- the first generated scene becomes the anchor image from that point on.

If neither `style_reference` nor `default_style_prompt` is set:
- scene generation must fail loudly instead of silently picking a style.

##### Prompt Assembly Rule

Per-chunk prompts should combine:
- the session style anchor (prompt or a reference to the anchor image)
- the narration text across all beats in the chunk
- the beat descriptions across all beats in the chunk
- aspect ratio and resolution from session config

The prompt must not include:
- references to second visual layers
- instructions to produce transparent or cutout output
- requests for readable text in the image

##### Scene Output Contract

Per-chunk outputs:
- `source/generated-assets/scenes/<chunk-id>.png` — the final downloaded scene image
- one entry per chunk in `manifests/scenes.manifest.json`

#### Asset Validity Rule

An asset is valid only if it can be visibly reviewed.

An asset is not valid if it is:
- only a task ID
- an unresolved URL
- a broken preview
- a fetch that returned HTML instead of media
- stale compared with the current shot list

#### Canonical Asset Output Locations

Generated scenes:
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/`

Fetched external assets (alternate mode only):
- `../spoolcast-content/sessions/<session-id>/source/fetched-assets/`

Scene manifests:
- `../spoolcast-content/sessions/<session-id>/manifests/scenes.manifest.json`

Review thumbnails:
- `../spoolcast-content/sessions/<session-id>/review/`

#### Scene Manifest Contract

Every scene-generation run should write or update one scene manifest.

Format: JSON.

Canonical filename: `scenes.manifest.json` inside `manifests/`.

Required top-level fields:
- `run_name`
- `session_id`
- `created_at`
- `style_anchor` — object with `kind` (`prompt`, `image_url`, `local_image`) and `value`
- `items`

Required per-item fields:
- `id` — scene id, typically equal to `chunk_id`
- `chunk_id`
- `role` — allowed values: `scene`
- `model` — kie.ai model name used
- `prompt` — the full prompt sent to the provider
- `task_id`
- `result_url`
- `local_path`
- `mime_type`
- `status` — allowed values: `success`, `failed`, `stale`

Optional per-item fields:
- `aspect_ratio`
- `resolution`
- `output_format`
- `image_input` — references to anchor images used
- `notes`

#### Kie Provider Spec

Current image-generation provider:
- Kie

Current env var:
- `KIE_API_KEY` in `spoolcast/.env`

Base URL:
- `https://api.kie.ai`

Submit endpoint:
- `POST /api/v1/jobs/createTask`

Polling endpoint:
- `GET /api/v1/jobs/recordInfo?taskId=<taskId>`

Auth:
- `Authorization: Bearer <KIE_API_KEY>`

Current known working models used in this project:
- `nano-banana-pro`
- `nano-banana-2`
- `seedream/5-lite-text-to-image`
- `wan 2.7 image`

Canonical request body shape:

```json
{
  "model": "nano-banana-2",
  "callBackUrl": "https://your-domain.com/api/callback",
  "input": {
    "prompt": "your prompt here",
    "image_input": [],
    "aspect_ratio": "16:9",
    "resolution": "2K",
    "output_format": "png"
  }
}
```

For image-reference jobs:
- put source image URLs in `input.image_input`

Initial response shape:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "task_nano-banana-2_1765178625768"
  }
}
```

Polling response shape:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "task_12345678",
    "model": "nano-banana-2",
    "state": "success",
    "param": "{\"model\":\"...\",\"input\":{\"prompt\":\"...\"}}",
    "resultJson": "{\"resultUrls\":[\"https://example.com/generated-content.jpg\"]}",
    "failCode": "",
    "failMsg": ""
  }
}
```

Known task states:
- `waiting`
- `queuing`
- `generating`
- `success`
- `fail`

After Kie polling succeeds:
- download the result immediately
- save it locally
- write a manifest entry containing `task_id`, `result_url`, `local_path`, and the style anchor reference if used

##### Calling kie from new scripts (rule)

Any new script that submits a kie task **MUST** use one of:

1. **`generate_scene.py`** — for normal per-chunk illustrations (preferred)
2. **`build_input_from_session(session_id, prompt=..., ...)`** from
   `kie_client.py` — for one-off images that bypass per-chunk style mixing
   (e.g. thumbnails, marketing assets)

**Forbidden**: calling `build_input_for_model()` directly in a one-off
script. Doing so bypasses the session config and can silently ship at
the wrong resolution. As of the kie_client update, `build_input_for_model()`
also requires `quality` with no default — so a missing arg is a hard
error, not a silent wrong value.

Why: a thumbnail script previously called `build_input_for_model()` and
omitted `quality`, which used the function's default ("basic" → "2K")
instead of the session config's "1K". Combined with kie_client having no
HTTP timeout, the bad-resolution request hung forever with no error
message. Cost ~30 minutes of debugging.

##### Gotchas (learned the hard way — don't relearn these)

**`resultJson` is a JSON-encoded STRING, not an object.** You must
`json.loads()` it before reading `resultUrls`. Reading `data.resultJson.resultUrls`
directly returns nothing and looks like the API failed when it didn't.
Same trap applies to `data.param`.

```python
import json
result_urls = json.loads(data["resultJson"]).get("resultUrls", [])
```

**`resultUrls` is camelCase, plural, and a list.** Not `result_url` /
`result_urls` / `image_url`. The local `KieResult` dataclass exposes it
as `result_urls` (snake_case Python convention) — pre-parsed from the
nested JSON string. Use `result.result_urls`, not `result.image_url`.

**Generated media URLs expire after 24 hours.** Hosted files retained
~14 days but the URL stops resolving after 24h. Download immediately on
poll success — don't store URLs and download later.

**`--image-ref` must be a URL, not a local file path.** Kie validates
the input shape and returns 422 "does not match format 'uri'" on local
paths. The `generate_scene.py` script auto-pulls the session's
`style_anchor` URL from the manifest if `--image-ref` is omitted — so
the cleanest call is `generate_scene.py --session ... --chunk ...
--narration ... --beat ...` with NO `--image-ref` flag.

**Model name matters.** Use `nano-banana-2` (with the `-2` suffix), not
`nano-banana`. The bare name returns 422 "model not supported".

##### Recovery procedure (when generation completes on kie.ai but local script was killed before downloading)

If `generate_scene.py` is interrupted between submission and download
(common when terminals close or processes get killed), the task is
still completing on kie.ai's side. Recovery:

1. Find the `taskId` in the kie.ai dashboard for that chunk.
2. Poll directly:
   ```bash
   curl -s -H "Authorization: Bearer $KIE_API_KEY" \
     "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<TASK_ID>"
   ```
3. Parse `data.resultJson` (JSON-decode it), pull the URL from `resultUrls[0]`,
   and `curl -o <chunk>-nano-1k.png <URL>` it into
   `sessions/<session>/source/generated-assets/scenes/`.
4. Optionally update `manifests/scenes.manifest.json` with a new entry
   for completeness (not strictly required for downstream rendering).

Do this within 24 hours of submission or the URL will have expired and
you'll need to re-bill the generation.

#### Reuse Rules

Reuse is preferred when:
- a later chunk intentionally returns to an earlier illustration
- a chunk is aesthetically identical to an adjacent chunk and the narration does not demand change

Reuse should be explicit in the shot list (same `Chunk` value across rows, or an explicit reuse note).

Do not silently duplicate work.

#### AI Budget Rule

`ai_budget` in `session.json` is a hard ceiling on successful scene generations for the session.

- count successful generations against the budget
- do not count cache hits or failures
- when the budget is exhausted, stop the pipeline and require an explicit config change before continuing

#### Transparency Rule

Transparency-heavy workflows are not the default.

Current default:
- do not rely on transparent cutout assets
- do not assume AI-generated transparency is reliable
- prefer full-frame backgrounds instead
- do not request transparent output from the model

#### Asset Failure Rules

If a source fails repeatedly:
- replace it entirely

Do not keep trying to force the same broken source.

If an asset type repeatedly causes fragile downstream behavior:
- simplify the workflow
- do not keep preserving a broken pattern

#### Validation Checklist

Before considering the asset stage complete:

1. every chunk in the shot list has a generated scene illustration
2. every illustration is locally visible and valid
3. every scene manifest entry includes provenance (task_id, result_url, local_path)
4. the style anchor is recorded
5. failed generations are clearly marked
6. reuse is explicit in the shot list
7. AI budget is not exceeded
8. **every generated image containing visible numbers, prices, labels, or other narration-relevant text has been audited against the actual narration** (see below)

#### Narration-Text Audit Rule

Any generated image that contains visible numbers, prices, UI labels, chart
values, receipt/invoice lines, or other text that a viewer can read must be
audited against the beat's narration before the chunk is locked. The image
model will confidently hallucinate plausible-looking numbers (TOTAL: $95.50
on a "price of a coffee" receipt, view counts, bar-chart heights, etc.) and
those numbers contradict the voice-over unless checked.

**Procedure:**
1. After generation, open the PNG and read every legible number/label in it.
2. Read the beat's narration and the narrations of adjacent chunks that
   reference the same quantity.
3. If any readable number or label is inconsistent with (or awkwardly
   specific relative to) the narration, regenerate with an explicit,
   numerical prompt: "The receipt shows exactly 'TOTAL: $2'. No other
   numbers visible." Vague prompts produce hallucinated specifics.
4. For chunks whose scene is intentionally text-free (stick figures, objects,
   abstract metaphor), re-prompt to explicitly suppress text ("no labels,
   no numbers, no writing anywhere in the image") if the first gen invents
   them.

**Chunks to audit by default:** any chunk whose narration mentions a price,
count, duration, percentage, rate, ratio, or proper noun; any chunk whose
beat description specifies a UI (receipt, chart, screen, label).

---

#### Overlay Sourcing (Logos, Badges, Contextual Markers)

Per the overlay carve-out in PIPELINE.md and the placement schema in PIPELINE.md, overlays are permitted on top of the primary chunk illustration. This section covers where overlay source images come from.

##### Required source qualities

Overlay images must be:
- **Authoritative**: brand logos from the brand's own press kit or official SVG, not fan-art versions
- **Clean alpha**: PNG with proper transparency, or SVG. No white boxes, no anti-aliased edges on solid backgrounds, no jpg artifacts
- **Appropriately sized at source**: at least 2x the target display size to avoid upscaling blur

AI-generated transparency is **still banned** — that was the original overlay failure mode. If an AI model is the only way to produce the overlay, pick a full-frame substitution instead (see Punchline Chunk Carve-Out below, or the scene illustration).

##### Sourcing order for brand logos

When a chunk needs a brand logo overlay, source in this order:

1. **Brand press kit / official download page** — always the canonical source. Brand names + "press kit" or "logo download" in search.
2. **Wikipedia's SVG for the brand** — usually licensed under Creative Commons or public domain, consistently clean.
3. **Simple Icons** (`simpleicons.org`) — SVG library of brand icons, MIT-licensed.
4. **Bing / DuckDuckGo image search** — parseable HTML with direct `murl` URLs, good fallback when canonical sources aren't responsive.
5. **Claude in Chrome → Google Image Search** — when other paths fail or the asset type is non-brand (memes, reference shots, screenshots of concepts). Extract first result URL from the rendered DOM.
6. **Direct brand CDN guesses** (`https://<brand>.com/favicon.png`, etc.) — last resort, often tiny.

Store downloaded overlay assets in `sessions/<session-id>/source/overlays/<brand>.png` or `.svg`. Filename must match what the shot list references.

##### Sourcing for non-logo overlays

For badges, callouts, checkmark icons, "NEW" labels, and similar small contextual markers:

- **Material Symbols** and **Feather Icons** — free icon libraries with SVG output
- **Hand-drawn in anchor style via kie.ai** — when the overlay should match the session's illustration aesthetic rather than stand out. Generate once, reuse across chunks.

For cleanly-cropped real screenshots (e.g., showing a specific UI element inline):
- Take the screenshot at 2x target resolution
- Crop tightly to the element
- Save as PNG with the surrounding area alpha-cleared (use a tool like Preview's Instant Alpha, or Figma's Remove Background)

##### Manifest entries

Each overlay source file gets a manifest entry in `source/overlays/overlays.manifest.json`:

```json
{
  "meta-logo": {
    "source_kind": "press-kit",
    "source_url": "https://about.meta.com/brand/",
    "local_path": "source/overlays/meta-logo.png",
    "license": "Meta brand guidelines (attribution not required)",
    "fetched_at": "2026-04-20T12:00:00Z",
    "native_width": 512,
    "native_height": 512
  }
}
```

This lets the review board and future sessions verify attribution and license status at a glance.

#### Punchline Chunk Carve-Out (Style-Anchor Override)

Default: every chunk's illustration is style-locked to the session anchor (see Style Anchor Rule above).

Exception: single-beat chunks marked as **deadpan punchlines** (see STORY.md heuristic 10a) may use a real meme image, reaction gif, screenshot, or external cultural-reference visual as the full-frame chunk image — deliberately breaking the anchor style for comedic punctuation.

Constraints:
- **Full-frame substitution only, never overlay.** The meme/reaction visual IS the chunk's image, not composited on top of a style-locked scene. The one-visual-layer rule (PIPELINE.md, `rules.md`) still applies.
- **Single-beat chunks only.** Multi-beat chunks stay in anchor style. The substitution is reserved for the specific moment the punchline lands.
- **Budget: ~1-2 per video.** Past that, the substitution stops being a spike and becomes a running device — the anchor style's consistency starts to feel porous. Rarity is what makes it work.
- **Flag in the shot list.** Set `image_source` to `meme` or `stock-image` with a `source_kind` of `google-image` or `youtube` per the alternate-mode schema below, and add a `punchline: true` marker in the chunk's notes so review can validate budget.

Example use: a short deadpan beat like *"Obviously."* or *"You know, casually."* lands at the exact moment a well-chosen reaction gif appears full-frame. Single-beat chunk, full substitution, back to anchor style on the next chunk.

#### Alternate Mode: Stock / Sourced Assets

This mode is supported but is not the default. It exists for sessions that explicitly need real footage — for example, showing real screenshots or real clips from the source session.

When running this mode:

##### Sourcing Order

When sourcing is needed, follow this order:

1. real assets from the source session
2. stock video
3. stock images
4. other videos from Google Video, YouTube, or broader web search
5. other images from Google Images or broader web search
6. reuse or combine duplicates
7. fall back to AI-illustrated scenes if nothing else fits

##### Fetch Pipeline

Asset fetching must be script-based and deterministic.

Required steps:

1. fetch asset
2. verify the fetched file type
3. if it is a video, create a preview thumbnail
4. if fetch fails, mark it clearly as failed
5. write the manifest entry
6. only use verified previews in the review board
7. replace failed assets, do not hide them

##### Fetch Rules

The fetch system should support:
- direct image URLs
- direct video URLs
- local files
- resolvable media pages when supported by scripts/APIs

It must reject:
- HTML pages saved as `.png` or `.jpg`
- fake media previews
- assets that cannot be shown visibly

##### Thumbnail Rules

If the asset is a video:
- keep the video file
- generate a thumbnail still
- store both
- the review board can use the thumbnail, but the renderer must use the real video

Expected naming:
- `asset-01.mp4`
- `asset-01-thumb.jpg`

##### Provenance Rules

Every non-local asset should record:
- original source URL
- source kind
- local saved path
- preview path if generated

If provenance is missing:
- the asset stage is incomplete

##### Alternate-Mode Manifest

When running this mode, add per-item entries with:
- `role`: `background`
- `source_kind`: one of `real`, `stock-video`, `stock-image`, `google-video`, `google-image`, `youtube`, `reuse`

Otherwise the manifest contract follows the same shape as the scene manifest.

## Part 2 — Preprocessor (reveal animation)

### Preprocessor Rules

#### Preprocessor Purpose

This file defines the scene preprocessor: the deterministic step between scene generation and video render.

The preprocessor takes one generated full-frame illustration and produces a numbered PNG sequence that reveals the illustration over time.

The preprocessor exists so the renderer never has to improvise reveal animation.

#### What The Preprocessor Is

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

#### Canonical Input

Inputs to the preprocessor:
- a generated scene PNG from `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/<chunk-id>.png`
- reveal parameters from the session config: `reveal_style`, `reveal_duration_seconds`, `scene_fps`
- the chunk id

#### Canonical Output

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

#### Supported Reveal Styles

##### `fade` (default, v1)
- frame N opacity = min(1, N / frameCount)
- underlying composition: fully opaque input image composited over a neutral background at a ramped alpha
- simplest and safest reveal; ships first

##### `paint`
- soft-edged progressive wipe from one side
- no visible edge artifacts
- direction is fixed per session (default: left to right); not per chunk

##### `edge-skeleton` (v2, stretch)
- detect edges on the input image (OpenCV or equivalent)
- reveal edges in stroke order over the first 60% of duration
- then reveal color fill under the edges over the remaining 40%
- intended to feel like hand-drawing, but optional

Unapproved reveal styles must not ship. Any new style requires a spec entry in this file before code references it.

#### Determinism Rule

Same (input image bytes, reveal_style, reveal_duration_seconds, scene_fps) must produce identical output frames every run.

The preprocessor must not:
- use random seeds
- depend on wall-clock time
- depend on hostname, user, or any environmental state

If you need any randomness (e.g. paint edge jitter), derive it from the input image hash.

#### Caching Rule

The preprocessor should not regenerate frames that are already valid.

- Compute `input_hash` from the input scene PNG bytes.
- If `frames.json` exists with matching `input_hash` and matching reveal params, skip regen.
- If any param differs, regenerate from scratch (delete the old folder first).
- A `--force` flag may skip the cache.

#### Remotion Rule

The renderer must play the frame sequence produced by the preprocessor.

The renderer must not:
- generate reveal animation inline
- apply additional fade/opacity/transition effects on top of the frame sequence
- change the reveal timing
- swap out any frame with an alternate image

If a different reveal is needed, update the session config and rerun the preprocessor. Do not solve it in the renderer.

#### Stale Output Rule

If the source scene image changes, the preprocessor must regenerate the frame folder.

Before regenerating:
- identify the old frame folder
- delete it or overwrite it completely
- do not leave a mixed folder with some old frames and some new frames

#### Validation Rules

A preprocessor run is invalid if:

- `frames.json` is missing
- the number of frame files does not match `frame_count` in `frames.json`
- the `input_hash` in `frames.json` does not match the current scene PNG
- the final frame does not equal the input scene PNG
- the reveal style is not in the allowed list
- the frame file names are not strictly sequential (`frame_0001.png` through `frame_NNNN.png`)

## Part 3 — Transitions

### Transition + camera rules

How to pick entrance transitions, reveal directions, pause values, and
per-beat camera moves per chunk. Evaluated top-down; first matching rule
wins.

#### Hard constraint: transition variety

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

#### Transition types

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

#### Entrance-picking rule (evaluated top-down)

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

#### Picking which chapters get chalkboard

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

#### Exit rule

- `image_source == "proof"` → **cut** out.
- Last chunk of whole video → **paint** out (closing flourish).
- Next chunk is proof → **cut** out.
- Next chunk is in a different scene (chapter boundary) → **paint** out.
- Else → **cut** out.

Exits are NEVER chalkboard — the eraser shape running in reverse reads
wrong. Use the same pre-gen frames as entrance (played reverse) for
paint-style exits.

#### Pause rule (between beats within a chunk)

| pause_after | Seconds |
|---|---|
| `none` | 0.0 |
| `short` (default) | 0.3 |
| `medium` | 0.5 |
| `long` | 0.8 |

Previously medium=0.8 and long=1.5 — both felt dead on 7-12s chunks.
These values keep the breath without stalling.

#### Camera rules (per-beat movements)

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

#### Reveal direction (chalkboard only)

Chalkboard runs on `random` — script picks one of 4 diagonals per seed.
No manual direction needed. For deterministic replay, pass `--seed`;
otherwise time-seeded variation per preprocess run.

Paint runs use `strategy` (not direction): `auto` or `center-out`. Do
not assign directional strategies.

#### Final pilot mix (validated)

Across 44 chunks:
- 28 cut (64%)
- 5 chalkboard (11%) — C1, C5, C18, C29, C38
- 4 paint-auto (9%) — C6, C8, C36, (one more if expanded)
- 7 paint-center-out (16%) — C11, C13, C20, C21, C26, C42, C44

This is the target distribution. If a new session ends up with 10+
chalkboards, rebalance before rendering.

#### When in doubt

Default to **paint-auto** + no per-beat camera. Only deviate when a
specific rule above triggers.
