# Spoolcast Rules Index

Start here.

Spoolcast turns chat, content, and ideas into illustrated videos. Each narration chunk becomes one AI-generated scene in a per-session locked style; a deterministic preprocessor reveals it over time; Remotion plays the resulting PNG sequences against audio.

This file tells any new agent or app:
- which rules files exist
- what each file is for
- what order to read them in

Read repo-local rules before making suggestions, writing workflow docs, or changing implementation details.

## Read Order

Read these files in this exact order:

1. [WORKFLOW_RULES.md](./WORKFLOW_RULES.md)
2. [SESSION_CONFIG_SPEC.md](./SESSION_CONFIG_SPEC.md)
3. [SHOT_LIST_SPEC.md](./SHOT_LIST_SPEC.md)
4. [ASSET_RULES.md](./ASSET_RULES.md)
5. [PREPROCESSOR_RULES.md](./PREPROCESSOR_RULES.md)
6. [REVIEW_BOARD_RULES.md](./REVIEW_BOARD_RULES.md)
7. [RENDER_RULES.md](./RENDER_RULES.md)

## What Each File Does

### WORKFLOW_RULES.md
Use this first.

It defines:
- the global system model
- source-of-truth rules
- the directory contract
- pipeline stages
- regeneration rules
- failure conditions
- validation rules

### SESSION_CONFIG_SPEC.md
Use this when reading, creating, or validating a per-session config file.

It defines:
- the canonical `session.json` location
- required and optional fields
- style anchor rules
- model selection
- budget rules

### SHOT_LIST_SPEC.md
Use this when reading, creating, validating, or editing the shot list.

It defines:
- what the shot list is
- required headers (including `Chunk`)
- field meanings
- required vs optional fields
- allowed values and formatting expectations
- how shot-list fields map to downstream outputs

### ASSET_RULES.md
Use this when generating, sourcing, validating, reusing, fetching, or budgeting visual assets.

It defines:
- the primary AI-illustrated scene pipeline
- the style anchor rule
- the scene manifest contract
- the Kie provider spec
- the alternate mode for stock / sourced assets
- AI budget rules

### PREPROCESSOR_RULES.md
Use this when building or modifying the scene preprocessor.

It defines:
- the input/output contract for reveal frame sequences
- supported reveal styles
- determinism and caching rules
- the renderer's restrictions on reveal behavior

### REVIEW_BOARD_RULES.md
Use this when building or validating the HTML review board.

It defines:
- what the review board must show per chunk
- layout expectations
- what counts as failure
- review-board validation rules

### RENDER_RULES.md
Use this when generating preview data, building Remotion behavior, or rendering video.

It defines:
- the preview-data schema (chunk-driven)
- motion mapping
- what must never be improvised
- the rule that the renderer plays preprocessor PNG sequences as-is
- regeneration requirements for video outputs

## Non-Negotiable System Defaults

These apply everywhere unless explicitly replaced by a future system rewrite:

- The shot list is the source of truth for structure and narration.
- The session config is the source of truth for style, reveal behavior, and budget.
- Videos use one visual layer per frame: the illustrated scene.
- Do not create, preserve, or read a second visual layer.
- One AI illustration per narration chunk is the default. Stock sourcing is an alternate mode, not the default.
- The preprocessor owns reveal animation; the renderer plays PNG sequences as-is.
- If a scene cannot be visibly reviewed, it is not done.
- When the shot list, session config, or scene manifest changes, downstream artifacts must be regenerated.
- If a legacy sheet still contains removed columns, delete them before continuing.
- Shared docs should avoid absolute local paths unless a path is truly required to make something work.

## If There Is A Conflict

If two files appear to conflict:

1. `SESSION_CONFIG_SPEC.md` wins for session config structure and fields.
2. `SHOT_LIST_SPEC.md` wins for shot-list structure and field meaning.
3. `ASSET_RULES.md` wins for scene generation, asset sourcing, and validation.
4. `PREPROCESSOR_RULES.md` wins for reveal animation behavior and frame output.
5. `REVIEW_BOARD_RULES.md` wins for HTML review-board behavior.
6. `RENDER_RULES.md` wins for preview/render behavior.
7. `WORKFLOW_RULES.md` wins for pipeline-level behavior, source of truth, and regeneration rules.

If a real conflict still remains:
- do not guess
- report the conflict clearly
- stop before making a silent assumption

## Expected Agent Behavior

A new agent should:

1. read this file
2. read the rule files in the required order
3. identify the current pipeline stage
4. make changes only within that stage unless regeneration is required
5. validate downstream outputs after any upstream change

## Expected App Behavior

A standalone app should:

- model the workflow as explicit stages
- keep the shot list and session config as the two per-session sources of truth
- enforce regeneration after upstream edits
- never silently carry stale downstream data
- use only illustrated scenes per chunk (or documented alternate-mode backgrounds)
- delete legacy removed columns before processing a sheet
- never generate reveal animation inside the renderer
