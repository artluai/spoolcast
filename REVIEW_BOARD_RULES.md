# Review Board Rules

## Purpose

This file defines how the HTML review board should work.

The review board exists for human review.

It is the primary place to verify:
- visual coverage
- shot timing context
- shot-to-shot continuity
- whether assets are actually visible

The review board is a proof surface.
Optimize for proof and clarity over flavor text.

## Canonical Output Location

Write review boards to:
- `../session-to-video-content/sessions/<session-id>/review/`

Preferred filenames:
- `shot-review.html`
- `shot-review-ch1-2.html`
- `shot-review-<range>.html`

## Required Inputs

The review-board builder must read:
- current shot list
- current asset manifest
- current local preview assets

It must not read:
- stale generated preview-data files
- deleted legacy columns
- old cached HTML as source

## Required Content Per Beat

Each beat row must show:
- shot id
- time range
- duration
- script
- beat description
- section summary
- actual visible background asset

## Global Review Rule

If the review board cannot visibly show an asset:
- that asset is not done

## Layout Rules

The review board should be:
- image-heavy
- simple
- easy to scan

It should not be:
- design-heavy
- cluttered with prompts
- cluttered with internal implementation text
- padded with decorative copy that makes review slower

## Visual Rules

The review board should reflect the current system:
- one background visual per beat
- no second visual layer

If extra visuals appear:
- either the source shot list is stale
- or the review board is reading stale/generated data

In either case:
- the board is wrong

## Asset Display Rules

The board must show:
- real visible previews
- local previews
- or directly renderable remote media when supported

It must not show:
- blank boxes pretending to be assets
- hidden page links as if they are finished
- stale deleted assets

## Video Display Rules

If the background asset is a video:
- the board may show a thumbnail still
- the board must label it clearly enough that a human knows it is video-backed

Do not:
- silently replace a video with only a still and pretend they are equivalent

## Review Board HTML Contract

Each beat card or row must map directly to one shot-list row.

Required data bindings:
- `Shot`
- `Start`
- `End`
- `Duration`
- `Section Summary`
- `Script / Narration`
- `Beat`
- `Background Visual`

No row may be synthesized without a source beat.

## Build Contract

The builder must:

1. read the shot list
2. resolve the current background visual for each beat
3. attach the current local preview media
4. render one visible row/card per beat
5. write the HTML output

If any beat fails media resolution:
- the board must show that failure clearly

## Review Board Validation Rules

The review board fails if:
- it shows assets that are no longer in the shot list
- it misses assets that are in the shot list
- it shows visuals from removed legacy columns
- it relies on unresolved links instead of visible previews
- it cannot distinguish failed assets from valid assets

## Regeneration Rule

Any time the shot list changes in a way that affects visible media:
- rebuild the review board

Do not trust an old HTML file after shot-list changes.

Before rebuild:
- overwrite or remove the old HTML file

## Human Review Goal

The review board should let a human answer:
- what is this beat
- what does it say
- what visual does it use
- is that visual actually there
- does the sequence make sense

If the board cannot answer those questions quickly:
- it is not good enough
