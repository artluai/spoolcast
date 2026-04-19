# Review Board Rules

## Purpose

This file defines how the HTML review board should work.

The review board exists for human review.

It is the primary place to verify:
- chunk coverage
- narration alignment
- chunk-to-chunk continuity
- whether illustrations are actually visible and match intent

The review board is a proof surface.
Optimize for proof and clarity over flavor text.

## Canonical Output Location

Write review boards to:
- `../spoolcast-content/sessions/<session-id>/review/`

Preferred filenames:
- `shot-review.html`
- `shot-review-ch1-2.html`
- `shot-review-<range>.html`

## Required Inputs

The review-board builder must read:
- current shot list (with `Chunk` populated)
- current session config
- current scene manifest
- current generated scene illustrations
- current local preview assets

It must not read:
- stale generated preview-data files
- deleted legacy columns
- old cached HTML as source
- preprocessor frame folders (reveal is for the renderer, not the board — show the final illustration instead)

## Required Content Per Chunk

Each chunk card must show:
- chunk id
- time range spanning all beats in the chunk
- combined duration
- the chunk's generated illustration
- the list of beats under the chunk, and for each beat:
  - shot id
  - individual time range
  - individual duration
  - script / narration line
  - beat description

## Global Review Rule

If the review board cannot visibly show an illustration for a chunk:
- that chunk is not done

## Layout Rules

The review board should be:
- image-heavy
- chunk-organized
- simple
- easy to scan

It should not be:
- design-heavy
- cluttered with prompts
- cluttered with internal implementation text
- padded with decorative copy that makes review slower
- organized as a flat per-beat list when chunks exist

## Visual Rules

The review board should reflect the current system:
- one illustration per chunk
- no second visual layer
- final-frame illustration shown, not the reveal animation

If extra visuals appear:
- either the shot list is stale
- or the board is reading stale/generated data

In either case:
- the board is wrong

## Asset Display Rules

The board must show:
- real locally-visible illustrations from the scene manifest
- or directly renderable remote media when supported (alternate mode only)

It must not show:
- blank boxes pretending to be assets
- task IDs or URLs as if they are finished
- stale deleted illustrations
- preprocessor intermediate frames

## Alternate Mode Display

If the session is running the alternate stock/sourced mode:
- the board may show a thumbnail still for video assets
- the board must label it clearly enough that a human knows it is video-backed

Do not:
- silently replace a video with only a still and pretend they are equivalent

## Review Board HTML Contract

Each chunk card must map directly to one unique `Chunk` value in the shot list.

Required data bindings per chunk card:
- `Chunk` id
- start time (min across beats in chunk)
- end time (max across beats in chunk)
- duration (sum across beats in chunk)
- illustration source (from scene manifest)

Required data bindings per nested beat row:
- `Shot`
- `Start`
- `End`
- `Duration`
- `Section Summary`
- `Script / Narration`
- `Beat`

No card may be synthesized without a source chunk.

## Build Contract

The builder must:

1. read the shot list
2. group rows by `Chunk`
3. resolve the current illustration for each chunk from the scene manifest
4. render one visible card per chunk with nested beat rows
5. write the HTML output

If any chunk fails illustration resolution:
- the board must show that failure clearly

## Review Board Validation Rules

The review board fails if:
- it shows chunks that are no longer in the shot list
- it misses chunks that are in the shot list
- it shows visuals from removed legacy columns
- it relies on unresolved links instead of visible previews
- it cannot distinguish failed scenes from valid scenes
- it shows the reveal sequence instead of the final illustration

## Regeneration Rule

Any time the shot list or scene manifest changes in a way that affects visible media:
- rebuild the review board

Do not trust an old HTML file after such changes.

Before rebuild:
- overwrite or remove the old HTML file

## Human Review Goal

The review board should let a human answer:
- what is this chunk
- what does it say across its beats
- what illustration does it use
- is that illustration actually there
- does the sequence make sense

If the board cannot answer those questions quickly:
- it is not good enough
