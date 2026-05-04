# Shipping

End-of-pipeline: review and publish.

Scope: review-board and A.1 mobile-export rules are `illustration-chunk-remotion` adapter rules. Publishing, captions, and platform checks are reusable only where a format adapter explicitly points here.

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

This file defines how the `illustration-chunk-remotion` HTML review board should work.

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

The review board should reflect the `illustration-chunk-remotion` system:
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

#### Thumbnail style registry

Every thumbnail prompt = registered style template + scene-specific block (subject, props, caption text). Pick from this registry or add a new entry; don't reinvent style language each session.

**`noir-debug`** — gritty black-and-white graphic novel / ink illustration. Heavy crosshatching, bold shadows, high contrast, sharp ink lines, cinematic desk lighting, dramatic noir atmosphere. Mostly pure black and white with only selective red accents. Bold distressed brush-lettering headline across the top; red brushstroke underline beneath the headline. Composition clean and thumbnail-readable, central subject, slightly ominous tone.

When using a registered style: prepend the template verbatim to the scene-specific block. Don't paraphrase — the template is the contract.

#### Hook-word series-reuse

Hook words and concepts used in the prior 2 series videos' titles or thumbnail captions are stale. Don't lean on the same angle ("lied," "AI fail," "broken," etc.) in back-to-back uploads — the viewer registers repetition as the channel running out of ideas. Swap the hook angle unless rerun is editorially correct (and named).

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

#### Publish order when mobile parts exist: widescreen first, then mobile

When a session ships both a widescreen master AND mobile parts (A.1 split), the widescreen uploads first and its URL is the source-of-truth reference. Any mobile-part caption that links back to the full video (typically Part 2's caption pointing at the widescreen) gets the URL filled in ONLY AFTER the widescreen is live.

Do NOT pre-fill placeholder URLs in mobile-part captions. A guess like `youtu.be/xxxxxxx` that turns out wrong ships viewers to the wrong video (or a sibling session's URL from an old tracker entry). If the mobile parts are drafted before the widescreen publishes, leave the URL slot as a literal `{{widescreen_url}}` token in the draft — substitute after publish, verify by clicking, then upload mobile.

Caught on dev-log-02: Part 2 caption drafted with the previous dev-log's URL reused as a placeholder. Would have shipped viewers from Part 2 to dev-log-01 if not caught.

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

- **Tesseract + pytesseract** (required for A.1 smart-crop). Used by `smart_crop_mobile.py` to deterministically locate text regions — overrides Qwen's text-bbox predictions, which drift spatially by 0.3–0.5 of the frame width and produce bad crops for any chunk with a speech bubble, label, or readable artifact. The code wraps `import pytesseract` in try/except (so `smart_crop` won't hard-fail without it), but without OCR it regresses to Qwen-only text localization — the exact failure mode we fixed with `text-bbox-via-OCR` this session. Install:

  ```
  brew install tesseract
  scripts/.venv/bin/pip install pytesseract
  ```

  Verify: `which tesseract` returns `/opt/homebrew/bin/tesseract` (or equivalent), and `scripts/.venv/bin/python -c "import pytesseract; print(pytesseract.get_tesseract_version())"` returns a version string.

### Caption style (burned-in, mobile A.1)

Currently burned captions only exist on mobile exports (widescreen master ships with a separate SRT, not burned). These specs are the mobile caption style.

| Field | Value | Note |
|---|---|---|
| Font | Montserrat Black | wide, heavy sans-serif — high legibility at mobile sizes |
| Fontsize | 72 | rendered at 1080×1920 canvas |
| ScaleX / ScaleY | 100 / 100 | **natural proportions — letters are NOT compressed**. Do not reduce ScaleY to fake tight line spacing; it smushes the text. Use per-line positioning (see below) instead |
| Primary colour | white | `PrimaryColour=&H00FFFFFF` |
| Outline colour | black | `OutlineColour=&H00000000` |
| Outline | 7 px | thick black stroke for high contrast against any scene |
| Shadow | 0 | no drop shadow |
| Case | **ALL CAPS** | narration text is uppercased before rendering. Wide caps at mobile scale read punchier than sentence-case lowercase |
| Line wrap | 31 chars / line (Python-side pre-wrap) | narrow enough to fit 1080px canvas at fontsize 72, wide enough that lines span near edge-to-edge |
| MarginL / MarginR | 10 / 10 | near-edge horizontal margin, maximizes usable width |
| Line positioning | **per-line `{\an5\pos(x,y)}` events** | each wrapped line is emitted as its own Dialogue event, anchored center at `(canvas_w/2, margin_v + i * LINE_STEP)`. Bypasses libass's default font-metric leading (which produces too-loose line gaps) |
| LINE_STEP | 45 px | baseline-to-baseline distance. Lines stack nearly touching — cap-to-cap gap is <4px |
| margin_v (first line y-top) | **9:16 full-bleed: 1300. 1:1 mobile or 16:9 mobile letterbox: 1558.** | See "Caption position by mobile aspect" below. |
| Alignment style field | 5 | Default style uses Alignment=5 (middle-center anchor), paired with inline `{\an5\pos()}` overrides |

The per-line positioning matters: libass doesn't reliably honor `LineSpacing` as a Script_Info extension across all builds, so tight line gaps via style-level metrics are unreliable. Explicit `\pos()` per line gives deterministic pixel-accurate stacking.

#### Caption position by mobile aspect

Captions land at one of two positions depending on the session's mobile aspect mode. The rule applies to mobile-canvas (1080×1920) burns only — widescreen 16:9 desktop ships a separate SRT and is not subject to this rule.

**Captions stay at one consistent position throughout a video — they do not jump per-chunk** even if individual chunks have different aspects (e.g. a 16:9 letterbox SVG chart inside an otherwise-1:1 session uses the session's caption position, not a per-chunk override).

**9:16 full-bleed mobile sessions** — `margin_v = 1300`. Captions overlay the lower portion of the content area, above the TikTok/IG/Shorts bottom-overlay UI zone (which extends to roughly y=1500–1600). Captions sit ON the image; outline keeps them legible.

**1:1 mobile or 16:9 mobile letterbox sessions** — `margin_v = 1558`. Captions live just below the image, near the top of the bottom letterbox bar:
- Content area for 1:1 ends at y=1500; for 16:9 mobile letterbox ends at y=1264. Below that is empty letterbox bar.
- Caption outline top ≈ y=1515, **15px below the 1:1 image bottom** — caption reads as part of the image's lower frame.
- Caption line stack runs y=1558 (line 1) → y=1603 (line 2) → y=1648 (line 3 if needed).
- Sits at the boundary of the platform UI overlay zone (y=1500–1600) but accepts brief overlap on the strictest platforms; gives priority to image-pairing legibility over UI-zone strictness.

**Why this margin_v:** the 15px gap between image bottom and caption-outline top makes the caption read as part of the image's lower frame, not floating in the bar. Wider gaps (25px+, 50px+) make the caption feel less integrated; this tight gap is the empirical sweet spot from pilot iteration.

**Choosing which position:** session-wide signal, not per-chunk. If the majority of a session's mobile assets are letterboxed (1:1 or 16:9 mobile), the whole session uses just-below-image bottom-bar captions. If the majority are 9:16 full-bleed mobile, the whole session uses over-content captions. Mixing positions across chunks within one video reads as inconsistent — pick one and commit.

**Why this rule exists:** pilot session was authored 16:9-native and retrofitted to A.1 with 1:1 letterbox as the dominant mobile aspect. Captions at the 9:16 default (1300) landed inside the 1:1 content area, covering visual punchlines (e.g. the question-mark circle in C13's "A vs B?" composition). Bottom-bar position keeps the comprehension-critical part of the image clean.

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

### Input precondition — A must be finished

**A.1 begins where A ends.** Its sole input is a shipped widescreen master from the A pipeline (`renders/<id>-<rate>x.mp4` plus the matching SRT, scene manifest, shot list, and per-chunk scene PNGs). Producing that master is A's job, not A.1's.

If a session lacks a shipped master — only a roughcut, a partial preview, or pre-pipeline experiment assets exist — A is incomplete. **Finish A first**, then start A.1. Do NOT treat "assemble a master from old assets so A.1 can consume it" as part of A.1; that work is closing out A.

Conversely, once a clean shipped master exists, every step from there to mobile parts is A.1 — scene mobile-cropping, stitcher, captions, chrome, splitting, thumbnails, per-part SRTs, pre-upload checklist.

The boundary test: if the artifact you're producing is reusable for the widescreen ship (a scene PNG, the master mp4, the rate-matched SRT), it belongs to A. If it only exists to make a mobile export (`scenes/mobile/`, burn-ASS, part badges, mobile thumbnails), it belongs to A.1.

### A (widescreen) vs A.1 (mobile) — separate pipelines, shared atoms

| | A (widescreen) | A.1 (mobile) |
|---|---|---|
| Canvas | 1920×1080 | 1080×1920 mobile canvas |
| Renderer | Remotion (headless browser) | ffmpeg stitcher |
| Scene source | `scenes/<chunk>.png` | `scenes/mobile/<chunk>-mobile.png` |
| Bumper rendering | Remotion live-render | mobile-native card rendered by `mobile_export.py`, not cropped from widescreen |
| SVG overlay | Browser-native | `rsvg-convert` → PNG → ffmpeg overlay |
| Meme / reuse composition | Remotion | ffmpeg overlay on parent mobile PNG |
| Playback rate | 1.15× post-process from 1.0× | 1.15× inherited from A |
| Captions | Separate SRT shipped alongside | Burned into video via libass |
| Watermark | None (clean video) | Bottom-bar, fixed position |
| Output | `renders/<session>-1.0x.mp4` + `-1.15x.mp4` | `renders/mobile/<session>-mobile-*.mp4` |

**Shared atoms** (§ Part 3 Caption Styling): Caveat font bundle, Montserrat Black bundle, JetBrains Mono bundle, Comic Neue Bold bundle, libass prereq, WrapStyle=0, pad-color=black gotcha.

**Separation principle:** A.1 has its own code path. Do not shim widescreen logic into A.1. When an A.1 path looks like "extract from the widescreen master and scale," that's a smell — check for a mobile-native source first (scene PNG, parent mobile PNG, shot-list `image_path`, Remotion live-render for bumpers) before falling back.

### Portrait-safe composition — A.1 scope only

When a session is **planned for A.1 mobile export** (not otherwise), beat descriptions for generated scenes should be authored with portrait-safety in mind so the 16:9 → 9:16 crop doesn't break them:

- **Prefer a single focal point**, supporting elements stacked vertically (above / below) rather than horizontally (left / right).
- **Avoid side-by-side / split-panel / two-panel / virgin-vs-chad layouts** unless the beat editorially requires an explicit contrastive comparison. Split-panel layouts fundamentally don't survive a 9:16 crop — header/footer text clips at panel seams, the contrastive structure breaks when one side partially leaves frame, and per-panel readability doesn't mean the overall scene reads.
- **Avoid full-width text banners** spanning the entire frame — wrap long on-screen text into two or three stacked lines instead.
- When a split-panel IS editorially required, note it explicitly in the `beat_description` so the A.1 pipeline knows to **regenerate the chunk at 9:16 from scratch** via `replay_mobile.py` instead of attempting a center-crop.

**This rule applies ONLY to sessions planned for A.1 mobile export.** Widescreen-only videos (no mobile variant planned) keep split-panel compositions fully available — they often land harder at 16:9 and remain valid editorial choices.

### Smart-crop element resolution — A.1 scope only

**Applies only to A.1 mobile export.** `smart_crop_mobile.py` uses a two-stage pipeline: Qwen-VL identifies visual elements (characters, text, objects) + their bboxes, comprehension-importance, and face_bbox for characters. Python computes the best 9:16 crop center geometrically via subset search + progressive tolerance.

#### The alone-crop test (how Qwen picks the focal)

For each element in the scene, ask: *"If the final 9:16 crop contained ONLY this element and the viewer also heard the narration, would the scene still make sense?"* Only elements that pass this test are candidates for **focal** (the element the crop aims at). Text is never focal when a character or key object is in frame — text alone cannot anchor a scene.

Focal-selection tiebreakers when multiple elements pass the test:

- **Action scenes** (narration is "someone doing something"): the actor character is focal.
- **Handoff / exchange scenes** (narration centers on a transfer or artifact): the RECIPIENT of the action is focal, NOT the deliverer. The deliverer is interchangeable (any messenger works); the recipient is the subject of the scene.
- **Solo monologue**: the speaker is focal.
- **Pure text cards** (no characters or objects): text becomes focal.

Decorative text (book titles, poster slogans, mug inscriptions) that does not carry the current narration's meaning is importance 4+ or omitted entirely — never primary.

#### Constraints (Python's fit logic)

- **Focal element** — must be ≤10% clipped. Character faces use `face_bbox` (tight head region, provided by Qwen), NOT the full body bbox. A character's body can clip more than 10% as long as the face stays within tolerance.
- **Text** — must have a **5% padding margin** from crop edges. Text touching the edge reads visually the same as clipped text, so padding prevents visual strain. Fall-back: ≤10% clip if padding impossible given other constraints.
- **Secondary characters** — faces ≤15% clip. Can be fully dropped from frame.
- **Decorative / contextual elements** — ≤20%, drop first when space is tight.

#### Fit algorithm (subset search + progressive tolerance)

Python explores all subsets of non-focal elements, preferring larger subsets that keep text. For each candidate subset, try passes in order:

1. **Pass 1: text padding (5%) + progressive focal-face tolerance** — try focal face at 10% → 12% → 15%. Text padding takes priority over strict focal face; if text padding requires the focal face to clip up to 15%, that's acceptable. Characters remain readable at 15% face clip.
2. **Pass 2: relaxed text (≤10% clip) + focal face 10%** — fallback when no padding configuration fits.
3. **Pass 3: focal alone** — last resort when geometry makes any combination impossible.

The subset search (rather than linear drop-by-priority) is important because sometimes a specific secondary element blocks the fit, not the lowest-importance one. Example: `[focal_char, text, other_char]` fails because `other_char` conflicts with focal — but `[focal_char, text]` works. Linear drop would remove text first; subset search tries `[focal_char, text]` directly.

#### OCR override

For elements where the bbox location is anchored to visible text (any `kind: text` element, plus objects/characters whose description references text — `"sticky note labeled 'redo'"`, `"book saying X"`, etc.), the bbox from Qwen is **replaced with Tesseract OCR's detected text region**. Qwen has high spatial error on small text (reports bbox positions off by 0.3–0.5 in fractional coordinates); OCR is deterministic.

Qwen handles semantic roles (what's a character, what's a text, what's the focal). Python + OCR handle geometric positioning.

#### Tiered Qwen calls (cost optimization)

1 Qwen call by default. Escalate to median-of-3 only for chunks where:

- 2+ characters are present (spatial variance matters most in crowded scenes)
- OR Qwen reports low/medium confidence
- OR the first-pass resolver drops to focal-only (fit failure — retry to see if better bboxes unlock a fuller fit)

Typical cost: ~$0.13 per 49-chunk session. Blanket median-of-3 would be ~$0.33; blanket single-call would be ~$0.10 but unstable on complex scenes.

#### What Qwen is NEVER passed

The chunk's pre-render `beat_description` brief. It can disagree with the final render ("no character" in brief, but the model drew two characters). Qwen receives the image + narration (the audible ground-truth line) only. This pixels-as-ground-truth posture is load-bearing.

Widescreen (A) rendering is unaffected — no cropping happens there.

Caught on dev-log-02 C1 + C9: these chunks exposed every failure mode in turn — speaker-midpoint bias, bbox hallucination on text location (fixed by OCR), importance misranking between deliverer and recipient (fixed by alone-crop test), face vs body constraint confusion (fixed by face_bbox), text-edge-touching (fixed by 5% padding with progressive focal tolerance). The current algorithm resolves all of them.

Caught on dev-log-02 mobile pass: 3 chunks (C14, C21, C44) generated as split-panel wojak layouts, Qwen's mobile-crop audit under-rated two of them because it evaluated each panel in isolation and missed that the overall composition broke. The upstream fix here (portrait-safe default at Stage 2 when mobile is planned) prevents the class of breakage before it reaches audit.

### Audit-fix paths — resize-to-fit vs paid regen

When `audit_mobile_crops.py` flags a chunk as broken, pick one:

- **Resize-to-fit** (free, default for clipped-edge failures): scale the widescreen scene to fit inside the 9:16 canvas, pad with a per-chunk color sampled from the source PNG's edges (median of 8 edge blocks — 4 corners + 4 mid-edges). White-for-everything fails on broll PNGs that aren't on a white background; per-chunk sampling makes the pad blend in.

  ```bash
  scripts/.venv/bin/python scripts/mobile_pad_to_fit.py \
      --session <id> --only <chunk-ids>
  ```

- **AI regen** (paid kie.ai, ~$0.05 per chunk): `batch_scenes.py --mobile-variant --only <chunks>`. Use when the composition needs a native portrait gen — split panels, off-canvas focal subject, beat that doesn't survive a scale-down.

### Mobile-crop audit — comprehension test

`audit_mobile_crops.py` grades each cropped mobile scene against a single primary question:

> **While the viewer hears this chunk's narration, does the cropped image still communicate the message that the script / beat is trying to convey?**

If the answer is no, the chunk fails — regardless of whether any individual element looks "clipped" in isolation. Visual edge-clipping, split-panel halving, severed sequential relationships (arrow → diagram, before → after, A vs B), and lost contrastive comparisons are all the **same failure mode**: the meaning of the moment is gone.

**Inputs the audit must receive per chunk:**
- the cropped mobile PNG (post-crop, what the viewer actually sees)
- the chunk's **narration** (concatenated beat narrations — the audible ground-truth line)
- the chunk's **beat_description** (the intended visual scaffolding)
- the chunk's **on_screen_text** (declared text the scene is supposed to render)

The audit grades the image against narration + beat, not the image in isolation. A frame that looks visually intact but no longer lands the beat (e.g. an "A vs B" comparison where B got cropped to a sliver) is broken.

**Common ways comprehension fails** (not an exhaustive list — anything that breaks the script-to-image link counts):

1. **Text clipped mid-word or mid-line** so the meaning is lost. A single compact word trimmed by one letter (e.g. "DEFAULT" → "DEFAUL") is recoverable from context — not broken.
2. **Key prop partially clipped at the edge** (STOP sign, red X, labeled object, arrow tip). Background scene dressing clipping is not broken; only focal props count.
3. **Character cut off** in a way that breaks the scene (face bisected by frame edge, body truncated such that the action no longer reads).
4. **Split-frame composition where the comparison is lost** — side-by-side or before/after layouts where one panel got discarded. A cropped split-panel is NOT automatically broken if the surviving panel alone still conveys the beat. Flag only when the surviving fragment no longer communicates without its missing pair.
5. **Severed sequential / relational composition** — narration describes "X leading to Y" or "X compared with Y" but the crop cut the connection between elements, leaving them visually disconnected.
6. **Any other essential scene element visibly truncated** in a way that changes what the scene communicates relative to the narration.

**Lean toward catching real failures over avoiding flags.** A false positive costs one regen call (~$0.04). A false negative ships a chunk where the viewer doesn't understand the moment — much more expensive. When uncertain, flag.

The audit's verdict per chunk: `broken` (true/false), `broken_reason` (one sentence tying the failure to the narration / beat), `element_clipped` (what specifically broke the scene, if any), `severity` (low / medium / high — how much meaning is lost).

**Caught on pilot:** Qwen's earlier audit prompt did not receive narration, evaluated images standalone, and was anchored toward false negatives by a "lean conservative" instruction. Two chunks (C13 split-panel A vs B halved, C21 severed arrow → diagram) passed audit but visibly broke the beat. The comprehension-test framing above replaces the visual-clipping-only framing.

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
| YouTube Shorts | 3 min (hard, since Oct 2024) | ≤60 s for the Shorts shelf algorithm sweet spot; 60 s–3 min still qualifies as a Short but is pushed less aggressively |

A video over a platform's preferred cap uploads fine; it just loses non-follower algo push. For source videos ≥60 s, run `mobile_export.py --split-duration <60 or 90>` once and use the same parts on TikTok, Shorts, and Reels.

Pick `--split-duration` per editorial trade-off:
- **60s** — maximizes per-part algo push on TikTok/Shorts, more parts, more between-part drop-off.
- **90s** — fewer parts, less algo boost. Use when a 60s split would yield 5+ parts (4–5 min source).

Default: 60s. 90s is an editorial override for fewer-parts.

### Split mode + part badge

- `--split-duration 60` cuts on chunk boundaries — never mid-sentence.
- **Split boundary cannot land on a meme chunk, and cannot split a meme from its setup narration.** The split must fall AFTER the meme's full companion narration chunk, never on or immediately before a meme. Why: memes depend on the setup narration chunk to land — if a part ends with the setup line and the next part opens cold with the meme (or the meme lives at the end of Part 1 without its setup), the punchline fails. The meme + its setup must always live in the same part. When picking the split point, scan forward from the target duration for the next chunk boundary that is NOT on a meme, NOT immediately after a meme's setup narration, and NOT immediately before a meme.
- Output files: `renders/<session>-mobile-9x16-pt1of3.mp4`, `-pt2of3.mp4`, `-pt3of3.mp4`.
- Every non-final part ends with a ~1 s "to be continued…" card (Caveat Bold, clean background) before hard cut. Final part just ends.
- A "Part 1 of 3" pill badge (Caveat Bold, top-right corner, white on subtle dark outline) burns into both the video and the mobile thumbnail for that part. Always written in full ("Part 1 of 3", not "1/3") because the spelled-out form reads as familiar mobile-platform convention. The badge uses the same libass style atoms as Part 3 captions. Sized to be readable in a phone-grid feed.

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

- **Crop:** `scripts/smart_crop_mobile.py` writes `source/generated-assets/scenes/mobile/<chunk>-mobile.png` from approved widescreen scene images.
- **Audit:** `scripts/audit_mobile_crops.py` writes `working/mobile-crop-audit.json`; export is blocked until the audit reports zero broken chunks.
- **Fix flagged crops only:** `scripts/mobile_pad_to_fit.py` for free fit/pad fixes; `scripts/replay_mobile.py` for byte-faithful aspect replay; `scripts/batch_scenes.py --mobile-variant --only <chunks>` only when replay is impossible or the shot-list intentionally changed.
- **Export:** `scripts/mobile_export.py` resolves mobile assets, renders bumper cards, builds clips, muxes master audio, burns captions/watermarks, splits parts, and writes per-part SRTs.
- **Thumbnails:** `scripts/mobile_thumbnails.py` generates per-part 1080×1920 thumbnails from `working/thumbnail-prompt.md`.
- **Shared helpers:** `caption_assets.py`, `smart_crop_mobile.py`, `replay_mobile.py`, `audit_mobile_crops.py`, `burn_captions.py`. Do NOT duplicate logic from these into one-off scripts.

### Mobile thumbnail (A.1)

Separate artifact from the video. Key differences from widescreen thumbnail:

- **Full-screen 1080×1920** (9:16) — unlike the video which uses 1080×1920 canvas with 4:5 content + letterbox bars, the thumbnail has NO bars. Covers the entire phone preview area in social feeds.
- **Per-part** when the mobile export is split. Split into 3 parts → 3 thumbnails. Each thumbnail carries its part's visual identity.
- **Headline baked in (kie), part indicator composited (PIL).** Mobile reuses the widescreen prompt verbatim, so kie bakes the same headline text with the same brush-lettering treatment as the widescreen — no separate title font, no font-mismatch. PIL composites only the part indicator on top.
  - **Headline** — same text as the widescreen thumbnail (e.g. `THE BUG WAS IN MY DEBUGGER.`). Baked by kie via the widescreen prompt; PIL adds nothing for the headline.
  - **Part indicator** — e.g. `PART 1 OF 3`. Montserrat Black, ≈50–70 px. Composited via PIL just below the kie-baked headline + red brushstroke underline. Consistent placement per session across all parts.
- **Base image** — default (a) a kie.ai-generated 9:16 thumbnail using the **widescreen's prompt verbatim** with only aspect/grid-safe adaptation appended. Fallback (b) a representative scene scaled-to-cover 9:16 — use as a stopgap when kie.ai spend isn't justified.

- **Thumbnail prompt persistence.** When a widescreen thumbnail is generated, save its prompt to `sessions/<id>/working/thumbnail-prompt.md`. Mobile and any other variants read this file as the source-of-truth scene+style. Aspect and headline-handling are appended per output. Reusing the persisted prompt keeps mobile visually consistent with the widescreen and removes the temptation to invent a new scene description.
- **File naming:** `renders/mobile/<session>-mobile-thumb-pt1of2.png`, `-pt2of2.png`, etc. One file per part.
- **Grid-safe area: top ~70% of the 9:16 frame.** TikTok / Reels / Shorts grid views center-crop the thumbnail to roughly square (4:5 or 1:1). All critical content — caption, figure, part badge, key visual — must live in the upper ~1344 px of the 1920 px frame. The bottom ~30% is bonus content visible only on full-tap view. Designs that put the punchline element (struck-out text, hand-lettered tagline, key annotation) in the bottom band lose it on grid.

A session that ships N mobile parts publishes N mobile thumbnails — one uploaded per TikTok / Reels / Shorts post.

### Mobile is a separate pipeline from widescreen

Mobile export (A.1) and widescreen export (A) are **separate pipelines**, not a shared one with mobile as a special case. Do not shim widescreen logic into mobile paths. A.1 has its own scene assets (`scenes/mobile/`), its own canvas (1080×1920 with 4:5 content), its own caption geometry, its own bumper rendering, its own meme handling.

When extending A.1, write A.1-native code. Do not default to "extract from the widescreen master and scale." Extracting from widescreen is a fallback only for pure external broll where no mobile-native source exists — everything else (generated scenes, bumpers, memes, reuse chunks) should resolve to a mobile-native asset. Silently reaching for widescreen is how a mobile export ends up looking like a shrunk widescreen.

### Playback rate parity with widescreen

Mobile export plays at the same rate as the shipped widescreen master. **The rate varies per session** — common values are 1.0×, 1.1×, 1.15×, 1.2×. There is no universal mobile rate; read it from session metadata (or infer from the shipped master's duration ÷ the 1.0× archive's duration).

Whatever the shipped rate, all three must match: audio (from the rate-matched master), video (concat at 1.0× then `setpts=PTS/rate`), and captions (rate-matched SRT). Using the 1.0× SRT against a 1.15× master — or any combination — drifts narration vs captions.

### Mobile layout conventions (A.1 only)

Apply to mobile exports only. Widescreen (A) outputs are unaffected.

- **Canvas** 1080×1920 full-bleed (no letterbox bars around the content). Scene PNGs are 9:16 native (from `smart_crop_mobile.py` or regenerated at 9:16 via kie.ai) and fill the canvas.
- **Captions** — see § Caption style (burned-in, mobile A.1) for the full spec. Summary: Montserrat Black, ALL CAPS, fontsize 72, natural ScaleY, per-line `\pos()` positioned events with LINE_STEP=45 px, top of first line at `margin_v=1300`, thick 7 px outline, near-edge-to-edge horizontal margins.
- **Top-row chrome** (row 1 of the frame): a single horizontal strip at `MarginV=30` from top containing three elements on the same baseline:
  - `artlu.ai` — top-left, JetBrains Mono, Fontsize=32 (= `watermark_size`), 65 % opacity (alpha 0x59).
  - `Part N` — top-center, Montserrat Black, Fontsize=42 (= `part_badge_size`, slightly larger than watermarks for a hint of hierarchy), 65 % opacity. Only drawn when `--split-duration` is used.
  - `made by spoolcast` — top-right, Comic Neue Bold, Fontsize=32, 65 % opacity.
  - Rationale: moved from bottom to top so TikTok/IG/Shorts platform UI (caption, username, audio, share buttons) — which overlays the bottom of the frame — doesn't obscure brand/part-badge.
- **Text-only title cards letterbox instead of crop.** When a chunk is text-only (no character, no narrative object — typography as content), smart-crop cannot produce a 9:16 crop that preserves the text; the text is inherently wider than the crop window. For these chunks, scale-to-fit the widescreen source into the 1080×1920 mobile canvas with paper-color (or transparent) bars top and bottom, rather than cropping. Caught on dev-log-02 C4: a title card *"how I caught an AI lying"* was cropped at the middle and only *"I caught"* was visible on mobile. Letterboxing shows the full title at smaller scale — every word visible. `smart_crop_mobile.py` detects this case (focal element kind=text AND text bbox wider than crop + tolerance) and emits a `letterbox` signal; `mobile_export.py`'s stitcher honors it by scaling-to-fit instead of cropping.
- **Meme inserts** are composited on top of the chunk's 9:16 scene PNG (or the parent's 9:16 scene when `image_source=reuse`), NOT a scaled-down widescreen composite. If a chunk's widescreen frame was `meme image over scene`, the mobile frame is `meme image over 9:16 scene` — the meme stays at its authored size relative to the mobile canvas.
- **Overlay width scaling for mobile:** overlays declared in the shot-list's `overlays` field carry widescreen-normalized widths (fraction of 1920-px canvas). On mobile, multiply the declared `width` by 1.8× before compositing, clip to 0.9 max. Positions (x, y) are NOT scaled — only width.
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
