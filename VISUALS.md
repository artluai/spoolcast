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

##### Style library (named styles with anchors and reference registries)

Styles are stored in a shared library at `spoolcast-content/styles/<name>/`. Each style owns a prompt, an anchor image, and a registry of neutral character/object references that are drawn in that style once and reused across sessions.

Directory layout:

    spoolcast-content/styles/<style-name>/
      style.json                          ← name, prompt, anchor metadata, reference map
      anchor.png                          ← master anchor image
      references/
        <name>.png                        ← neutral reference image (character or object)

`style.json` schema:

    {
      "name": "wojak-comic",
      "description": "<what this style is for>",
      "default_style_prompt": "<the prompt every generation in this style applies>",
      "anchor": {
        "image_path": "anchor.png",
        "image_url": "https://kie.ai/...",      ← kie result URL (ephemeral, ~24h)
        "url_fetched_at": "2026-04-21T..."
      } | null,
      "references": {
        "<name>": {
          "kind": "character" | "object",
          "description": "<plain-text description>",
          "image_path": "references/<name>.png",
          "image_url": "...",
          "url_fetched_at": "..."
        }
      }
    }

Sessions connect to a style via `session.json`'s `style` field:

    {
      "session_id": "my-session",
      "style": "wojak-comic",
      ...
    }

When `style` is set, the style's `default_style_prompt` and anchor URL are authoritative for this session — the legacy `style_reference` / `default_style_prompt` fields on `session.json` itself are ignored. Sessions without a `style` field fall back to the legacy behavior and continue to work unchanged.

###### How to register a style

First time creating a style:

1. `mkdir -p spoolcast-content/styles/<style-name>/references` — make the folder.
2. Create `style.json` with `name`, `description`, `default_style_prompt`, `"anchor": null`, `"references": {}`.
3. Generate the master anchor image:
   ```
   scripts/.venv/bin/python scripts/generate_reference.py \
       --style <style-name> --anchor --no-anchor-ref \
       --description "<what the anchor should contain — e.g. a representative character in the locked style>"
   ```
   - `--anchor` writes to `anchor.png` and updates `style.anchor` in `style.json`.
   - `--no-anchor-ref` tells the generator NOT to pass an existing anchor as `image_input` (there isn't one yet).

After this, `style.anchor` is populated with the kie URL + local path. Every subsequent generation in this style uses the anchor as its base `image_input` unless overridden by a chunk's references (see below).

###### How to register a character or object

Library-scoped (reusable across sessions — keep descriptions neutral, no scene-specific pose):

    scripts/.venv/bin/python scripts/generate_reference.py \
        --style <style-name> --name <name> --kind character|object \
        --description "<neutral description: who or what this is, no scene>"

The generator writes `references/<name>.png` and registers it in `style.json`.

Session-scoped (overrides library version for THIS session only — use when the character does one specific thing across most of the video):

    scripts/.venv/bin/python scripts/generate_reference.py \
        --session <session-id> --name <name> --kind character|object \
        --description "<session-specific: e.g. the builder, sitting at a desk>"

The generator writes to `sessions/<id>/source/generated-assets/references/<name>.png` and registers in `session.json`'s `characters` / `objects` map.

###### How scene generation uses references

Per-chunk, set a `references` array on the chunk pointing at registered names:

    { "id": "C4", "references": ["builder"], ... }

During `generate_scene.py`:

1. If the chunk has a `references` array with at least one entry: resolve each name through `style_library.resolve_reference` (session overrides take precedence over library entries), pick the **first** reference with a live kie URL, and that URL becomes the scene's single `image_input` value.
2. If the chunk has NO `references` (or the list is empty): **generate prompt-only — do NOT pass any `image_input`.** The style is locked through the `default_style_prompt` text, not through a reference image. The session's style anchor URL is NOT used as a fallback in this path.

**Why this split — "visual anchor when something specific recurs, text anchor otherwise."** Passing the style anchor as image_input on chunks that don't need character/object consistency causes visual bleed-through: artifacts like duplicated desks, wrong arm geometry, extra characters that shouldn't be in frame, and props pulled in from the anchor that don't belong in the abstract scene. Chunks that represent pages, diagrams, title cards, blank backgrounds, split panels, or any composition that doesn't recur — these should generate prompt-only and let the style words (not style image) drive consistency. Chunks with a character or recurring object need the identity-lock that only the image reference provides.

Concrete: if your shot-list has a text-page chunk, a rules.md page chunk, a title card, a diagram, a blank payoff page — none of those should list the style anchor as a reference. They should generate from the prompt alone. A character chunk (builder, chad) lists the character in `references` and gets the image anchor naturally.

**Only one `image_input` URL is passed per generation.** kie.ai's `image_input` field is technically an array, but passing multiple reference images confuses compositional tendencies — the model produces mushier results. When a scene needs two distinct characters in frame together, register a combined reference (character sheet showing both characters in the locked style) as its own entry and reference that one name.

**Legacy fallback (sessions without a `style` field).** The pre-library manifest-based style anchor still fires on chunks without `references`. This is the old behavior — kept for pre-style-library sessions only. New sessions using the style library follow the prompt-only rule above.

###### Validator enforcement

`scripts/validate_shot_list.py` reads the session's `characters`, `objects`, and (if `style` is set) the style's `references` registry. For every chunk with a `references` field, each name must resolve to a registered entry in one of those maps. Missing names fail validation loudly rather than silently generating with a wrong anchor.

###### Legacy behavior (sessions without a `style` field)

If `session.json` has `style_reference` set to an image URL or local path:
- use it directly as the anchor for the first generation.

If `style_reference` is a descriptive prompt:
- the first generated scene becomes the anchor image from that point on.

If neither `style_reference` nor `default_style_prompt` is set:
- scene generation must fail loudly instead of silently picking a style.

This pre-library behavior is preserved so existing sessions continue to render unchanged.

##### Prompt Assembly Rule

Per-chunk prompts are composed from **three structured slots** on the chunk (see PIPELINE.md § `visual_direction` / `on_screen_text` / `motion_notes`), not from one free-form blob. Structured assembly is what keeps stage direction, literal text, and motion from bleeding into each other during generation.

The generator sends:
- the session style anchor (prompt or reference image)
- the chunk's `visual_direction` — how the image should look/feel
- an explicit "render these exact words on the frame" instruction composed from the chunk's `on_screen_text` array, when non-empty
- aspect ratio and resolution from session config

The generator **does not send**:
- the chunk's `motion_notes` — still-image models can't render motion; describing motion produces overlapping simultaneous elements (phantom limbs, duplicate objects). Motion belongs to the reveal/animation layer and is consumed there.
- references to second visual layers
- instructions to produce transparent or cutout output

Backward compatibility: if a chunk has no structured slots, the legacy `beat_description` blob is used verbatim as a fallback. New sessions should populate the structured slots explicitly.

##### Prompt Hygiene Rules

Generated scenes fail most often on three failure classes, all preventable at prompt-authoring time:

1. **One focal subject per frame.** Default to a single character / object / composition element as the eye's target. A multi-panel layout (comic strip, before/after split) is acceptable when the panel structure is explicit in `visual_direction` — but free-floating competing subjects without structural partition cause composition overload. If a chunk needs two characters interacting, that's one scene (the interaction); two characters doing unrelated things is two chunks.
2. **Describe end states, not processes.** A still image cannot render a symbol mid-transformation, a character mid-motion, or a scene in the act of changing — the model draws every frame of that motion at once, producing duplicated elements and phantom body parts. Describe either the before state or the after state, and split into two chunks if both matter. Ink strokes mid-motion, hands holding multiple props, "the character turns and says" — all variants of the same bug.
3. **Prefer simple poses over clever ones.** Current image models reliably break on poses where the character's anatomy is partially occluded, contorted, or holding multiple things — heads under hoods, hands gripping multiple props, characters mid-motion, face obscured by objects. The first move is to simplify the pose in `visual_direction` rather than fight the model. If a specific pose is editorially required and keeps breaking, use a reference image for the character (declared in the chunk's `references`) — but that's the escape hatch, not the default.
4. **Empty text slots get invented.** If the visual mentions anything that holds words (card, page, sign, screen, label, document, book, banner, poster, ledger), either write the exact words into `on_screen_text` OR say it's `blank` / `wordless` / `no text` / `out of focus` / `illegible` inside `visual_direction`. Never leave it ambiguous — the generator will fill the empty slot with invented text, and the invention is almost never what you wanted.

Post-generation check: `audit_scenes.py` runs a vision pass (Qwen-VL) on every generated scene and flags extra limbs, malformed faces/hands, duplicate characters, missing declared on-screen text, hallucinated text, composition overload, and **structural mobile-safety** (split-panels, focal in a side-third). A non-empty audit blocks render the same way `audit_narration.py` does — except the mobile flags, which do not block the widescreen render but populate `mobile_unsafe: true` and a suggested `mobile_focal` on the shot-list chunk.

The widescreen-based mobile-safety check is a coarse first pass. It does NOT reliably catch text-clipping on text-heavy scenes — the model has a strong "centered = safe" bias and will not imagine the crop to inspect what lives in the side thirds. For the authoritative legibility check, run `audit_mobile_crops.py` on the already-cropped mobile PNGs (see `scripts/audit_mobile_crops.py`). That audit looks at what the mobile viewer actually sees and flags chunks where essential content was clipped at the frame edge. Writes `working/mobile-crop-audit.json`.

**A.1 audit flow in full:** (1) `audit_scenes.py` widescreen pass — catches structural + flags coarse mobile-safety, (2) crop all widescreen scenes to `scenes/mobile/` per the A.1 fill-order rule, (3) `audit_mobile_crops.py` on the cropped outputs — this is the authoritative legibility check. The widescreen pass alone is not sufficient for mobile shipping; always run the post-crop audit before mobile export.

##### Mobile-variant scene generation (A.1)

When a chunk is flagged `mobile_unsafe: true` and the user runs the optional mobile-export chain (SHIPPING.md § Part 4), `generate_scene.py --mobile-variant` produces a portrait-native scene for that chunk. The generator passes the target mobile aspect ratio (9:16 or 1:1) to the provider so the model composes the scene *for* the mobile canvas — it does not crop a 16:9 render. Existing prompt-hygiene rules apply unchanged; there is no special hygiene rule for mobile regens because the generator is already composing at the mobile aspect, so crop-margin concerns don't apply.

A mobile-first authoring path (ROADMAP.md Process B — sessions composed natively at 9:16 from chunk 1) skips this flag entirely: every scene in a Process B session is generated at the mobile aspect from the start, and `mobile_unsafe` / `mobile_focal` are meaningless there because no cropping ever happens.

##### Aspect ratio is a compositional input

The same prompt at different aspect ratios produces different compositions. The model adapts to fill the canvas — taller canvases tend to get additional invented elements (extra panels, extra characters, extra dialogue) that weren't in the prompt. Byte-identical prompts at 16:9 vs 1:1 vs 4:5 are NOT interchangeable: replaying a widescreen prompt at a mobile aspect does not produce "the widescreen image cropped" — it produces a new composition.

Two non-interchangeable paths when mobile output is needed:

- **Identical content at a new aspect** → crop the existing widescreen asset (lossy, may lose edge content).
- **New composition optimized for the aspect** → regenerate with the new aspect (may diverge from the widescreen narrative).

A feature or script that involves aspect change must document which path it uses. Never conflate.

Concrete example from this session: C25 had a prompt describing 3 side-by-side option cards. At 16:9 the model drew exactly that. At 1:1, with the same prompt, the model added 2 bottom sub-panels with invented character dialogue to fill the taller canvas.

##### Previous-video broll framing

When a chunk plays a clip that originated in a prior video (either a separately-shipped video in the same project, or an earlier iteration of the current video), the broll must be composited inside a TV or monitor graphic rather than filling the frame edge-to-edge.

The framing:
- the broll plays inside a bezel-styled TV/monitor positioned roughly centered in the canvas (~80% width, 16:9 aspect) — thick grey bezel, subtle drop shadow, rounded corners
- the surrounding canvas is dimmed to a neutral dark grey so the TV is the focal point
- for **video broll** (moving clip), a small REC indicator (red rewind-style triangles + "REC" label) sits in the bottom-right corner of the screen — signals "playback of a recording"
- for **still broll** (a single frame from a prior video, `image_source: broll_image`), no REC indicator — a still can't be "playing", and a play-marker on a static frame reads wrong. The TV frame itself carries the "this is from another video" signal.

Why this framing is load-bearing: full-frame broll from a prior video forces the viewer to interpret two overlapping signals ("what am I looking at?" + "is this the same video?"). The TV-inside-a-scene framing resolves both signals in half a second — the viewer reads "recording playing on a screen" and the cognitive load drops to zero. Without the frame, previous-video broll reads as either a style-break error or a scene that's failing to land.

Implementation: the TV-frame + REC indicator are applied **at render time by the Remotion `TVFrameWrapper` component** (see `src/Composition.tsx`), not by AI generation. The broll asset itself (video file or still image) plays as-is; the renderer wraps it. This means there is no separate AI-gen composite scene for TV-framed broll chunks — the `image_source` stays as `broll` / `broll_image` and no kie.ai call is made for the frame.

Declaration: set `broll_source_kind` to `sibling-video` (shipped previous video in the same project) or `self-reject` (earlier iteration of the current video). Set `broll_framing` to `tv-screen`. `visual_direction` / `on_screen_text` / `motion_notes` are not used on these chunks (the visual is the TV-wrapped broll asset; no AI scene to direct).

Enforcement: `validate_shot_list.py` blocks render on any broll chunk whose `broll_source_kind` is `sibling-video` or `self-reject` and whose `broll_framing` is not `tv-screen`. External-capture and meme broll can still be full-frame; the rule is specifically about footage the viewer might otherwise mistake for "the current video glitching."

Schema aliases: the canonical `broll_framing` value is `"tv-screen"`. The legacy value `"tv"` is accepted by the renderer for backward compatibility with pre-schema-formalization sessions but should be migrated to `"tv-screen"` on any touched chunk.

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
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/` — widescreen masters (`<chunk>.png`)
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/mobile/` — mobile-variant PNGs (`<chunk>-mobile.png`) when Process A.1 regeneration has run

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
- `id` — scene id; equals `chunk_id` for widescreen items, `<chunk_id>-mobile` for mobile variants
- `chunk_id`
- `role` — allowed values: `scene` (widescreen A master), `scene-mobile` (A.1 mobile variant)
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
- `post_processing` — object recording any transform applied to the kie.ai delivery (crop, scale, letterbox, color-correct). Shape: `{"step": "<short-name>", "<param>": "<value>"}`. Example: `{"step": "center-crop-1x1-to-4x5", "crop": "820:1024:102:0"}`. Makes the asset's full transformation history reproducible without re-deriving from code.
- `replay_source_task_id` — for items produced by `replay_mobile.py`, the `task_id` of the widescreen manifest entry whose prompt + image_input were replayed.

##### Manifest race condition (known failure mode)

`generate_scene.py`'s manifest write is a read-modify-save sequence, not an atomic transaction. When two processes run `generate_scene.py` (or `batch_scenes.py`) concurrently against the same session, both load the same manifest snapshot, each appends its item to its own in-memory copy, and each saves — the second writer's save silently drops the first writer's item. The orphaned chunk keeps its PNG on disk but loses its manifest entry.

Consequence: orphaned chunks cannot be byte-faithfully replayed at a new aspect (`replay_mobile.py` requires a manifest entry with the original prompt + image_input). They fall back to re-derivation via `batch_scenes.py`, which carries drift risk since the shot-list can have mutated since the original run.

Mitigation currently in `generate_scene.py`: the manifest read + mutate + write is wrapped in an exclusive `fcntl.flock` on the manifest file (`_locked_manifest_rw`). Serializes concurrent writers — one waits while the other finishes the full cycle. POSIX-only; on non-POSIX hosts the race returns. Not a concern on macOS/Linux.

Known incident: `spoolcast-dev-log` found with 4 chunks (C6, C28, C39, C41) orphaned. Root cause was two parallel `batch_scenes.py` runs writing to the manifest concurrently. The lock fix above landed after this incident.

##### Manifest is ground truth for historical generations

The shot-list is mutable — fields drift via backfill, normalization, audit write-backs. The manifest is append-only per generation and records the exact `prompt` + `image_input` sent to kie.ai.

- Reproducing or replaying a past call → read manifest.
- Current authoring intent → read shot-list.
- Byte-faithful replay requires the manifest; `compose_prompt` re-derives from the current shot-list and can diverge silently when shot-list fields have been edited since the original generation.

See `scripts/replay_mobile.py` — submits the manifest's widescreen prompt + image_input verbatim to kie.ai with only `aspect_ratio` overridden, bypassing `compose_prompt` entirely.

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

#### Asset Verification Principles

Apply to any asset before it ships to the shot-list — illustrations, broll, memes, proofs, overlays.

1. **Verify before ship.** Confirm every asset's content matches what the plan says it should show. Method varies with asset type and available tools — frame inspection, hashing, metadata checks, text audit, pixel comparison. The principle is unchanged across methods.
2. **Labels are hypotheses, content is evidence.** Filenames, manifest entries, prose descriptions, commit messages, transcript captions describe intent at write-time. They drift from actual content. Only the asset itself is authoritative.
3. **Suspicious signals block delivery.** Duplicate extracts, byte-identical outputs across differently-labeled sources, matched-timestamp frames that look identical across clips supposed to differ, missing described elements, durations that don't fit the described content — any one of these stops delivery. Not a caveat, not a handoff footnote.
4. **Verification is the agent's job — never delegated.** The agent runs verification autonomously. Delegating verification to the user is banned, including as a last resort. If the user is in autopilot, delegation would break the contract. If the user is not in autopilot, delegation wastes their time on work the agent can do.
5. **Autonomous corrective action before escalation.** When verification fails, the agent tries reasonable autonomous fixes — different source, different extraction range, different asset, reduce scope, restructure the section. Escalate to the user only for substantive editorial judgment calls or the defined autopilot escape hatches (rule conflict, budget, missing hard dependency, ethical/factual concern).
6. **Privileged tool access is a bonus, not a fallback.** Rules must hold without repo/script/API access. If a verification approach only works because the agent happens to have regeneration tooling, the rule is capability-specific and won't transfer. Privilege is for doing better, not for patching around skipped checks.

Failure mode these prevent: agent trusts source-material prose, extracts assets based on label match, ships without content verification, mislabeled assets reach the shot-list, rework required at review or later. Verification is always cheaper than late rework.

#### Asset Verification Enforcement

Rules above describe behavior. The enforcement mechanism — what prevents pattern-matching from silently skipping the rules — is procedural and asset-type-specific.

**Video / audio assets — require a sidecar file on disk.**

Any non-illustration video or audio asset referenced in the shot-list must have a sidecar JSON next to it at `<asset>.verified.json` with these required fields:

- `verified_at` — ISO 8601 timestamp
- `verified_content` — one-line description of what the agent confirmed the asset shows (must match what the shot-list's `beat_description` will say)
- `verification_method` — e.g., `"dense-frame inspection at t=0.3,0.6,0.9,1.2,1.5,1.8,2.1,2.4"`, `"ffmpeg ssim comparison against saga-reject-01.mp4"`, `"user-confirmed playback"`
- `verified_by` — `agent` | `user`

If the sidecar is missing or any required field is empty, the asset is treated as **unverified**. The agent is blocked from claiming in chat, in the shot-list `image_path`, or in any plan proposal that the asset contains any specific content. The block is strict — no claim-plus-caveat, no "flagged for review." Unverified assets cannot be referenced as if verified.

The shot-list validator checks for sidecars on every `broll` / `broll_image` / `external_*` / `meme` chunk that points to a video or audio file. Missing sidecar = validation failure = cannot proceed to render.

**Image assets — require in-session Read.**

Any non-generated image asset (meme stills, proof screenshots, overlays, external_screenshot) referenced in the shot-list must have been viewed by the agent via the Read tool in the current session before the agent makes any content claim about it. Image verification does not require a sidecar because the Read inspection IS the verification. Session-bounded — verification from a prior session does not carry over; the agent must re-Read.

Generated illustrations (`image_source: "generated"`) follow their own narration-text audit rule above and do not require either mechanism; the kie.ai contract + the text audit is the verification path for those.

**Why asset-type-specific enforcement.**

Sidecars exist because the agent cannot directly play video or audio — inspection requires extracting frames or probing metadata, and pattern-matching can easily skip that work. The sidecar makes the verification state visible on disk so the validator can block on it. Images the agent CAN inspect directly, so the cheapest-enforceable check is "must have called Read" — the file open is the verification. For illustrations, the generation pipeline already has text-content checks; adding a sidecar would be redundant ceremony.

The rule this is the mechanical enforcement for: *"Verification is the agent's job — never delegated"* + *"Labels are hypotheses, content is evidence."* Without the sidecar or the Read, these rules depend on the agent remembering to verify. With them, the verification state is either on disk (video/audio) or in the current session (image), and the agent physically cannot claim an unverified asset without creating the verification evidence first.

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

Exception: single-beat chunks marked as **deadpan punchlines** (see STORY.md § Deadpan punchlines) may use a real meme image, reaction gif, screenshot, or external cultural-reference visual — deliberately breaking the anchor style for comedic punctuation.

**Two forms are allowed — pick the one that lands the beat:**

| form | when to use | shape |
|---|---|---|
| **full-frame substitution** | the punchline erases the prior scene (reset, hard shift) | the meme/reaction IS the chunk's image, `image_source: meme`, full canvas. |
| **overlay on reused scene** | the punchline stamps on top of the prior scene (reaction to it, not replacement) | `image_source: reuse` pointing back at the prior chunk, plus an `overlays` entry placing the stamp/reaction artifact at a zone with appear/disappear timing. |

Pick based on intent. A REJECTED stamp slamming down on a builder-at-desk scene reads as a reaction TO the scene — use overlay. A SpongeBob time-card covering the screen reads as "time passes, reset" — use full-frame.

Constraints that apply to both forms:
- **Single-beat chunks only.** Multi-beat chunks stay in anchor style. Reserved for the specific moment the punchline lands.
- **Budget: ~1-2 per video, editorial.** Past that, the device stops being a spike and becomes a running visual — rarity is what makes it work.
- **Flag in the shot list.** Set `punchline: true` on the chunk so validation can see the intent. For full-frame: `image_source: meme`. For overlay: `image_source: reuse`, `continuity: callback-to-<prev>`, plus an `overlays` entry with the artifact's position/size/timing.

Preferences for the overlay form (not requirements):
- **Transparent background on the overlay asset.** A stamp / icon / sign with alpha channel sits cleanly on top of the reused scene. A full photo with its own background (e.g. a landscape wood-log photo) covers most of the underlay and reads as full-frame substitution instead of an overlay — use full-frame in that case. When in doubt, check: can the viewer still see the scene beneath the overlay artifact?
- **Medium-contrast between overlay and underlay.** If the underlay is an illustrated / drawn scene (anchor style), a real-world photo as the overlay lands harder than another drawing — the medium shift IS the spike. Drawing-on-drawing can work but it's softer; the viewer may read it as one continuous illustration rather than a reaction punctuating the scene. Pick the medium contrast deliberately, not by default.

The one-visual-layer rule (`rules.md`, PIPELINE.md) still applies: in both forms, the viewer sees exactly one primary illustration. Overlay form doesn't violate that — the reused prior scene IS the primary layer, the stamp is a small overlay the same way a logo or label is allowed.

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

##### Inter-chunk transition vocabulary

Two named transitions cover every boundary. No other modes are allowed. Fade-to-white as a standalone exit is banned — it leaves the viewer looking at a blank canvas with nothing to parse.

| name | when to use | behavior | default duration |
|---|---|---|---|
| `cut` | meme / broll / broll_image / reuse / proof chunks; punchlines; reveal-group internals; first chunk of the video; **any chunk whose previous chunk is a meme / broll / reuse / proof** (see post-insert cut rule below); any chunk where the previous chunk has no valid still-image underlay (broll video, bumper) | instant, no animation | 0 frames |
| `crossfade` | **default** between any two illustrated chunks where the previous chunk has a renderable still-image underlay | prior chunk's last frame renders as an underlay while the incoming chunk fades in 0 → 1 opacity | 0.35s (≈10 frames at 30fps) |

**Post-insert cut rule.** A meme / broll / reuse / proof insert takes no transition on EITHER side. The cut-IN rule is obvious (insert lands hard for punch). The cut-OUT rule is less obvious but just as load-bearing: if the next illustrated chunk crossfades out of a transparent-bg PNG (e.g. the stamp meme), the viewer sees the insert's background color shift mid-fade as the next chunk's bg bleeds through. Reads as a weird color-shift transition. Hard cut both sides keeps the insert surgical.

Crossfade is **entrance-side only**: the incoming chunk does the fade-in; the previous chunk simply holds its final frame as the underlay. There is no "exit crossfade" — every chunk's exit is a cut (hold last frame, let the next chunk take over).

**Underlay must match the prior chunk's visible end state.** If the prior chunk had a camera effect running (push-in, pan, zoom), the underlay during crossfade renders the prior image at the prior chunk's FINAL camera transform — not at the image's natural 1.0-zoom origin. Without this, the viewer sees: zoomed-in prior chunk → snap back to 1.0-zoom underlay → crossfade to new chunk. The snap-back is jarring and reads as a glitch. Implementation: `Composition.tsx` computes `computeCamera(priorChunk, priorChunk.durationFrames - 1, fps)` and applies that transform to the underlay div.

Underlay-validity rule: crossfade needs something to fade FROM. When the previous chunk is a broll video (no decodable still), a bumper (title card rendered from text, no image file), or missing an image path, the crossfade degrades automatically to `cut`. No fade-in-from-white allowed.

Read-time downstream: crossfade entrances count fully toward the readable window (the text is visible from frame one, just at reduced opacity for ~0.35s, which is still legible for held-text). `cut` entrances trivially count the full chunk duration.

##### Bumper render rule

Bumpers are chapter title cards. They render at **opacity 1 from frame 0** — no fade-in. A fade-from-0 against a white background produces a pure-white first frame that reads as a flash; the audit catches it. A hard cut into the bumper IS the act-boundary signal and doesn't need softening. Bumper exit is also a cut (the bumper holds until the next chunk takes over).

##### Paint-on (deferred)

Paint-on stroke reveals were the original spoolcast transition aesthetic. They are currently deferred because the existing `stroke_reveal.py` preprocessor outputs RGB PNGs with a white background (no alpha), which means any paint-on animation starts from a white canvas — producing visible white flashes at the start of every paint-on chunk. Using paint-on at scene boundaries stacked the problem: flash-at-end + flash-at-start = multi-second animated white.

Before paint-on can return to the vocabulary, the preprocessor must be updated to emit RGBA PNG frames where pixels that haven't been painted yet are transparent (not white). Then the renderer can composite paint-on frames over the prior chunk's final frame as an underlay — no white ever visible.

Until that preprocessor update ships, paint-on is not a valid `entrance` value. `build_preview_data.py` does not emit it; all scene-opener moments use `cut` or `crossfade` depending on underlay validity.

These are defaults for all sessions. The two named transitions (`cut`, `crossfade`) are the only allowed values — no new named transitions without a spec entry here first.

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
