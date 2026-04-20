# Shot List Specification

## Purpose

This file defines what the shot list is, which fields it must contain, what each field means, what values are allowed, and how those fields are used downstream.

The shot list is the source of truth.

## Canonical Structure

The shot list is currently represented as a workbook/table with one row per beat or shot.

Each row should describe exactly one beat-level unit that can be:
- reviewed in the HTML board
- converted into preview data
- rendered into video

## Required Headers

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

## Overlay Spec

Per the overlay carve-out in `WORKFLOW_RULES.md`, chunks may include explicitly-specified overlays on top of the primary illustration (brand logos, official badges, cleanly-cropped screenshots).

The `Overlays` column, when present, holds a JSON array of overlay specs. Each entry is a JSON object with fields defined in `RENDER_RULES.md` (Overlay Placement Schema):

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

Every field listed in `RENDER_RULES.md` overlay schema is required per overlay (no silent defaults). If any field is missing, the render will fail loudly rather than guess.

Constraints (enforced at validation time, not render time):
- Hard cap: 3 concurrent overlays per chunk at any moment.
- Soft cap per video: ~5-10 overlay insertions total. More than that is a design smell — redesign as full-frame scenes.

Typical use: brand-name mention in narration gets the brand's logo inserted at the word's timestamp, top-right corner, ~12% canvas width, fades in and out over ~0.3s.

## Removed Columns Rule

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

## Time Format Rules

### `Start`
Accepted formats:
- `00:00`
- `00:00.0`
- `00:00.00`
- `0:00`

Meaning:
- elapsed time from chapter or sequence start

### `End`
Accepted formats:
- `00:00`
- `00:00.0`
- `00:00.00`
- `0:00`

Meaning:
- elapsed time from chapter or sequence start

### `Duration`
Accepted formats:
- `4s`
- `4.0s`
- `4.25s`

Do not use:
- bare integers like `4`
- words like `four seconds`

### `Pause After`
Accepted formats:
- blank
- `0s`
- `0.5s`
- `1.0s`

Do not use prose like:
- `small pause`
- `tiny beat`

## Field Meanings

### `#`
Optional ordinal index.
Used only for human reference.

### `Chapter`
Human-readable chapter grouping.
Used for grouping shots into sections.

Format expectation:
- `01`
- `02`
- or short stable chapter label

### `Shot`
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

### `Section Summary`
Short summary of what this beat is doing in the larger chapter.

Used by:
- review board
- planning clarity

### `Narration Segment`
Optional segmentation label for script organization.

Used by:
- script organization
- optional chapter/script grouping

### `Script / Narration`
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

#### Pronunciation Rule

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

### `Beat`
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

### `Background Visual`
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

### `Movement`
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

### `Interaction`
Required explanation of what the visual change is doing narratively.

This answers:
- why this beat changes
- what the audience should feel or understand

Use sentence form.

Good:
- `The frame shifts from ordinary ad analysis into visible overload.`
- `This background change makes the format feel more suspicious.`

### `Extras / Notes`
Optional human notes.

Use for:
- extra clarification
- optional ideas
- warnings

Do not rely on this field for core required behavior if a proper field exists.

### `Camera`
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

### `Tone Job`
Required description of what kind of visual source should be used.

Examples:
- `stock ad-collage montage`
- `brain heatmap / MRI / lab background`
- `official product explainer background`
- `generated surreal ad overload background`

Used by:
- sourcing
- review sanity checks

### `Asset To Find`
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

### `Priority`
Optional urgency/need field.

Allowed values:
- blank
- `need-stock`
- `graphic`
- `reuse`
- `nice-to-have`
- `approved`

Do not use ad hoc labels unless the system is updated to support them.

### `Chunk`
Required grouping identifier.

A chunk groups one or more adjacent shot-list rows under a single AI-generated illustration.

Format expectation:
- short stable id
- examples: `C1`, `C2`, `C3`, or descriptive labels like `C1-hook`, `C2-question`

Rules:
- beats with the same `Chunk` value share one illustration
- chunks must be contiguous in the shot list — do not skip rows and return to the same chunk later unless the narrative explicitly calls for reuse
- a chunk should pass the chunking heuristics in `WORKFLOW_RULES.md § 3. Chunking`
- if a chunk intentionally reuses a prior chunk's illustration, use the `Continuity` field (see below)

Used by:
- scene generation — one illustration per unique chunk
- preprocessor — one frame folder per unique chunk
- render — chunks are the timeline scheduling unit

### `Continuity`
Required per-chunk field declaring how this chunk relates to the previous chunk.

Allowed values:
- `standalone` — new visual world; no obligation to carry character/setting from the prior chunk
- `continues-from-prev` — same arc as the previous chunk; image must visually relate (shared character, setting, or motif)
- `callback-to-<chunk-id>` — deliberately returns to a specific earlier chunk's world

Default (blank): `standalone`.

See `WORKFLOW_RULES.md § 3. Chunking → Chunk Continuity` for how this drives generation.

### `Image Source`
Required per-chunk field declaring where the chunk's image comes from.

Allowed values:
- `generated` — AI-illustrated scene, produced by the scene-generation stage (default)
- `proof` — a real image (chart, screenshot, diagram) from the source session's artifacts; used briefly to prove reality. Style-clash with illustrated scenes is intentional.
- `reuse` — reuses the exact image from a prior chunk (used with `callback-to-<chunk-id>`)

Default (blank): `generated`.

For `proof` chunks:
- `image_path` points at the real file (usually in `source/artifacts/` or `source/fetched-assets/`)
- the scene-generation stage is skipped for this chunk — no kie.ai call
- `Beat Description` and `Full Prompt` may describe what the proof shows, but are not fed to a generator
- keep proof inserts brief (typically 2-4 seconds) — use illustrated concept scenes to carry the story, proof inserts only to prove reality

For `reuse` chunks:
- `image_path` points at an earlier chunk's generated file
- no new generation is produced

### `Camera Target` (optional)
Used when the camera frames a specific region of the chunk's illustration during a beat.

Allowed values (zone vocabulary — remaps to pixel coordinates by aspect ratio):
- `center`
- `left-third`, `right-third`
- `top-third`, `bottom-third`
- `upper-middle`, `lower-middle`
- `top-left`, `top-right`, `bottom-left`, `bottom-right`
- `top`, `bottom`, `left`, `right`

Blank = camera inherits previous position (static).

### `Camera Zoom` (optional)
Vocabulary only, no raw numbers:
- `wide` — full canvas visible (1.0x)
- `medium` — ~70% of canvas visible (1.4x)
- `tight` — ~45% of canvas visible (2.2x)
- `close` — ~30% of canvas visible (3.3x)

Blank = inherit previous zoom.

### `Camera Reason` (required when Camera Target is set)
One-sentence explanation of why the camera moves on this beat. If you can't state a reason, don't move the camera.

## Required Fields For A Valid Beat

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

## Background Rules

Every beat must have a background plan.

That background may be:
- a new background
- a reused background
- a returned background from an earlier beat
- a full-height vertical background when the source media is vertical

If two adjacent beats use the same background:
- that must be treated downstream as one continuous background run

## Reuse Rules

If a beat intentionally reuses a background:
- the shot list should make that obvious
- the downstream system should not interpret it as a brand-new visual unless the source actually changes

Preferred reuse markers:
- `same as 01B`
- `return to 02A background`
- same hyperlink/local path as prior beat

## Canonical Example Row

Example valid beat:

| Shot | Start | End | Duration | Script / Narration | Beat | Background Visual | Movement | Interaction | Camera | Tone Job | Asset To Find | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01C | 00:08.0 | 00:12.0 | 4.0s | Which means everybody is trying to make theirs work better. | ad pile becomes visibly crowded | https://example.com/ad-collage.mp4 | Background changes | The frame becomes intentionally too busy before any analysis starts. | Slow push | stock sponsored-post / banner / inbox ad collage | pexels ad collage night billboard | need-stock |

## Downstream Field Mapping

### Review board uses:
- `Shot`
- `Start`
- `End`
- `Duration`
- `Section Summary`
- `Script / Narration`
- `Beat`
- `Background Visual`

### Scene generation uses:
- `Chunk`
- `Script / Narration` (combined across the chunk's beats)
- `Beat` (combined across the chunk's beats)
- `Tone Job`
- `Background Visual` (for intent, when present)

### Asset sourcing (alternate mode) uses:
- `Background Visual`
- `Tone Job`
- `Asset To Find`
- `Priority`

### Preview-data generation uses:
- `Shot`
- `Chunk`
- `Duration`
- `Script / Narration`
- `Movement`
- `Camera`

### Render uses:
- `Shot`
- `Chunk`
- `Duration`
- `Movement`
- `Camera`

## What The Shot List Must Not Do

The shot list must not:
- depend on hidden agent memory
- assume a renderer will improvise layouts
- preserve removed columns from the old two-layer model
- use vague timing or motion language that requires guessing

## Validation Rules

The shot list fails validation if:
- required fields are blank
- removed legacy columns are still present
- two downstream artifacts contradict the shot list
- background intent is ambiguous enough that the renderer would need to guess
- any required field uses a non-supported format
