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

All videos use one primary visual layer per frame: the illustrated scene.

That means:
- each narration chunk is represented by one AI-generated full-frame illustration
- the illustration is the whole scene at the primary layer
- emphasis comes from moving to the next illustration on the next chunk
- returning to a prior illustration later is allowed

### Overlay carve-out

Overlays (logos, badges, small reference artifacts) are permitted on top of the primary illustration, under strict constraints:

- every overlay's position, size, entry timestamp, exit timestamp, and any entry/exit transition must be **explicitly specified per-overlay** in the shot list
- the renderer may not improvise placement, size, or timing — it only plays the specified values
- overlay source images must have **authoritative clean alpha** — brand logos from press kits or SVG libraries, official badges, cleanly-cropped real screenshots
- AI-generated transparency or AI-judged cutouts are still banned (the original failure mode)
- overlays are rare by construction — used for brand-mention logo inserts and similar small contextual markers, not as a routine visual device

See `RENDER_RULES.md` (overlay placement schema), `SHOT_LIST_SPEC.md` (overlay fields), and `ASSET_RULES.md` (overlay sourcing) for the concrete contracts. See `DESIGN_NOTES.md` "Killed: foreground overlays → Reconsidered" for the reasoning behind reopening this.

If a legacy sheet still contains removed columns from an older model:
- delete those columns before doing any other work

## Tracker Project Organization (One Project Per Shipped Video)

Each shipped video is a standalone unit of work tracked as **its own artlu-tracker project** — not grouped into a broader "spoolcast project" or a session-level project.

Why per-video: the tracker's unit of record is "a publishable piece of content." A single spoolcast session folder might span multiple chat sessions, refactors, and restarts before the video ships. The tracker project is the stable identity of the finished thing: its core message, its shipped URL, its journal entries.

The pilot video followed this pattern — it was tracked as *"TRIBE brain-prediction ad-test explainer — spoolcast pilot video"*, distinct from the tool-building project *"chat to video workflow - session to video"*. Future videos should use the same convention.

Session → tracker mapping:
- Each `spoolcast-content/sessions/<session-id>/session.json` should reference the tracker project name in its `notes` field for cross-reference.
- Journal entries per video go under that video's tracker project, not the workflow project.
- Paired videos (e.g., a V1 explainer + V2 dev-log about the same subject) each get their own tracker project.

External writes to the tracker (create project, add journal entry) require explicit user yes in chat per the best-practices rule — same as commits and PRs.

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

### Stage 4 ordering rule: external assets before AI generation

Within Stage 4 (scene generation), produce assets in this order:

1. **External / fetched / file-derived assets first.** Anything that's free and reversible: screenshots (via headless browser), B-roll extractions from existing videos, audio A/B samples from existing TTS renders, composite images from existing PNG files, file-format conversions (xlsx → PNG, json → highlighted code image), overlays sourced from brand press kits / SVG libraries. All of these can be produced cheaply and iterated on at zero cost per iteration.
2. **Re-approve the shot list after external assets are produced.** A screenshot may be illegible at the target size. A B-roll clip may have bad framing. A composite may lack contrast. A converted xlsx may show irrelevant columns. Fix those chunks before proceeding — the chunk may need a different visual approach, a different asset source, or a cropping pass.
3. **AI-generated assets second.** Submit the kie.ai image batch only after external assets are locked and the shot list has been re-approved. Image generation costs real money per generation and each regeneration is wasteful. TTS comes after images (narration text is locked by then; any script edit triggered by a visual issue would have been caught in step 2).

Why the ordering: external assets are real-world constraints. If one doesn't work, the chunk has to change, and any AI generation done against the old chunk spec is wasted. Front-loading the zero-cost work protects the spend on the variable-cost work.

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

Canonical method: `SCRIPT_EXTRACTION_RULES.md` (repo root). This is the primary reference for any agent running this stage — it captures the real editorial process that produced `tribe-session-001`, including the 10-stage pipeline, heuristics, quality tests, and rejection criteria.
Original brief (now secondary): `spoolcast-content/shared/video-generation-skill-spec.md`.

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
- shot list with `Continuity` declared per chunk (see below)

Each unique `Chunk` value corresponds to one illustration.

#### Chunking Heuristics (Stop-And-Check Questions)

Hard numeric rules ("max N beats per chunk") are not used — pacing is editorial judgment, not math. Instead, for every proposed chunk, stop and ask:

1. **Visual subject test**: can ONE simple image honestly represent what's being narrated across all these lines? If the narration shifts from "analyst doing normal work" to "brain patterns," those are different visual worlds — split.
2. **Pan-justification test**: would this chunk need more than 1-2 camera moves to stay coherent? If yes, it's probably too much for one image — split.
3. **Time-on-screen soft cap**: any image sitting on screen longer than ~10 seconds needs to earn that hold (strong visual, intentional slow beat). Narration of 15s+ on a static image with no justification → split.
4. **Visual economy**: if describing the image takes more than 2 short sentences, it's too complex for one illustration — split.

Long-pause markers in the voiceover script (`pause_after: "long"`) are a hint, not a chunking rule. They help suggest boundaries but do not replace the four tests above.

The real prevention of bad chunking is visual review of the shot list (xlsx) **before** any image is generated — merged-cell spans make over-large chunks visible at a glance.

#### Chunk Continuity

Chunks relate to each other in one of three ways. Every chunk declares its continuity explicitly:

- `standalone` — new visual world; no obligation to carry character/setting from the prior chunk. Use when narration introduces a new idea.
- `continues-from-prev` — same arc as the previous chunk. Use when narration is still inside one wider idea/mini-story. The image must visually relate to the previous chunk (same character, same setting, or shared motif).
- `callback-to-<chunk-id>` — deliberately returns to a specific earlier chunk's world (for emphasis or narrative loop).

Blank defaults to `standalone`.

For `continues-from-prev` chunks, the generation step must:
1. pass the previous chunk's image as `image_input` (for style + character/setting consistency)
2. state the shared thread explicitly in the prompt ("same stick figure character at the same desk")
3. focus the new prompt on what CHANGED, not what stayed the same

For `callback-to-<chunk-id>` chunks, do the same but with the specific earlier chunk's image as reference.

Arcs (multi-chunk mini-stories) emerge implicitly from consecutive `continues-from-prev` chunks. No separate arc data structure is needed.

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
