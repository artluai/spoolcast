# Pipeline

Procedural reference — read top-to-bottom as you move through stages.
Workflow → Session config spec → Shot-list spec → Render config.

## Table of Contents

- [Part 1 — Workflow](#part-1--workflow)
  - [Purpose](#purpose)
  - [System Goal](#system-goal)
  - [Source Of Truth](#source-of-truth)
  - [Global Visual Model](#global-visual-model)
  - [Tracker Project Organization (One Project Per Shipped Video)](#tracker-project-organization-one-project-per-shipped-video)
  - [Canonical Directory Contract](#canonical-directory-contract)
  - [Canonical Content Layout](#canonical-content-layout)
  - [Pipeline Stages](#pipeline-stages)
  - [Stage Inputs And Outputs](#stage-inputs-and-outputs)
  - [Regeneration Rule](#regeneration-rule)
  - [Stale Output Cleanup Rule](#stale-output-cleanup-rule)
  - [Long-Running Job Rule](#long-running-job-rule)
  - [Reviewability Rule](#reviewability-rule)
  - [No Improvisation Rule](#no-improvisation-rule)
  - [No Mechanized Editorial Rule](#no-mechanized-editorial-rule)
  - [Failure Conditions](#failure-conditions)
  - [Validation Checklist](#validation-checklist)
  - [Environment Rule](#environment-rule)
- [Part 2 — Session Config Spec](#part-2--session-config-spec)
  - [Purpose](#purpose-1)
  - [Canonical Location](#canonical-location)
  - [Required Fields](#required-fields)
  - [Optional Fields](#optional-fields)
  - [Style Anchor Rule](#style-anchor-rule)
  - [Model Selection Rule](#model-selection-rule)
  - [Budget Rule](#budget-rule)
  - [Example](#example)
  - [Resolution + Aspect Ratio + Canvas Dimensions](#resolution--aspect-ratio--canvas-dimensions)
  - [Validation Rules](#validation-rules)
- [Part 3 — Shot-List Spec](#part-3--shot-list-spec)
  - [Purpose](#purpose-2)
  - [Canonical Structure](#canonical-structure)
  - [Required Headers](#required-headers)
  - [Overlay Spec](#overlay-spec)
  - [Removed Columns Rule](#removed-columns-rule)
  - [Time Format Rules](#time-format-rules)
  - [Field Meanings](#field-meanings)
  - [Required Fields For A Valid Beat](#required-fields-for-a-valid-beat)
  - [Background Rules](#background-rules)
  - [Reuse Rules](#reuse-rules)
  - [Canonical Example Row](#canonical-example-row)
  - [Downstream Field Mapping](#downstream-field-mapping)
  - [What The Shot List Must Not Do](#what-the-shot-list-must-not-do)
  - [Validation Rules](#validation-rules-1)
- [Part 4 — Render Config](#part-4--render-config)
  - [Purpose](#purpose-3)
  - [Preview Rule](#preview-rule)
  - [Runtime Requirements](#runtime-requirements)
  - [Canonical Render Inputs](#canonical-render-inputs)
  - [Required Render Behavior](#required-render-behavior)
  - [Preview-Data Schema](#preview-data-schema)
  - [Chunk Timeline Rule](#chunk-timeline-rule)
  - [Reveal Rule](#reveal-rule)
  - [Background Rules](#background-rules-1)
  - [Removed Columns Rule](#removed-columns-rule-1)
  - [Shot-List To Render Mapping](#shot-list-to-render-mapping)
  - [Motion Mapping](#motion-mapping)
  - [Audio Contract](#audio-contract)
  - [Visual Effect Rules](#visual-effect-rules)
  - [Overlay Placement Schema](#overlay-placement-schema)
  - [Preview-Data Rules](#preview-data-rules)
  - [Render Commands](#render-commands)
  - [Render Regeneration Rule](#render-regeneration-rule)
  - [Validation Rules](#validation-rules-2)
  - [Long-Running Render Rule](#long-running-render-rule)

## Part 1 — Workflow

### Workflow Rules

#### Purpose

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

#### System Goal

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

#### Source Of Truth

Two per-session sources of truth coexist:

- **Shot list** is the source of truth for structure: chapters, beats, chunks, narration text, timing, visual intent.
- **Session config** is the source of truth for style, image provider, reveal behavior, and AI budget (see PIPELINE.md § Session Config Spec).

Downstream artifacts may include:
- scene manifests
- generated scene illustrations
- preprocessor frame sequences
- review-board HTML
- preview-data files
- Remotion render output

None of those may silently override the shot list or the session config.

Shared documentation should avoid absolute local paths unless a path is truly required for a working local setup.

#### Global Visual Model

All videos use one primary visual layer per frame: the illustrated scene.

That means:
- each narration chunk is represented by one AI-generated full-frame illustration
- the illustration is the whole scene at the primary layer
- emphasis comes from moving to the next illustration on the next chunk
- returning to a prior illustration later is allowed

##### Overlay carve-out

Overlays (logos, badges, small reference artifacts) are permitted on top of the primary illustration, under strict constraints:

- every overlay's position, size, entry timestamp, exit timestamp, and any entry/exit transition must be **explicitly specified per-overlay** in the shot list
- the renderer may not improvise placement, size, or timing — it only plays the specified values
- overlay source images must have **authoritative clean alpha** — brand logos from press kits or SVG libraries, official badges, cleanly-cropped real screenshots
- AI-generated transparency or AI-judged cutouts are still banned (the original failure mode)
- overlays are rare by construction — used for brand-mention logo inserts and similar small contextual markers, not as a routine visual device

See PIPELINE.md § Render Config (overlay placement schema), PIPELINE.md § Shot-List Spec (overlay fields), and VISUALS.md (overlay sourcing) for the concrete contracts. See `DESIGN_NOTES.md` "Killed: foreground overlays → Reconsidered" for the reasoning behind reopening this.

If a legacy sheet still contains removed columns from an older model:
- delete those columns before doing any other work

#### Tracker Project Organization (One Project Per Shipped Video)

Each shipped video is a standalone unit of work tracked as **its own artlu-tracker project** — not grouped into a broader "spoolcast project" or a session-level project.

Why per-video: the tracker's unit of record is "a publishable piece of content." A single spoolcast session folder might span multiple chat sessions, refactors, and restarts before the video ships. The tracker project is the stable identity of the finished thing: its core message, its shipped URL, its journal entries.

The pilot video followed this pattern — it was tracked as *"TRIBE brain-prediction ad-test explainer — spoolcast pilot video"*, distinct from the tool-building project *"chat to video workflow - session to video"*. Future videos should use the same convention.

Session → tracker mapping:
- Each `spoolcast-content/sessions/<session-id>/session.json` should reference the tracker project name in its `notes` field for cross-reference.
- Journal entries per video go under that video's tracker project, not the workflow project.
- Paired videos (e.g., a V1 explainer + V2 dev-log about the same subject) each get their own tracker project.

External writes to the tracker (create project, add journal entry) require explicit user yes in chat per the best-practices rule — same as commits and PRs.

#### Canonical Directory Contract

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

#### Canonical Content Layout

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
- `session.json`: per-session config (see PIPELINE.md § Session Config Spec)
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

#### Pipeline Stages

The workflow has seven separate stages:

1. source-to-script (editorial, externally owned)
2. shot-list editing — structural validation (`validate_shot_list.py`) and narration audit (`audit_narration.py` via Qwen) gate this stage. Both must pass before Stage 4.
3. chunking (group shot-list rows into illustration units)
4. scene generation (one AI illustration per chunk). Two auditor gates sit around this stage: the narration audit before (script-level) and the scene audit after (`audit_scenes.py` via Qwen-VL, vision-level — catches OCR mismatches between rendered images and declared `on_screen_text`, anatomy/composition failures, and hallucinated text)
5. scene preprocessing (reveal frame sequences per chunk)
6. review-board generation (human check)
7. preview-data generation and video rendering

Each stage must have:
- a known input
- a known output
- a clear validation step

Do not blur these stages together.

##### Stage 4 ordering rule: external assets before AI generation

Within Stage 4 (scene generation), produce assets in this order:

1. **External / fetched / file-derived assets first.** Anything that's free and reversible: screenshots (via headless browser), B-roll extractions from existing videos, audio A/B samples from existing TTS renders, composite images from existing PNG files, file-format conversions (xlsx → PNG, json → highlighted code image), overlays sourced from brand press kits / SVG libraries. All of these can be produced cheaply and iterated on at zero cost per iteration.

   **Mechanically enforced** by `scripts/batch_scenes.py` pre-flight check: before any paid kie.ai call runs, the script walks the shot-list and verifies every `broll` / `meme` / `external_*` chunk has its `image_path` on disk AND (for motion assets) a verification sidecar per VISUALS.md § Asset Verification Enforcement. If any external is missing, the batch refuses to start and lists the blockers. Override only with `--skip-external-check` (intentional preview-only use). This closes the pattern-match failure where an agent proceeds directly to paid generation because the user said "go" without enforcing the ordering rule.
2. **Asset QA pass** (see below) — run quality checks on every external asset produced. Fix or flag anything that won't hold up at target display size.
3. **Re-approve the shot list after external assets + QA are complete.** A screenshot may be illegible at the target size. A B-roll clip may have bad framing. A composite may lack contrast. A converted xlsx may show irrelevant columns. Fix those chunks before proceeding — the chunk may need a different visual approach, a different asset source, or a cropping pass.
4. **AI-generated assets next.** Submit the kie.ai image batch only after external assets are locked and the shot list has been re-approved. Image generation costs real money per generation and each regeneration is wasteful.
5. **TTS batch last.** Narration text is locked by now; any script edit triggered by a visual issue would have been caught in step 3.

Why the ordering: external assets are real-world constraints. If one doesn't work, the chunk has to change, and any AI generation done against the old chunk spec is wasted. Front-loading the zero-cost work protects the spend on the variable-cost work.

##### Asset QA pass (within Stage 4)

After external assets are produced, before user re-approval, run an automated QA pass on every external asset. Surface the results as a structured report in chat — the user reviews concerns before the shot list is re-approved.

**Required checks per asset type:**

- **Images (PNG/JPG/raster):**
  - File exists and > 2KB (suspicious below this; usually indicates a placeholder, a broken download, or a favicon masquerading as a logo).
  - Native dimensions on the longer axis ≥ 2× the target overlay/display size. If the overlay is rendered at 200px wide, the source must be ≥ 400px wide.
  - Aspect ratio sane for intended placement.
- **SVG:**
  - File size ≥ 300 bytes (anything smaller is likely a placeholder).
  - Contains at least one of `<path>`, `<g>`, `<polygon>`, `<rect>` with meaningful `d` / geometry.
- **Video (MP4):**
  - Duration within ±1.5 sec of planned slot.
  - Resolution ≥ 720p for anything intended to be visible at full frame.
  - Audio track present when narration is expected from the clip itself.
- **Audio (MP3/WAV):**
  - Duration > 0.5 sec, < 30 sec (unless explicitly a long-form insert).
  - Peak amplitude non-trivial (not silent).

**Output format:** a second sheet in the shot-list xlsx named `assets`. One row per unique external asset referenced by the shot list (primary-scene images, B-roll videos, audio, overlay logos). Columns: Status (✅ / ⚠️ / ❌), Asset Path, Type (image/svg/video/audio), Purpose (primary vs overlay), Used By (which chunks reference it), Size, Dims/Dur, Concern. Row fill color reflects status (green/amber/red). Summary row at bottom tallies totals.

The `assets` sheet is regenerated every time the shot list is written — it stays in sync automatically. This keeps the QA pass one click away from the shot list itself, not buried in chat scrollback.

The QA pass does not auto-reject — it surfaces. The user decides.

##### Optional `box/` folder for user-supplied assets

Each session may include an optional `source/box/` folder where the user drops arbitrary assets they have locally — screenshots, photos, short clips, reference images, logos, anything. The folder is never required to contain anything; an empty `box/` never fails a stage.

**Agent behavior when external assets are being produced:**

- Scan `source/box/` for files at the start of Stage 4.
- For each file, make a best-effort guess at what it's for — filename hints, image contents (via preview), surrounding chunk context from the shot list. Examples: a file named `screenshot-terminal.png` in a project where chunk C38 calls for a terminal capture → guess that it fills C38.
- If the guess is confident (filename is unambiguous or visual content obviously matches), copy the file (not move) to the appropriate `external-assets/` or `overlays/` location with a normalized name. Record the mapping in chat.
- If the guess is uncertain, surface the file to the user in chat with 2-3 best-guess options: *"I found `photo-01.jpg` in `box/` — is this for C4 (meme punchline), C44 (Zara panel alternate), or unrelated?"*
- Files the user says are unrelated stay in `box/`, untouched.

The point: reduce friction when the user already has the right asset on hand. No need to figure out the canonical path — drop it in `box/`, let the agent route it.

This is strictly additive. If the user never drops anything in `box/`, everything works the same as before.

For fragile visual systems:
- validate changes in a prototype or duplicate first when possible
- port the approved version back into the main implementation only after the behavior is clearly correct

#### Stage Inputs And Outputs

##### 1. Source-to-Script (externally owned)

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

Canonical method: STORY.md (repo root). This is the primary reference for any agent running this stage — it captures the real editorial process that produced `tribe-session-001`, including the 10-stage pipeline, heuristics, quality tests, and rejection criteria.
Original brief (now secondary): `spoolcast-content/shared/video-generation-skill-spec.md`.

Canonical output locations:
- `../spoolcast-content/sessions/<session-id>/script/` — screenplay, scene plan, voiceover
- `../spoolcast-content/sessions/<session-id>/shot-list/` — canonical shot-list file

Downstream stages read from these outputs; they do not call back into this stage.

##### 2. Shot-List Editing

Input:
- shot list produced by stage 1, or manual edits

Output:
- updated shot list

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/shot-list/`

##### 3. Chunking

Input:
- shot list with narration per beat

Output:
- shot list with `Chunk` column populated per beat (see PIPELINE.md § Shot-List Spec)
- shot list with `Continuity` declared per chunk (see below)

Each unique `Chunk` value corresponds to one illustration.

###### Chunking Heuristics (Stop-And-Check Questions)

Hard numeric rules ("max N beats per chunk") are not used — pacing is editorial judgment, not math. Instead, for every proposed chunk, stop and ask:

1. **Visual subject test**: can ONE simple image honestly represent what's being narrated across all these lines? If the narration shifts from "analyst doing normal work" to "brain patterns," those are different visual worlds — split.
2. **Pan-justification test**: would this chunk need more than 1-2 camera moves to stay coherent? If yes, it's probably too much for one image — split.
3. **Time-on-screen soft cap**: any image sitting on screen longer than ~10 seconds needs to earn that hold (strong visual, intentional slow beat). Narration of 15s+ on a static image with no justification → split.
4. **Visual economy**: if describing the image takes more than 2 short sentences, it's too complex for one illustration — split.

Long-pause markers in the voiceover script (`pause_after: "long"`) are a hint, not a chunking rule. They help suggest boundaries but do not replace the four tests above.

The real prevention of bad chunking is visual review of the shot list (xlsx) **before** any image is generated — merged-cell spans make over-large chunks visible at a glance.

###### Chunk Continuity

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

##### 4. Scene Generation

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

##### 5. Scene Preprocessing

Input:
- generated scene PNG per chunk
- reveal parameters from session config

Output:
- per-chunk frame sequence folder

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/frames/<chunk-id>/`

See VISUALS.md.

##### 6. Review-Board Generation

Input:
- shot list
- scene manifest
- generated scene illustrations

Output:
- HTML review board

Canonical output location:
- `../spoolcast-content/sessions/<session-id>/review/`

##### 7. Preview-Data Generation And Rendering

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

#### Regeneration Rule

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

#### Stale Output Cleanup Rule

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

#### Long-Running Job Rule

For long-running jobs:
- start the job
- stop talking
- do not keep polling unless explicitly asked

Applies to:
- renders
- AI image generation
- preprocessor batch runs

#### Reviewability Rule

If a scene illustration cannot be visibly reviewed, it is not done.

This rule applies before render trust.

A scene is not done if:
- it only exists as a task ID
- it cannot be previewed on the review board
- the local file is missing or corrupt
- it is stale compared with the current shot list

When building anything meant for external review:
- optimize for proof and clarity over flavor text

#### No Improvisation Rule

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

#### No Mechanized Editorial Rule

Stage 1 (source-to-script) must not be mechanized with a general-purpose LLM loop that writes screenplays from templates.

This stage depends on judgment about story arc, pacing, turning points, and tone — qualities that degrade when mechanized. If you are building tooling for this stage, it should be agent-assist (a human or capable agent in the loop), not an autonomous pipeline.

This rule may be revisited once STORY.md is written and the process is well enough understood to automate without quality loss.

#### Failure Conditions

A task is not complete if any of these are true:

- stage 1 outputs are missing or inconsistent (no screenplay, or shot list doesn't match the screenplay)
- the shot list is not correct
- the session config is invalid (see PIPELINE.md § Session Config Spec validation rules)
- any chunk is missing a generated scene illustration
- any chunk is missing a valid preprocessor frame folder
- the review board does not match the shot list
- the preview-data file does not match the shot list
- the render is based on stale preview data
- deleted columns still influence downstream output
- the scene manifest contains unresolved required scenes
- content files were written into the repo when they belong in the content root
- the renderer applies any reveal effect on top of preprocessor frames

#### Validation Checklist

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

#### Environment Rule

Use a known-good local render environment.

Render reliability matters more than clever background execution tricks.

Prefer:
- a stable local Node/runtime setup (Node 22 — see PIPELINE.md § Render Config)
- a stable Python environment for the preprocessor
- direct user-terminal render commands when needed

Avoid:
- fragile detached launch patterns unless proven stable

## Part 2 — Session Config Spec

### Session Config Spec

#### Purpose

This file defines the per-session configuration file that controls how a session is generated and rendered.

The session config is one of two per-session sources of truth:
- the shot list = structure, narration, timing
- the session config = style, provider, reveal behavior, budget

#### Canonical Location

Every session must have a session config at:

- `../spoolcast-content/sessions/<session-id>/session.json`

#### Required Fields

- `session_id` — string, must match the folder name
- `ai_budget` — integer, max number of image generations allowed for the session
- `preferred_model` — string, the kie.ai model name used by default for scene generation

#### Optional Fields

- `style_reference` — string. Either a descriptive style prompt or a URL/local path to a reference image.
- `default_style_prompt` — string. Fallback style prompt used when `style_reference` is not set.
- `reveal_style` — string enum. Default: `fade`. Allowed values defined in VISUALS.md.
- `reveal_duration_seconds` — number. Default: `1.5`.
- `scene_fps` — integer. Default: `30`.
- `resolution` — string. Default: `2K`. Allowed: `1K`, `2K`, `4K`.
- `aspect_ratio` — string. Default: `16:9`.
- `output_format` — string. Default: `png`.
- `notes` — string. Human notes, not read by any pipeline.

#### Style Anchor Rule

The session config controls per-session style consistency.

- The first scene generation in the session establishes the visual style anchor.
- The anchor is recorded in the session's scene manifest.
- Every subsequent scene generation must pass the anchor reference back in as `image_input` (see VISUALS.md — Kie Provider Spec).
- If `style_reference` is an image URL, use it directly as the anchor for the first generation.
- If `style_reference` is a prompt string, the first generated scene becomes the anchor image.
- If neither `style_reference` nor `default_style_prompt` is set, scene generation must fail loudly instead of silently picking a style.

#### Model Selection Rule

`preferred_model` sets the default. Any scene may override via its own prompt metadata, but the override should be explicit in the generation request, not silent.

Known working models are listed in VISUALS.md — Kie Provider Spec.

#### Budget Rule

`ai_budget` is the hard ceiling on **number of image generations** (count, not dollars) allowed for the session.

- Count every successful generation against the budget.
- Do not count failures or cache hits.
- When the budget is exhausted, the pipeline must stop and require explicit config change before continuing.

Approximate dollar-cost translation (for planning): at nano-banana-2 1K resolution, roughly $0.05-0.08 per generation as of 2026-04. A 60-gen session runs ~$3-5 at current rates. The per-project dollar cap is a user/project decision, not a rule in this pipeline — set `ai_budget` to the generation count that fits your dollar target, and rerun the math when kie.ai pricing changes. Do not confuse the field's integer value with dollars.

#### Example

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
  "resolution": "1K",
  "aspect_ratio": "16:9",
  "output_format": "png",
  "notes": "first reference case for illustrated pipeline"
}
```

#### Resolution + Aspect Ratio + Canvas Dimensions

`resolution` controls image generation quality (kie.ai value). Allowed:
`1K` (project default — kept low for cost), `2K`, `4K`. Project standard
is `1K`; never silently default to anything else.

`aspect_ratio` controls both:
1. The aspect of generated illustrations (passed to kie.ai)
2. The Remotion composition's canvas dimensions

Canvas dimension mapping (resolved in `build_preview_data.py`,
overridable via explicit `width` / `height` in session.json):

| aspect_ratio | width × height | use case |
|---|---|---|
| `16:9` | 1920 × 1080 | YouTube, landscape video |
| `9:16` | 1080 × 1920 | Shorts, Reels, TikTok |
| `1:1`  | 1080 × 1080 | IG feed, square posts |
| `4:5`  | 1080 × 1350 | IG portrait |
| `21:9` | 2520 × 1080 | ultra-wide |

For mobile-first (`9:16`) or square (`1:1`) sessions:
- Image prompts must compose vertically (TOP/BOTTOM thinking, not LEFT/RIGHT)
- Camera zone vocabulary still works (uses percentages) but `left-third`/
  `right-third` become very narrow strips on portrait — prefer
  `upper-middle`/`lower-middle` for portrait sessions
- Reveal scripts (chalkboard, paint) work on any aspect — no changes needed

To override canvas dims explicitly, add `width` and `height` ints to
session.json. Otherwise they're derived from `aspect_ratio`.

#### Validation Rules

A session is invalid if:

- `session.json` is missing
- `session_id` does not match the folder name
- `ai_budget` is missing or not a positive integer
- `preferred_model` is missing
- neither `style_reference` nor `default_style_prompt` is set
- `reveal_style` is set to a value not allowed by VISUALS.md
- `resolution` is set to a value other than `1K`/`2K`/`4K`
- `aspect_ratio` is set to a value not in the canvas-dimension table
  AND no explicit `width`+`height` provided

## Part 3 — Shot-List Spec

### Shot List Specification

#### Purpose

This file defines what the shot list is, which fields it must contain, what each field means, what values are allowed, and how those fields are used downstream.

The shot list is the source of truth.

#### Canonical Structure

The shot list is currently represented as a workbook/table with one row per beat or shot.

Each row should describe exactly one beat-level unit that can be:
- reviewed in the HTML board
- converted into preview data
- rendered into video

#### Required Headers

The current canonical header set is:

1. `#`
2. `Chapter`
3. `Shot`
4. `Start`
5. `End`
6. `Duration`
7. `Section Summary`
8. `Narration Segment`
9. `Script / Narration`
10. `Pause After`
11. `Beat`
12. `Background Visual`
13. `Movement`
14. `Interaction`
15. `Extras / Notes`
16. `Camera`
17. `Tone Job`
18. `Asset To Find`
19. `Priority`
20. `Chunk`
21. `Overlays` (optional — see Overlay Spec below)

#### Overlay Spec

Per the overlay carve-out in PIPELINE.md § Workflow, chunks may include explicitly-specified overlays on top of the primary illustration (brand logos, official badges, cleanly-cropped screenshots).

The `Overlays` column, when present, holds a JSON array of overlay specs. Each entry is a JSON object with fields defined in PIPELINE.md § Render Config (Overlay Placement Schema):

```json
[
  {
    "source": "assets/overlays/meta-logo.png",
    "timing_start_s": 1.2,
    "timing_end_s": 2.8,
    "x": 0.85,
    "y": 0.15,
    "anchor": "top-right",
    "width": 0.12,
    "entry_transition": "fade-in",
    "exit_transition": "fade-out"
  }
]
```

If the column is empty, the chunk has no overlays — primary illustration only.

Every field listed in PIPELINE.md § Render Config overlay schema is required per overlay (no silent defaults). If any field is missing, the render will fail loudly rather than guess.

Constraints (enforced at validation time, not render time):
- Hard cap: 3 concurrent overlays per chunk at any moment.
- Soft cap per video: ~5-10 overlay insertions total. More than that is a design smell — redesign as full-frame scenes.

Typical use: brand-name mention in narration gets the brand's logo inserted at the word's timestamp, top-right corner, ~12% canvas width, fades in and out over ~0.3s.

#### Removed Columns Rule

The shot list must not contain the removed legacy columns from the old two-layer model.

Delete these columns anywhere they still exist:
- `Foreground 1`
- `Foreground 2`
- `Foreground 3`
- `Foreground 4`
- `Foreground Text 1`
- `Foreground Text 2`

Do not leave them blank.
Do not preserve them for compatibility.
Delete them.

#### Time Format Rules

##### `Start`
Accepted formats:
- `00:00`
- `00:00.0`
- `00:00.00`
- `0:00`

Meaning:
- elapsed time from chapter or sequence start

##### `End`
Accepted formats:
- `00:00`
- `00:00.0`
- `00:00.00`
- `0:00`

Meaning:
- elapsed time from chapter or sequence start

##### `Duration`
Accepted formats:
- `4s`
- `4.0s`
- `4.25s`

Do not use:
- bare integers like `4`
- words like `four seconds`

##### `Pause After`
Accepted formats:
- blank
- `0s`
- `0.5s`
- `1.0s`

Do not use prose like:
- `small pause`
- `tiny beat`

#### Field Meanings

##### `#`
Optional ordinal index.
Used only for human reference.

##### `Chapter`
Human-readable chapter grouping.
Used for grouping shots into sections.

Format expectation:
- `01`
- `02`
- or short stable chapter label

##### `Shot`
Required unique shot/beat identifier.

Format expectation:
- short stable id
- chapter prefix + shot sequence

Examples:
- `01A`
- `02F`

Used by:
- asset manifests
- review board
- preview-data generation
- render debugging

##### `Section Summary`
Short summary of what this beat is doing in the larger chapter.

Used by:
- review board
- planning clarity

##### `Narration Segment`
Optional segmentation label for script organization.

Used by:
- script organization
- optional chapter/script grouping

##### `Script / Narration`
Required spoken text for the beat.

Used by:
- review board
- preview-data generation
- render timing context
- TTS synthesis (the narration text is sent to the TTS provider verbatim)

This field should contain:
- the exact spoken line
- one beat-level unit of narration
- text written the way you want it pronounced (see Pronunciation Rule below)

Do not put:
- multiple unrelated beats in one cell
- production notes instead of narration

###### Pronunciation Rule

Narration text is sent to TTS verbatim. Whatever you write is what the
voice will say. Acronyms are the common trip hazard:

- **Acronyms pronounced as words** (ROAS = "roe-ass", NASA = "nah-suh"):
  **expand to the full term** in the narration. Example:
  - Bad: `"...click-through rate, watch time, and ROAS."` (TTS says "R-O-A-S")
  - Good: `"...click-through rate, watch time, and return on ad spend."`

- **Acronyms pronounced letter-by-letter** (RFP, GPU, VPS, CEO, FAQ):
  write them as-is — TTS handles letter-by-letter acronyms correctly.
  Optionally hyphenate (`R-F-P`) if TTS mispronounces them as a single
  word.

- **Words that happen to look like acronyms** (TRIBE, LAMBDA, SCRUM):
  write them as regular words — TTS pronounces them as words.

- **Numbers and units**: write them the way you want them spoken. `"3.5
  hours"` is fine; `"3.5h"` may get said as "three point five H."

- **Unusual proper nouns** (product names, model names): pronounce how
  the narration reads aloud. If needed, spell phonetically: `"Co-lab"`
  instead of `"Colab"` if TTS says it wrong.

The rule: **read your narration aloud. If you wouldn't pronounce a
letter cluster the way it's written, rewrite it.**

##### `Beat`
Required concise visual/narrative beat description.

This should explain what the beat is doing on screen.

Used by:
- review board
- planning
- debugging visual intent

Good:
- `normal metrics frame gets established`
- `the story pivots from normal metrics to a stranger question`

Bad:
- `make this cool`
- `something interesting`

##### `Background Visual`
Required current visual for the beat.

This is the primary visual field in the system.

Allowed contents:
- direct media URL
- hyperlink formula
- short descriptive label for a reused/known background
- local file URL if appropriate
- explicit reuse markers such as `same as 01B`

In the current system:
- this field is the visual driver
- this is what the review board should show
- this is what the preview/render pipeline should use

##### `Movement`
Required shot-motion description.

This describes how the beat should feel visually.

Allowed values:
- `Static`
- `Hold`
- `Slow push`
- `Slow push in`
- `Slow push out`
- `Gentle pan left`
- `Gentle pan right`
- `Lateral pan`
- `Return to prior background`
- `Background changes`
- `Background tightens`
- `Background widens`

Do not use vague values such as:
- `better`
- `dynamic`
- `whatever feels right`

##### `Interaction`
Required explanation of what the visual change is doing narratively.

This answers:
- why this beat changes
- what the audience should feel or understand

Use sentence form.

Good:
- `The frame shifts from ordinary ad analysis into visible overload.`
- `This background change makes the format feel more suspicious.`

##### `Extras / Notes`
Optional human notes.

Use for:
- extra clarification
- optional ideas
- warnings

Do not rely on this field for core required behavior if a proper field exists.

##### `Camera`
Required camera behavior note.

Allowed values:
- `Static`
- `Hold`
- `Slow push`
- `Slow push in`
- `Slow push out`
- `Gentle pan left`
- `Gentle pan right`
- `Lateral pan`
- `Continuous run move`
- `Cut`

Not allowed:
- `Impact shake`
- `Micro zoom on impact`
- `Random motion`

##### `Tone Job`
Required description of what kind of visual source should be used.

Examples:
- `stock ad-collage montage`
- `brain heatmap / MRI / lab background`
- `official product explainer background`
- `generated surreal ad overload background`

Used by:
- sourcing
- review sanity checks

##### `Asset To Find`
Optional sourcing to-do field.

Use when the background visual is not yet resolved.

Accepted values:
- blank
- exact search term
- exact source needed
- exact replacement needed

Examples:
- `pexels crowd billboard montage`
- `official product explainer still`
- `google images mri heatmap`

##### `Priority`
Optional urgency/need field.

Allowed values:
- blank
- `need-stock`
- `graphic`
- `reuse`
- `nice-to-have`
- `approved`

Do not use ad hoc labels unless the system is updated to support them.

##### `Chunk`
Required grouping identifier.

A chunk groups one or more adjacent shot-list rows under a single AI-generated illustration.

Format expectation:
- short stable id
- examples: `C1`, `C2`, `C3`, or descriptive labels like `C1-hook`, `C2-question`

Rules:
- beats with the same `Chunk` value share one illustration
- chunks must be contiguous in the shot list — do not skip rows and return to the same chunk later unless the narrative explicitly calls for reuse
- a chunk should pass the chunking heuristics in PIPELINE.md § Workflow → 3. Chunking
- if a chunk intentionally reuses a prior chunk's illustration, use the `Continuity` field (see below)

Used by:
- scene generation — one illustration per unique chunk
- preprocessor — one frame folder per unique chunk
- render — chunks are the timeline scheduling unit

##### `Continuity`
Required per-chunk field declaring how this chunk relates to the previous chunk.

Allowed values:
- `standalone` — new visual world; no obligation to carry character/setting from the prior chunk
- `continues-from-prev` — same arc as the previous chunk; image must visually relate (shared character, setting, or motif)
- `callback-to-<chunk-id>` — deliberately returns to a specific earlier chunk's world

Default (blank): `standalone`.

See PIPELINE.md § Workflow → 3. Chunking → Chunk Continuity for how this drives generation.

##### `Image Source`
Required per-chunk field declaring where the chunk's image comes from.

Allowed values:
- `generated` — AI-illustrated scene, produced by the scene-generation stage (default)
- `proof` — a real image (chart, screenshot, diagram) from the source session's artifacts; used briefly to prove reality. Style-clash with illustrated scenes is intentional.
- `reuse` — reuses the exact image from a prior chunk (used with `callback-to-<chunk-id>`)
- `meme` — a cultural-reference punchline artifact. `meme` is a **punchline role**, not a file-format constraint. The classic case is a still image (this-is-fine dog, Wall-E frame, is-this-a-pigeon panel), but animated meme gifs and short cultural-reference video clips (SpongeBob time-card, looping reaction clips) are first-class and route through the broll video pipeline when they are the canonical form. Default to the most engaging form per STORY.md § Broll "Format default: lean toward motion." Whether the asset is a PNG, GIF, or MP4 is a file-format detail — editorially it's all "meme broll" and is governed by the same broll rules (context + attention + spacing + no-repeat)
- `broll` — a video clip (mp4/mov/webm) plays during this chunk. Requires `context_justification` (see below). See STORY.md § Part 2 for the broll context rule.
- `broll_image` — a still image from external broll footage (one frame of a real clip); letterboxed like a meme
- `external_screenshot`, `external_xlsx`, `external_json`, `external_terminal` — cleanly-cropped real UI / file / terminal captures, style-clash intentional
- `composite_pilot` — composited output from a prior pilot, used as proof

Default (blank): `generated`.

For `proof` chunks:
- `image_path` points at the real file (usually in `source/artifacts/` or `source/fetched-assets/`)
- the scene-generation stage is skipped for this chunk — no kie.ai call
- `Beat Description` and `Full Prompt` may describe what the proof shows, but are not fed to a generator
- keep proof inserts brief (typically 2-4 seconds) — use illustrated concept scenes to carry the story, proof inserts only to prove reality

For `reuse` chunks:
- `image_path` points at an earlier chunk's generated file
- no new generation is produced

##### `boundary_kind`
Required on every chunk. Declares the size of the transition INTO this chunk from the previous chunk. Drives which pause tier and which signal the builder emits. See STORY.md § Part 2 for the full pacing contract.

Allowed values:
- `continues-thread` — new chunk but same sub-topic; narration continues the thread. Default pause 0.8–1.2s.
- `topic-shift` — new topic within the same Act. Narration must open with a bridge sentence that names what just ended and what begins. Default pause 1.2–1.8s.
- `act-boundary` — opens a new Act. Requires `act_title` and `act_opener_line`. Preceded by a silent bumper (1.5–2s) unless this is the first chunk of the video. Pause before 1.0s, after bumper 0.5s.
- `bumper` — a standalone title-card chunk with no narration. Requires `act_title` only; no beats. Emitted automatically by the builder when an `act-boundary` chunk follows an Act; author doesn't usually write bumper chunks by hand.

##### `weight`
Required on every chunk. `normal` or `high`. Flag `high` on the promise, preview, thesis, and punchline chunks. High-weight means ≥1.5s silence after the chunk, the image lingers on screen, the camera doesn't move during the chunk, and list-item beats inside get ≥1s pause (not 0.3–0.6s).

Default (blank): `normal`.

##### `context_justification`
Required when `Image Source` is `broll` (or any non-illustration source). One sentence naming the context mechanism that makes this broll obvious to a cold viewer within 2 seconds. One of:
- spoken setup ("narration immediately before says 'watch this…'")
- visual continuity ("prior chunk's illustration shows the thing abstractly; this plays the real thing")
- recognition ("clip is a culturally known artifact — this-is-fine dog / Wall-E")
- topical match ("narration names the exact thing as the clip plays, clip IS that thing")
- on-broll label ("caption overlay names the clip")
- callback ("clearly references an earlier established moment")

Empty or "none" → validator rejects. See STORY.md § Part 2 "Broll requires obvious viewer context."

##### `visual_direction`
Optional per-chunk field. Free-form description of how the image should look and feel — composition, mood, character pose, framing. Sent to the image model as style guidance.

Split out from the legacy `beat_description` field so stage direction doesn't leak into the rendered frame. Does not describe motion; does not contain literal on-screen text. Use `motion_notes` for motion and `on_screen_text` for literal text.

If `visual_direction` is absent, the legacy `beat_description` field is used verbatim (backward compatibility for older sessions). New sessions should populate `visual_direction` explicitly.

##### `on_screen_text`
Optional per-chunk field. An array of strings, each string being a block of literal text that will appear on the rendered frame exactly as written (title card, caption, label, document text, rule card, meme overlay, handwritten note). Empty array (or missing) means no text on screen.

Used for two purposes:
1. **Read-time floor check.** The validator computes `total_word_count × 0.35` seconds of required read-time and rejects chunks whose estimated duration falls below the floor. See STORY.md § On-screen text read-time.
2. **Literal-text rendering.** The scene generator composes a separate "render these exact words on the frame" instruction from this field, instead of hoping the image model extracts text out of prose.

Rule: if a viewer is expected to read text on the frame, declare it here. Do not hide it inside `visual_direction` prose.

**Empty text slots get invented.** If `visual_direction` mentions anything that holds words (card, page, sign, screen, label, document, book, banner, poster, ledger), either write the exact words into `on_screen_text` OR say it's `blank` / `wordless` / `no text` / `out of focus` / `illegible` inside `visual_direction`. Leaving it ambiguous means the generator fills the empty slot with invented text — almost never what you wanted. See VISUALS.md § Prompt Hygiene Rules.

Default (blank/missing): `[]`.

##### `motion_notes`
Optional per-chunk field. Free-form description of motion the beat is trying to convey — redraws, transitions, state changes, hand movements. **Never sent to the still-image model** — a still image cannot render motion, and attempting it produces simultaneous overlapping frames (phantom limbs, duplicate objects). The reveal/animation layer consumes this field; the scene generator ignores it.

If the motion is the editorial point of the chunk, consider: (a) splitting into two chunks (before + after), (b) using a `reveal_group` across adjacent chunks, or (c) describing only the *end state* in `visual_direction`.

##### `broll_source_kind`
Required when `image_source` is `broll` or `broll_image`. Declares where the broll footage originated. One of:

- `sibling-video` — clip lifted from a previously shipped video in the same project (e.g. a V1 end-card referenced from V2)
- `self-reject` — clip generated during an earlier iteration of the *current* video (rejected takes, saga clips, reveal attempts)
- `external-capture` — real-world footage or third-party video captured for this session
- `meme` — cultural-reference clip (this-is-fine, SpongeBob time-card, reaction gif)
- `stock` — generic stock footage

Used by the validator to enforce `broll_framing` rules. See VISUALS.md § Previous-video broll framing.

##### `broll_framing`
Required when `image_source` is `broll` or `broll_image`. Declares how the clip is composited into the frame. One of:

- `tv-screen` — the clip plays inside a TV or monitor graphic, background dimmed. For video broll, a REC indicator is added to the bottom-right of the TV screen; for still broll, no indicator. **Required** when `broll_source_kind` is `sibling-video` or `self-reject`. Applied at render time by the Remotion `TVFrameWrapper` component (`src/Composition.tsx`) — no AI-gen composite scene needed.
- `full-frame` — the clip fills the canvas edge-to-edge
- `inset` — the clip sits inside a letterboxed or framed inset, anchored to a zone

The `tv-screen` requirement for sibling/self-reject broll exists so the viewer reads "that's a clip from another video" without narration labor — see VISUALS.md § Previous-video broll framing.

Schema aliases: the canonical value is `"tv-screen"`. The renderer also accepts the legacy value `"tv"` for backward compatibility with pre-schema-formalization sessions.

##### `punchline`
Optional boolean. Mark `true` when the chunk's narration is a single deadpan beat (one- to three-word reaction, capstone line, understated aside — e.g. "Obviously.", "That's it."). See STORY.md § Deadpan punchlines.

Rules applied when `punchline: true`:
- the chunk must contain exactly one beat
- `image_source` should be `meme` (or `broll_image` for a stamp / reaction gif)
- the image should be a full-frame cultural-reference artifact, not a style-locked scene

Validator flags any chunk containing a ≤3-word beat that is not the sole beat in its chunk — those beats almost certainly belong in their own `punchline: true` chunk.

##### `not_a_punchline`
Optional boolean on a chunk or an individual beat. Opts out of the deadpan-punchline validator check when a short beat is structurally NOT a deadpan — the most common case is a short line that previews an enumerated list the following chunks expand, or a callback cue whose short length is deliberate setup rather than comedic punctuation.

Use sparingly. The default behavior (flagging short beats inside multi-beat chunks) catches real failures; most `not_a_punchline` overrides mean the chunk should actually be split. Only set this flag when the short beat truly serves a non-deadpan structural role the regex patterns can't detect automatically.

##### `readtime_override`
Optional boolean. When `true`, the validator's read-time floor check is bypassed for this chunk. Use when the author has deliberately picked a shorter hold by ear (typical: the card was already seen recently, text is scannable at a glance, or the viewer is meant to glance rather than read). The flag is explicit so the override is recorded as an intentional author decision, not a silent timing shortcut. See STORY.md § Author opt-out.

##### `silent_hold` and `hold_duration_sec`
Optional fields used for chunks that hold a prior frame silently while the viewer reads on-screen text or absorbs a beat.

- `silent_hold: true` — marks the chunk as an intentional silent hold. Allows the chunk's beats to carry empty narration without tripping the "beat missing narration" validator rule. Typically paired with `image_source: reuse`.
- `hold_duration_sec: <number>` — explicit duration (in user-facing seconds) the chunk occupies in the timeline. Overrides the validator's default narration-plus-pause estimate so the read-time floor check uses the real hold time.

Common use: a chunk carries a dense on-screen text card (`on_screen_text` with many words) whose `read-time floor = word_count × 0.35s` exceeds what the narrated beat and its `pause_after` can provide. The narrated chunk does its job (intro / setup), then a following silent-hold chunk inherits the same image (`image_source: reuse`) and holds it for the remaining read time. The silent-hold chunk owns the `on_screen_text` declaration (so the floor isn't double-counted across the pair).

##### `act_title`
Required when `boundary_kind` is `act-boundary` or `bumper`. The text rendered on the bumper card. No prefix, no number — just the Act name (e.g., `"ANATOMY"`, `"PROOF"`, `"OUTRO"`). Hand-drawn type style.

##### `act_opener_line`
Required when `boundary_kind` is `act-boundary`. The narration line that previews what the Act covers. Often doubles as the first beat of the chunk. Used by the builder to confirm the opener does preview work, not just generic transition.

##### `broll_audio` (optional, for broll chunks)
One of `mute` | `duck` | `full`. Default `mute`. Governs how the broll's own audio mixes with the spoken narration.
- `mute` — broll audio silenced completely (default — use when narration plays during broll)
- `duck` — broll audio at ~15% during narration, full between lines (rarely useful)
- `full` — broll audio at full volume, no narration overlaps (use only when the clip's audio IS the content)

Two audio tracks never play simultaneously at full volume. See STORY.md § Part 2.

##### `start_from_sec` (optional, for broll chunks)
Number. Seconds into the source video to begin playback. Default 0. Used to play different sections of the same source clip across multiple broll chunks.

##### `reveal_group` (optional)
Freeform string. Adjacent chunks sharing the same `reveal_group` value form one reveal group — a rhetorical unit that plays with a single reveal rhythm. See STORY.md § Part 2 "Reveal groups" for the full behavior contract.

Inside a group:
- First chunk wipes in normally, wipe-out suppressed
- Middle chunks: both wipes suppressed (hard cut both sides)
- Last chunk: wipe-in suppressed, wipe-out normal
- Default `pause_after` between chunks: `"tight"` (0.15s), not the 0.3s default

Constraints (validator enforces):
- Non-adjacent chunks with the same value are an error
- `boundary_kind: "bumper"` or `"act-boundary"` chunks cannot be inside a group
- All chunks in a group must share the same `scene`
- Group size: 2–5 chunks (typical 2–4)

##### `Camera Target` (optional)
Used when the camera frames a specific region of the chunk's illustration during a beat.

Allowed values (zone vocabulary — remaps to pixel coordinates by aspect ratio):
- `center`
- `left-third`, `right-third`
- `top-third`, `bottom-third`
- `upper-middle`, `lower-middle`
- `top-left`, `top-right`, `bottom-left`, `bottom-right`
- `top`, `bottom`, `left`, `right`

Blank = camera inherits previous position (static).

##### `Camera Zoom` (optional)
Vocabulary only, no raw numbers:
- `wide` — full canvas visible (1.0x)
- `medium` — ~70% of canvas visible (1.4x)
- `tight` — ~45% of canvas visible (2.2x)
- `close` — ~30% of canvas visible (3.3x)

Blank = inherit previous zoom.

##### `Camera Reason` (required when Camera Target is set)
One-sentence explanation of why the camera moves on this beat. If you can't state a reason, don't move the camera.

#### Required Fields For A Valid Beat

At minimum, a beat must have:
- `Shot`
- `Duration`
- `Script / Narration`
- `Beat`
- `Background Visual`
- `Movement`
- `Interaction`
- `Camera`
- `Tone Job`
- `Chunk`

#### Background Rules

Every beat must have a background plan.

That background may be:
- a new background
- a reused background
- a returned background from an earlier beat
- a full-height vertical background when the source media is vertical

If two adjacent beats use the same background:
- that must be treated downstream as one continuous background run

#### Reuse Rules

If a beat intentionally reuses a background:
- the shot list should make that obvious
- the downstream system should not interpret it as a brand-new visual unless the source actually changes

Preferred reuse markers:
- `same as 01B`
- `return to 02A background`
- same hyperlink/local path as prior beat

#### Canonical Example Row

Example valid beat:

| Shot | Start | End | Duration | Script / Narration | Beat | Background Visual | Movement | Interaction | Camera | Tone Job | Asset To Find | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01C | 00:08.0 | 00:12.0 | 4.0s | Which means everybody is trying to make theirs work better. | ad pile becomes visibly crowded | https://example.com/ad-collage.mp4 | Background changes | The frame becomes intentionally too busy before any analysis starts. | Slow push | stock sponsored-post / banner / inbox ad collage | pexels ad collage night billboard | need-stock |

#### Downstream Field Mapping

##### Review board uses:
- `Shot`
- `Start`
- `End`
- `Duration`
- `Section Summary`
- `Script / Narration`
- `Beat`
- `Background Visual`

##### Scene generation uses:
- `Chunk`
- `Script / Narration` (combined across the chunk's beats)
- `Beat` (combined across the chunk's beats)
- `Tone Job`
- `Background Visual` (for intent, when present)

##### Asset sourcing (alternate mode) uses:
- `Background Visual`
- `Tone Job`
- `Asset To Find`
- `Priority`

##### Preview-data generation uses:
- `Shot`
- `Chunk`
- `Duration`
- `Script / Narration`
- `Movement`
- `Camera`

##### Render uses:
- `Shot`
- `Chunk`
- `Duration`
- `Movement`
- `Camera`

#### What The Shot List Must Not Do

The shot list must not:
- depend on hidden agent memory
- assume a renderer will improvise layouts
- preserve removed columns from the old two-layer model
- use vague timing or motion language that requires guessing

#### Validation Rules

The shot list fails validation if:
- required fields are blank
- removed legacy columns are still present
- two downstream artifacts contradict the shot list
- background intent is ambiguous enough that the renderer would need to guess
- any required field uses a non-supported format

## Part 4 — Render Config

### Render Rules

#### Purpose

This file defines how preview-data generation and Remotion rendering should behave.

#### Preview Rule

The preview should act like a rough cut.

It should not act like:
- a debug export
- a diagnostics page
- a review board converted directly into a video

#### Runtime Requirements

Current known-good setup:
- Node 22

Known issue:
- Node 24 caused repeated Rspack / Remotion native-binding failures on this machine

If render/build fails with Rspack native-binding errors:

1. switch to Node 22
2. remove `node_modules`
3. reinstall dependencies
4. retry render

#### Canonical Render Inputs

The renderer should read:
- the current generated preview-data file
- the current scene manifest
- the current preprocessor frame folders
- the current audio metadata

It must not read:
- stale review-board HTML
- stale deleted preview-data files
- removed legacy columns
- raw scene PNGs directly (reveal is the preprocessor's job — see VISUALS.md)

#### Required Render Behavior

The preview should:
- play each chunk's preprocessor frame sequence synced to its narration audio
- hold the final frame for the remainder of the chunk after the reveal completes
- advance to the next chunk's frame sequence on chunk change
- use full session audio correctly
- remove debug text from frame
- reflect the current shot list and session config exactly

#### Preview-Data Schema

Generated preview-data for each session must contain:
- `sessionId`
- `fps`
- `chunks` — ordered array of chunk objects

Each chunk object must contain:
- `chunkId`
- `beats` — array of shot ids that fall under this chunk
- `framesDir` — path to the preprocessor output folder for this chunk
- `frameCount`
- `revealDurationSeconds`
- `chunkDurationSeconds` — total time this chunk occupies in the timeline
- `startFrame` — global frame index at which this chunk begins
- `endFrame` — global frame index at which this chunk ends
- `narrationAudioSrc` — path to the audio used for this chunk
- `narrationStartSeconds` — offset into `narrationAudioSrc`
- `narrationEndSeconds`

Optional per-chunk fields:
- `cameraMotion` — optional light motion applied on top of the frame playback (see Motion Mapping below)
- `holdFrameIndex` — which frame to hold after reveal completes (default: last frame)

#### Chunk Timeline Rule

The chunk is the unit of timeline scheduling.

- frames within a chunk come from the preprocessor, nothing else
- chunk boundaries align with chunk changes in the shot list
- adjacent chunks using the same illustration should be represented as one chunk in the shot list first, not stitched at render time

#### Reveal Rule

The reveal animation is owned entirely by the preprocessor.

The renderer must:
- play the PNG sequence as-is
- hold the final frame after the sequence completes
- not re-time the sequence
- not apply fade, scale, or blur on top

If a different reveal is needed, update the session config and rerun the preprocessor.

#### Background Rules

The illustrated scene is the only visual layer.

If the session switches to the alternate stock/sourced mode (see VISUALS.md):
- backgrounds are still the only visual layer
- vertical source media must be rendered as full-height backgrounds
- adjacent beats that share a background should be grouped into one chunk upstream, not stitched at render time

#### Removed Columns Rule

The render pipeline must not read, preserve, or recreate data from removed legacy columns.

If a legacy shot list still contains those columns:
- delete them upstream first
- then regenerate preview data
- then rerender

#### Shot-List To Render Mapping

##### `Shot`
Used for:
- debug identification
- review labeling

##### `Chunk`
Used for:
- grouping beats into illustration units
- driving the render timeline

##### `Duration`
Used for:
- frame allocation inside a chunk

##### `Script / Narration`
Used for:
- narration audio alignment
- debug only when explicitly enabled

##### `Movement`
Used for:
- optional per-chunk camera motion on top of the frame playback

##### `Camera`
Used for:
- optional per-chunk camera behavior

Note: prior visual-intent fields (`Tone Job`, `Background Visual`, `Asset To Find`, `Priority`) are primarily used by the scene generation stage, not the render stage.

#### Motion Mapping

Camera motion is optional and applied on top of the preprocessor frame playback.

Default:
- `Static` or `Hold` — no camera motion

Allowed on top of frame playback:
- `Slow push in` — gentle scale-in across the chunk
- `Slow push out` — gentle scale-out across the chunk
- `Gentle pan left` — slow horizontal translation left across the chunk
- `Gentle pan right` — slow horizontal translation right across the chunk

Not allowed by default:
- impact shake
- micro zoom on impact
- arbitrary camera pops
- decorative transitions between chunks
- reveal effects overlaid on frame playback

#### Audio Contract

The render pipeline must know:
- where audio lives
- whether timing is chunk-level or session-level
- start and end offsets for playback

If audio is session-level:
- attach it once at session scope with mapped offsets per chunk
- do not accidentally play only the first chunk

If audio is chunk-level:
- each chunk must define its own audio segment explicitly

#### Visual Effect Rules

Do not apply global visual effects by default that darken or stylize the whole frame unnecessarily.

Disallowed by default:
- global gradient overlays
- decorative darkening layers that are not explicitly needed
- any effect applied on top of preprocessor frames

#### Overlay Placement Schema

The one-visual-layer rule allows a carve-out for explicitly-specified overlays (see PIPELINE.md § Workflow Overlay carve-out). This section defines the schema.

##### Per-overlay fields (read by renderer, specified in shot list)

Every overlay entry must specify ALL of the following — no defaults, no improvisation:

- `source` — path or URL to the overlay image (PNG with clean alpha preferred, SVG acceptable if rasterized at render time)
- `timing_start_s` — number of seconds into the chunk when the overlay appears. `0.0` for chunk-start.
- `timing_end_s` — number of seconds into the chunk when the overlay disappears. Must be `> timing_start_s`.
- `x` — horizontal position in 0.0-1.0 coordinates (0 = left edge, 1 = right edge) OR absolute pixels. Convention: use normalized coords.
- `y` — vertical position, same convention.
- `anchor` — which point of the overlay image is placed at (x, y). One of: `top-left`, `top-right`, `center`, `bottom-left`, `bottom-right`. Default convention: `center`.
- `width` — target width in normalized coords (0.0-1.0 fraction of canvas width) OR absolute pixels. Convention: use normalized.
- `height` — optional. If omitted, height is computed from source aspect ratio. Specify only when forcing a non-native aspect.
- `entry_transition` — one of: `cut`, `fade-in`, `pop-in`, `slide-in-left`, `slide-in-right`, `slide-in-top`, `slide-in-bottom`. Default `fade-in` over 0.2s.
- `exit_transition` — same vocabulary as entry. Default `fade-out` over 0.2s.

##### Renderer behavior

On each frame, the renderer:
- iterates overlays for the current chunk
- for each overlay, checks if the current chunk-relative time is within `[timing_start_s, timing_end_s]` (including transition time)
- composites the overlay at the specified position / size / anchor with the specified entry/exit transition state
- does NOT compute its own positions, sizes, timings, or transitions

If an overlay entry is missing any required field, the renderer must fail loudly (not silently substitute defaults).

##### Caps

To preserve the "overlays are rare" principle:
- Hard cap: 3 concurrent overlays on screen at any moment. Anything over 3 requires a rule-conflict flag.
- Soft cap per video: ~5-10 overlay insertions total. More than that should be redesigned as full-frame scenes, not overlay-stacked.

#### Preview-Data Rules

Preview-data generation must:
- read from the current shot list
- read from the current session config
- read from the current scene manifest
- read from the current preprocessor frame folders
- export only the layers allowed by the current system

Current rule:
- preview data must contain one-chunk-per-entry with frame sequence references
- no foreground layer entries

#### Render Commands

Typical local render flow:

1. go to repo root
2. confirm Node 22
3. confirm scene manifest and frame folders exist for every chunk
4. regenerate preview data if upstream changed
5. run the render from the repo root
6. **run `audit_render.py` on the output. render is not "done" until the audit passes.**

The exact render command can vary, but it must:
- use the current composition entry
- write output into the content root `renders/` directory

#### Render Audit Rule (load-bearing)

A rendered mp4 is not "done" until `scripts/audit_render.py` passes against it. The audit is a programmatic check of the final artifact (not of intermediate preview-data) that encodes every known failure class: white-flash detection at chunk boundaries, OCR verification of declared `on_screen_text`, overlay-presence checks, duration integrity. The list grows over time — every new user-reported bug class gets added as a check, so the audit gets smarter per session.

Semantics:
- On pass, audit_render writes a sentinel at `<session>/working/render-audit.passed` recording the mp4 path + audit timestamp.
- On fail, the sentinel is removed and a report is written at `<session>/working/render-audit.json` with one failure record per issue.
- Downstream stages (publish, post-process to 1.15x, mark-as-shipped) must require the sentinel's presence + recency. No shipping without audit.

Applies in both modes (PIPELINE.md § Delivery Modes):
- Human-in-loop: audit fails → Claude reports the failures → user picks fix / accept / override.
- Autonomous: audit fails → Claude diagnoses and re-renders, up to a bounded retry count. Same-failure short-circuit: if attempt N+1 fails the exact same check as N, stop immediately — the fix isn't working and more retries burn budget without progress.

"Verified" means the audit passed. "Code changed" is not verification; neither is "I extracted a few frames by eye." The audit is the mechanical verification that's the same in both modes.

#### Render Regeneration Rule

When any of these change:
- shot list (including `Chunk` values)
- session config
- scene illustrations
- preprocessor frame folders
- preview-data generation logic
- composition logic

Then the video must be rerendered.

Do not trust an older MP4 if any upstream layer has changed.

Before rerender:
- overwrite or remove the prior MP4 if it shares the same output path

#### Validation Rules

The render fails if:
- it shows deleted elements
- it uses stale preview data
- a chunk plays a frame folder whose scene does not match the current scene manifest
- any chunk's frame count does not match its preview-data entry
- reveal timing is modified inside the renderer
- reused illustrations play with fresh reveal when they should hold
- audio plays incorrectly across the planned duration
- motion is arbitrary or visually distracting

#### Long-Running Render Rule

When starting a render:
- start it
- let it run
- avoid noisy polling unless explicitly requested

For reliability:
- prefer stable direct terminal renders over fragile detached launch patterns
