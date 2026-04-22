# Design Notes

Why the rules are the way they are. What was tried and abandoned. Constraints discovered in real builds.

This file is not a rule file. It is context for agents and humans who need to understand *why* the rules look the way they do, and what failure modes the current design is protecting against.

Rules tell you what to do. Design notes tell you why. If you're thinking about changing a rule, read the relevant design note first.

## When To Update This File

Update DESIGN_NOTES when:

- A rule is being challenged or reconsidered — document the challenge and the decision, even if the decision is "keep it."
- A feature or approach is tried and abandoned — record what failed, how we knew it failed, and what replaced it.
- A major design decision lands — capture the reasoning so future agents don't undo it.
- A rule changes — move the old rationale to a "History" block, write the new one.
- A post-build retrospective exposes a gap in the rules — capture the learning here first, then update rules if needed.
- A new external constraint shows up (API pricing change, provider behavior shift, tooling break) — record it so we don't silently forget why we chose what we chose.
- A question or real use of the rules exposes a gap — if someone asks "don't we already have X?" and the rules can't answer that, that's a missing piece. Capture the gap here, then update the rules.
- A rule is being worked around instead of followed — either the rule is wrong or the practice is wrong. Analyze which before deciding what to change.

Do **not** update DESIGN_NOTES for:

- Minor rule wording changes.
- Style preferences.
- Speculation about things that haven't been tried yet.
- "What if we wanted to do X" hypotheticals.

The test: *if someone read the rules without this file and would be tempted to undo a good decision, this file is missing context.*

## Current Design Decisions And Their Reasons

### One visual layer per frame (no overlays, no compositing)

Rule source: `WORKFLOW_RULES.md`, `RENDER_RULES.md`.

Reason: Remotion cannot reliably place, size, or time floating foreground elements. Every attempt to put "a small thing on top of a background" produced drift — wrong position, wrong size, wrong timing, ugly transitions. The renderer improvises, and its improvisations are bad. We removed the entire second-layer concept to close that failure mode.

If you are tempted to add back a foreground layer: don't. Change the background instead, or generate a new full-frame illustration that has the emphasis built in.

### AI-illustrated scenes as the primary visual source

Rule source: `ASSET_RULES.md` (Primary Visual Pipeline).

Reason: We tried stock-footage-per-beat first (see killed approaches below). It was brittle, drift-prone, and required AI to judge visual fit — which AI can't do reliably. Switching to per-chunk AI-generated illustrations in a locked style removed two failure modes at once: no more stock-matching judgment, no more per-beat sourcing logistics.

If you are tempted to go back to stock-per-beat as the default: read the "Killed: stock footage per beat" note below first.

### Script is the atomic driver, not the shot-list row

Rule source: `SHOT_LIST_SPEC.md` (Chunk field), `WORKFLOW_RULES.md`.

Reason: Real-world narration flows don't map cleanly to per-row images. One image often needs to cover several beats. Forcing one image per row produced redundant illustrations and broke narrative pacing. Chunks let the narration shape the visual rhythm instead of the spreadsheet structure.

### Preprocessor owns reveal animation, not Remotion

Rule source: `PREPROCESSOR_RULES.md`, `RENDER_RULES.md`.

Reason: Remotion improvises when asked to animate. A deterministic script producing numbered PNG frames removes all improvisation from the reveal. Frame N is always the same frame. Same image in, same frames out. The renderer just plays them.

This also means: no AI tokens are spent on animation. The preprocessor is dumb, deterministic, local.

### Node 22 for Remotion

Rule source: `RENDER_RULES.md` (Runtime Requirements).

Reason: Node 24 caused repeated Rspack / Remotion native-binding failures on development machines (`ERR_DLOPEN_FAILED`, code-signature load failures). Node 22 was the first fallback that worked across projects. Treat as a cross-project runtime compatibility issue, not a one-off repo quirk.

### Google Cloud TTS (Chirp3-HD) over ElevenLabs

Rule source: not yet in rules. Belongs in a session config default.

Reason: ElevenLabs at daily-video pace is $99-330/month (Pro or Scale tier). Google Cloud Chirp3-HD has a 1M chars/month free tier that comfortably covers ~20 minutes of narration per day. Quality on Chirp3-HD is genuinely close to ElevenLabs for narrator-over-illustrations work. The provider is wrapped in a swap-friendly client so OpenAI TTS or CosyVoice can replace it with a small code change if the free tier ever stops fitting.

### Kie.ai as the image provider

Rule source: `ASSET_RULES.md` (Kie Provider Spec).

Reason: Already set up, working, supports all the models we want to try (nano-banana-2, nano-banana-pro, seedream, wan). No reason to switch providers mid-build. If Kie changes pricing or model availability unfavorably, revisit.

### Script extraction (source-to-script stage) is externally owned

Rule source: `SCRIPT_EXTRACTION_RULES.md` (primary) and `WORKFLOW_RULES.md` (Stage 1: Source-to-Script).

Reason: Turning a raw session package into a screenplay, scene plan, and shot list is an editorially-driven stage, not a mechanical one. It requires judgment about story arc, turning points, what to cut and keep, where humor lands without becoming gimmicky, and how dense to make the narration.

An earlier pass (Codex executing the brief in `spoolcast-content/shared/video-generation-skill-spec.md`) produced high-quality output because of that judgment, not because the process was rigorous. Codex then self-documented the actual method as `SCRIPT_EXTRACTION_RULES.md`, which is now the canonical reference.

Decision: this stage is owned by a capable agent with the full session package in context — typically Codex or Claude in a dedicated session with the raw transcript and logs loaded. The spoolcast repo provides the method (`SCRIPT_EXTRACTION_RULES.md`) and the output contract, not automation code.

If you are tempted to "automate" script extraction with a general-purpose LLM loop: don't, yet. Mechanized script-writing is how spoolcast becomes AI slop. The quality bar is "feel like following real work" — that comes from judgment on the raw material, not from a pipeline. The rules in `SCRIPT_EXTRACTION_RULES.md` are a method for an agent to apply, not an algorithm for a script to execute.

### Rule files live in the repo; session content lives in the content dir

Rule source: `WORKFLOW_RULES.md` (Canonical Directory Contract).

Reason: The repo is the reusable scaffold. Session-specific content (media, data, scripts, working files) doesn't belong in the repo — it bloats history and conflates "the workflow" with "one specific video." The split lets the repo stay small, public-friendly, and reusable across sessions.

## What We Tried And Killed

### Killed: foreground overlays (cutouts on top of backgrounds) → Reconsidered (bounded carve-out)

**Original kill (tribe-session-001).** Approximately 15 beats had generated foreground elements meant to float over backgrounds. Every overlay needed manual fixup — drift in placement, wrong sizing, half-broken AI-generated transparency. The renderer couldn't improvise positioning reliably. Abandoned in favor of illustrated full-frame scenes.

The stated reopen condition at the time was: *"a real breakthrough in how Remotion handles per-beat positional data AND a reliable way to judge AI-generated transparency. Neither condition is met."*

**Reconsidered (2026-04-20, spoolcast-explainer session).** The reopen condition is now met for a specific sub-class of overlays:

1. **Per-overlay positional data is specifiable, not improvised.** Remotion itself was never the problem — it just needs exact values. The original failure was asking the renderer (or an AI layer above it) to pick placement/size/timing. A shot-list column that hard-codes position, size, entry/exit timing, and transition style per overlay sidesteps this entirely. Remotion just reads and places.

2. **The transparency problem only applies to AI-generated overlay sources.** Brand logos from press kits, Wikipedia SVGs, Clearbit-served PNGs, Material Symbols, and cleanly-cropped real screenshots all come with authoritative clean alpha. Those source classes were never the failure mode.

So the rule was reopened in a **bounded** way: overlays allowed *only* when (a) every placement/size/timing parameter is explicitly specified in the shot list, and (b) the source image is authoritative with clean alpha. AI-improvised placement and AI-generated transparency remain banned. Renderer may not silently default-fill missing fields — it fails loudly.

The original motivating use case: brand-name mentions in narration ("Meta", "kie.ai", "OpenCV") get the brand logo inserted at the word's timestamp, small, upper-corner, for ~1-2 seconds. This adds attribution and visual texture without breaking the primary illustration.

Constraints to prevent overlay creep:
- Hard cap: 3 concurrent overlays on screen at any moment.
- Soft cap per video: ~5-10 overlay insertions total.
- If a chunk "needs" more than one overlay, consider whether a full-frame scene would be a better fit — that's the original lesson and it still applies.

Codified in:
- `rules.md` Non-Negotiable System Defaults (updated)
- `WORKFLOW_RULES.md` "Global Visual Model → Overlay carve-out" (new subsection)
- `RENDER_RULES.md` "Overlay Placement Schema" (new section, defines per-overlay fields)
- `SHOT_LIST_SPEC.md` header 21 `Overlays` + "Overlay Spec" subsection (new)
- `ASSET_RULES.md` "Overlay Sourcing" (new section, defines authoritative-source rules)

Kills the brand-logo auto-insertion from the *Deferred* list — it's now active with the overlay system.

### Killed: AI-judged stock footage selection

Tried: prompt an AI to pick matching stock videos or images per beat. Failure mode: AI couldn't judge visual fit, transparency, or quality. It kept choosing bad matches with confident-sounding rationale. Abandoned.

This is why `ASSET_RULES.md` lists stock sourcing as an "alternate mode" rather than "primary with AI picker."

### Killed: stock footage per beat as the default

Tried first, as the original tribe-session-001 workflow. Brittle in multiple ways:
- sourcing logistics were heavy (per beat, sometimes per retry)
- stale generated files drifted from the shot list constantly
- the "Remotion can't place overlays" problem showed up here too
- the visual result felt like stock-cut-and-paste, not a told story

Abandoned as the default. Kept as an optional alternate mode for sessions that genuinely need real footage (e.g. real screenshots from the source session).

### Killed: ElevenLabs as the TTS provider

Initial TTS provider (wired up by codex). At daily-video pace, ElevenLabs requires the Scale tier (~$330/month). Not worth it when Google Cloud TTS Chirp3-HD hits the same quality for $0 at our volume. ElevenLabs-specific env vars (`ELEVENLABS_*`) are safe to remove from `.env` — they're dead config.

### Killed: tribe-specific baked into the repo

Original setup had tribe-specific media, data, and scripts in the repo. Made the repo heavy, single-use, and confusing for anyone trying to understand "what is this system." Separated into repo (scaffold) + content dir (session-specific) to fix this. Old assets kept in `spoolcast-content/sessions/tribe-session-001/` for reference, not for pipeline use.

## Lessons Learned

- Remotion is not good at improvising layout, placement, or timing. Keep it as a dumb playback engine.
- AI image models can't reliably judge whether a sourced image works for a given beat. Don't rely on AI curation of assets.
- Stale generated files are a major failure mode. Regeneration must be explicit, not silent.
- Script and narration are more reliable atomic units than shot-list rows for image generation.
- Fragile visual systems should be simplified, not preserved.
- Provider choice matters at daily-video pace. A tier that "works for one video" can be 50x too expensive at 30 videos.
- When a complex system has drift across layers (shot list / review / preview / render), the fix is usually fewer layers, not better sync.
- Rule files written from a long working session always have gaps. The gaps surface when the rules are used or questioned — treat "don't we already have a system for X?" as a trigger to update, not as pushback. The questioner is usually right.
- Editorial stages (story, voice, pacing, humor) are hard to mechanize without making everything feel generic. Leave them to agents with full context and judgment. Mechanize the downstream plumbing (images, preprocessor, render) where determinism helps quality.
- **Same-turn codification**: any heuristic or rule agreed on in conversation must land in a rules file in the same turn — not "we'll write that down later." if it isn't written, the next decision reasons from scratch and re-breaks the rule. this was observed after an 8-beat chunk was created despite the agent having just argued for "smaller chunks, more pictures" earlier in the same session. the heuristic existed in chat; nobody wrote it down; it was forgotten within minutes.
- Chunking failure modes: "group by long-pause markers" is a structural signal that can produce chunks with too many beats. Long-pause alone does not pass the visual-subject test. Always apply the stop-and-check heuristics in `WORKFLOW_RULES.md § 3. Chunking` before committing chunk boundaries.
- Continuity concept: chunks relate to each other either as standalone or as part of a multi-chunk arc. Arcs emerge from consecutive `continues-from-prev` chunks — no separate data structure needed. Encoded per-chunk rather than as a top-level grouping.

## Lessons from the first ship (2026-04-20, pilot video shipped to YouTube)

### Killed: chalkboard wipe as the chapter-boundary default

Original `TRANSITION_RULES.md` rule: every chapter boundary gets
chalkboard. Across 44 chunks that produced 10 chalkboards in a row —
read as one repeated style, bored the viewer. Killed the
chapter-boundary-implies-chalkboard rule. Now requires BOTH narrative
significance AND single-subject/clear-composition. Chaos / many-equal-
elements images skip chalkboard regardless. Final pilot ended at 5
chalkboards / 4 paint-auto / 7 paint-center-out / 28 cut.

### Killed: silent defaults in `build_input_for_model()`

Function originally had `quality="basic"` default that mapped to "2K"
for nano-banana-2 — but the pilot session config specifies `"resolution":
"1K"`. A one-off thumbnail script called `build_input_for_model()`
without passing `quality`, silently shipped at 2K, hung the kie API
(combined with no HTTP timeout), 30 minutes wasted.

Killed the default. `quality` is now required (no default → hard
TypeError if missing). Added `build_input_from_session()` helper that
reads session.json so callers can't drift from the project standard
even if they want to. Direct calls to `build_input_for_model()` in
new one-off scripts are now forbidden by `ASSET_RULES.md`.

### Killed: auto-applied generic camera template on long chunks

Tried auto-applying a wide → upper-middle medium → wide pan to all
13 long multi-beat chunks. Most looked terrible — the camera was
panning to "upper-middle" on images that had no content there, just
zooming to nothing. Only 2 chunks (C2 manually crafted, C36 with
content-justified left-third / right-third) worked.

Killed the auto-template. Camera moves now must be content-justified
per chunk. If you can't pick a specific zone based on the image, do
NOT add camera moves — the default subtle push-in is safer than a
wrong target.

### Killed: independent push-in on continues-from-prev chunks

Default subtle push-in (1.0 → 1.08 over chunk duration) was applied
to every chunk. On cuts between continuing chunks (same character,
same scene), each independent push-in caused the camera to "rewind"
from 1.08 back to 1.0 at every cut — read as a jarring tiny zoom-out.

Killed the default for continues-from-prev / callback chunks. Those
hold steady at zoom 1.0. Only standalone chunks get the subtle
push-in. Implemented in `Composition.tsx` `computeCamera()`.

## More lessons learned

- **Rules without a conflict-detection mechanism become snapshots, not constraints.**
  Multiple times during the pilot ship, user requests contradicted
  documented rules, and the rule got silently rewritten to match.
  That defeats the point. Fix: rule-conflict protocol added to
  `rules.md` — surface the conflict explicitly with options
  (update / one-off / keep) before changing any rule.
- **Image content vetoes narrative position.** Chalkboard wipe is
  beautiful on single-subject images and ugly on chaos. The "chapter
  boundary deserves a wipe" rule has to defer to the image — chaos
  scenes always go paint-auto.
- **One-off scripts MUST read session config.** The 2K vs 1K bug
  proved that even when the wrapper has a "smart" default, ad-hoc
  scripts that bypass session.json drift from the project standard.
  Required helper (`build_input_from_session`) makes the right thing
  the easy thing.
- **No-default-arg is a real defense.** Removing the silent default
  from `quality` made the bug surface as a hard TypeError instead of
  a silent wrong value. Worth doing for every config-mirroring arg.
- **HTTP requests need timeouts everywhere.** A `requests.Session`
  with no timeout will hang indefinitely on a stuck connection or a
  request the API can't process. 60s `REQUEST_TIMEOUT_SECONDS`
  added to all kie POST/GET calls.
- **Don't pipe long-running commands through head/tail/grep.** They
  buffer until upstream exits. Working processes look hung; if you
  kill them, you've created the bug you thought you found. Codified
  in `rules.md` "Diagnostic anti-pattern: pipe-buffering."
- **Read the script before titling.** Chunk titles, scene_title,
  and beat_descriptions are visual scaffolding, not narrative
  content. Titles and thumbnails generated from them tend to mis-sell
  the video (sell the question instead of the answer). New
  `PUBLISHING_RULES.md` mandates reading the full voiceover
  narration before any title/description/thumbnail work.
- **The shipped product is the strongest argument for the workflow.**
  https://youtu.be/hqbmHuEtayM exists. Pipeline works end-to-end.

## Lessons from the spoolcast-explainer session (pre-ship)

During source-analysis and screenplay drafting for the explainer
video, four real gaps in the Stage 1 rules surfaced. All were
observed in use, not speculation.

1. **The single biggest gap: no requirement to declare the core
   message.** The agent was treating all sections with roughly equal
   weight and depth, diluting the sections that carried the video's
   actual thesis. The builder caught this as the meta-cause of
   several other gaps: without a declared core message, the agent
   had no north star for what to cut vs expand, what to define vs
   assume, what to open on, or what the ending should answer. Section
   importance is downstream of this — declaring sections as
   "important" independently is fake precision. Fixed: Job E in
   `SCRIPT_EXTRACTION_RULES.md` §3 and rule 9 in §8. Also surfaced
   downstream into `PUBLISHING_RULES.md` top-level "core-message
   rule" — the title/thumbnail/description are not "aligned with"
   the core message, they ARE the core message expressed in an
   attention-grabbing way honest to the script.

   **Follow-on gap caught during the same session.** After the rule
   was added, the agent immediately guessed a core message and wrote
   it directly into the source analysis without confirming with the
   builder. This violated the already-documented Substance-Before-Form
   rule (`rules.md`) but happened anyway because the Stage 1 rule for
   Job E didn't explicitly call out user confirmation. Two iterations
   later, the builder proposed a different and sharper core message
   in their own words — which became the final one. Fix: Job E now
   requires proposing 2-3 candidates in plain language, naming the
   tradeoffs, and waiting for the user to pick or rephrase before
   writing anything into the source analysis. Enforcement language
   also added to rule 9 of §8. The lesson: load-bearing editorial
   decisions need user confirmation even when a rule exists saying
   "declare X" — declaring and confirming are different things.

2. **Viewer orientation missing from Stage 1 rules.** The existing
   "find the practical question first" rule is about story logic;
   it doesn't protect against a cold open that launches into concept
   before the viewer knows what/who/why/what-they'll-see. Observed:
   the first screenplay draft stacked three abstraction paragraphs
   before the viewer saw anything concrete. Same failure mode as
   the TRIBE pilot's cold open. Fixed: viewer-orientation gate in
   `SCRIPT_EXTRACTION_RULES.md` "Gates Between Versions."

3. **No concept-inventory gate.** Central concepts (*beat*, *chunk*,
   how images match chunks) went unexplained in the v1 draft even
   though they carry the thesis. The builder caught the gap on
   review; had to add the entire "how the script gets made"
   section mid-stream. Fixed: concept-inventory gate in
   `SCRIPT_EXTRACTION_RULES.md` "Gates Between Versions."

4. **Substance-before-form pattern undocumented.** The agent
   repeatedly jumped to visual specifics before the builder had
   agreed on what the section was trying to say, wasting iterations.
   Observed: four back-and-forths on hook images before the builder
   stopped the loop and demanded plain-words-first. Fixed: new
   "Substance Before Form" section in `rules.md` (global
   agent-behavior rule, not just Stage 1 — applies to camera choices,
   thumbnail concepts, reveal styles, any creative/editorial decision
   where an agent is collaborating with the user).

5. **No short-version summary at the top of each screenplay draft.**
   The user repeatedly said "too much text" during v1 and v2 review
   cycles — the symptom. The cause: every review forced the user to
   parse a full prose draft to catch issues that were actually at
   the spine level. A short-version summary block (core message,
   spine with target times, what changed, flags for review) at the
   top of each screenplay file lets the user accept, reject, or
   redirect in seconds. Fixed: new "Screenplay File Format" section
   in `SCRIPT_EXTRACTION_RULES.md` and rule 12 in §8. The principle:
   drafting takes effort; reviewing shouldn't.

   **Follow-on — review artifacts are just two things.** The
   short-version rule then exposed a broader pattern: across the
   whole Stage 1 pipeline, the agent was handing the user
   markdown files (source analysis, screenplay prose, scene plan,
   voiceover script) for "review." The user pushed back: they want
   only the short version in chat and the final xlsx. Everything
   else is working scaffolding that shouldn't pull their attention.
   Fixed: new top-level "Review-Artifact Policy" section in
   `SCRIPT_EXTRACTION_RULES.md` locks the rule: only two review
   artifacts per pipeline — the short version in chat, and the
   shot list xlsx when it exists.

6. **Effort spent is not importance — the agent kept weighting
   content by how much work went into it.** Two related failure
   modes surfaced during shot-list review:

   - **Inflating sagas.** The chalkboard-wipe transition took
     multi-day stretches and nine iterations during the pilot.
     That effort is real but doesn't make it video-worthy on its
     own — if the core message doesn't call for it, the saga
     shouldn't be mentioned. The user flagged this explicitly:
     "just because we spent a long time on something doesn't
     mean it's important."
   - **Underweighting quick breakthroughs.** Image-ref chaining
     is a small afternoon insight with a tiny code footprint,
     but it's the mechanism that makes the whole style-lock
     work. It deserves significant screen time regardless of
     how cheap it was to implement.
   - **Abstract over concrete.** The agent's first shot list
     spent 8 chunks on an "editorial workshop" (abstract
     decisions: find the question, find the turning point,
     declare the core message). The user pushed back: that's
     meta-commentary. The actual anti-slop craft — chunking,
     throughline matching, beat rewriting, pronunciation fixes,
     the 15-second split rule — is more interesting and more
     specific. Go concrete.

   Fixed: new heuristic 11 ("Effort is not importance — weight
   by core-message service only") in `SCRIPT_EXTRACTION_RULES.md`
   Heuristics section, plus rules 13 and 14 in §8 ("Rules I Wish
   The Original Spec Had Said Explicitly").

7. **Deadpan punchline beats need their own visual moment.** During
   review the builder noted that short comedic beats like
   *"Obviously."* or *"You know, casually."* were buried inside
   multi-beat chunks — so the image didn't change at the moment
   the joke landed. The deadpan line had no visual punctuation.
   Separating these beats into their own single-beat chunks
   restores the rhythm: the new image IS the beat. The builder
   also raised the idea of using real meme / reaction visuals for
   the peak deadpan beats — which required reconciling with the
   one-visual-layer rule (no overlays). Resolution: the meme
   replaces the chunk's image full-frame, not overlaid, preserving
   the one-layer rule. Limited to 1-2 per video to stay a spike.
   Fixed: new heuristic 10a in `SCRIPT_EXTRACTION_RULES.md`
   ("Deadpan punchline beats get their own single-beat chunk")
   plus a "Punchline Chunk Carve-Out" section in `ASSET_RULES.md`
   that authorizes the style-anchor override specifically for
   those single-beat punchline chunks.

8. **Planned-vs-shipped honesty in narration.** During shot-list
   review the builder caught that the V1 script's Zara/agent-layer
   beats used present-tense framing ("Zara watches every signal...")
   that implied the integration was shipped and running. In reality
   the Zara chatbot exists and posts in Matrix but the spoolcast
   pipeline integration is designed and not yet built. Over-claiming
   once poisons viewer trust across the whole video: every other
   claim becomes suspect. Fix: new Job D-1 in
   `SCRIPT_EXTRACTION_RULES.md` §3 ("mark planned-vs-shipped for
   every system component") + rule 14a in §8. Narration must use
   explicit planned-state language for designed-but-not-built
   components: "still being built," "the next piece," "once it's
   wired up," "designed to work this way." Rewrote Scene 10 of V1
   with those verbs; substance unchanged, framing honest.

9. **External assets before AI generation (Stage 4 ordering).**
   During V1 shot-list review the builder flagged that AI image
   generation (real money per call) should not fire until all the
   free / reversible external assets are produced and the shot list
   is re-approved. If an external asset fails the chunk has to
   change, and any AI gen done against the old chunk is wasted.
   Fix: Stage 4 ordering rule in `WORKFLOW_RULES.md` (external
   assets first → re-approve shot list → AI generation second →
   TTS last). This front-loads zero-cost work to protect the
   variable-cost work. Also incidentally lines up with the
   substance-before-form principle in `rules.md` — the external
   assets often surface structural issues that AI gen would bury.

10. **Cold-open visual density is not uniform across the video.**
    During V1 shot-list re-review the builder pointed out that
    Scene 1 chunk C1 had 3 beats on one image — meaning the first
    ~6-7 seconds of the video held a single static illustration.
    That's the exact opposite of what a cold open needs. The
    first 10-15 seconds is where attention is most fragile; a slow
    visual pace loses viewers before the premise lands. Fix: new
    heuristic 9a in `SCRIPT_EXTRACTION_RULES.md` ("Cold-open visual
    density"), rule 14b in §8. Target image change every 2-3 sec in
    the cold open, relaxing to 7-10 sec for the rest of the video.
    Chunks in the cold open should rarely exceed 4 sec. Applied
    retroactively to V1: C1 split into C1/C1B/C1C (one beat each),
    C5 split into C5/C5B/C5C. Scene 1 now has ~15 chunks for ~45
    seconds, vs the 8 it had before.

11. **Meta-rules are demonstrated by the video, not listed inside
    its content.** When building V1's Scene 3 "anti-slop catalog,"
    the first draft included items like "declare a core message,"
    "define terms before first use," and "orient the viewer in the
    cold open." The builder pointed out these are meta-rules — they
    apply to *any* scripted video. Putting them in the catalog
    turns the video into "how to make videos," which is the wrong
    subject and wrong audience. The catalog should cover the craft
    specific to the system being explained. The meta-rules should
    be *demonstrated* by the video itself (the video has a core
    message, defines terms before using them, orients the viewer)
    rather than narrated. Fix: new heuristic 9b in
    `SCRIPT_EXTRACTION_RULES.md` ("Meta-rules are demonstrated, not
    listed"), rule 14c in §8. Applied retroactively to V1: Scene 3
    catalog covers only spoolcast-specific craft (chunks-as-image-
    unit, throughline matching, 15-sec rule, beat rewriting, TTS
    pronunciation, human editorial judgment). Meta-rules cut.

12. **Per-video tracker project organization.** Discussion early in
    the V1 build surfaced that the artlu-tracker pattern is "one
    tracker project per shipped video," not "one project per
    codebase" or "one project per session." The pilot video
    followed this — it was tracked as *"TRIBE brain-prediction
    ad-test explainer — spoolcast pilot video,"* separate from
    the workflow tool's tracker entry. Fix: documented in
    `WORKFLOW_RULES.md` under new "Tracker Project Organization"
    section, with the session.json ↔ tracker-project name
    cross-reference convention.

13. **Asset QA pass between external-asset production and
    re-approval.** During V1's external-asset production run, the
    batch sourced several brand logos from Google's favicon
    service (Adobe, Descript) as fallbacks when higher-quality
    sources weren't available, and a simpleicons SVG for
    ElevenLabs came back suspiciously small (173 bytes).
    Without a structured QA step, these could silently ship — the
    viewer sees a blurry pixelated logo or a blank overlay box.
    Fix: new "Asset QA pass" sub-section in `WORKFLOW_RULES.md`
    Stage 4 ordering. Automated checks on every external asset
    (file size, dimensions, SVG content, video duration, audio
    amplitude); report surfaces ⚠️/❌ items to the user before
    re-approval so the quality-limited assets are either re-sourced
    or explicitly accepted. Prevents the failure mode where the
    pipeline claims "assets produced" but some assets are
    unusable.

14b. **Never offload production work to the user as an option.**
    During the external-asset production pass, the agent presented
    options like *"(a) I capture terminal stdout, or (b) you do a
    QuickTime recording"*. The user pushed back — the `(b)` option
    is just the agent giving up disguised as choice. The agent was
    hired specifically to not make the user do this work. Fix: new
    "Don't Offload Production Work To The User" section in
    `rules.md` alongside Substance-Before-Form. If the agent hits
    a genuine limitation, name it honestly and propose alternatives
    the agent itself can execute — not user labor disguised as a
    second option. The `box/` folder remains a user-initiated drop
    point, not an agent fallback.

14. **Optional `box/` folder for user-supplied assets.** The
    external-asset production also exposed that the user often has
    the right asset on hand (a YouTube analytics screenshot, a
    specific Zara chat recording, a brand press-kit download) but
    has no clear place to drop it into the session. Fix: new
    "Optional `box/` folder" sub-section in `WORKFLOW_RULES.md`.
    Each session may have `source/box/` where the user drops any
    files. The agent scans at the start of Stage 4, best-effort
    guesses each file's purpose, and either auto-routes (confident
    match) or surfaces to the user (*"is this for C4 or C44?"*).
    Files the user says are unrelated stay in `box/` untouched.
    Strictly additive — an empty `box/` never fails anything.
    Reduces friction for user-contributed assets.

**Noted but not mandated:** the payoff-preview pattern in the cold
open (5-10 seconds of the actual output before any technical
explanation). Observed to help once, not yet observed enough times
to lift to a rule. Logged as a pattern worth considering in
`SCRIPT_EXTRACTION_RULES.md` "Patterns Observed, Not Yet Rules."

**Deferred:** a trigger/passive-content layer above Stage 1 — the
agent that watches signals and decides when a video exists. Belongs
in a future `TRIGGER_RULES.md` once the Zara/Animabot integration
is shipped. Logged here so it's not forgotten.

**Brand-logo auto-insertion — PROMOTED from Deferred to Active (2026-04-20).** Now enabled by the overlay carve-out. When narration mentions a known brand ("Meta", "Tesla", "Google Cloud", "kie.ai", "OpenCV", "Remotion"), the pipeline identifies the word's timestamp from TTS metadata and inserts the brand logo as an explicitly-specified overlay per the shot-list schema. See `RENDER_RULES.md` Overlay Placement Schema and `ASSET_RULES.md` Overlay Sourcing for the contracts. See the "Reconsidered" subsection under "Killed: foreground overlays" above for the reasoning and constraints.

### Lesson: image models hallucinate specific numbers on receipts / charts / UI (2026-04-20)

During V1 review of `spoolcast-explainer`, the C23 "price of a coffee"
receipt was generated as `TOTAL: $95.50` with invented line items
($2.00, $5.50, $4.00). The narration says "price of a coffee" and the
preceding chunk (C22) had already locked the breakdown as $2/$0/$0/$0.
The image model reads "receipt with a total underlined" and confidently
fills in plausible-looking but wrong specifics.

Same failure mode observed in smaller doses:
- C2's laptop screen shows "0 Views" — matches narration by luck, not
  by design.
- C24's bar chart axis labels (10/100/1000) happen to work for
  "$500–$2000" only because log-scale is forgiving.

Fix: new "Narration-Text Audit Rule" in `VISUALS.md § Assets` requires
reading every legible number/label in every generated image against
the actual narration before locking. Re-prompts must be explicit:
`'TOTAL: $2'` not `"a receipt with a total"`. Vague prompts invite
hallucinated specifics.

Also added to the `VISUALS.md § Assets` Validation Checklist as step 8.
This is the kind of failure that passes visual QA at a glance — the
image looks great, the receipt looks like a receipt — and only gets
caught when a human reads the audio and the pixels together.

### Lesson: context at every transition, enforced by schema (2026-04-20)

V1→V2 review of `spoolcast-explainer` surfaced four related pacing
failures that all traced back to one root cause: the video treated
every transition as equal weight.

Observed failures:
- **0:27 jarring jump.** Cold Open ended, Act 2 began, no signal. A
  1-second broll fragment appeared with no setup, followed by the
  "next seven minutes" promise — three conceptual frames inside ~3
  seconds. Viewer had no scaffold.
- **1A → 1B jarring.** Two adjacent ideas (production constraints
  → distribution failure) had no bridge sentence connecting them.
  Half-second pause between chunks was identical to within-chunk
  beat pauses.
- **3:00 four-layers preview rushed.** The chunk that frames the
  rest of the video — THE roadmap preview — got the same pacing
  as any beat. Four technical names flew by. Viewer didn't retain
  the map.
- **Broll played without viewer context.** C7 (0:27), C30 (3:48),
  C32 (4:08) all played pilot-related clips with either no setup
  or narration talking over the broll audio. C41 (5:05) was the
  only broll that worked — it had explicit "watch this" prep.

Root cause framing (user's diagnosis): *"there NEEDS TO BE CONTEXT
AND REASON WHY THE ROLL IS BEING PLAYED AND IT NEEDS TO BE OBVIOUS
TO THE VIEWER"* — generalized to every transition, not just broll.

Fix: new Part 2 in `STORY.md` — "Pacing and Viewer Context." Four
transition sizes (beat, chunk-continues, chunk-topic-shift, Act),
each with its own required signal (tiny pause; small pause; bridge
narration + longer pause; bumper + opener). Plus: `weight: high`
flag for promises/previews/thesis/punchlines that need linger-and-
silence regardless of slot size. Plus: six allowed forms of broll
context (spoken setup / visual continuity / recognition / topical
match / on-broll label / callback) with a required
`context_justification` field on every broll chunk.

Enforcement layered:
1. **Schema-level** — three new required fields on the shot list
   (`boundary_kind`, `weight`, `context_justification`) plus
   `act_title` / `act_opener_line` where applicable. Pipeline
   refuses to build preview-data without them.
2. **Human review** — xlsx surfaces the fields; reviewer applies
   the 2-second gut-check on every broll row.
3. **Audio-first re-timing** — after TTS generates real mp3s, a
   re-timing pass recomputes every pause from measured durations
   and applies the pause tiers. Nothing is locked until real audio
   exists.

This is a durability fix, not a one-time patch. A future V1-of-some-
other-video can't repeat these failures because the schema won't
let you build it.

The key insight the user pushed me toward: **pauses alone don't give
context — pauses are just space. Context is the signal that fills
the space.** A title card, a bridge sentence, a linger moment,
a visual continuity — these are the mechanisms that let the viewer
orient. The pause is only the breath that lets the mechanism land.

### Lesson: rule-file consolidation (2026-04-20)

Same day as the pacing rewrite, the 13 rule files collapsed to 6:
- `rules.md` (kept — index + global agent rules)
- `PIPELINE.md` (new — merges WORKFLOW + SESSION_CONFIG_SPEC +
  SHOT_LIST_SPEC + RENDER_RULES)
- `STORY.md` (new — merges SCRIPT_EXTRACTION_RULES + new PACING
  content)
- `VISUALS.md` (new — merges ASSET_RULES + PREPROCESSOR_RULES +
  TRANSITION_RULES)
- `SHIPPING.md` (new — merges REVIEW_BOARD_RULES + PUBLISHING_RULES)
- `DESIGN_NOTES.md` (kept — this file, the why log)

Why: 13 files meant mental overhead on every lookup ("which file
is the right one?") and made it easy for related rules to drift
apart across files. Six files with clear charters — procedural,
editorial, visual, end-of-pipeline, why, index — match how
authors actually think about the work.

No content was trimmed in the merge. Every rule from every source
file was preserved verbatim, just moved and demoted in heading
level. Cross-references were rewritten to point to new sections
(e.g., `ASSET_RULES.md § Style Anchor` → `VISUALS.md § Assets §
Style Anchor`).

The grouping logic:
- **PIPELINE** = how you move through stages, plus the contracts
  (session config, shot list, render) the stages produce/consume.
  Specs live with the pipeline that uses them.
- **STORY** = everything about what the video says and how it
  lands. Script extraction and pacing are the same concern at
  different altitudes.
- **VISUALS** = everything on screen and how it animates. Assets,
  preprocessor, transitions were always artificially split.
- **SHIPPING** = the last mile. Review and publish together
  because they're both "preparing the final artifact for a
  specific audience."

## Three bug classes learned during spoolcast-dev-log V4 (April 2026)

### Timeline-gap class

Any code path that advances `running_frame` in `build_preview_data.py` AFTER `chunk_end_frame = running_frame` has been captured produces a white-flash gap in the rendered video. The chunk's `durationFrames` doesn't include the advance, but the next chunk's `startFrame` does — so the renderer sees a gap of N frames where no Sequence is active, and the composition's white background shows through.

Hit twice on V4: once with the `weight: high` tail-pause bump, once with the `hold_duration_sec` extension. Fix in both places was the same: after advancing `running_frame`, re-assign `chunk_end_frame = running_frame`.

Durable rule: any function that extends a chunk's duration must update both fields atomically. Consider wrapping this into a helper so future extensions can't forget.

### Paint-on deferred

`stroke_reveal.py` outputs RGB PNG frames with a white background (pixels that haven't been painted yet are white, not transparent). Any entrance that plays the stroke-reveal animation therefore starts from a visible white canvas — a flash, not a reveal.

Paint-on is deferred from the transition vocabulary (`cut` + `crossfade` only for now) until the preprocessor emits RGBA frames where unpainted pixels are transparent. Then paint-on can composite over the prior chunk's final frame as an underlay, and the reveal feels like strokes appearing on an existing scene rather than strokes appearing on a blank page.

### Loop-index leak

During a `build_preview_data.py` refactor, a `for i, chunk in enumerate(chunks_out):` loop got simplified to `for chunk in chunks_out:` — but the body still referenced `i` (which was leaking from a prior `enumerate` loop). Every chunk ended up computing its prior-frame underlay from `chunks_out[49]` (the last `i` value) — all 50 chunks inherited the final chunk's image as their underlay.

Rule: when simplifying a loop that drops `enumerate`, grep the loop body for lone `i` / `idx` / `j` references before committing. Python won't warn you — it'll silently use the leaked variable from the enclosing scope.
