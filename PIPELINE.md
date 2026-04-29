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

### End-to-end flow (decision tree)

Single reference for how a session moves from empty state to shipped. Widescreen (A) is the mandatory path; mobile (A.1) is an optional fork after Stage 8 shipping. Every stage has a mechanical gate that must pass before the next stage starts.

| # | Stage | What it does | Driver | In → Out | Gate | On fail |
|---|---|---|---|---|---|---|
| 0 | Scaffold | Creates session dir + config | `init_session.py` | ids, budget, style → `session.json` + subdirs | config parses | fix config |
| 1a | Core message | Locks the one-sentence takeaway | agent | raw source → locked core message | user confirms (STORY.md § Job E) | surface gap, don't proceed |
| 1b | Structure | Decides Act / chapter shape | agent | core message → Act structure | user approves | revise |
| 1c | Screenplay | Drafts v1 → v3 voiceover | agent | structure → `voiceover.md` + drafts | v3 on disk | re-draft |
| 2 | Shot-list | Per-beat shot-list from screenplay | shot-list editor | v3 → `shot-list.json/.xlsx` | `validate_shot_list.py` = 0 | fix violations |
| 3 | Chunking | Groups beats into illustration units | agent | beats → chunks | all chunks have `boundary_kind` + `weight` | author chunks |
| 4a | Narration audit | QA on narration text | `audit_narration.py` | narration → `narration-audit.json` | exit 0 | fix narration |
| 4b | External pre-flight | Ensures externals + sidecars on disk before any kie call | `batch_scenes.py` pre-flight | shot-list → externals verified | pre-flight passes | source missing asset |
| 4c | Scene gen | One AI illustration per chunk | `batch_scenes.py` / `generate_scene.py` | shot-list + style → `scenes/*.png` + manifest | PNG + manifest entry per chunk | regen failed chunks |
| 4d | Scene audit | Vision QA on PNGs (Qwen-VL) | `audit_scenes.py` | PNGs → `scene-audit.json` | exit 0 | regen flagged |
| 5 | Preprocess | Builds reveal frame sequences | `batch_preprocess.py` | PNGs → `frames/*/` | all frame counts present | re-preprocess |
| 6 | Review board | Human-review HTML artifact | `build_review_board.py` | shot-list + scenes → `review/shot-review.html` | human review passes | regen flagged |
| 7 | Render | Remotion assembles the widescreen video | `render_with_audit.sh` | preview-data + frames + audio → `<session>-1.0x.mp4` | `audit_render.py` passes | fix flagged frames |
| 8a | Rate post-process | Speeds 1.0× → shipped rate (optional) | ffmpeg `setpts` | 1.0× mp4 → `<session>-<rate>x.mp4` | duration matches expected | re-run |
| 8b | Captions SRT | Full SRT at shipped rate | `generate_srt.py` | preview-data + shot-list → `<session>-<rate>x.srt` | cue count > 0 | regenerate |
| 8c | Thumbnail | Widescreen YouTube thumbnail | `generate_thumbnail.py` | prompt → `<session>-thumbnail-1920x1080.png` | exactly 1920×1080 | rescale |
| 8d | Publish | Upload to YouTube | `publish_youtube.py` | Stage 8 artifacts → YouTube URL | Pre-upload checklist (SHIPPING.md § Part 2) ✓ | fix failing items |
| — | **Decision** | Ship mobile variants? | agent/user | Stage 8 artifacts → branch into A.1 or end | user chooses | widescreen ends |
| A.1-1 | Prereq | Stage 8 complete | — | — | `render-audit.passed` sentinel | complete widescreen |
| A.1-2 | Mobile crop fill | Center-crops widescreen scenes → 4:5 | `mobile_export.py` (planned) | `scenes/*.png` → `scenes/mobile/*-mobile.png` | every non-bumper generated chunk has a mobile PNG | re-run crop |
| A.1-3 | Mobile-crop audit | Vision check on cropped PNGs | `audit_mobile_crops.py` | mobile PNGs → `mobile-crop-audit.json` | report written | re-run |
| A.1-4 | Regen at 4:5 | Byte-faithful replay, aspect-only override | `replay_mobile.py --aspect 4:5` | flagged + manifest → regen PNGs | regen OR orphan warning logged | orphan → continue; kie fail → retry once |
| A.1-5 | Re-audit regens | Catches broken regens | `audit_mobile_crops.py --only` | regens → audit | 0 broken after 1 retry | fail loudly at retry limit |
| A.1-6 | Mobile render | Stitches mobile PNGs at shipped rate | `mobile_export.py` (planned) | mobile PNGs + master + SRT → per-part MP4(s) | exact 1080×1920, duration matches rate | re-run |
| A.1-7 | Burn captions | Baked into step 6 via libass | `caption_assets.py` + ffmpeg | rate-matched SRT → captioned MP4 | no font-fallback warnings | verify fontsdir |
| A.1-8 | Duration / split | Split on chunk boundaries if > platform cap | part logic in step 6 | total duration → N parts | each part ≤ platform cap at shipped rate | adjust split |
| A.1-9 | Thumbnail per part | 1080×1920 full-screen thumbnails | `generate_mobile_thumbnail.py` (planned) | base + title + part → `*-mobile-thumb-pt<n>of<total>.png` | exact 1080×1920, no bars | regen |
| A.1-10 | Per-part SRTs | Windowed SRTs for accessibility upload | windowing utility (planned) | shipped SRT → `*-mobile-pt<n>of<total>.srt` | duration matches part MP4 | re-window |
| A.1-11 | Final audit | Mechanical pre-upload checklist | `audit_mobile_publish.py` (planned) | all per-part artifacts → report | SHIPPING.md § A.1 Pre-upload checklist ✓ | fix items |
| A.1-12 | Publish per part | Upload to platform(s) | platform uploaders (manual) | per-part artifacts → platform URLs | platform accepts | platform troubleshoot |

**Universal principles for the table above:**

- **Mechanical gates are mandatory.** A stage "passed" only when the listed gate passed — never when the code "looks right." See rules.md § Verified = mechanical check passed.
- **`Driver: agent` is AI-driven by default but human-doable.** Per rules.md § Delivery Modes, the AI agent executes these stages autonomously in autopilot mode, with user confirmation in agent-skill mode. A human reviewer may also drive the stage directly. The stage's gate is what's mandatory, not who drives it.
- **A.1 never shims A code paths.** When an A.1 stage looks like "extract from widescreen master and scale," check for a mobile-native source first. See SHIPPING.md § A vs A.1 separation.
- **Failures surface loudly, not silently.** Manifest orphans, rate mismatches, audit regressions — all surface with specific warnings so a reviewer can correlate bad output with the cause (rules.md § Empirical verification beats logical inference).

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
- `source/generated-assets/scenes/`: per-chunk AI-generated illustration PNGs. Widescreen masters (A) at the top level (`<chunk>.png`); mobile-variant PNGs (A.1) under `scenes/mobile/<chunk>-mobile.png` so they stay isolated from the widescreen assets.
- `source/fetched-assets/`: externally sourced media when running the alternate stock mode
- `frames/<chunk-id>/`: preprocessor output — numbered PNG sequences per chunk
- `manifests/`: scene manifests and other deterministic generated metadata
- `review/`: HTML review boards and local preview media
- `renders/`: MP4 outputs. Widescreen (A) masters and their SRTs live at the top level of this directory. If the optional mobile-export chain (A.1) runs, its deliverables land under `renders/mobile/` — see SHIPPING.md § Part 4 for the mobile file-naming convention.

##### Variant outputs in subdirectories

Asset variants (mobile, 4:5, per-platform, future aspects) land under `<canonical>/<variant>/`, not mixed with the canonical root. Widescreen (A) sits at the root; mobile (A.1) under `mobile/`.

- `scenes/<chunk>.png` (widescreen) + `scenes/mobile/<chunk>-mobile.png` (A.1)
- `renders/<id>-1.0x.mp4` (widescreen) + `renders/mobile/<id>-mobile-9x16.mp4` (A.1)

Keep the variant suffix in the filename too (`-mobile`) — makes a file identifiable when pulled out of its folder context.

##### Fill order for variant folders: crops first, regens second

When populating a variant folder (e.g. `scenes/mobile/`), fill every eligible slot first with the cheap path — typically a post-processed crop of the widescreen master. Then overwrite only the slots where a crop loses content (flagged by audit as `mobile_unsafe`) with a regenerated asset.

Why this order: a regen costs real money per call; a crop is free. Starting with crops means the variant folder is self-sufficient after the cheap pass — every chunk has a mobile PNG on disk. The regen pass then targets exactly the chunks that need a new composition, without re-doing work the crop could have done.

Reverse order (regens first, then crops) leaves gaps in the folder and makes the regen decision unnecessarily early. Concrete cost in this session: we skipped the crop pass and went straight to regens for 9 chunks — even the ones that would have survived a crop fine. Cheaper and simpler to have cropped all first.
- `working/`: temporary planning artifacts that should not become source of truth

#### Pipeline Stages

The workflow has nine separate stages:

1. source-to-script (editorial, externally owned)
1.5. **asset inventory** — survey every real artifact already on disk or easily sourceable that could illustrate a concrete reference in the narration. Output: `sessions/<id>/working/asset-inventory.md`, one-line entries with paths, grouped by kind (prior shipped videos/renders/frames, session files, manifests, style anchors, chat transcripts, existing screenshots). No acquisition here — this is a survey, not a sourcing step. Purpose: collapses the concrete-reference check at Stage 2 from a search into a lookup. See rules.md § Non-Negotiable System Defaults for the check itself.
1.7. **character / object roster** — after the script is locked and before beat descriptions are written, enumerate every recurring character/object the script names at the role level ("the narrator," "the AI that lied"), then map each to the session's locked style library: existing ref / plan a new ref / one-off prompt-only. Output: `sessions/<id>/working/character-roster.md` mapping `<role> → <library/session ref key>` with chunk/Act coverage. Every Stage 2 beat description consults the roster and names roster entries by their reference key; every matching chunk gets `references: [...]` tags. See rules.md § Mode 1 Gate List for the full contract.
2. shot-list editing — structural validation (`validate_shot_list.py`) and narration audit (`audit_narration.py` via Qwen) gate this stage. Both must pass before Stage 4. **Before locking the shot list**, run the Concrete-reference check (rules.md § Non-Negotiable System Defaults) per chunk: scan narration for references to specific real things, match against the Stage 1.5 inventory, default each matched cell's visual to broll rather than an AI redraw. Any chunk that picks illustration over a matched real artifact records a one-line justification in the shot-list cell (schema: `context_justification`). Also run the Recurring-reference check (rules.md § Non-Negotiable System Defaults): scan scene descriptions for characters / objects that appear in 2+ chunks, register references, add `references: ["name"]` on matching chunks. `audit_narration.py` enforces this by flagging any chunk whose scene description names a recurring character/object (present in ≥2 chunks) but that has neither a `references` array nor a `context_justification` — exit non-zero on unjustified drift risk.
3. chunking (group shot-list rows into illustration units)
4. scene generation (one AI illustration per chunk, except cells defaulted to broll in Stage 2). Two auditor gates sit around this stage: the narration audit before (script-level) and the scene audit after (`audit_scenes.py` via Qwen-VL, vision-level — catches OCR mismatches between rendered images and declared `on_screen_text`, anatomy/composition failures, and hallucinated text)
5. scene preprocessing (reveal frame sequences per chunk)
6. review-board generation (human check)
7. preview-data generation and video rendering

Each stage must have:
- a known input
- a known output
- a clear validation step
- **an audit pass before declaring done.** A stage isn't done until its audit script passes (`audit_mobile_crops.py`, `audit_render.py`, `audit_narration.py`, etc.). Production-script exit-0 is necessary, not sufficient.

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

##### Audit-gated stage outputs

Production scripts with associated audits must gate output on the audit. `mobile_export.py` runs `audit_mobile_crops.py`; `render_with_audit.sh` already does this for widescreen render. Pattern: pre-flight (refuse to start) or post-flight (refuse to publish). Override only with an explicit `--skip-audit` flag for intentional preview-only iterations.

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

### Post-Stage 8: Mobile Export from Widescreen (A.1, optional)

**Scope.** This section covers the *derivation* path — starting from a shipped 16:9 master and producing mobile variants by cropping, caption-burning, and optionally splitting into parts for TikTok. A **mobile-first authoring path** (sessions composed natively at 9:16 from chunk 1, never touching 16:9) is tracked separately in ROADMAP.md as Process B and uses a different chain. The two paths share caption styling, the bundled Caveat font, and the libass prereq — all documented in `SHIPPING.md § Caption Styling` and referenced by both.

**Fully automated chain (runs end-to-end when mobile export is requested; no human gate between steps):**

1. **Prereq:** widescreen master shipped (Stage 8, audit_render mechanical pass).
2. **Crop** every non-bumper `image_source: generated` widescreen PNG to 4:5 into `scenes/mobile/<chunk>-mobile.png`. Bumpers skipped — ROADMAP item 5 (Remotion-native) handles them.
3. **Audit** the cropped PNGs via `audit_mobile_crops.py`. Flags broken/clipped chunks. Writes `working/mobile-crop-audit.json`. Note: `audit_scenes.py` on widescreen PNGs covers STRUCTURAL mobile-safety only (split-panels, off-center focals) and misses text-clipping — `audit_mobile_crops.py` is the authoritative legibility check for A.1. Both are useful at different stages.
4. **Regen** every flagged chunk at native 4:5 via `replay_mobile.py --aspect 4:5`. Byte-faithful: reads the widescreen prompt + image_input from the manifest, only overrides aspect. If any flagged chunk has no manifest entry (orphan — see VISUALS.md § Manifest race condition), the replay logs a warning and skips that chunk; the chain CONTINUES rather than halting. The orphan chunk retains its cropped-from-widescreen version in `scenes/mobile/` as a fallback, and the warning is surfaced at the end so a reviewer can correlate any bad output with the skipped chunks.
5. **Re-audit** the regens via `audit_mobile_crops.py`. Anything still broken → auto-retry once. Fail loudly at retry limit.
6. **Render** the mobile video via Remotion at 4:5 canvas: scene PNGs + live-rendered bumpers (ROADMAP item 5) + preprocessor reveal frames.
7. **Burn captions** via ffmpeg libass using the SHIPPING.md § Part 3 caption style.
8. **Duration check.** If the result exceeds the target platform cap (Reels ≤3 min algo / TikTok ≤60 s favored / Shorts 60 s hard) → auto-split on chunk boundaries with a "to be continued…" card + part badge.
9. **Regenerate thumbnail** at mobile aspect (4:5 or 9:16 per platform target).
10. **Final mechanical audit** (duration match, libass font-fallback check, frame sampling for visible artifacts) + ship.

The widescreen audit runs once per session regardless; the mobile chain runs only when mobile output is requested.

#### Prompt replay vs re-derivation (byte-faithful mobile regen)

The shot-list is mutable on-disk state. Between the original widescreen scene generation and any later mobile regeneration, fields may have been normalized, backfilled, or cleaned — e.g., `on_screen_text=[]` added to chunks that previously had no such field at all. `compose_prompt` reads the CURRENT shot-list, so its output can drift even when the visible chunk semantics haven't changed. A literal "same prompt" claim requires replaying the historical prompt, not re-deriving from today's shot-list.

When the goal is *"produce the same scene as the widescreen, just at a different aspect"*, use `scripts/replay_mobile.py`. It reads the exact `prompt` and `image_input` from the widescreen manifest entry (`role="scene"`) and submits them to kie.ai with only `aspect_ratio` overridden. No re-composition via `compose_prompt`, no shot-list reads, no preamble injection.

Recommended flow:
1. `scripts/replay_mobile.py --session <id> --chunks <ids> --dry-run` — diffs widescreen vs current `scene-mobile` prompts per chunk and flags drift.
2. Inspect the diff. Chunks that MATCH are safe to regen either way. Chunks that DIFFER should be replayed, not re-derived.
3. Run for real with the same `--chunks` list and an `--aspect` override (typical: `--aspect 1:1` if the mobile deliverable will be cropped to 4:5 post-hoc).

Prefer replay when:
- The widescreen generation is known-good (scene was shipped or reviewed).
- We want byte-faithful reproduction at a new aspect.
- The shot-list has been touched since the widescreen was made.

Prefer re-derivation (`batch_scenes.py --mobile-variant`) when:
- The scene is being regenerated *because* the current shot-list diverges intentionally (audit flagged it, user edited a chunk).
- The widescreen manifest entry is missing or the image_input URL is dead.

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
- `mobile_aspect` — string. Default: `9:16`. Allowed: `9:16` (full-frame portrait), `1:1` (square letterboxed inside the 1080×1920 mobile canvas). Declared at Stage 0 because the choice affects scene composition (1:1 preserves more horizontal layouts; 9:16 accepts more aggressive vertical reframing), the mobile-crop comprehension audit's expectations, and how thumbnails should be staged. Late-binding aspect at mobile-export time means scenes get composed for one aspect and cropped to a different one, breaking the audit. Pick once at Stage 0; pick holistically — the mobile aspect, the widescreen aspect, and the thumbnail aspect should be considered together (e.g. a 9:16 thumbnail constrains the mobile choice toward 9:16).
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

**Current default (as of 2026-04-23):** `gpt-image-2-text-to-image`. When a chunk has `references: [...]`, `kie_client.py` auto-swaps to `gpt-image-2-image-to-image` (the same family, `input_urls` field). Treat the pair as one logical model.

Known working models are listed in VISUALS.md — Kie Provider Spec. The default can be overridden per-session by setting `preferred_model` in `session.json`, or per-call via `--model` on CLI scripts. All other models (`nano-banana-2`, `nano-banana-pro`, `seedream/5-lite-text-to-image`, `seedream/5-lite-image-to-image`, `wan 2.7 image`) remain fully supported.

#### Budget Rule

`ai_budget` is the hard ceiling on **number of image generations** (count, not dollars) allowed for the session.

- Count every successful generation against the budget.
- Do not count failures or cache hits.
- When the budget is exhausted, the pipeline must stop and require explicit config change before continuing.

Approximate dollar-cost translation (for planning): at nano-banana-2 1K resolution, roughly $0.05-0.08 per generation as of 2026-04. A 60-gen session runs ~$3-5 at nano-banana rates. GPT Image 2 pricing has not been calibrated in this repo — verify with the first call's credit burn before a full batch.

**Soft dollar cap: ~$3 per video.** Recommended default for a single dev-log-style session. Pick the integer `ai_budget` that lands at or below $3 given the model you've chosen. Harder-to-generate work (larger resolutions, more pricey models, heavy regen needed) will push higher — name the expected overage in chat before starting if the session needs it.

The per-project dollar cap is a user/project decision; the $3 soft cap is a recommended default, not a hard rule. Set `ai_budget` to the generation count that fits your dollar target, and rerun the math when kie.ai pricing changes. Do not confuse the integer value of `ai_budget` with dollars — the field counts generations, not money.

#### Example

```json
{
  "session_id": "example-session-001",
  "ai_budget": 40,
  "preferred_model": "gpt-image-2-text-to-image",
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

**A.1 mobile overlay adjustments:** the `Overlays` column's `width` is normalized to widescreen canvas (1920-px). When the mobile export chain (A.1) composites these on the 1080-px mobile canvas, it multiplies `width` by 1.8× (capped at 0.9) — compensates for the tall 4:5 mobile canvas making normalized widths feel visually smaller. Position (x, y) is NOT scaled. SVG overlay sources must be rasterized via `rsvg-convert` before compositing (ffmpeg has no SVG decoder). See SHIPPING.md § Mobile layout conventions + § SVG overlay rasterization.

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

Pluralist field — used for three distinct kinds of justification, all one-line:

1. **Broll context** (original use) — when `Image Source` is `broll` or `broll_image`. One sentence naming the context mechanism that makes this broll obvious to a cold viewer within 2 seconds. One of: spoken setup, visual continuity, recognition, topical match, on-broll label, callback. Empty or "none" → validator rejects. See STORY.md § Part 2 "Broll requires obvious viewer context."
2. **Illustration-over-broll** — when the Concrete-reference check matched a real artifact but the cell stayed `generated`. One sentence explaining why (e.g. layman-legibility, beat requires visual language that real artifact can't carry, abstract schematic). See rules.md § Non-Negotiable System Defaults.
3. **Illustration-over-reference** — when a recurring character/object appears but the chunk has no `references` entry. One sentence explaining why (e.g. one-off cameo, intentional drift, stylized variant). See rules.md § Non-Negotiable System Defaults.

Broll context (case 1) uses the six named mechanisms above. Cases 2 and 3 are free-text justifications — no enum. The validator only requires *presence* of the field for cases 2 and 3; quality of the justification is agent/human judgment.

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

#### Mobile-Export Fields (optional, populated by audit)

These fields support the optional post-render mobile-export chain (Process A.1 — mobile variants derived from the widescreen master). Populated automatically during `audit_scenes.py`, which runs on every session regardless of whether mobile export is ever invoked, so that if a user later decides to produce mobile variants the crop-safety analysis is already on disk.

A mobile-first authoring path (Process B — sessions composed natively at 9:16) is a separate pipeline tracked in ROADMAP.md and does not use these fields.

##### `mobile_focal` (optional)
Zone from the Camera Target vocabulary (§ Camera Target) indicating where the focal content lives for a 9:16 center-crop of this chunk. Default `center`. Audit may suggest a non-center value when the focal subject or declared `on_screen_text` would fall outside a center-crop; authors may override the audit's suggestion.

##### `mobile_unsafe` (optional, audit-populated)
Boolean. Audit sets `true` when a 9:16 center-crop at the chunk's `mobile_focal` would lose the focal subject or any declared `on_screen_text`. Authors do not hand-set this field; they regenerate the chunk via `generate_scene.py --mobile-variant` and the audit re-evaluates.

##### `mobile_image_path` (optional)
Path to a portrait-native regenerated scene (typically `source/generated-assets/scenes/<chunk-id>-mobile.png`). Populated after `generate_scene.py --mobile-variant` runs on a `mobile_unsafe: true` chunk. Falls back to `image_path` when absent.

##### `mobile_overlays` (optional)
Overlay[] array with 9:16 coordinates, overriding the widescreen overlay positions for mobile export. Omit to inherit widescreen overlays unchanged (coordinates will be remapped by the crop logic, which may or may not land the overlay correctly — override explicitly when the inherited position is wrong).

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
