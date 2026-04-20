# Shipping

End-of-pipeline: review and publish.

## Table of Contents

- [Part 1 — Review Board](#part-1--review-board)
  - [Purpose](#purpose)
  - [Canonical Output Location](#canonical-output-location)
  - [Required Inputs](#required-inputs)
  - [Required Content Per Chunk](#required-content-per-chunk)
  - [Global Review Rule](#global-review-rule)
  - [Layout Rules](#layout-rules)
  - [Visual Rules](#visual-rules)
  - [Asset Display Rules](#asset-display-rules)
  - [Alternate Mode Display](#alternate-mode-display)
  - [Review Board HTML Contract](#review-board-html-contract)
  - [Build Contract](#build-contract)
  - [Review Board Validation Rules](#review-board-validation-rules)
  - [Regeneration Rule](#regeneration-rule)
  - [Human Review Goal](#human-review-goal)
- [Part 2 — Publishing](#part-2--publishing)
  - [The core-message rule (READ FIRST)](#the-core-message-rule-read-first)
  - [The script-first rule (CRITICAL)](#the-script-first-rule-critical)
  - [The "actual hook" test](#the-actual-hook-test)
  - [Title structure](#title-structure)
  - [Thumbnail concept](#thumbnail-concept)
  - [Description structure](#description-structure)
  - [Workflow](#workflow)
  - [What this prevents](#what-this-prevents)

## Part 1 — Review Board

### Review Board Rules

#### Purpose

This file defines how the HTML review board should work.

The review board exists for human review.

It is the primary place to verify:
- chunk coverage
- narration alignment
- chunk-to-chunk continuity
- whether illustrations are actually visible and match intent

The review board is a proof surface.
Optimize for proof and clarity over flavor text.

#### Canonical Output Location

Write review boards to:
- `../spoolcast-content/sessions/<session-id>/review/`

Preferred filenames:
- `shot-review.html`
- `shot-review-ch1-2.html`
- `shot-review-<range>.html`

#### Required Inputs

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

#### Required Content Per Chunk

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

#### Global Review Rule

If the review board cannot visibly show an illustration for a chunk:
- that chunk is not done

#### Layout Rules

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

#### Visual Rules

The review board should reflect the current system:
- one illustration per chunk
- no second visual layer
- final-frame illustration shown, not the reveal animation

If extra visuals appear:
- either the shot list is stale
- or the board is reading stale/generated data

In either case:
- the board is wrong

#### Asset Display Rules

The board must show:
- real locally-visible illustrations from the scene manifest
- or directly renderable remote media when supported (alternate mode only)

It must not show:
- blank boxes pretending to be assets
- task IDs or URLs as if they are finished
- stale deleted illustrations
- preprocessor intermediate frames

#### Alternate Mode Display

If the session is running the alternate stock/sourced mode:
- the board may show a thumbnail still for video assets
- the board must label it clearly enough that a human knows it is video-backed

Do not:
- silently replace a video with only a still and pretend they are equivalent

#### Review Board HTML Contract

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

#### Build Contract

The builder must:

1. read the shot list
2. group rows by `Chunk`
3. resolve the current illustration for each chunk from the scene manifest
4. render one visible card per chunk with nested beat rows
5. write the HTML output

If any chunk fails illustration resolution:
- the board must show that failure clearly

#### Review Board Validation Rules

The review board fails if:
- it shows chunks that are no longer in the shot list
- it misses chunks that are in the shot list
- it shows visuals from removed legacy columns
- it relies on unresolved links instead of visible previews
- it cannot distinguish failed scenes from valid scenes
- it shows the reveal sequence instead of the final illustration

#### Regeneration Rule

Any time the shot list or scene manifest changes in a way that affects visible media:
- rebuild the review board

Do not trust an old HTML file after such changes.

Before rebuild:
- overwrite or remove the old HTML file

#### Human Review Goal

The review board should let a human answer:
- what is this chunk
- what does it say across its beats
- what illustration does it use
- is that illustration actually there
- does the sequence make sense

If the board cannot answer those questions quickly:
- it is not good enough

## Part 2 — Publishing

### Publishing Rules

How to make titles, descriptions, and thumbnails that actually match
what a video is about — not what the chunks/scenes/beat-descriptions
imply.

#### The core-message rule (READ FIRST)

Before anything else, know the **core message** — the one thing the
viewer must come away with from the video. This is declared in the
source analysis at Stage 1 (see `STORY.md` §3 Job E).
If you are generating publishing artifacts without a declared core
message, stop and surface that gap before continuing.

The publishing artifacts — title, thumbnail, description — are **the
core message expressed in the most attention-grabbing way that is
honest to the script.** Not a summary. Not a teaser. The core message,
sharpened into something someone will click on.

The tension: core messages are usually abstract. Attention-grabbing
titles are concrete and specific. The craft is finding the concrete,
specific expression of the abstract core message that pulls the viewer
in — without lying about what the video is.

If the title is about a topic other than the core message, the title
is wrong. If the thumbnail visualizes a scene that isn't the core
message, the thumbnail is wrong. If the description's first line
isn't a sharpened version of the core message, the description is
wrong.

The rest of this document — the script-first rule, the actual-hook
test, title and thumbnail patterns — is a toolkit for finding that
concrete expression.

#### The script-first rule (CRITICAL)

**Before generating any title, description, or thumbnail concept,
READ the full voiceover narration end-to-end.** Do NOT infer from:

- chunk titles / scene_title fields
- beat_description fields (those are visual scaffolding, not narrative)
- the project name or session id
- chapter timestamps alone

Read the actual sentences the narrator speaks. The script is in either:

1. `sessions/<id>/script/voiceover.md` (preferred location, may be empty)
2. Concatenated `narration` fields from `shot-list/shot-list.json`
   beats, in chunk order

The fastest way to get the script is the latter:

```bash
python3 -c "
import json
sl = json.load(open('sessions/<id>/shot-list/shot-list.json'))
for c in sl['chunks']:
    for b in c.get('beats', []):
        print(b.get('narration',''))
"
```

#### The "actual hook" test

After reading the script, identify the **actual hook**: the concrete,
specific expression of the core message that will pull a viewer in.
This is usually the surprising claim, finding, or twist the video
makes — rarely the setup or premise. The hook and the core message
aren't two different things; the hook is the core message, made
concrete and attention-grabbing.

Test the hook against these questions:

1. **Is this the question, or the answer?** Most videos are sold by
   the setup ("can AI predict X?") but the real value is the answer
   ("AI predicted A but the market said B"). Sell the answer.
2. **Is there a conflict/twist?** If the video has a "but" moment
   ("the model favored A, but the market favored B"), the title and
   thumbnail must surface that conflict. The conflict IS the click.
3. **Does the title imply something the script disproves?** If the
   script shows the AI didn't reliably pick winners but the title says
   "AI picks winning ads", you're misleading the viewer. They will
   bounce immediately and tank watch time. Be accurate.
4. **Could the title be true of a generic AI explainer?** If yes,
   too vague. Add the SPECIFIC claim from the script.

#### Title structure

Aim for under 60 characters. Pattern that usually works:

- `<specific subject> <specific finding>` — e.g. "Meta's brain-AI
  picked the wrong winning ad"
- `<personal experience> <specific result>` — e.g. "I let an AI
  predict my ad winner. It got it wrong."
- `<question that the video actually answers>` — e.g. "Can AI predict
  which ad wins? Mine couldn't."

Avoid:
- Generic "AI does X" framings
- Vague capability claims ("scores ads")
- Titles that describe the SETUP not the FINDING

#### Thumbnail concept

**Zero-prior-context rule.** Every thumbnail must communicate the hook using only what a viewer can read in the thumbnail itself. Assume the viewer has never heard of the product, the creator, the project, or anything the video references. No brand recognition. No insider knowledge. Only the image, the text, and universally-shared mental models (a laptop, a chat bubble, a receipt, a confused face).

A thumbnail that relies on the viewer knowing *"spoolcast is a pipeline"* or *"the four layers"* fails. The viewer needs to understand the PROMISE of the video in 1 second from the pixels alone.

Test: show the thumbnail to someone who has never seen the video or heard of the product. Can they state, in one sentence, what the video appears to be about? If no, the thumbnail is too internal and needs rework.

Concrete V6 failure that drove this rule: a thumbnail showing a pipeline conveyor belt with *"IMAGE → ANIMATION → VOICE → RENDER"* stations reads as meaningful to anyone inside the project. To a cold viewer it's abstract factory iconography with no promise attached. The fix: switch to a scene that communicates the outcome using universal shorthand (a builder at a laptop, a chat notification with a finished video, a surprised face) + a self-contained caption the viewer can read independently ("I DIDN'T MAKE THIS VIDEO.").

Thumbnail concept must reflect the actual hook, not the premise.

For a "model vs market" mismatch video, the concept should visualize
the **disagreement** — not just "AI thinks". Examples:

- Two side-by-side ads: AI brain pointing to one with checkmark,
  dollar sign pointing to the other with checkmark (split-screen
  conflict)
- A brain + an X over a dollar sign + a checkmark over a different
  dollar sign (the model lost, the market won)
- A character looking confused at two contradicting score sheets

For style, see `VISUALS.md` re: prompt-only style overrides for
thumbnails (typically allow ONE accent color even when scenes are
locked to monochrome).

#### Don't self-hedge in the title or thumbnail

Above-the-fold language (title, thumbnail text, first two lines of description) must lead with the **strongest accurate** claim — never the most hedged accurate claim. Hedging words that belong in the video's narration (where nuance is earned) sabotage the click when they appear on the thumbnail.

**Anti-pattern vocabulary — remove from titles and thumbnails:**

- *mostly, kind of, pretty much, basically, almost, sort of, arguably, roughly, essentially*
- *tries to, attempts to, aims to* (implies uncertain outcome → framing of failure)
- Parenthetical caveats — *"(if it works)", "(mostly)", "(sometimes)"*
- Wishy-washy verbs — *"might", "could", "may"* when the video actually demonstrates the thing

**The distinction between hedging and overclaiming:**

| | Thumbnail claim | Video shows | Verdict |
|---|---|---|---|
| **Overclaim** | "AI picks winning ads" | AI didn't pick winners | Dishonest — viewer bounces |
| **Underhedge** | "Automated video pipeline" | Pipeline is mostly automated, one human step | **Correct** — honest + clickable |
| **Self-hedge** | "Mostly automated" video pipeline | Pipeline is mostly automated | Honest but click-rejecting — weakens for no gain |

The viewer's job is to decide whether to click. A hedge on the thumbnail converts "will I learn something bold here?" into "meh, sounds lukewarm." Save the "mostly" for the beat inside the video where the one remaining manual step is the actual subject. On the thumbnail, **lead with the bold claim the video spends seven minutes earning**.

Concrete example from this session: *"$3. MOSTLY AUTOMATED."* on a thumbnail is click-rejecting — the word "mostly" tells the viewer the pitch is soft. Replace with *"$3. AUTOMATED."* or just *"AUTOMATED."* — same video, same honesty, no self-undercut.

The test: read your thumbnail text aloud with zero context. Does it sound like a strong claim someone would stop scrolling for? If it includes a hedge, it's not that. Rewrite.

#### Description structure

First 2-3 lines (above YouTube's "show more" cutoff) must contain:

1. The setup in one sentence
2. The actual finding/twist in one sentence

Then chapters (real timestamps from `preview-data.json`), then links,
then tags.

Do NOT bury the finding. Do NOT use the description to set up surprise
the viewer can already see in the title.

#### Workflow

1. Read the script (full narration concatenation)
2. Identify the actual hook (the answer, not the question)
3. Draft title, description, thumbnail concept based on hook
4. Generate thumbnail via `generate_thumbnail.py` (uses session-aware
   helper from `VISUALS.md`)
5. Pull real chapter timestamps from `preview-data.json`

#### What this prevents

A previous session generated a title and thumbnail concept based on
chunk titles + the session name, without reading the script. The
result mis-sold the video — title implied "AI scores ads" when the
actual finding was "AI's score and market score disagreed". The user
caught it; the rule above is the systemic fix.
