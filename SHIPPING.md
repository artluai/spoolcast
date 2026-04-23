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
- [Part 3 — Caption Styling (shared reference)](#part-3--caption-styling-shared-reference)
  - [Prerequisites](#prerequisites)
  - [Caption style (burned-in)](#caption-style-burned-in)
  - [Cue stripping for burn-in](#cue-stripping-for-burn-in)
- [Part 4 — Mobile Export from Widescreen (A.1, optional)](#part-4--mobile-export-from-widescreen-a1-optional)
  - [When this applies](#when-this-applies)
  - [Platform duration](#platform-duration)
  - [Split mode + part badge](#split-mode--part-badge)
  - [Mobile thumbnail](#mobile-thumbnail)

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

##### Copy principle: hit the psyche, not describe the topic

Every title, description, and thumbnail caption should pull on a core human drive — not report what the video contains. "A video about X" is a topic description; nobody clicks a topic description. Copy lands when the reader's brain registers an unmet want *before* it registers a subject.

The author's job is to find the specific drive that fits the specific content, then commit to it. There is no fixed menu of drives to pick from — the human psyche is bigger than any list would cover. What follows are examples that have worked, not an exhaustive catalog. If none of them fit, the answer is to find a new lever — not to force-fit the content into one of these.

Examples that have landed:

- **Cheat, not lesson.** Hand the reader a shortcut to knowledge someone else earned the hard way. "How I stopped", "what N rejected takes taught me", "the one setting that fixed." Signals "I went through this so you don't have to." *Test: does it read "I feel that AND this person figured out a shortcut I don't have"?*
- **Hidden mechanism.** Imply the reader's current model is incomplete in a specific way. "What's actually happening when X", "the real reason Y happens." *Test: does it feel like lifting a curtain?*
- **Private frustration named.** Put words to a pain the reader has felt but couldn't articulate — "silently breaking rules", "quietly dropping context." The validation alone drives the click. *Test: does the reader say "YES, that's exactly it" before finishing the title?*
- **Expensive mistake, free lesson.** Someone else paid the cost; the reader gets the insight free. "I lost $X because I did Y." *Test: does the title imply real pain the author paid for?*

Don't try to hit several at once — levers interfere. Pick the one strongest for this specific content and commit. And don't start from the example list above — start from the content, find the drive, then check whether an existing example fits or a new one is needed.

Anti-patterns — copy that describes the topic instead of pulling on a drive:
- "How to..." — tutorial framing, no earned-insight feeling
- "Best practices for X" — academic consensus, no pain, no drive
- "A guide to X" — instruction manual, no human lever
- "Why AI is broken" — analysis with no fix signal
- "The AI problem nobody's talking about" — vague, names no specific pain
- "How X actually works" — sounds like a lecture unless it signals contrarian mechanism

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

**Thumbnail dimensions: exactly 1920×1080.** YouTube expects 16:9 thumbnails and letterboxes anything that deviates — including near-16:9 outputs like kie.ai's 1376×768 (which is 1.7917:1, subtly wider than 1.7778:1). The letterbox shows up as a thin black bar at the top or bottom of the thumbnail in the channel grid and under the player.

After generating a thumbnail, always rescale to 1920×1080 before uploading:

```bash
ffmpeg -y -i thumbnail.png -vf "scale=1920:1080:flags=lanczos" thumbnail-1920x1080.png
```

A direct scale (not preserving aspect via padding) is correct here — kie.ai outputs are close enough to 16:9 that the 0.5-1% horizontal stretch is imperceptible, and any pad-to-fit approach reintroduces the black bars we're trying to eliminate.

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
6. Generate captions via `generate_srt.py` — both narration AND on-screen
   text are included (see Captions rule below)

#### Captions (SRT) must include on-screen text

The caption file ships both **narration** and **on-screen text** as cues. Narration alone isn't enough — a large share of YouTube viewers watch with sound off (mobile, autoplay, work-safe), and any text rendered inside the video's frames (rule cards, labels, stamps, titles) is invisible to them unless the caption includes it.

Implementation (`generate_srt.py`): narration cues come from beat-level narration text; on-screen cues come from each chunk's `on_screen_text` field and span the chunk's full duration, bracketed as `[on-screen: …]` so a reader distinguishes them from spoken dialogue.

This pairs with STORY.md § On-screen text read-time. The declared `on_screen_text` drives three things: the validator (read-time math), the scene generator (literal-text rendering), and the caption file (on-screen-text cues). One source of truth, three consumers.

Post-processing note: if the shipped video is sped up to a non-1.0x rate after Remotion renders (e.g. 1.15x), produce a matching rescaled SRT (timestamps divided by the rate). Both files ship — the 1.0x master SRT is an archive; the rate-matched SRT is what gets uploaded alongside the final video.

**Caption density cap — don't overpopulate with text.** The on-screen-text cues are for the sound-off viewer, not a transcript of every legible pixel. When a chunk's `on_screen_text` is short (a stamp, a label, a title card), include it verbatim. When it's long (a dense rules.md card with 30+ words + headings + bullets), prefer a short blurb over the full dump — something like `[on-screen: rules.md card showing the three-option protocol]` instead of the full card verbatim. Two failure modes the cap prevents: (a) captions filling the whole frame and covering the actual visual the viewer is trying to watch, (b) reading speed mismatches where the caption has more words than the text it's describing has time to be read. Rule of thumb: if the `[on-screen: ...]` cue exceeds ~15 words, compress to a blurb.

#### Pre-upload checklist

Before uploading to YouTube, every shipped video must have:

1. **Final video at the intended playback rate** (1.15x post-processed if applicable, 1.0x otherwise). Confirm by checking the mp4's duration against the expected.
2. **Thumbnail rescaled to exactly 1920×1080** (see Thumbnail dimensions above). `ffprobe` the file to verify dimensions before upload, not after.
3. **SRT matching the shipped video's playback rate.** If you upload the 1.15x final, upload the 1.15x SRT — never the 1.0x master SRT against a 1.15x video. Timestamp drift compounds across the video.
4. **Chapter timestamps in the description at the shipped rate.** Same trap as SRT — chapter marks computed from a 1.0x preview-data must be divided by the playback rate before pasting into the description. A video uploaded at 1.15x with 1.0x chapter timestamps will have the chapters drift further off-sync toward the end.
5. **Title + description + tags drafted per the Copy principle** (hit the psyche, not describe the topic).

Verify all five before publish. A mismatched rate on any of (1), (3), (4) is the class of failure most likely to slip through — catch it at the checklist stage, not after viewers flag it.

#### What this prevents

A previous session generated a title and thumbnail concept based on
chunk titles + the session name, without reading the script. The
result mis-sold the video — title implied "AI scores ads" when the
actual finding was "AI's score and market score disagreed". The user
caught it; the rule above is the systemic fix.

## Part 3 — Caption Styling (shared reference)

Applies to any burned-in caption path: widescreen-derived mobile (Part 4 below, Process A.1), mobile-first authoring (ROADMAP.md Process B) when it lands, any future subtitle-burn use case. Kept as a standalone reference so both paths consume the same atoms without copy-paste drift.

### Prerequisites

- **ffmpeg with libass.** The default homebrew ffmpeg formula does NOT include libass — the `subtitles` filter will be missing and every burn call will fail with *"No such filter: 'subtitles'"*. Install the libass-enabled build via the `homebrew-ffmpeg` tap:

  ```
  brew tap homebrew-ffmpeg/ffmpeg
  brew install homebrew-ffmpeg/ffmpeg/ffmpeg
  ```

  Verify: `ffmpeg -filters 2>&1 | grep subtitles` must return a match. If it doesn't, the tap wasn't used.

- **Caveat-Bold.ttf.** Bundled at `spoolcast/scripts/assets/fonts/Caveat-Bold.ttf`. Loaded by libass via `fontsdir=` — do NOT rely on system font resolution. Re-fetch from the fontsource CDN if missing: `https://cdn.jsdelivr.net/fontsource/fonts/caveat@latest/latin-700-normal.ttf`.

### Caption style (burned-in)

| Field | Value | Note |
|---|---|---|
| Font | Caveat Bold | matches the bumper house font |
| Fontsize | 56 | libass `Fontsize=56` |
| Primary colour | white | `PrimaryColour=&H00FFFFFF` |
| Outline colour | black | `OutlineColour=&H00000000` |
| Outline | 4 px | readable over any illustrated background |
| Shadow | 0 | no drop shadow; keeps the mark clean |
| Alignment | bottom-center | ASS `Alignment=2` (numpad convention) |
| MarginV | 80 for 1920×1080 widescreen; 250 for 1080×1920 portrait | libass interprets MarginV as distance from the alignment anchor — see `scripts/burn_captions.py` for the known-good defaults per aspect |
| Line length | max ~32 chars/line, 2 lines max | libass auto-wraps at word boundaries only when `WrapStyle=0` is set in the ASS Script Info. WrapStyle=2 disables word wrap entirely and long cues get clipped at the frame edge (caused visible caption loss like "enough to discover" → "ugh to discover" on our first mobile test). Always use `WrapStyle=0` for burned-in captions. |
| Case | sentence case | ALL CAPS reads wrong against the quiet spoolcast tone |
| Punctuation | keep commas + periods | natural narration punctuation; no emoji |

### Cue stripping for burn-in

The canonical SRT includes both narration cues and `[on-screen: …]` bracketed cues (SHIPPING.md § Captions). For burned-in captions, strip the bracketed cues — the frame already shows the on-screen text and repeating it in captions is redundant and clutters the thumb zone:

```
scripts/.venv/bin/python scripts/generate_srt.py \
    --session <id> \
    --exclude-onscreen-cues \
    --out <working-dir>/<id>-burn.srt
```

`scripts/burn_captions.py` invokes this automatically when no `--srt` override is provided.

## Part 4 — Mobile Export from Widescreen (A.1, optional)

### When this applies

When the user wants Reels / TikTok / Shorts variants *derived from* a shipped 16:9 video. Skipped entirely for YouTube-only videos, and for sessions authored mobile-first (ROADMAP.md Process B, which has its own chain).

Consumes caption styling, font bundle, and libass prereq from § Part 3. The rest of this Part covers the A.1-specific bits: pipeline separation, output location, duration caps, split-into-parts, part badge, mobile thumbnail, overlay handling.

### A (widescreen) vs A.1 (mobile) — separate pipelines, shared atoms

| | A (widescreen) | A.1 (mobile) |
|---|---|---|
| Canvas | 1920×1080 | 1080×1920 (4:5 content centered) |
| Renderer | Remotion (headless browser) | ffmpeg stitcher |
| Scene source | `scenes/<chunk>.png` | `scenes/mobile/<chunk>-mobile.png` |
| Bumper rendering | Remotion live-render (ROADMAP #5) | ffmpeg `drawtext` (A.1 temporary path) |
| SVG overlay | Browser-native | `rsvg-convert` → PNG → ffmpeg overlay |
| Meme / reuse composition | Remotion | ffmpeg overlay on parent mobile PNG |
| Playback rate | 1.15× post-process from 1.0× | 1.15× inherited from A |
| Captions | Separate SRT shipped alongside | Burned into video via libass |
| Watermark | None (clean video) | Bottom-bar, fixed position |
| Output | `renders/<session>-1.0x.mp4` + `-1.15x.mp4` | `renders/mobile/<session>-mobile-*.mp4` |

**Shared atoms** (§ Part 3 Caption Styling): Caveat font bundle, Montserrat Black bundle, JetBrains Mono bundle, Comic Neue Bold bundle, libass prereq, WrapStyle=0, pad-color=black gotcha.

**Separation principle:** A.1 has its own code path. Do not shim widescreen logic into A.1. When an A.1 path looks like "extract from the widescreen master and scale," that's a smell — check for a mobile-native source first (scene PNG, parent mobile PNG, shot-list `image_path`, drawtext live-render) before falling back.

### Output location

A.1 deliverables land under a `mobile/` subdirectory of `renders/` — keeps them conceptually in the session's renders but isolated from the A (widescreen) outputs:

```
sessions/<id>/
  renders/
    <id>-1.0x.mp4                      ← widescreen master (A, unchanged)
    <id>-1.0x.srt                      ← widescreen SRT (A, unchanged)
    mobile/
      <id>-1.0x-mobile-9x16.mp4        ← A.1 mobile export
      <id>-1.0x-mobile-9x16-pt1of3.mp4 ← split parts (when --split-duration is used)
      <id>-1.0x-mobile-thumb-9x16.png  ← A.1 mobile thumbnail
  working/
    <id>-1.0x-mobile-9x16.ass          ← intermediate burn-ASS, stays in working/
    <id>-1.0x-burn.srt                 ← intermediate burn-SRT, stays in working/
```

Intermediate ASS / SRT files stay under `working/` because they're pipeline byproducts, not deliverables.

### Platform duration

| Platform | Technical cap | Algorithm sweet spot |
|---|---|---|
| Instagram Reels | 20 min | ≤3 min for non-follower reach; ideal ≤90 s |
| TikTok | 10 min | ≤60 s favored |
| YouTube Shorts | 60 s (hard) | — |

A video over a platform's preferred cap uploads fine but won't get pushed to non-followers. For source videos ≥60 s targeting TikTok/Shorts, use `export_mobile.py --split-duration 60` to produce multi-part exports.

### Split mode + part badge

- `--split-duration 60` cuts on chunk boundaries — never mid-sentence.
- Output files: `renders/<session>-mobile-9x16-pt1of3.mp4`, `-pt2of3.mp4`, `-pt3of3.mp4`.
- Every non-final part ends with a ~1 s "to be continued…" card (Caveat Bold, clean background) before hard cut. Final part just ends.
- A "1/3" pill badge (Caveat Bold, top-right corner, white on subtle dark outline) burns into both the video and the mobile thumbnail for that part. The badge uses the same libass style atoms as Part 3 captions.

### Per-part SRT upload files (A.1)

In addition to burning captions into the video, each mobile part gets its own SRT file for upload as the platform's accessibility caption layer.

- **Path:** `renders/mobile/<session>-mobile-pt<n>of<total>.srt`
- **Content:** narration-only cues (no `[on-screen:]` bracketed cues — matches what's burned into the part's MP4).
- **Time range:** windowed to the part's shipped-rate time range. Timestamps are rebased so each part's SRT starts at `00:00:00,000` and ends at the part's duration.
- **Source:** derive from the session's shipped-rate SRT (e.g. `renders/<session>-1.15x.srt` if shipped at 1.15×), stripping `[on-screen:]` cues and windowing to the part's range.
- **Use:** upload alongside the corresponding `pt<n>of<total>.mp4` to TikTok / Reels / Shorts. The burned captions handle the visual display; the uploaded SRT powers accessibility features (screen readers, auto-caption toggles, language detection).

### Pre-upload checklist (A.1)

Before publishing any mobile part:

1. **Video**: 1080×1920, duration ≤ platform cap (computed at shipped rate), libass burn has no font-fallback warnings.
2. **Captions**: burned in Montserrat Black, top-anchored at the designated y, WrapStyle=0 active, no clipping at frame edges.
3. **Watermark**: `artlu.ai` bottom-left, `made by spoolcast` bottom-right present on every frame.
4. **Part badge**: `part N of M` on top black bar, centered.
5. **SRT**: per-part file exists, duration matches the MP4, narration-only (no `[on-screen:]` cues).
6. **Thumbnail**: 1080×1920 full-screen, title + part indicator baked in, no letterbox bars.
7. **Playback rate**: MP4 duration = widescreen master's duration / shipped-rate × (part fraction). If off by more than 1%, rate parity broke somewhere.

A mismatch on any of (1), (5), (7) is the class of failure most likely to slip through — catch at this checklist stage, not after viewers flag it.

### Pipeline script location (A.1)

- **Production path (planned):** `scripts/mobile_export.py` — replaces the current test stitcher. Uses `scripts/caption_assets.py` for ASS generation, `scripts/replay_mobile.py` for chunk regens at new aspects, `scripts/audit_mobile_crops.py` for legibility audits.
- **Current state:** `/tmp/build_mobile_test.py` is a session-specific test harness with hardcoded rate and paths. Graduating it to `scripts/mobile_export.py` means parameterizing session id, auto-detecting shipped rate, and wiring into the full Post-Stage 8 chain (PIPELINE.md § Post-Stage 8).
- **Shared helpers already at scripts/:** `caption_assets.py`, `replay_mobile.py`, `audit_mobile_crops.py`, `burn_captions.py`. Do NOT duplicate logic from these into the stitcher — import and reuse.

### Mobile thumbnail (A.1)

Separate artifact from the video. Key differences from widescreen thumbnail:

- **Full-screen 1080×1920** (9:16) — unlike the video which uses 1080×1920 canvas with 4:5 content + letterbox bars, the thumbnail has NO bars. Covers the entire phone preview area in social feeds.
- **Per-part** when the mobile export is split. Split into 3 parts → 3 thumbnails. Each thumbnail carries its part's visual identity.
- **Title + part indicator baked in.** Unlike the widescreen thumbnail (prompt-only, no text overlay), the mobile thumbnail composites BOTH the video's title and a part indicator onto the base image:
  - **Title** — the video's promotional title. Caveat Bold, large (≈120–160 px at 1080-wide canvas). Positioned upper or lower third depending on base image content.
  - **Part indicator** — e.g. `PART 1 OF 2`. Montserrat Black, smaller (≈50–70 px). Positioned above OR below the title — consistent placement per session across all parts.
- **Base image** — either (a) a kie.ai-generated 9:16 thumbnail (prompt-only, matching widescreen convention) or (b) a representative scene scaled-to-cover 9:16. Option (a) is preferred when the video has a distinct cover concept; option (b) is a stopgap using an existing scene asset.
- **File naming:** `renders/mobile/<session>-mobile-thumb-pt1of2.png`, `-pt2of2.png`, etc. One file per part.

A session that ships N mobile parts publishes N mobile thumbnails — one uploaded per TikTok / Reels / Shorts post.

### Mobile is a separate pipeline from widescreen

Mobile export (A.1) and widescreen export (A) are **separate pipelines**, not a shared one with mobile as a special case. Do not shim widescreen logic into mobile paths. A.1 has its own scene assets (`scenes/mobile/`), its own canvas (1080×1920 with 4:5 content), its own caption geometry, its own bumper rendering, its own meme handling.

When extending A.1, write A.1-native code. Do not default to "extract from the widescreen master and scale." Extracting from widescreen is a fallback only for pure external broll where no mobile-native source exists — everything else (generated scenes, bumpers, memes, reuse chunks) should resolve to a mobile-native asset. Silently reaching for widescreen is how a mobile export ends up looking like a shrunk widescreen.

### Playback rate parity with widescreen

Mobile export plays at the same rate as the shipped widescreen master. **The rate varies per session** — common values are 1.0×, 1.1×, 1.15×, 1.2×. There is no universal mobile rate; read it from session metadata (or infer from the shipped master's duration ÷ the 1.0× archive's duration).

Whatever the shipped rate, all three must match: audio (from the rate-matched master), video (concat at 1.0× then `setpts=PTS/rate`), and captions (rate-matched SRT). Using the 1.0× SRT against a 1.15× master — or any combination — drifts narration vs captions.

### Mobile layout conventions (A.1 only)

Apply to mobile exports only. Widescreen (A) outputs are unaffected.

- **Canvas** 1080×1920; 4:5 content area (1080×1350) centered vertically; 285-px black letterbox bars top and bottom.
- **Caption anchor (conditional)** — caption alignment depends on estimated line count after wrap:
  - **1–3 lines (the common case):** top-anchored, ASS `Alignment=8`, caption top edge at y≈1660 (≈25 px gap below the content area bottom at y=1635). Multi-line captions grow DOWNWARD; the first-line position is invariant across 1-, 2-, and 3-line cues.
  - **4+ lines (rare, long cues):** bottom-anchored, ASS `Alignment=2`, caption bottom baseline at y≈1830 (≈10 px gap above the watermark top). Caption grows UPWARD into the content area, partially overlapping the video frame bottom. Accepted overlap: long cues are rare and the alternative (captions off-screen) is worse.
  - Heuristic for classification: estimate chars-per-line at ~18 at Fontsize 70 in Montserrat Black in a 1020-px caption area, divide cue text length, round up. If ≥ 4, use bottom-anchored style; else top-anchored.
- **Caption side margins** `MarginL = MarginR = 30` — captions may stretch close to the horizontal edges but not touch them. Gives the wrap algorithm plenty of width to keep sentences on fewer lines.
- **Watermark position is invariant across all mobile exports.** `artlu.ai` (JetBrains Mono) bottom-left of the bottom bar, Alignment=1. `made by spoolcast` (Comic Neue Bold) bottom-right, Alignment=3. Never moves, never resizes proportional to caption size. Treat these as fixed brand placement, not tunable parameters.
- **Part badge** (when `--split-duration` is used) top-center of the top bar, ASS `Alignment=8`, MarginV chosen so badge is centered in the 285-px top bar (≈MarginV=150 at Fontsize=60 in Montserrat Black).
- **Meme inserts** are composited on top of the chunk's 4:5 scene PNG (or the parent's 4:5 scene when `image_source=reuse`), NOT a scaled-down widescreen composite. If a chunk's widescreen frame was `meme image over scene`, the mobile frame is `meme image over 4:5 scene` — the meme stays at its authored size relative to the mobile canvas, not shrunk by the 1.78→0.80 aspect change.
- **Overlay width scaling for mobile:** overlays declared in the shot-list's `overlays` field carry widescreen-normalized widths (fraction of 1920-px canvas). On mobile, multiply the declared `width` by 1.8× before compositing, clip to 0.9 max. Rationale: the 4:5 mobile canvas has more vertical real estate than 16:9, so a normalized overlay at the same proportion feels visually smaller. The 1.8× multiplier restores perceptual weight. Positions (x, y) are NOT scaled — only width.

### SVG overlay rasterization (A.1 only)

ffmpeg has no SVG decoder. Widescreen uses Remotion's headless-browser SVG rasterization; A.1 cannot share that. For any overlay declared as SVG in the shot-list's `overlays` field, rasterize to PNG via `rsvg-convert` (from `librsvg`) before compositing:

```
rsvg-convert --width 1080 --keep-aspect-ratio --output <dest>.png <source>.svg
```

Cache the rasterized PNG under `working/` during a stitch run. Feed the PNG to ffmpeg's overlay filter.

**Dependency:** `brew install librsvg` (macOS) or equivalent. Verify with `which rsvg-convert`.

### Reuse punchline composition (A.1)

For `image_source: reuse` chunks (e.g. punchline chunks C3P/C10P/C28P that reuse a parent's scene with an overlay on top), the A.1 composition flow is:

1. Resolve the parent chunk id from the shot-list's `image_path` field (e.g. `source/generated-assets/scenes/C3.png` → parent `C3`).
2. Use `scenes/mobile/<parent>-mobile.png` as the base. If the parent has no mobile PNG yet, fall back to the parent's widescreen PNG scaled-to-fit with black pad (last resort).
3. For each overlay in the chunk's `overlays` field:
   - Resolve asset. If SVG, rasterize via `rsvg-convert` (see above).
   - Width: `overlay.width * 1080 * 1.8` (mobile overlay multiplier, clipped to 0.9 max).
   - Position: `(overlay.x * 1080, overlay.y * 1350)` anchored at the overlay's center.
   - Composite via ffmpeg `overlay` filter.
4. Scale the composited result to 1080×1350 with black pad, write the clip.

**What NOT to do:** extract the composited region from the widescreen master and scale it down. The widescreen composite is at 16:9 proportions; scaling to 4:5 shrinks the overlay and imports the "widescreen-looking" aesthetic into A.1. The overlay must be applied at A.1's native canvas.

### Broll fallback (A.1)

Pure broll chunks (`image_source: broll / external_*`) that have no mobile scene PNG and no overlay list fall back to extracting the chunk's segment from the **1.0× widescreen master** (not the 1.15×), scaled-to-fit 1080×1350 with black pad. Rationale: all other A.1 clips are built at 1.0× durations (image-loops with `-t <dur_1x>`); the final ffmpeg step applies `setpts=PTS/1.15` to speed everything up uniformly to 1.15×. Using the 1.0× master here keeps pace consistent. Using the 1.15× master would double-speed the broll segment.

This is the only acceptable widescreen-master extraction in A.1. Every other chunk source (generated scene, bumper, meme, reuse) must resolve to a mobile-native asset.

### Compositing gotcha: pad color

When scaling scene PNGs into a mobile canvas via `ffmpeg -vf "scale=...:force_original_aspect_ratio=decrease,pad=W:H:X:Y:color=..."`, the scale step can produce sub-pixel rounding (e.g. 820→1080 scale yields 1349.75 → 1349 rendered height instead of the 1350 target). The pad then fills the 1-pixel gap. If `color=white`, a visible white hairline fringe shows up where the scaled content meets the pad.

Fix: set `color=black` on the inner pad so any sub-pixel fringe blends with the outer 9:16 letterbox bars (which are also black). Applies to any compositing step that stacks scale + pad. Noticed on our first mobile test as a 1px white border at the content-bar boundary.
