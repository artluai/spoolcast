# Workflow Rules

## Purpose

These are the global system rules for any agent or app working on spoolcast.

This file defines:
- the system model
- the pipeline stages
- the source of truth
- the directory contract
- regeneration rules
- validation rules
- failure conditions

This file is generic.
It must not depend on any specific session.

## System Goal

Turn a session — a chat, a build, a conversation, an idea — into:

1. a screenplay and shot list that tell the real story honestly
2. one AI-generated illustration per narration chunk in a per-session locked visual style
3. a deterministic reveal of each illustration (via the preprocessor)
4. a reliable final video rendered by Remotion against narration audio

The system should minimize:
- stale data
- arbitrary visual decisions
- hidden assumptions
- renderer improvisation
- mechanized editorial judgment

When something is important across chats or tools:
- write it into the repo docs
- do not trust chat memory

## Source Of Truth

Two per-session sources of truth coexist:

- **Shot list** is the source of truth for structure: chapters, beats, chunks, narration text, timing, visual intent.
- **Session config** is the source of truth for style, image provider, reveal behavior, and AI budget (see `SESSION_CONFIG_SPEC.md`).

Downstream artifacts may include:
- scene manifests
- generated scene illustrations
- preprocessor frame sequences
- review-board HTML
- preview-data files
- Remotion render output

None of those may silently override the shot list or the session config.

Shared documentation should avoid absolute local paths unless a path is truly required for a working local setup.

## Global Visual Model

All videos use one visual layer per frame: the illustrated scene.

That means:
- each narration chunk is represented by one AI-generated full-frame illustration
- the illustration is the whole scene; no overlays, no compositing
- emphasis comes from moving to the next illustration on the next chunk
- returning to a prior illustration later is allowed

This system does not use a second visual layer.

If a legacy sheet still contains removed columns from an older model:
- delete those columns before doing any other work

## Canonical Directory Contract

Two roots exist:

1. repo root
2. content root

Canonical roots:
- repo root: `spoolcast/`
- content root: `../spoolcast-content/`

The repo root contains:
- renderer code
- scripts
- rules docs
- templates
- generated preview-data code when needed by the renderer

The content root contains:
- session source packages (transcripts, logs, artifacts)
- screenplays, scene plans, and shot lists
- session configs
- source media
- generated scene illustrations
- preprocessor frame sequences
- scene manifests
- review boards
- renders
- working notes

## Canonical Content Layout

Per-session content should follow this structure:

1. `../spoolcast-content/sessions/<session-id>/session.json`
2. `../spoolcast-content/sessions/<session-id>/source/` — raw session package (transcript, logs, artifacts, notes)
3. `../spoolcast-content/sessions/<session-id>/script/` — screenplay, scene plan, voiceover script
4. `../spoolcast-content/sessions/<session-id>/shot-list/` — canonical shot-list file
5. `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/`
6. `../spoolcast-content/sessions/<session-id>/source/fetched-assets/`
7. `../spoolcast-content/sessions/<session-id>/frames/<chunk-id>/`
8. `../spoolcast-content/sessions/<session-id>/manifests/`
9. `../spoolcast-content/sessions/<session-id>/review/`
10. `../spoolcast-content/sessions/<session-id>/renders/`
11. `../spoolcast-content/sessions/<session-id>/working/`

Expected contents:
- `session.json`: per-session config (see `SESSION_CONFIG_SPEC.md`)
- `source/`: raw session package (transcript, logs, artifacts, notes) plus session media
- `script/`: screenplay, scene plan, voiceover script, and any intermediate editorial drafts
- `shot-list/`: canonical shot-list file (workbook or equivalent)
- `source/generated-assets/scenes/`: per-chunk AI-generated illustration PNGs
- `source/fetched-assets/`: externally sourced media when running the alternate stock mode
- `frames/<chunk-id>/`: preprocessor output — numbered PNG sequences per chunk
- `manifests/`: scene manifests and other deterministic generated metadata
- `review/`: HTML review boards and local preview media
- `renders/`: MP4 outputs
- `working/`: temporary planning artifacts that should not become source of truth

## Pipeline Stages

The workflow has seven separate stages:

1. source-to-script (editorial, externally owned)
2. shot-list editing
3. chunking (group shot-list rows into illustration units)
4. scene generation (one AI illustration per chunk)
5. scene preprocessing (reveal frame sequences per chunk)
6. review-board generation (human check)
7. preview-data generation and video rendering

Each stage must have:
- a known input
- a known output
- a clear validation step

Do not blur these stages together.

For fragile visual systems:
- validate changes in a prototype or duplicate first when possible
- port the approved version back into the main implementation only after the behavior is clearly correct

## Stage Inputs And Outputs

### 1. Source-to-Script (externally owned)

Input:
- raw session package: transcript, logs, artifacts, notes
- optional reference files, screenshots, short clips, external links

Output:
- a screenplay
- a scene plan
- a voiceover script (for TTS or narration)
- a shot list with narration per beat, chunks defined, timing and visual intent set

This stage is editorially-driven. Its quality depends on judgment about story arc, turning points, pacing, and tone — not on mechanical process.

Current default: handled by a capable agent (typically Codex or Claude in a dedicated session) with the raw session package in full context. Spoolcast's repo does not currently provide code for this stage.

Brief: `spoolcast-content/shared/video-generation-skill-spec.md`.
Detailed method (pending): `SCRIPT_EXTRACTION_RULES.md`. When this file is authored, this stage's rules expand and the brief becomes a secondary reference.

Canonical output locations:
- `../spoolcast-content/sessions/<session-id>/script/` — screenplay, scene plan, voiceover
- `../spoolcast-content/sessions/<session-id>/shot-list/` — canonical shot-list file

Downstream stages read from these outputs; they do not call back into this stage.

### 2. Shot-List Editing

Input:
- shot list produced by stage 1, or manual edits

Output:
- updated shot list

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/shot-list/`

### 3. Chunking

Input:
- shot list with narration per beat

Output:
- shot list with `Chunk` column populated per beat (see `SHOT_LIST_SPEC.md`)

Each unique `Chunk` value corresponds to one illustration.

### 4. Scene Generation

Input:
- shot list
- session config
- per-chunk prompt derived from narration + beat descriptions

Output:
- one illustration PNG per chunk
- scene manifest

Canonical output locations:
- `../spoolcast-content/sessions/<session-id>/source/generated-assets/scenes/<chunk-id>.png`
- `../spoolcast-content/sessions/<session-id>/manifests/scenes.manifest.json`

### 5. Scene Preprocessing

Input:
- generated scene PNG per chunk
- reveal parameters from session config

Output:
- per-chunk frame sequence folder

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/frames/<chunk-id>/`

See `PREPROCESSOR_RULES.md`.

### 6. Review-Board Generation

Input:
- shot list
- scene manifest
- generated scene illustrations

Output:
- HTML review board

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/review/`

### 7. Preview-Data Generation And Rendering

Input:
- shot list
- scene manifest
- frame sequences
- audio timing data

Output:
- generated preview-data file for the renderer
- rendered MP4

Canonical locations:
- preview data: repo `src/data/` or another renderer-owned generated-data directory
- render: `../spoolcast-content/sessions/<session-id>/renders/`

## Regeneration Rule

When an upstream source changes, every affected downstream artifact must be regenerated.

Examples:

- If the screenplay or shot list narration changes:
  - regenerate any affected scene illustration
  - regenerate preprocessor frames for that chunk
  - regenerate review board
  - regenerate preview-data
  - rerender video output

- If the session config changes reveal params:
  - regenerate preprocessor frames for all chunks
  - regenerate preview-data
  - rerender video output

- If a scene illustration is regenerated:
  - regenerate preprocessor frames for that chunk
  - regenerate review board
  - rerender video output

Do not assume one rebuilt layer updates the rest.

## Stale Output Cleanup Rule

Regeneration is not enough if stale files can still be read.

Before regenerating an output layer:
- identify the old output file(s)
- overwrite them or delete them
- confirm downstream code is not still pointing at old paths

At minimum, treat these as stale-sensitive:
- generated scene PNGs
- preprocessor frame folders
- HTML review boards
- generated preview-data files
- scene manifests
- rendered MP4s

## Long-Running Job Rule

For long-running jobs:
- start the job
- stop talking
- do not keep polling unless explicitly asked

Applies to:
- renders
- AI image generation
- preprocessor batch runs

## Reviewability Rule

If a scene illustration cannot be visibly reviewed, it is not done.

This rule applies before render trust.

A scene is not done if:
- it only exists as a task ID
- it cannot be previewed on the review board
- the local file is missing or corrupt
- it is stale compared with the current shot list

When building anything meant for external review:
- optimize for proof and clarity over flavor text

## No Improvisation Rule

The renderer must not improvise:
- where something appears
- how large it is
- when it appears
- why it appears
- how it reveals

If a visual decision matters, it must come from:
- the shot list
- the session config
- the preprocessor output
- or another deterministic system rule

## No Mechanized Editorial Rule

Stage 1 (source-to-script) must not be mechanized with a general-purpose LLM loop that writes screenplays from templates.

This stage depends on judgment about story arc, pacing, turning points, and tone — qualities that degrade when mechanized. If you are building tooling for this stage, it should be agent-assist (a human or capable agent in the loop), not an autonomous pipeline.

This rule may be revisited once `SCRIPT_EXTRACTION_RULES.md` is written and the process is well enough understood to automate without quality loss.

## Failure Conditions

A task is not complete if any of these are true:

- stage 1 outputs are missing or inconsistent (no screenplay, or shot list doesn't match the screenplay)
- the shot list is not correct
- the session config is invalid (see `SESSION_CONFIG_SPEC.md` validation rules)
- any chunk is missing a generated scene illustration
- any chunk is missing a valid preprocessor frame folder
- the review board does not match the shot list
- the preview-data file does not match the shot list
- the render is based on stale preview data
- deleted columns still influence downstream output
- the scene manifest contains unresolved required scenes
- content files were written into the repo when they belong in the content root
- the renderer applies any reveal effect on top of preprocessor frames

## Validation Checklist

Before saying a state is correct, verify:

1. stage 1 outputs exist and are consistent (screenplay → shot list → chunks all tell the same story)
2. shot list reflects intended plan and has `Chunk` populated
3. session config is valid
4. every chunk has a generated illustration
5. every chunk has a valid preprocessor frame folder
6. review board reflects shot list + current illustrations
7. preview-data file reflects shot list + current frame folders
8. render output reflects current preview-data
9. file locations match the directory contract

If any one layer is stale:
- the work is not done

## Environment Rule

Use a known-good local render environment.

Render reliability matters more than clever background execution tricks.

Prefer:
- a stable local Node/runtime setup (Node 22 — see `RENDER_RULES.md`)
- a stable Python environment for the preprocessor
- direct user-terminal render commands when needed

Avoid:
- fragile detached launch patterns unless proven stable
