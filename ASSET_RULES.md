# Asset Rules

## Purpose

This file defines how agents and apps should generate, source, validate, reuse, fetch, manifest, and budget visual assets.

## Global Asset Rule

The primary visual system uses one AI-generated illustration per narration chunk.

That means:
- generate illustrations per chunk, not per beat
- do not build a workflow that depends on a second visual layer
- create contrast by moving to the next illustration on the next chunk
- reuse a prior chunk's illustration explicitly when narrative calls for it

A second mode — stock and sourced assets — is supported but is not the default. See "Alternate Mode: Stock / Sourced Assets" below.

## Primary Visual Pipeline: AI-Illustrated Scenes

### Model

The primary provider is kie.ai. See the Kie Provider Spec section below.

### Per-Chunk Generation Rule

For each unique `Chunk` value in the shot list:
- compose a prompt from the chunk's narration and beat descriptions
- merge the session's style anchor (prompt or reference image)
- submit a scene generation job
- on success, download the result into `source/generated-assets/scenes/<chunk-id>.png`
- write or update the scene manifest

Do not generate more than one illustration per chunk unless the prior generation is being replaced.

### Style Anchor Rule

Every session has one locked visual style.

- The style anchor is established on the first successful scene generation.
- The anchor is recorded in the scene manifest (anchor type, source, task id if applicable).
- Every subsequent scene generation in the session must pass the anchor reference back in through `input.image_input` so character and style stay consistent across chunks.

If `session.json` has `style_reference` set to an image URL or local path:
- use it directly as the anchor for the first generation.

If `style_reference` is a descriptive prompt:
- the first generated scene becomes the anchor image from that point on.

If neither `style_reference` nor `default_style_prompt` is set:
- scene generation must fail loudly instead of silently picking a style.

### Prompt Assembly Rule

Per-chunk prompts should combine:
- the session style anchor (prompt or a reference to the anchor image)
- the narration text across all beats in the chunk
- the beat descriptions across all beats in the chunk
- aspect ratio and resolution from session config

The prompt must not include:
- references to second visual layers
- instructions to produce transparent or cutout output
- requests for readable text in the image

### Scene Output Contract

Per-chunk outputs:
- `source/generated-assets/scenes/<chunk-id>.png` — the final downloaded scene image
- one entry per chunk in `manifests/scenes.manifest.json`

## Asset Validity Rule

An asset is valid only if it can be visibly reviewed.

An asset is not valid if it is:
- only a task ID
- an unresolved URL
- a broken preview
- a fetch that returned HTML instead of media
- stale compared with the current shot list

## Canonical Asset Output Locations

Generated scenes:
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/`

Fetched external assets (alternate mode only):
- `../spoolcast-content/sessions/<session-id>/source/fetched-assets/`

Scene manifests:
- `../spoolcast-content/sessions/<session-id>/manifests/scenes.manifest.json`

Review thumbnails:
- `../spoolcast-content/sessions/<session-id>/review/`

## Scene Manifest Contract

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

## Kie Provider Spec

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

### Gotchas (learned the hard way — don't relearn these)

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

### Recovery procedure (when generation completes on kie.ai but local
script was killed before downloading)

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

## Reuse Rules

Reuse is preferred when:
- a later chunk intentionally returns to an earlier illustration
- a chunk is aesthetically identical to an adjacent chunk and the narration does not demand change

Reuse should be explicit in the shot list (same `Chunk` value across rows, or an explicit reuse note).

Do not silently duplicate work.

## AI Budget Rule

`ai_budget` in `session.json` is a hard ceiling on successful scene generations for the session.

- count successful generations against the budget
- do not count cache hits or failures
- when the budget is exhausted, stop the pipeline and require an explicit config change before continuing

## Transparency Rule

Transparency-heavy workflows are not the default.

Current default:
- do not rely on transparent cutout assets
- do not assume AI-generated transparency is reliable
- prefer full-frame backgrounds instead
- do not request transparent output from the model

## Asset Failure Rules

If a source fails repeatedly:
- replace it entirely

Do not keep trying to force the same broken source.

If an asset type repeatedly causes fragile downstream behavior:
- simplify the workflow
- do not keep preserving a broken pattern

## Validation Checklist

Before considering the asset stage complete:

1. every chunk in the shot list has a generated scene illustration
2. every illustration is locally visible and valid
3. every scene manifest entry includes provenance (task_id, result_url, local_path)
4. the style anchor is recorded
5. failed generations are clearly marked
6. reuse is explicit in the shot list
7. AI budget is not exceeded

---

## Alternate Mode: Stock / Sourced Assets

This mode is supported but is not the default. It exists for sessions that explicitly need real footage — for example, showing real screenshots or real clips from the source session.

When running this mode:

### Sourcing Order

When sourcing is needed, follow this order:

1. real assets from the source session
2. stock video
3. stock images
4. other videos from Google Video, YouTube, or broader web search
5. other images from Google Images or broader web search
6. reuse or combine duplicates
7. fall back to AI-illustrated scenes if nothing else fits

### Fetch Pipeline

Asset fetching must be script-based and deterministic.

Required steps:

1. fetch asset
2. verify the fetched file type
3. if it is a video, create a preview thumbnail
4. if fetch fails, mark it clearly as failed
5. write the manifest entry
6. only use verified previews in the review board
7. replace failed assets, do not hide them

### Fetch Rules

The fetch system should support:
- direct image URLs
- direct video URLs
- local files
- resolvable media pages when supported by scripts/APIs

It must reject:
- HTML pages saved as `.png` or `.jpg`
- fake media previews
- assets that cannot be shown visibly

### Thumbnail Rules

If the asset is a video:
- keep the video file
- generate a thumbnail still
- store both
- the review board can use the thumbnail, but the renderer must use the real video

Expected naming:
- `asset-01.mp4`
- `asset-01-thumb.jpg`

### Provenance Rules

Every non-local asset should record:
- original source URL
- source kind
- local saved path
- preview path if generated

If provenance is missing:
- the asset stage is incomplete

### Alternate-Mode Manifest

When running this mode, add per-item entries with:
- `role`: `background`
- `source_kind`: one of `real`, `stock-video`, `stock-image`, `google-video`, `google-image`, `youtube`, `reuse`

Otherwise the manifest contract follows the same shape as the scene manifest.
