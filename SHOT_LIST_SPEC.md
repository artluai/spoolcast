# Shot List Specification

## Purpose

This file defines what the shot list is, which fields it must contain, what each field means, and how those fields are used downstream.

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

## Field Meanings

### `#`
Optional ordinal index.
Used only for human reference.

### `Chapter`
Human-readable chapter grouping.
Used for grouping shots into sections.

### `Shot`
Required unique shot/beat identifier.

Format expectation:
- short stable id
- usually includes chapter prefix and shot sequence

Examples:
- `01A`
- `02F`

Used by:
- asset manifests
- review board
- preview-data generation
- render debugging

### `Start`
Expected start time of the beat in the current edit plan.

Used by:
- review board display
- human checking

### `End`
Expected end time of the beat in the current edit plan.

Used by:
- review board display
- human checking

### `Duration`
Beat duration.

Used by:
- shot planning
- preview-data timing allocation

Format:
- seconds string such as `4.0s`
- or another deterministic duration format that downstream tools know how to parse

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

### `Pause After`
Optional pause or spacing note after the beat.

Used by:
- pacing logic
- voiceover planning

### `Beat`
Required concise visual/narrative beat description.

This should explain what the beat is doing on screen.

Used by:
- review board
- planning
- debugging visual intent

### `Background Visual`
Required current visual for the beat.

This is the primary visual field in the system.

Allowed contents:
- direct media URL
- hyperlink formula
- short descriptive label for a reused/known background
- local file URL if appropriate

In the current system:
- this field is the visual driver
- this is what the review board should show
- this is what the preview/render pipeline should use

### `Movement`
Required shot-motion description.

This describes how the beat should feel visually.

Examples:
- `Slow push`
- `Static`
- `Lateral pan`
- `Background changes to a tighter proof image`

Used by:
- render interpretation
- motion mapping

### `Interaction`
Required explanation of what the visual change is doing narratively.

This answers:
- why this beat changes
- what the audience should feel or understand

Used by:
- render interpretation
- planning validation

### `Extras / Notes`
Optional human notes.

Use for:
- extra clarification
- optional ideas
- warnings

Do not rely on this field for core required behavior if a proper field exists.

### `Camera`
Required camera behavior note.

Examples:
- `Slow push`
- `Static`
- `Lateral pan`

Used by:
- render motion mapping

Avoid vague decorative instructions.

### `Tone Job`
Required description of what kind of visual source should be used.

Examples:
- `stock ad-collage montage`
- `brain heatmap / MRI / lab background`
- `official product explainer background`

Used by:
- sourcing
- review sanity checks

### `Asset To Find`
Optional sourcing to-do field.

Use when the background visual is not yet resolved.

### `Priority`
Optional urgency/need field.

Use when sourcing or production needs prioritization.

## Required Fields For A Valid Beat

At minimum, a beat should have:
- `Shot`
- `Duration`
- `Script / Narration`
- `Beat`
- `Background Visual`
- `Movement`
- `Interaction`
- `Camera`
- `Tone Job`

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

## What The Shot List Must Not Do

The shot list must not:
- depend on hidden agent memory
- assume a renderer will improvise layouts
- preserve removed columns from the old two-layer model

## Validation Rules

The shot list fails validation if:
- required fields are blank
- removed legacy columns are still present
- two downstream artifacts contradict the shot list
- background intent is ambiguous enough that the renderer would need to guess
