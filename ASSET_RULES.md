# Asset Rules

## Purpose

This file defines how agents and apps should source, validate, reuse, fetch, and budget assets.

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

## Asset Fetch Pipeline

Asset fetching must be script-based and deterministic.

Required steps:

1. fetch asset
2. verify the fetched file type
3. if it is a video, create a preview thumbnail
4. if fetch fails, mark it clearly as failed
5. only use verified previews in the review board
6. replace failed assets, do not hide them

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

## Search Rules

When sourcing from Google or broader web search:
- search by the visual needed
- prefer assets that match the current beat’s tone and shot purpose
- prefer assets that are easy to preview and reuse

Do not search for overly similar replacements if the goal is contrast between beats.

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
3. failed fetches are clearly marked
4. duplicates have been intentionally reused where appropriate
5. AI has only been used where justified
