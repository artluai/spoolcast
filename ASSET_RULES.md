# Asset Rules

## Purpose

This file defines how agents and apps should source, validate, reuse, fetch, manifest, and budget assets.

## Global Asset Rule

The current system uses one visual asset per beat: the background.

That means:
- source and validate background assets first
- do not build a workflow that depends on a second visual layer
- create contrast by changing the background between beats instead

## Asset Sourcing Order

Always source visuals in this exact order:

1. real assets
2. stock video
3. stock images
4. other videos from Google Video, YouTube, or broader web search
5. other images from Google Images or broader web search
6. reuse or combine duplicates
7. AI only if nothing else works

If many assets remain unresolved after step 6:
- repeat steps 4 to 6
- only then use AI

## Reuse Rules

Reuse is preferred when:
- two beats need the same visual world
- a later beat can intentionally return to an earlier background
- a visual can be repeated to create contrast around a middle background change

Reuse should be explicit.

Do not silently duplicate work.

## Asset Validity Rule

An asset is valid only if it can be visibly reviewed.

An asset is not valid if it is:
- only a page link
- an unresolved web page
- a broken preview
- a fetch that returned HTML instead of media
- a stale asset no longer referenced by the shot list

## Canonical Asset Output Locations

Fetched external assets:
- `../spoolcast-content/sessions/<session-id>/source/fetched-assets/`

AI-generated assets:
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/`

Asset manifests:
- `../spoolcast-content/sessions/<session-id>/manifests/`

Review thumbnails:
- `../spoolcast-content/sessions/<session-id>/review/`

## Asset Manifest Contract

Every sourcing run should write one manifest.

Allowed manifest format:
- JSON

Expected manifest filename:
- `<run-name>.manifest.json`
- or `manifest.json` inside a run folder

Required top-level fields:
- `run_name`
- `session_id`
- `created_at`
- `source_type`
- `items`

Required per-item fields:
- `id`
- `shot`
- `role`
- `source_kind`
- `source_url`
- `local_path`
- `preview_path`
- `mime_type`
- `status`

Optional per-item fields:
- `model`
- `task_id`
- `result_url`
- `prompt`
- `notes`

Allowed `role` values:
- `background`

Allowed `source_kind` values:
- `real`
- `stock-video`
- `stock-image`
- `google-video`
- `google-image`
- `youtube`
- `reuse`
- `ai`

Allowed `status` values:
- `success`
- `failed`
- `stale`

## Asset Fetch Pipeline

Asset fetching must be script-based and deterministic.

Required steps:

1. fetch asset
2. verify the fetched file type
3. if it is a video, create a preview thumbnail
4. if fetch fails, mark it clearly as failed
5. write the manifest entry
6. only use verified previews in the review board
7. replace failed assets, do not hide them

## Fetch Rules

The fetch system should support:
- direct image URLs
- direct video URLs
- local files
- resolvable media pages when supported by scripts/APIs

It must reject:
- HTML pages saved as `.png` or `.jpg`
- fake media previews
- assets that cannot be shown visibly

## Thumbnail Rules

If the asset is a video:
- keep the video file
- generate a thumbnail still
- store both
- the review board can use the thumbnail, but the renderer must use the real video

Expected naming:
- `asset-01.mp4`
- `asset-01-thumb.jpg`

## Search Rules

When sourcing from Google or broader web search:
- search by the visual needed
- prefer assets that match the current beat’s tone and shot purpose
- prefer assets that are easy to preview and reuse

Do not search for overly similar replacements if the goal is contrast between beats.

## Provenance Rules

Every non-local asset should record:
- original source URL
- source kind
- local saved path
- preview path if generated

If provenance is missing:
- the asset stage is incomplete

## AI Rules

AI is last resort only.

Use AI only when:
- nothing acceptable can be sourced
- reuse is not enough
- the asset is inherently custom

Do not use AI just because it is easy.

## AI Budget Rule

Every video must have an explicit AI budget.

At minimum:
- define a total AI budget before generating assets
- track which beats are consuming it

Do not exceed the budget casually.

## Kie Provider Spec

Current image-generation provider:
- Kie

Current env var:
- `KIE_API_KEY`

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
- write a manifest entry containing `task_id`, `result_url`, and `local_path`

## Asset Failure Rules

If a source fails repeatedly:
- replace it entirely

Do not keep trying to force the same broken source.

If an asset type repeatedly causes fragile downstream behavior:
- simplify the workflow
- do not keep preserving a broken pattern

## Transparency Rule

Transparency-heavy workflows are not the default.

Current default:
- do not rely on transparent cutout assets
- do not assume AI-generated transparency is reliable
- prefer full-frame or full-height backgrounds instead

## Validation Checklist

Before considering the asset stage complete:

1. every required beat has a visible background asset
2. every asset can be previewed
3. every non-local asset has provenance
4. every asset run wrote a manifest
5. failed fetches are clearly marked
6. duplicates have been intentionally reused where appropriate
7. AI has only been used where justified
