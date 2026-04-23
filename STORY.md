# Story

Everything editorial: script extraction, pacing, and viewer context.

## Table of Contents

- [Part 1 — Script Extraction](#part-1--script-extraction)
  - [Script Extraction Rules](#script-extraction-rules)
  - [Why This Document Exists](#why-this-document-exists)
  - [The Actual Pipeline, In Order](#the-actual-pipeline-in-order)
  - [Review-Artifact Policy (READ FIRST)](#review-artifact-policy-read-first)
  - [Screenplay File Format and Workflow](#screenplay-file-format-and-workflow)
  - [Gates Between Versions](#gates-between-versions)
  - [Heuristics I Actually Used](#heuristics-i-actually-used)
  - [Patterns Observed, Not Yet Rules](#patterns-observed-not-yet-rules)
  - [Three Real Editorial Decisions Between Screenplay v1, v2, and v3](#three-real-editorial-decisions-between-screenplay-v1-v2-and-v3)
  - [Quality Tests: How I Knew The Screenplay Was Ready](#quality-tests-how-i-knew-the-screenplay-was-ready)
  - [What Would Have Made Me Reject The Screenplay](#what-would-have-made-me-reject-the-screenplay)
  - [Things I Tried, Or Nearly Tried, That Did Not Work](#things-i-tried-or-nearly-tried-that-did-not-work)
  - [Rules I Wish The Original Spec Had Said Explicitly](#rules-i-wish-the-original-spec-had-said-explicitly)
  - [The Short Version To Remember](#the-short-version-to-remember)
- [Part 2 — Pacing and Viewer Context](#part-2--pacing-and-viewer-context)
  - [Purpose](#purpose)
  - [The meta-rule](#the-meta-rule)
  - [The viewer-cognition test (apply to every adjacent beat pair)](#the-viewer-cognition-test-apply-to-every-adjacent-beat-pair)
  - [Bridge archetypes](#bridge-archetypes)
  - [Acts are the editorial unit](#acts-are-the-editorial-unit)
  - [The four transition sizes](#the-four-transition-sizes)
  - [Signals by transition, in detail](#signals-by-transition-in-detail)
  - [Bumper rendering](#bumper-rendering)
  - [High-weight chunks](#high-weight-chunks)
  - [Broll requires obvious viewer context](#broll-requires-obvious-viewer-context)
  - [Audio-first re-timing](#audio-first-re-timing)
  - [Shot-list schema additions](#shot-list-schema-additions)
  - [Pairwise narration audit (the automated durability layer)](#pairwise-narration-audit-the-automated-durability-layer)
  - [Two-layer enforcement, restated](#two-layer-enforcement-restated)
  - [Why these rules, concrete cases](#why-these-rules-concrete-cases)
  - [Relationship to Part 1](#relationship-to-part-1)

## Part 1 — Script Extraction

### Script Extraction Rules

#### Why This Document Exists

The current spoolcast rules explain the system well once a session has already become a shot list.

They do **not** capture the most editorially important stage well enough:

- how a raw session package becomes a story
- how the story becomes a screenplay
- how the screenplay becomes a scene plan
- how the scene plan becomes a shot list

This document records the actual method used on a real session package so future agents do not flatten this stage into generic summarization.

The point is not to sound principled.
The point is to preserve the working editorial process that produced a screenplay, a scene plan, and then a shot board that were actually usable.

This is based on the real `tribe-session-001` pipeline:

- raw session package in `../spoolcast-content/sessions/tribe-session-001/source/`
- analysis in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-source-analysis.md`
- screenplay drafts in:
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v1.md`
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v2.md`
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v3.md`
- scene plan in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-b-roll-plan.md`
- beat-level narration script in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-voiceover-script.md`
- shot list in `../spoolcast-content/sessions/tribe-session-001/working/tribe-shot-board.xlsx`

---

#### The Actual Pipeline, In Order

This is the order that was actually followed.

It matters.

The main failure mode is skipping the middle and pretending a transcript can go straight into a shot list.
It cannot.

##### 1. Start by stabilizing the raw session package

Before any writing, the package had to be treated like evidence, not inspiration.

The raw package for `tribe-session-001` contained:

- `manifest.json`
- `transcript.md`
- `notes.md`
- `logs.md`
- a few recovered image artifacts
- many missing screenshot references

The first job was not “start drafting.”
The first job was:

- confirm what the package actually contains
- confirm what is missing
- confirm what is trustworthy
- confirm what cannot be relied on visually

For this session, that changed the later script materially.

The package notes made clear:

- a lot of screenshots were gone
- the transcript had been rebuilt from session logs
- some visual artifacts were recreated as SVGs
- the source package was good enough to tell the story
- the source package was **not** good enough to support a screenshot-heavy reconstruction

That meant the screenplay could not depend on “then we show the exact screenshot from the session.”
That is not a visual preference note.
That is an editorial constraint.

##### 2. Read the session transcript to understand what the session was really about

The next step was **not** summarizing the transcript.
It was identifying what kind of story was actually inside it.

The transcript was read looking for:

- the practical question that started the session
- the friction that made the session real
- the first moment where the session stopped being generic
- the result that actually changed the interpretation
- the final answer the session earned

The key distinction here:

- the transcript contains many events
- only some of them belong to the story spine

For `tribe-session-001`, the raw session started with a practical product question:

- can Meta’s TRIBE v2 analyze a video ad and help say whether the ad is good or bad?

That mattered more than the existence of TRIBE itself.

This is where the editorial method diverges from a generic “explain the technology” workflow.
The story was **not** “Meta released an interesting model.”
The story was:

- a practical workflow question met a strange research model
- the setup was painful
- the experiment worked enough to be interesting
- the result disagreed with the market

That is the spine.

##### 3. Write a source analysis before drafting any screenplay

A separate source-analysis file was written first.
That was not optional.
That file forced the story to be extracted before tone or narration rhythm got involved.

The analysis step did four jobs.

###### Job A: reduce the transcript to hard facts

For `tribe-session-001`, the hard facts included:

- TRIBE predicts brain-response patterns from video, audio, and text
- it does not produce a direct good/bad ad score
- the model is under a non-commercial license
- local setup failed in multiple ways
- Colab on a Tesla T4 could run it
- each short clip still took about 3 hours 32 minutes to encode
- TRIBE-style signals favored Video A
- real ROAS favored Video B

This stripped out noise and gave the later drafts a factual floor.

###### Job B: identify the strongest story turn

This is the step where the editorial center gets chosen.

The strongest turn was not:

- “the model exists”
- “the model worked”
- “the setup was annoying”

It was:

- the model produced interpretable structure
- that structure disagreed with the market result

That mismatch became the turning point.

This was explicitly recorded in the source analysis because if it is not written down here, later drafts drift back toward generic tech explanation.

###### Job C: decide what kind of story this is

The source analysis turned the package into a specific narrative shape:

1. practical goal
2. setup friction
3. real experiment
4. interesting mismatch
5. interpretation
6. operational reality

That shape is not cosmetic.
It later determined the order of scenes.

###### Job D: decide what the video should **not** pretend

The analysis also wrote down the anti-claims:

- do not imply TRIBE directly reads real human brains
- do not imply the model proved it can pick winning ads
- do not rely on missing screenshots
- do not force a clean linear success story

Those constraints later saved the screenplay from hype.

###### Job D-1: mark planned-vs-shipped for every system component

Extension of Job D anti-claims. Every component the video describes must be clearly categorized as one of:

- **Shipped and working** — already built, in use, can be claimed as-is.
- **Designed and planned, not built yet** — the design exists but the code doesn't run. Must be marked explicitly in narration: *"still being built,"* *"the next piece,"* *"this is the plan,"* *"once it's wired up,"* *"designed to work this way."*
- **Speculative / idea-stage** — not even fully designed. Either mark as speculative outright or cut from the video.

Never imply a component does something it doesn't. Viewers can tell. Once one claim gets caught overreaching, every other claim in the video becomes suspect for the rest of the runtime.

In source analysis, build a small table listing every component the video describes with its current status. Check the screenplay against it at v3.

Concrete example from the spoolcast-explainer session: the Zara/agent layer is designed and partially built (Zara the chatbot exists and posts in a Matrix room; the spoolcast-integration piece is not yet wired). The V1 script uses language like *"still being built as of this video"* and *"once it's wired up, Zara will watch…"* instead of present-tense claims that would imply shipped behavior. Same content, honest framing.

###### Job E: declare the core message — confirmed with the user, not guessed

Name — in one sentence — the single thing the viewer must come away with. Not the story spine. Not the summary. Not the topic. The one message. Every section of the video either serves this message or it shouldn't be in the video. Section importance is *derived* from how much each section serves the core message, not declared independently.

**The core message must be confirmed with the user before being written into the source analysis.** This is the most load-bearing editorial decision in the entire pipeline — every downstream decision (what to cut, what to expand, what to open on, what the ending answers, how the title is worded, what the thumbnail shows) is derived from it. A guessed core message that sounds plausible can lock in the wrong framing for the whole video; the user then spends iterations reacting to downstream effects without realizing the root cause.

Required process:

1. **Propose 2-3 candidate core messages** in plain language. Each takes a distinct angle — e.g. architecture-focused vs outcome-focused, audience-specific vs broad, abstract principle vs concrete promise.
2. **Name the tradeoffs** for each — who it speaks to, what it assumes about the viewer, what it leaves out.
3. **Wait for the user to pick, edit, or propose their own phrasing.** The user's own words usually land sharper than candidate proposals, because the user has lived with the project.
4. **Only then write the confirmed core message into the source analysis §6.5 / Job E section.**

Do not proceed to the story angle, screenplay drafting, or any downstream work until the core message is explicitly confirmed.

Example from the spoolcast-explainer session: three candidates were proposed (architecture-thesis, outcome-focused, memorable-short-form). The user picked the outcome-focused candidate, then rephrased it in their own words. The final core message — *"Using AI video to get attention can be a passive process — and mostly automated — now"* — was materially sharper than any of the three proposals. Had the agent locked in its first guess instead of proposing and confirming, the video would have been pitched to the wrong audience.

Without a declared core message, the agent has no north star for what to cut vs expand, what to define vs assume, what to open on, or what the ending should answer. Attention drifts to whichever section is currently on the page, not to the one that matters most.

**Mechanical enforcement.** The confirmed core message is written into `session.json` as the `core_message` field (single sentence, locked). `scripts/audit_narration.py` runs a core-message alignment pass: for each beat, the auditor decides whether the beat serves the locked message — setup, evidence, analogy, payoff, generalization, or callback — or whether it's decorative / tangential / off-thesis. Off-thesis beats are flagged with a proposed fix (cut / rewrite / move). `build_preview_data.py` refuses to produce a final render while alignment flags are unresolved, on the same gate as layman and overweight. Without this enforcement, beats that felt important during drafting but don't actually serve the thesis tend to survive into the render.

###### Job F: deliverable-feasibility check — no creative commitment without confirmed deliverables

Before narration locks any claim that depends on specific deliverables being available, confirm those deliverables are actually available — existing on disk and matching the plan, sourceable within budget and time, or regenerable with available tools. This includes (but isn't named as) every shape of deliverable-dependent creative choice — visual artifacts, audio cuts, proof screenshots, real iteration outputs, cultural references, archival clips, anything the narration will name or imply a viewer should see.

What "confirm" means at this stage:
- The specific deliverable exists or can be produced
- Its actual content (not its label or intent) matches what the plan will describe
- Any quantitative commitment (*N distinct items*, *a before/after pair*, *a three-step progression*) has each element independently confirmed, not inferred from a collection's existence
- The verification uses the same rules as VISUALS.md § Asset Verification Principles — labels are hypotheses, content is evidence

If a deliverable is not confirmed, the narration must change at the planning stage — before it locks — to match what is actually deliverable. Do not draft narration that commits to specifics and hope the deliverable will materialize in production.

**Counter-balance clause — this rule must not be read as a bias.** The right response to a feasibility failure is to find or produce the missing deliverable, not to avoid creative commitments that require specific deliverables. Real artifacts, real iterations, and real evidence played on screen carry engagement illustrations alone cannot match. This check exists to make those stories *shippable*, not to nudge the agent toward safer alternatives. If the agent notices itself gravitating away from deliverable-heavy angles when proposing options, that bias is the thing this rule must not produce.

Failure mode this prevents: commit to a creative concept based on a source-material description (*"use the saga renders as an iteration-hell montage"*), draft narration around it, discover at production that the required deliverables don't exist in the needed form, rewrite mid-flight. The 2-second version: *"can we actually get these?"* gets answered before narration says *"these specific ones."*

##### 4. Pick the story angle only after the source analysis is done

Only after the source analysis existed was the story angle chosen.

The recommended angle was:

- “Meta built a model to predict brain-response patterns from video. The surprising part was not that it worked. The surprising part was what happened when its answer disagreed with the market.”

This choice mattered because it prevented the piece from collapsing into one of the two bad default versions.

Bad default version 1:
- “here is what TRIBE is”

Bad default version 2:
- “I tried a new Meta model and here is the result”

The chosen angle did something better:

- it made the mismatch the center
- it kept the session practical
- it gave the piece a reveal
- it made the conclusion earned instead of generic

##### 5. Draft screenplay v1 from the source-grounded spine

The first screenplay draft was not trying to be final.
It was trying to prove that the story spine could hold.

Version 1 did these things correctly:

- started with normal ad-analysis logic
- introduced the strange TRIBE premise quickly
- moved into setup friction
- ran the A/B experiment
- centered the model-vs-market mismatch
- treated runtime pain as part of the ending
- avoided overclaiming

That was enough for a valid first pass.

What version 1 was **not** trying to solve yet:

- exact comedic rhythm
- beat-level shot-board pacing
- cold-open punch
- chapterized structure
- line-by-line voiceover timing

Version 1 was essentially the “does this story work as prose?” pass.

##### 6. Rewrite into screenplay v2 for voice, pressure, and better line-level contrast

Version 2 was not just a polish pass.
It changed how the story sounded.

This pass did three main things.

###### A. Increased deadpan pressure

Examples:

- v1: “Which sounds either very advanced or mildly unreasonable. Possibly both.”
- v2: “Which is either impressive, concerning, or a very efficient combination of both.”

That change made the voice feel drier and less like a generic explainer.

###### B. Made the session feel more deliberately absurd without becoming jokey

Examples:

- v1 moved directly from the question into TRIBE explanation
- v2 inserted: “Because apparently just watching the ad was no longer enough.”

That line does real editorial work.
It tells the viewer how to emotionally read the premise.

###### C. Sharpened the conclusion into tool-type language

Version 2 got clearer that the real conclusion was not “good model” or “bad model.”
It was:

- this looks more like a research or interpretation layer than a winner-picker

That was an editorial classification, not a summary.

##### 7. Rewrite into screenplay v3 to match beatable video structure

Version 3 was the screenplay that matched the shot-board reality.

This pass did not just improve phrasing.
It restructured the screenplay into something that could be split into scenes and beats cleanly.

This is where the pipeline moved from “screenplay” to “screenplay that can become a shot list.”

The major changes in v3 were:

- stronger cold open
- chapter-worthy scene boundaries
- clearer “why this matters now” section
- explicit guardrail section about not literal mind-reading
- more bite-sized lines that can survive as independent voiceover units
- clearer pauses and reveal moments

Version 3 is where the script stopped being only readable and became buildable.

##### 8. Build the scene plan after the screenplay, not before it

The scene plan was written after the screenplay stabilized.

That order matters.

If the scene plan comes first, it tends to become a gallery of asset ideas.
That is not what it is for.

The scene plan should answer:

- what each scene is trying to make the viewer understand
- what visual job each scene must do
- what visual sourcing priority belongs there
- where local proof assets must be used
- where stock or generated assets are acceptable

For `tribe-session-001`, the scene plan became `tribe-session-001-b-roll-plan.md`.

That plan was organized by scenes like:

- Scene 1: cold open
- Scene 2: what TRIBE is
- Scene 3: why this mattered
- Scene 4: the real question
- Scene 5: setup friction
- Scene 6: experiment design
- Scene 7: guardrail
- Scene 8: model answer
- Scene 9: market answer
- Scene 10: what the mismatch means
- Scene 11: runtime reality

That is not just a production convenience.
It is proof that the screenplay had already been broken into meaningful editorial modules.

##### 9. Convert the screenplay into a beat-level voiceover script before building the shot list

Before the beat-level shot board was usable, the screenplay was rewritten into a voiceover script with one audio chunk per shot row.

This intermediate step mattered because screenplay paragraphs are still too large.

The voiceover script introduced:

- one row-sized line at a time
- named shot ids like `01A`, `01B`, `01C`
- pause planning (`none`, `short`, `medium`, `long`)
- scene-by-scene structure that could be timed

Example:

- screenplay v3 line cluster:
  - “What if a model looked at a video and tried to predict brain-response patterns from it?”
  - “Because apparently just watching the ad was no longer enough.”
  - “Brain-response patterns. You know. Casually.”

became separate beat units:

- `01G` “What if a model looked at a video”
- `01H` “and tried to predict brain-response patterns from it?”
- `01I` “Because apparently just watching the ad was no longer enough.”
- `01J` “Brain-response patterns. You know. Casually.”

That is the real bridge between screenplay and shot list.

##### 10. Build the shot list from the voiceover script, not from the transcript

The shot list was not made by summarizing the transcript into rows.
It was made by converting the already-structured voiceover script into beat rows.

For each shot-list row, the process was:

1. take one voiceover unit
2. assign it a shot id
3. assign it a rough duration
4. write the beat description
5. choose the background visual job
6. write movement
7. write interaction
8. write camera
9. write tone job
10. mark asset-to-find if unresolved

This is where “editorial understanding” becomes production structure.

For example, `01A` was not just “first sentence in transcript.”
It became:

- script: “Ads are everywhere now.”
- beat: ad world is saturated
- movement: layers drift and stack
- interaction: the frame should feel crowded before any analysis starts
- camera: constant small pushes
- tone job: stock ad-collage montage

That row shows why the screenplay mattered.
The shot list is not a transcript index.
It is a statement of how the narration should behave on screen.

---

#### Review-Artifact Policy (READ FIRST)

Across the whole Stage 1 pipeline, review happens at exactly these surfaces:

1. **Short version in chat** — used ONLY at two specific gates:
   - **After source analysis** (Job A–D written, Job E locked): short version = core message, spine, turning point, anti-claims, planned-vs-shipped flags, any review flags. User confirms the spine is right before screenplay drafting begins.
   - **After structure is proposed** (Act/chapter shape): short version = the bullet list of Acts with one-line per beat. User confirms the structure is right before screenplay drafting begins.
2. **Shot-list xlsx** — the single consolidated review artifact for the actual script. Narration, beat, background, camera, chunk — all visible in one scannable grid, per row. The user reviews the script by reading the xlsx, not by reading a prose screenplay.

Between screenplay v1, v2, v3 — **no short-version chat summary is sent for review.** Screenplay prose is a working doc written to disk for traceability only. The substance-before-form gate has already fired at the source-analysis and structure short-versions; the voice/pacing/line-level craft that v1→v2→v3 refines is best reviewed via the shot-list xlsx (where the viewer can see ten beats at once instead of scrolling a wall of prose).

Everything else — source analysis prose, screenplay v1/v2/v3 prose, scene plan, voiceover script — is a **working doc**. Working docs are written to disk for traceability, but are **not** linked to the user for review. The user should never have to open a markdown file to approve a stage.

Why: reading prose drafts is the highest-cost form of review. Short versions capture substantive (spine-level) decisions cheaply; the xlsx captures the concrete script completely and visually. Handing over v1/v2/v3 chat summaries between them turns review into a wall-of-text exercise where spine-level issues were already caught upstream.

A stage is not "ready for review" unless the agent has presented the appropriate artifact for that gate: short version in chat at source-analysis and structure gates; shot-list xlsx at the script gate.

#### Screenplay File Format and Workflow

Screenplay v1 / v2 / v3 are **working docs**, not review artifacts. Per the Review-Artifact Policy above, they are drafted to disk for traceability and are not reviewed in chat between versions.

The spine-level substance-before-form gate that used to live in per-version short summaries has moved upstream: it now lives in the **source-analysis short summary** and the **structure short summary** (see Review-Artifact Policy). By the time screenplay v1 drafting begins, the spine is already confirmed — what v1 → v2 → v3 does is refine voice, pacing, and line-level craft against that locked spine.

##### Required workflow

1. **Source analysis** written to disk. Short version presented in chat. User confirms spine.
2. **Structure** proposed in chat (short version). User confirms structure.
3. **Screenplay v1** drafted to disk. Proves the confirmed spine holds as prose. No chat review.
4. **Screenplay v2** drafted to disk. Voice / pressure / deadpan tuning pass. No chat review.
5. **Screenplay v3** drafted to disk. Beat-level rewrite — lines sized to survive as independent voiceover units. No chat review.
6. **Voiceover script** derived from v3 (one audio chunk per row), written to disk. No chat review.
7. **Shot-list xlsx** generated from the voiceover script + scene plan. User reviews the xlsx — this is the consolidated review surface where narration, beat, background, camera, and chunk are visible together.

##### Required on-disk file format (each screenplay version)

Each v1/v2/v3 file on disk begins with a short summary block at the top (for agent traceability and future-session context), then a `---` separator, then the full prose draft below. The fields mirror what the chat summary used to contain:

- **Core message (confirmed)** — one line from §3 Job E.
- **Spine** — ordered list of Acts/sections with one-line descriptions and target narration times. Running total at bottom.
- **What changed from the previous version** — bullet list (skip for v1).
- **Flags** — any ambiguities the agent wants to revisit when building the shot list.

This is a traceability artifact the agent may re-read later, not a user review artifact. It is not presented in chat.

##### Why the policy moved upstream

Drafting a full screenplay takes real effort; reviewing one shouldn't. The old policy caught spine-level issues by requiring a short version before drafting prose at every version gate. That is still the right principle — but the cheapest place to apply it is ONCE, at the source-analysis stage (catching the core-message / anti-claims / turning point) and ONCE, at the structure stage (catching the Act shape). After both are locked, v1 → v2 → v3 runs on disk without further chat gates, and the shot-list xlsx becomes the single consolidated review surface where narration + beat + background + camera can be seen together in one grid.

The failure mode the new policy prevents: short-version chat summaries piling up between v1/v2/v3 become wall-of-text reviews themselves, without actually showing the user more than they already saw at the structure stage. The xlsx is a better review surface for line-level craft because the visual grid shows pacing, repetition, and weight at a glance.

The test: by the time the xlsx is handed over, every spine decision should already have been confirmed upstream. The xlsx review should catch line-level issues (narration phrasing, beat pacing, camera / background choices), not spine-level ones.

This rule applies to every review point in the screenplay pipeline.

---

#### The four drafting checks (apply to every beat, every version)

Four checks the agent MUST run on every beat while drafting — screenplay v1, v2, v3, voiceover, and shot-list. These are not audit-only concepts. The audit (`scripts/audit_narration.py`) is a safety net; drafting is the primary filter. If drafting ignores them, the audit becomes the only barrier and the failure mode is late / expensive rework.

Apply each to the beat currently being written, BEFORE committing it to the draft.

1. **Alignment — does this beat serve the core message?**
   Name the beat's job toward the locked core message in one sentence: setup, evidence, analogy, payoff, generalization, callback. If the job is unclear or the beat would fit just as well in a different video, the beat is off-thesis — cut, rewrite to serve the thesis, or move elsewhere. See § Job E and the `core_message` field in `session.json`.

2. **Layman — can a non-technical viewer understand this beat from the narration alone?**
   Without having read any rule file, technical doc, or the project's glossary. If a technical term appears, the plain version must EITHER (a) be given in the same beat, OR (b) be established in an earlier beat still fresh in viewer memory. A beat can be short and well-paced yet still use a term the viewer has no frame for — those fail this check. See § Layman-first explanation rule for the general principle.

3. **Overweight — is this beat the right density for its position in the video?**
   Cold opens dense-quick. Middle sections relaxed. Proof / punchline moments slow. Could half the words be cut without losing the argument? Is jargon stacked? Are multiple concepts packed when they'd land better spread out? If yes: split, simplify, or cut.

4. **Bridge — does this beat follow naturally from the previous beat?**
   The viewer should not experience an unbridged orthogonal jump. Apply the viewer-cognition test: what is the viewer thinking after the prior beat — does this beat answer that thought, or introduce something the prior beat didn't set up? Valid bridge archetypes (setup-consequence, state-question, claim-evidence, problem-solution, comparison, strict tricolon, closing-conclusion, callback) handle the transition without an added bridge line; everything else needs one. See § Pairwise narration audit for the full archetype list and the deterministic post-filter rules.

**What these checks are for, in one line:** alignment keeps the beat on-thesis, layman keeps it understandable, overweight keeps it the right size, bridge keeps it in sequence. A beat can pass one and fail another — you run all four.

**Procedural integration:**
- Screenplay v1 drafting: run the four checks per beat before moving to the next beat.
- v1 → v2 rewrite: scan each v1 beat against all four; every rewrite must improve at least one check without regressing another.
- v2 → v3 rewrite: apply again at beat-breakable granularity, where individual lines must survive as single-beat narration units.
- Voiceover + shot-list: still apply — the shot-list is the last chance to catch before TTS generation locks the narration into audio.
- Audit pass: catches what drafting missed. A clean audit run indicates drafting worked; many flags indicate the checks weren't being applied during drafting.

**Failure mode this rule prevents:** agent drafts all three screenplay versions without applying these four checks beat-by-beat, produces narration that pattern-matches prior screenplays' jargon and structure, relies on the audit gate to catch issues, then bypasses the audit gate for convenience. The four checks then never fire at all. Happened on V2 (spoolcast-dev-log) — documented in DESIGN_NOTES.md as a cautionary case.

---

#### Gates Between Versions

These are concrete gates the screenplay must pass between draft versions. A draft that fails a gate isn't ready to move to the next version.

##### Viewer-orientation gate (v2 → v3)

The cold open must explicitly answer four questions inside the first ~30 seconds of narration:

- **What is this thing?** Name it.
- **Who is it for?** Stake out the audience.
- **Why should I keep watching?** Concrete pain or visible payoff.
- **What am I about to see?** Enough preview that the rest of the video is orientation, not confusion.

If any of these is only implicit, the cold open is not ready. This gate protects against the failure mode where the viewer is lost for the first 30-60 seconds because the script launched into concept before grounding them. Same failure mode observed in the TRIBE pilot's cold open.

##### Concept-inventory gate (v2 → v3)

List every non-obvious term the script uses in its argument — project-specific (*beat*, *chunk*, *image-ref*), technical (*deterministic*, *headless*, *HTTP request*), domain-specific. For each: is it defined before first use? If not, define at first use or cut the usage.

"Non-obvious" is judged relative to the target viewer implied by the core message. A developer audience doesn't need *HTTP request* defined; a general audience does. A reader of the spoolcast rules understands *chunk*; a first-time viewer does not.

This gate protects against the failure mode where central concepts carry the thesis but remain undefined — the viewer nods along without actually following the argument.

##### Layman-first explanation rule

Applies to everything presented to a viewer: narration in the final video, and chat output to the user during the build (structure proposals, plan summaries, option lists, fix explanations).

The rule:

1. **Lead with the plain-English version.** If an idea can be said in everyday words, say it that way first. A concrete analogy or a small scenario usually lands better than a definition.
2. **Technical terms are allowed — but only after the plain version exists, and only with a short in-line explanation the first time the term appears.** "Deterministic — meaning: same input, same output, no surprises." "Preprocessor — a script that prepares the image before the video is rendered."
3. **Never assume the reader has the jargon.** Default posture: the listener / reader has never seen this project before. Reading the rules docs does not count as viewer context for the YouTube audience, and it does not count as build context for a user who is making decisions at the substance level, not the implementation level.
4. **Don't test the rule against whether the reader *could* figure it out** — test it against whether the reader should have to. If the plain version was one sentence away, skipping it is a failure.

Concrete failure example (caught during V2 structure phase): the fix was presented as *"the rule-conflict protocol: surface, present (update / exception / keep), wait."* The user asked for the layman version. The plain version — *"the AI stops and asks the human to pick instead of silently overwriting the rule"* — was one sentence away and should have led.

The test: if a non-technical reader skims your explanation and walks away thinking *"I understood what this is doing,"* it passed. If they walk away thinking *"I got the general vibe but not the mechanics,"* lead with the layman version and keep the technical version as a second pass.

Applies equally to:
- **Narration** — the YouTube viewer is a stranger. Introduce every load-bearing concept in layman form before any technical framing.
- **In-chat presentation to the user** — the user is smart and the substance owner, but they are not pre-loaded on every mechanism. When proposing a fix, a structure, or a decision, lead with what it DOES in plain terms before naming the mechanism.

**Mechanical enforcement on the narration side.** The layman-first rule is procedurally enforced by the layman-accessibility pass in `scripts/audit_narration.py`. For each beat, the auditor asks whether a non-technical viewer can understand it from the narration alone — and flags beats that rely on unexplained jargon / terms-of-art / insider vocabulary. The auditor maintains a rolling glossary: a term flagged on first use is considered "established" for subsequent beats, so the rule catches first-use violations without punishing legitimate reuse. `build_preview_data.py` refuses to produce a final render while layman flags are unresolved; the only way past is to address the flag or build as an explicit preview via `--skip-audit --preview` (which writes a bypass marker so the render is not mistaken for final). Prose rules on this one lose to pattern-matching in agent drafting — the audit pass is what actually enforces the rule.

##### Timestamps, not chunk IDs

When referring to a moment in the video during chat, use the video timestamp (`0:42`, `1:15`, `3:28`) — not the shot-list chunk ID (`C14`, `C32`). Chunk IDs are build-time addresses; the user experiences the video as a time-indexed stream. A user reading *"adjust C14"* has no way to know where C14 falls in the video without opening the xlsx and counting. A user reading *"adjust 1:26"* can picture the moment immediately.

Chunk IDs are fine in on-disk artifacts (shot-list, screenplays, scene manifests, logs) — they're the right primary key there. The rule is about chat output to the user during review gates.

When both the user and the agent need to refer to the same beat, prefer *"the 1:26 beat about rule rewriting"* — timestamp plus a short semantic anchor — over either identifier alone. Pure timestamps can drift if the shot-list re-times; the semantic anchor survives.

##### Full filepaths, not repo-relative

When referring to a file on disk in chat, use the absolute filepath (`/Users/.../spoolcast-content/sessions/.../shot-list.xlsx`), not a repo-relative path (`sessions/.../shot-list.xlsx`) or a content-root-relative path. Relative paths only resolve for a reader standing in the right working directory; absolute paths open from anywhere. The user is not standing in the agent's cwd — they're in a chat window. Make paths clickable on first mention.

Exception: on-disk canonical doc contents (the rule files themselves, written artifacts meant to be read inside the repo) use relative paths because the doc's own context resolves them. The rule is about chat, not about persistent files.

---

#### Heuristics I Actually Used

These are not abstract principles.
These are the rules that were actually applied.

##### 1. Find the practical question first

If the session starts from a practical goal, that goal should anchor the story.

For `tribe-session-001`, the real opening question was not:

- what is TRIBE?

It was:

- can TRIBE say something useful about ad quality in a real workflow?

That single choice made the video much better because it gave the viewer a job immediately.

Rule:
- start from the thing that someone was trying to figure out in practice
- use the technology explanation only after the viewer has a reason to care

##### 2. Treat friction as part of the story if it changes the conclusion

Not all setup pain belongs in the final story.
Only include it if it changes what the session means.

In this case, setup friction stayed because it proved:

- the workflow was not lightweight
- the tool was not production-ready
- runtime pain was part of the answer, not just an annoyance

Rule:
- keep friction if it changes the viewer’s final judgment
- cut friction if it is only “we had some trouble along the way” filler

##### 3. The turning point is where the interpretation changes, not where the data appears

This is one of the most important rules.

The turning point was not:

- when TRIBE produced output

The turning point was:

- when TRIBE favored Video A, but real ROAS favored Video B

That is the moment where the viewer has to reclassify the tool.

Rule:
- the turning point is the moment that changes what the result means
- not merely the first chart, first output, or first “success” moment

##### 4. Make the ending answer the opening question in a stricter form

The opening question was:

- can this help judge whether a video ad is good or bad?

The ending answer became:

- it can produce structured signals worth studying, but not signals reliable enough to trust on their own or cheap enough to use as a normal scoring layer

That matters because the ending is not a vague recap.
It is the opening question answered under pressure.

Rule:
- the ending should not just summarize events
- it should answer the session’s real starting question with more precision than the opening had

##### 5. Humor should come from contrast, not punchlines

This piece worked best when the humor came from:

- very serious subject matter
- very matter-of-fact delivery
- slightly absurd implications

Examples that worked:

- “Because apparently just watching the ad was no longer enough.”
- “Brain-response patterns. You know. Casually.”
- “It was not immediately persuaded.”
- “this was less quick scoring pass, and more excellent, the rest of the day has made other plans.”

What did **not** work:

- winky internet jokes
- meme phrasing
- trying to make every section funny
- sarcasm that made the experiment sound fake or unserious

Rule:
- humor lands best when the script stays calm
- the narration should sound like it is underreacting to something inherently strange

##### 6. Guardrails belong where the viewer is most likely to overinterpret

The line “TRIBE is not reading a real person’s brain” did not exist just because it was accurate.
It existed because that is exactly where a viewer would overclaim what the model is doing.

That is why v3 carved out a separate guardrail scene.

Rule:
- put anti-misunderstanding language at the exact moment the misunderstanding becomes likely
- do not save it for a footnote at the end

##### 7. A screenplay is ready for shot-list conversion when the lines can survive alone

If a screenplay paragraph only works as a paragraph, it is not ready.

The shot list needs lines that can survive as separate beats.

Example:

This works as separate beats:

- “And the output was not random noise.”
- “TRIBE-style signals favored Video A.”
- “Video A showed the stronger early hook.”
- “Several target regions also leaned higher for A.”
- “If the model had been allowed to cast a confident vote, it would have had opinions.”

That section can become a scene because each line has one job.

Rule:
- if a sentence is carrying two different ideas, split it before the shot-list stage

##### 8. Use outside-world context only if it strengthens the session question

The Meta timing context was added in v3, but it was bounded.
It served one purpose:

- why did this feel worth looking at right then?

It was not allowed to turn into a generic state-of-the-AI-race paragraph.

Rule:
- outside context is allowed only if it increases the stakes of the session’s actual question
- if it pulls the piece away from the session, cut it

##### 9. Every beat in the shot list should answer “why this visual now?”

This is the rule that separates real shot planning from transcription.

For every shot row, there should be a reason the visual changes **now**.

Example:

`01F`:
- script: “Then we wanted to ask a much stranger question.”
- visual change reason: the frame has to pivot from familiar metrics into something that feels stranger

If there is no reason for the visual change, the row is under-specified.

##### 10. Do not let proof assets take over the piece

Official proof matters.
But proof is not the story.

The official TRIBE page/model card was useful as a scene element.
It was not strong enough to carry the main scene visually.

Rule:
- use proof inserts briefly to prove reality
- use stronger concept visuals to carry the scene emotionally and editorially

##### 9a. Cold-open visual density

The cold open — roughly the first 10-15 seconds — is where viewer attention is most fragile. Decisions about whether to keep watching happen here. A slow visual pace loses viewers before the premise lands.

Rules for the cold open specifically:

- **Chunks must rarely exceed 4 seconds.** Most should be single-beat chunks.
- **Target image-change cadence of once every 2-3 seconds** — significantly denser than the rest of the video's 7-10 second average.
- **Never hold one image across 3+ beats in the cold open.** If a narration block has 3 distinct thoughts, split the chunk three ways, one image per thought.
- **Overlays, meme spikes, and micro-panels all count toward visual variety** — anything that changes what's on screen while narration runs.

The density curve across a video: **very dense (0-15s) → dense (15-60s) → normal pacing (rest)**. This is intentional, not uniform.

Concrete: a narration block like *"You build things. Getting attention for what you built is a separate job. Different skills. Different time. Different energy."* in the cold open probably wants each sentence as its own chunk — three images in ~7 seconds, not one image across all three. The tricolon *"Different skills / Different time / Different energy"* can even be a three-panel micro-montage inside a single chunk if that lands cleaner than three separate chunks.

Outside the cold open, this rule relaxes — long multi-beat chunks are fine past the 15-second mark because the viewer has already committed. Within the cold open, they're a failure mode.

##### 9a-2. Cold-open → Act 1 handoff: continuous, not reset

The cold open ends on a thesis-shaped line (a punchline, a reveal, a reframe — the line that tells the viewer what this video is really about). The first line of Act 1 must build on that line, not start a fresh "let me set up a story from scratch" introduction. A reset breaks the handoff and the viewer experiences a jump.

The failure mode: cold open lands *"A rule you rewrite every time you break it is not a rule. It's a log."* — a conclusion — and then Act 1 opens with *"I was building a project with an AI partner."* — a neutral setup that would also fit the first line of a completely different video. The viewer has just been told the ending of the thesis; going back to generic setup feels like starting over.

The fix, applied per-chunk: the first beat of Act 1 must reference, answer, or build on what the cold open just established. It can do any of:

- **Name the subject.** If the cold open said *"rules that mutate are logs,"* Act 1 can open with *"I learned this the hard way, building a project with an AI partner."* — now the setup is explicitly the evidence for the cold-open claim, not a new topic.
- **Take the cold open as a given and proceed.** *"Here's how that happens in practice."* — treats the cold open's conclusion as premise.
- **Ask what the cold open just made you ask.** *"So how do you write rules that don't do that?"*

Diagnostic: read the cold open's last line and the Act 1 opener aloud, in sequence. If the Act 1 opener would work equally well as the *first* line of the video (no cold open preceding), the handoff is broken.

Applies to the cold-open → Act 1 handoff only; later Act transitions have their own bumper + opener contract (see § Acts are the editorial unit). This is specifically about the cold-open's thesis-landing → setup-of-story transition, which the bumper system doesn't protect.

##### 9b. Meta-rules are demonstrated, not listed

When a video is ABOUT a specific system or pipeline, the content catalog should cover the **specific craft unique to that system** — not the meta-rules that apply to any scripted video.

Meta-rules like *"declare a core message,"* *"define terms before first use,"* *"orient the viewer in the cold open"* are real and important — but they belong in `STORY.md`, not in the video's content. The video should *demonstrate* those meta-rules by following them, not narrate them as items in a catalog.

Why: if a video prescribes these meta-rules to the viewer, it becomes a video about "how to make videos." That's a different video, with a different audience and a different core message. When covering a specific system, trust the viewer to absorb the meta-craft implicitly from watching it applied.

Concrete example: the V1 spoolcast-explainer video has an "anti-slop processes" catalog (Scene 3). The catalog does NOT include:
- "declare a core message" (meta — video demonstrates by having one)
- "define terms before first use" (meta — video demonstrates by defining *beat* and *chunk* before using them)
- "orient the viewer in the cold open" (meta — video demonstrates by passing the viewer-orientation gate in its own cold open)

The catalog DOES include:
- chunks-not-beats-as-image-unit, throughline-matching, 15-sec split rule, beat rewriting, TTS pronunciation, editorial judgment stays human.

Those are spoolcast-specific craft. They belong in the video because they explain the *subject* of the video. The meta-rules that shaped how the video itself was written are out of scope for the video's content.

The test: if an item in your catalog would still be relevant if the video were about a different system, it's meta — demonstrate it, don't list it.

##### 10a. Deadpan punchline beats get their own single-beat chunk

Short beats that carry comedic weight — one-word reactions, deadpan capstones, understated asides like *"Obviously."*, *"You know, casually."*, *"Structurally, it was."*, *"That's the whole trick."* — need their own chunk so the image changes at the exact moment the line lands.

When a punchline is buried mid-chunk, the visual stays constant and the joke has nothing to punctuate it. The reveal of a new image IS the rhythm that makes the deadpan line land.

**How to identify a punchline beat:**
- Short (under ~6 words is the sweet spot).
- Deadpan tonality — matter-of-fact, slightly absurd when you think about it.
- Often a capstone to a preceding setup ("Close enough that nobody notices.").
- Rhythmically distinct from its neighbors (surrounded by longer, more technical lines).

**Punchline visual options** (see `VISUALS.md` carve-out for the allowed range):
- Same style-anchor character with an exaggerated reaction face.
- A real meme / reaction gif / cultural reference image, full-frame, deliberately breaking the anchor style. Spike device, not a running visual — each one must independently pass the contrast + specificity test (§ Broll earns attention) AND carry its own distinct recognition the viewer can pin in half a second.

**How many memes?** No hard budget, no subject-type classification. The test is per-beat, not per-video: does removing this meme weaken the beat it lands in? If yes, keep it. If it's there for decoration or humor-for-its-own-sake, cut it. Count is a consequence of applying the per-beat test honestly — a subject that benefits from tone counterweight will naturally earn more memes; a subject that doesn't will earn fewer. Don't target a number either way.

Guardrails that keep memes working as spikes:
- No repeated memes — a repeat isn't a spike.
- No back-to-back memes within ~30 seconds — clustering collapses the spike effect. If two earn their slot close together, space them by moving one or drop the weaker.
- If memes start feeling like a running visual device rather than punctuation, the per-beat test is being applied loosely — recheck each one against "does removing this weaken the beat?"

Not an overlay in either case — the punchline chunk's image replaces the scene for that beat, preserving the one-visual-layer rule.

##### 11. Effort is not importance — weight by core-message service only

The amount of time, effort, or iteration spent on something during the project is NOT a signal of whether it deserves screen time in the video. Two failure modes this protects against.

**Inflating the saga.** A feature that took ten iterations to get right is not automatically video-worthy. If the final result doesn't serve the core message, the journey behind it doesn't either. Concrete example: a pilot session burned multi-day stretches on the chalkboard-wipe transition, iterating through nine visually-distinct attempts before one landed. That effort was real. But if the next video's core message is "passive content for builders," the chalkboard saga doesn't serve it — cut it entirely. Do not even mention it. Time spent does not buy screen time.

**Underweighting the breakthrough.** A decision that took minutes can be the most important thing in the video. Concrete example: image-ref chaining — the insight that passing a prior generation's URL back as a reference image locks style across scenes — is maybe twenty lines of wrapper code and a short afternoon realization. But it's the mechanism that makes every downstream illustration consistent, and deserves significant screen time. Cheap to produce does not mean small to explain.

The test is always: **does this serve the core message**. If yes, weight it by how much it delivers the message — regardless of how cheap or expensive it was to produce. If no, cut it regardless of how much time you spent on it.

**Related — concrete over abstract.** Specific concrete processes are always stronger video content than abstract meta-commentary about the same topic. *"We iterated on the reveal animation until the vibe was right"* is weaker than *"the per-pixel reveal-time map assigns each pixel a time between zero and the chunk's duration; connected components reveal in parallel."* When in doubt about how to cover a section, go concrete. Abstract decision-making process is usually less interesting than the specific craft moves that resulted from those decisions.

---

#### Patterns Observed, Not Yet Rules

##### Payoff preview in the cold open

For explainer-style videos where the output is itself visible (e.g. a video about a system that produces videos), inserting a 5-10 second preview of the actual output inside the cold open can turn later technical sections into callbacks rather than abstractions. When the viewer has already seen what the system produces, every technical beat becomes "here's how that thing you just saw gets made" — stronger than "here's a thing I'll describe."

Observed to help in one session. Not yet a hard rule — a cold open can succeed without it when the viewer-orientation gate is passed cleanly. Consider when the output is concrete and recognizable in a few seconds. Does not apply to narrative / dev-log videos where the output *is* the story itself, or to videos where the output only makes sense after the full explanation.

---

#### Three Real Editorial Decisions Between Screenplay v1, v2, and v3

These are specific changes that mattered.

##### Decision 1: Change the opening from “ordinary tool explanation” to “ad-saturated world”

In v1, the opening was:

- “Most ad analysis tools do something very normal.”

That is clear, but it is not very visual and it enters as explanation.

In v3, the opening became:

- “Ads are everywhere now.”
- “Which means everybody is trying to make theirs work better.”
- “And most ad-analysis tools do something very reasonable.”
- “They look at click-through rate, watch time, conversion rate, and ROAS.”

Why this change mattered:

- it made the opening visual before it became technical
- it created a normal-world baseline
- it gave the later TRIBE premise something to interrupt
- it split the introduction into lines that could actually become separate beats

Principle this proves:
- open on a world the viewer already understands
- then introduce the strange question as a disruption of that world

##### Decision 2: Insert the explicit absurdity line before the formal explanation

Version 1 moved into the TRIBE explanation relatively cleanly.
Version 2 inserted:

- “Because apparently just watching the ad was no longer enough.”

Version 3 kept it and then followed with:

- “Brain-response patterns. You know. Casually.”

Why this change mattered:

- it told the viewer how to emotionally read the premise
- it created deadpan pressure before the exposition arrived
- it made the explanation feel like a real escalation, not just documentation

Principle this proves:
- when the premise is inherently weird, name the weirdness before explaining the mechanism
- otherwise the script becomes dry too early

##### Decision 3: Add a dedicated guardrail scene about not literal mind-reading

In earlier drafts, the anti-overclaim was present as a note or implication.
In v3 it became a real scene:

- “Not in a mystical way.”
- “Not in a literal mind-reading way.”
- “TRIBE is not reading a real person’s brain.”
- “It is predicting response patterns from the content of the video.”

Why this change mattered:

- it protected the piece from fake-sci-fi drift
- it kept the conclusion honest
- it created a clean reset between experiment design and model answer
- it made the later mismatch easier to trust because the piece had already drawn its own boundaries

Principle this proves:
- if a viewer is likely to overread the system’s power, install a guardrail scene before the result scene

##### Decision 4: Shift the final takeaway from “interesting experiment” to “category of tool”

Version 1 already implied that TRIBE was more useful as a research layer than a winner picker.
Versions 2 and 3 made that much more explicit and central.

This was not just wording.
It was a change in the kind of answer the piece offers.

Instead of ending on:
- the experiment was honest

it ended on:
- this tool belongs in a different category than the original question hoped for

Principle this proves:
- the best conclusion often classifies the tool, not merely reports the result

---

#### Quality Tests: How I Knew The Screenplay Was Ready

The screenplay was ready when it passed all of these tests.

##### 1. Source-grounded test

Could every important claim be traced back to the source package?

For this session, that meant:

- no invented setup details
- no fake screenshots treated as evidence
- no hype language about TRIBE reading brains
- no invented business metrics

If a line felt good but could not be defended from source, it had to go.

##### 2. Story-shape test

Did the piece actually have this shape?

- practical question
- friction
- experiment
- turning point mismatch
- interpretation
- operational conclusion

If one of those stages was missing, the piece tended to flatten into either summary or explainer mode.

##### 3. Turning-point clarity test

Was the mismatch clearly the center of gravity?

If the viewer could finish the piece and still think the main point was “Meta made a weird model,” the script was not ready.

The viewer should come away with:

- the useful part was the disagreement between model reward and market reward

##### 4. Beatability test

Could the script be broken into separate lines without destroying the logic?

This is the bridge to the shot list.

If too many lines required the neighboring sentence to make sense, the piece was still in essay form and needed another pass.

##### 5. Visualability test

Could each major section imply a clear visual job?

Examples:

- ad-saturated world
- ordinary metrics world
- TRIBE premise world
- setup friction / terminal / auth pain
- experiment-design explainer
- model answer
- market answer
- runtime reality

If a section had no obvious visual job, it was usually too abstract and needed rewriting.

**Extension — visual-sketch first, text-card last.** When drafting each narration line, sketch the scene in your head alongside the words — *"narrator leaning toward laptop, frustrated"*, not just *"the line the viewer hears."* If you can't picture a scene for a line at writing time, the line is too abstract and should be rewritten before it reaches the shot-list. Text-cards (handwritten line on a clean page) are a *last-resort* visual — valid only for the cold-open hook, the single thesis-landing moment, and the channel sign-off. Everything else gets a visible action / character / scene. Reaching for typography as the default for "important" beats is the anti-pattern — it reads as weighty in the writer's head and as dead air in the viewer's eye. If an important line can be *shown* with a character reacting, an object changing, or a diagram landing — that's almost always better than putting the line on a page.

##### 6. Tone-control test

Was the piece dry without becoming smug?

The deadpan tone had to do three things at once:

- keep the subject serious
- let the absurdity land
- avoid sounding like the script was mocking the work

If the humor made the whole experiment feel unserious, that version had to be rejected.

##### 7. Ending-answer test

Did the ending answer the opening question more precisely than the opening asked it?

If the ending was just:
- this was interesting

it failed.

If the ending said:
- useful signals, wrong category, too heavy operationally

it passed.

---

#### What Would Have Made Me Reject The Screenplay

Any of these would have been rejection-level failures.

- The piece opens by explaining TRIBE before establishing the practical reason to care.
- The mismatch between TRIBE’s preference and market outcome is not the main reveal.
- The script implies literal mind-reading.
- The script sounds like a hype video for Meta research.
- The script becomes too dependent on screenshots that do not actually exist.
- The humor becomes internet-jokey instead of deadpan.
- The ending does not answer the opening question directly.
- The lines are too long and essay-like to survive conversion into beat-level narration.
- The piece contains scene paragraphs that cannot be assigned a clear visual job.

---

#### Things I Tried, Or Nearly Tried, That Did Not Work

These false starts matter because future agents will naturally drift toward them again.

##### 1. The generic “what is TRIBE?” explainer opening

This is the most tempting bad version.

It sounds reasonable because the tool is unfamiliar.
But it weakens the story because it starts from explanation instead of stakes.

Why it failed:
- it made the piece about the model instead of the workflow question
- it removed pressure from the first minute
- it delayed the viewer’s reason to care

##### 2. Treating setup pain as just a comedy section

The setup friction was funny in places, but keeping it only for comic relief would have been wrong.

Why it failed:
- the friction actually changed the conclusion
- runtime pain and environment pain were part of the answer
- reducing them to “funny failure montage” would have weakened the operational takeaway

##### 3. Letting outside Meta / AI-race context take over the piece

There was a real temptation to build a broader “where Meta sits in AI” section.

Some of that context was useful.
Too much of it pulled the piece away from the actual session.

Why it failed:
- the story stopped being about a real test and became industry commentary
- it delayed the experiment itself

##### 4. Writing paragraphs that sound good but cannot be shot

Some screenplay prose can sound polished but collapses when converted into beats.

Why it failed:
- it created rows that had no clear visual change
- it forced too much information into single lines
- it made pacing control much harder later

##### 5. Relying on missing screenshots

The package contained many missing screenshot references.

Why it failed:
- the visuals were not actually available
- building the story around them would have made the piece fragile and fake-specific
- the solution had to be concept visuals, official proof inserts, diagrams, and reconstructed explainer assets instead

##### 6. Treating the result as a clean victory or a clean failure

Both of those were weaker than the actual truth.

Bad version A:
- the model worked, amazing

Bad version B:
- the model was wrong, useless

Why both failed:
- both destroy the real value of the mismatch
- both flatten the tool into a binary judgment the session did not earn

---

#### Rules I Wish The Original Spec Had Said Explicitly

These are the taste decisions that were applied in practice and should now be treated as explicit rules.

##### 1. The first draft after the transcript should be a source analysis, not a screenplay

Do not go raw package -> screenplay.

Always do:
- raw package -> source analysis -> screenplay

Without the source analysis step, the turning point is too easy to miss.

##### 2. The story angle must be chosen before draft v1

A screenplay should not begin as open-ended paraphrase.
It needs a declared story angle.

For example:
- “the surprising part was not that it worked, but what happened when it disagreed with the market”

That angle should exist before prose drafting begins.

##### 3. The turning point must be named explicitly in analysis docs

Do not assume it will remain obvious later.
Write it down.

If the source analysis does not name the strongest turn in a sentence, the screenplay will drift.

##### 4. Humor must come from underreaction

The system should explicitly say:

- do not write jokes first
- write the sentence straight
- let the absurdity create the humor

##### 5. The screenplay is not ready until it can be split into beat-sized lines

This should be a formal gate, not a vague preference.

If the screenplay still behaves like an essay, it is not ready for scene plan or shot list.

##### 6. Every scene needs a visual job before shot-listing begins

Not a visual asset.
A visual job.

Examples:
- saturate the world with ads
- re-establish ordinary metrics logic
- introduce the weird TRIBE premise
- cancel the chatbot frame
- show the experiment variables clearly
- prove the mismatch

##### 7. Guardrails should be treated as story beats, not cleanup notes

If the subject invites a predictable misunderstanding, put the correction into the main structure.
Do not hide it in notes or rely on the narrator’s tone to fix it.

##### 8. The ending should classify the tool, not merely review the experiment

The strongest endings answer:
- what kind of thing is this actually?

That is better than simply repeating the results.

##### 9. The core message must be declared before drafting AND confirmed with the user

See §3 Job E. One sentence naming the single thing the viewer must come away with. Every section either serves that message or gets cut. Section importance is downstream of this, not declared independently.

The core message is too load-bearing to guess. Always propose 2-3 candidates in plain language, name the tradeoffs, and wait for the user to confirm or rephrase. Never write a guessed core message into the source analysis and proceed as if it's locked — that's a substance-before-form violation (`rules.md`) dressed up as progress.

Two gaps this closes: first, without a declared core message the agent treats sections with roughly equal weight, diluting the sections that carry the thesis. Second, a guessed core message that sounds plausible can lock in the wrong framing for the entire video — the user then spends iterations reacting to downstream effects without realizing the root cause is upstream.

##### 10. The cold open must pass the viewer-orientation gate

Four questions answered explicitly in the first ~30 seconds: what is this thing, who is it for, why should I keep watching, what am I about to see. See "Gates Between Versions" above.

##### 11. Every non-obvious term must be defined before first use

Relative to the target viewer implied by the core message. See the concept-inventory gate under "Gates Between Versions."

##### 12. Every screenplay version is a two-step workflow: short version, confirm, then prose

Not just a file-format requirement — a workflow enforcement. Write the short version first. Present it directly in chat (not via file link). Stop. Wait for explicit user confirmation that the spine is right. Only then draft the full prose.

See "Screenplay File Format and Workflow" above for the enforced steps. A draft that was written in a single turn — short version and full prose together, with the short version only visible inside the file — violates this rule even if the file is formatted correctly.

The test: if the user has not explicitly said the spine looks right, the full prose should not exist yet.

##### 13. Effort spent is not importance

See heuristic 11 above. The amount of time, iteration, or struggle that went into a piece of work is not a signal of whether that work deserves space in the video. Don't let a long saga get covered just because it was expensive. Don't let a quick decision get underweighted because it was cheap. The core message is the only test.

Concrete trap to avoid: during drafting, the agent often over-weights content that was recently or heavily worked on — editorial decisions the agent just wrote rules about, iteration sagas that felt substantial in memory — because that work is vivid. Vividness in the agent's working memory is not evidence of relevance to the viewer. Filter every candidate section against the core message. If a section passes only because "we did a lot of work on this," cut it.

##### 14b. Cold-open density is not uniform across the video

The first ~15 seconds should hit at 2-3 sec per chunk. After that, pacing relaxes to the session's normal 7-10 sec average. See heuristic 9a. A video with uniformly slow pacing loses attention in the cold open; a video with uniformly fast pacing exhausts the viewer in the middle.

##### 14c. Demonstrate meta-rules; don't list them in the video's content

When the video is about a specific system, cover the system-specific craft. Meta-rules that apply to any scripted video (core message, concept-inventory, viewer orientation) are demonstrated by the video itself, not named as catalog items. See heuristic 9b. Putting meta-rules inside the content turns the video into "how to make videos" — wrong subject, wrong audience.

##### 14a. Planned-vs-shipped distinction must be explicit

Every system component the video describes must be clearly marked as shipped, planned, or speculative. See §3 Job D-1. Language like *"still being built,"* *"the next piece,"* *"once it's wired up,"* *"designed to work this way"* is required for planned components. Never use present-tense framing that implies a planned thing is already shipped — viewers can tell, and getting caught once poisons every other claim in the video.

##### 14. Concrete craft beats abstract commentary

See heuristic 11 "related" paragraph above. When covering a section, choose the specific concrete process over the abstract description of the decision-making that produced it. Viewers learn from watching the actual move; they glaze over descriptions of how moves are chosen. Every time a draft reaches for "we thought carefully about X" or "we decided that Y," check whether the concrete move can replace that sentence. Usually it can.

---

#### The Short Version To Remember

The actual method was:

1. stabilize the package
2. read for the practical question, not for summary points
3. write source analysis first — including the declared core message and anti-claims
4. identify the strongest turning point
5. choose the story angle
6. write screenplay v1 around the spine
7. rewrite for voice and pressure; pass the viewer-orientation and concept-inventory gates
8. rewrite again for beatability and scene structure
9. build the scene plan from the stabilized screenplay
10. build the voiceover script from the screenplay
11. build the shot list from the voiceover script

The main rule underneath all of it:

Do not confuse “what happened in the session” with “what the story is.”

The raw package tells you what happened.
The editorial work is deciding what the session **means**, and then writing only enough of the session to prove that meaning.

## Part 2 — Pacing and Viewer Context

### Purpose

Part 1 produces the narration. Part 2 governs how that narration lands on the viewer: the breathing room between thoughts, the signals at each transition, and the context a viewer needs to follow along.

The root failure mode this part prevents: treating every cut as equal weight. When beat-to-beat, chunk-to-chunk, topic-shift, and Act-boundary transitions all get the same half-second pause, the viewer loses orientation at every big shift. This part makes transition signals proportional to the size of the shift, and bakes those requirements into the shot-list schema so the pipeline can't render a video that violates them.

### The meta-rule

**Every beat, and every adjacent pair of beats, must be calibrated to viewer cognition at that exact moment of the video.** There are two symmetric failure modes:

- **Underweight — the viewer has a gap they can't bridge without effort.** Not enough context, missing connective tissue, topic/emotional jumps that skip the reasoning. Fix: add a bridge beat, add context, extend the pause.
- **Overweight — the viewer has more detail than they can absorb or care about.** Density too high, jargon stacked, decorative precision, multiple concepts in one beat when they'd land better spread out. Fix: cut, simplify, split across beats.

Both failures produce the same observable symptom — the viewer zones out. Diagnose which direction the calibration is off, and correct in that direction.

Structural categories (beat-boundary / chunk-boundary / Act-boundary) follow from this principle. They exist to match the size of the signal to the size of the shift, but they're secondary to the viewer-cognition test. A transition that's structurally "continues-thread" but has an unbridged logical jump still fails Part 2.

### The viewer-cognition test (apply to every adjacent beat pair)

For every adjacent pair of beats (not just chunks — every pair, inside and across chunks):

1. Read beat N aloud. Stop.
2. Ask: *what is the viewer thinking at this exact moment? What question naturally forms in their head?*
3. Read beat N+1.
4. Does N+1 answer that question, or does it introduce something orthogonal?
5. If orthogonal → **bridge beat missing** (underweight failure). Insert a beat that connects.
6. Separately: is beat N+1 itself overloaded? Could half of it be cut without losing the argument? If yes → **simplify** (overweight failure).

Applied concretely:

- **Anti-example (underweight, V1):** *"You build things."* → *"Getting attention for what you built is a separate job."* The viewer's implicit question after "You build things" is *"…and?"* or *"okay, something happened with the thing?"* — not *"wait, is attention the problem?"* The jump skips the emotional beat that makes the problem land. Fix: insert *"It came out great. Now what?"* between them. The viewer follows the arc.

- **Anti-example (overweight, hypothetical):** *"The real fix is a Python script that computes a per-pixel reveal-time map based on the chunk's duration and the component's position relative to the centroid."* Packed, decorative, the viewer glazes. Fix: split across beats AND simplify — *"The real fix is a Python script. It paints the image stroke by stroke. Bigger shapes start early, small details fill in later."*

### Bridge archetypes

When inserting a bridge or rewriting a beat to connect, use one of these patterns. If an adjacent pair doesn't fit any archetype and the second beat isn't the obvious next thought, the bridge is genuinely missing.

| Archetype | Shape | Example |
|---|---|---|
| **Setup → consequence** | fact → what it means | "X happened. Which means Y." |
| **State → question** | experience → implied question → answer | "You build things. It came out great. Now what?" |
| **Claim → evidence** | assertion → proof | "X is true. Watch this — here it is." |
| **Problem → attempt → failure** | pain point → naive fix → why it fails | "The naive fix is a CSS wipe. It's robotic every time." |
| **Problem → solution** | pain point → real fix | "Total per video: a coffee." |
| **Comparison → judgment** | two things → which wins | "A does this. B does that. B is what we chose." |
| **Enumerated list** (strict — see below) | explicit markers signal "list coming" — no bridge between items | "One. Images grouped by chunk. Two. Images show throughlines. Three. Chunks cap at 15 seconds." |
| **Tricolon / anaphora** (strict — see below) | parallel grammar + repeated opening word, structure does the work | "Different skills. Different time. Different energy." |
| **Closing / conclusion** | signals the wrap-up is starting — callback to opening, recap framing, or explicit "so..." | "So where does this leave us?" / "Which brings us back to…" / "In short." |
| **Callback** | explicit reference to earlier establishment | "Remember the layer diagram? This is layer three." |

#### The enumerated-list archetype is STRICT

"Enumerated list" only qualifies — and only then suspends the bridge requirement between items — when the list is *explicitly marked* as a list. Required signals (at least one):

- **Ordinal markers** leading each item: *"One. … Two. … Three."* or *"First. … Then. … Finally."* or *"Step 1. … Step 2."*
- **"Here are X things"** or equivalent upfront enumerate-framing ("There are four of them. The first is…")

Beats that are merely *adjacent parallel statements* without these markers DO still need bridges. Items can be short and syntactically similar — that's not enough. Without an explicit list signal, the viewer has no frame for treating these as members of a list rather than a jumpy sequence of separate thoughts.

Anti-example (previously mislabeled as "enumerated"): *"Story. Script. Images. Animation. Camera. Timing. Rendering."* — six nouns in a row is a word-dump, not a list. Either mark it explicitly (*"The generic model does all of it. Story. Script. Images…"*) or bridge between items.

Anti-example: C22's budget breakdown — *"Images — roughly one to three dollars. Voice — Google Cloud. Free within the monthly tier. Animation and render — both run locally. Zero cloud cost."* These read as adjacent parallel statements but have no enumerator. Either add *"Three costs. One: images…"* or let each line bridge the next.

#### The tricolon/anaphora archetype is STRICT

"Tricolon" only qualifies when ALL of these are present:

- **Three (or very rarely four) items, not more.** Longer lists stop reading as rhythmic parallel and start reading as a dump.
- **Same opening word or phrase on each item** (anaphora): *"Different skills. Different time. Different energy."* / *"AI voice. AI images. AI title."*
- **Grammatically identical structure** across items.
- **Short** — each item fits in one short sentence.

When all four are true, the parallel structure itself is the bridge; the rhythm carries the viewer. If any one is missing, treat as adjacent-statements and apply normal bridge requirements.

This test is how a future reviewer (human or bot) decides whether parallel-looking text actually qualifies for the no-bridge-needed carve-out. Default is "needs a bridge" unless the stricter test passes.

### Reveal groups

A **reveal group** is a named set of adjacent chunks that play as one rhetorical unit. The canonical case is a setup-turn-punchline arc like *"You build things." / "It came out great." / "Now what?"* — three illustrations, but one rhythm. Per-chunk reveals between them fragment what should be one beat.

**Visual behavior inside a group:**
- First chunk: normal reveal-in per its `reveal_type`. Its wipe-out is suppressed (the group keeps going).
- Middle chunks: both wipe-in and wipe-out suppressed. The chunk appears at its final frame instantly, disappears the same way.
- Last chunk: wipe-in suppressed. Normal reveal-out if specified.
- Audio and camera: completely unaffected. Pauses still play, camera interpolates normally.

**Cadence inside a group:**
- Default pause between chunks inside a group is **0.15s** (one quick breath, ~4 frames at 30fps), not the normal 0.3s. The tight pause is what creates the BOOM-BOOM-BOOM rhythm. Reveal suppression alone isn't enough — a normal 0.3s pause still reads as "pause, new thought."
- Author can override `pause_after` per-beat if a specific pause needs room.
- The pause on the **last** beat of the group is normal — the final beat lands before the next idea begins. That breath is part of the joke.

**Summary behavior:**

| Position in group | Wipe-in | Wipe-out | Pause-after default |
|---|---|---|---|
| First | normal | 0 (suppressed) | 0.15s |
| Middle | 0 (suppressed) | 0 (suppressed) | 0.15s |
| Last | 0 (suppressed) | normal | author's value (normal) |

**Note on "rushed-after-a-group" perception.** When the next chunk after a reveal group feels rushed, the cause is usually not the pause — it's the TTS speed of the next line landing too fast against the cadence the group just set. The fix is typically a **targeted speaking_rate reduction** on the specific beats (regenerate those mp3s via `tts_client.py --speaking-rate 0.95` so at Remotion's 1.1x playback they're effectively ~1.045x — slightly slower than surrounding content). Extending the pause to 1.0s+ was tried in a V7→V8 iteration and made the transition feel stalled instead of fixed. Pauses that long between the punchline and the next sentence break the thread. Prefer speaking-rate adjustments to pause extension when the complaint is "the next line feels fast."

**When to use a reveal group:**
- Setup → turn → punchline arcs
- Tricolons / tight rhythmic clusters that span chunks
- Enumerated quick-fire beats ("Story. Script. Images. Animation. Camera.")
- A callback where a beat visually picks up from an earlier chunk

**When NOT to use one:**
- Topic shifts — those NEED the fresh reveal to signal a new idea
- Standalone beats with real pauses between them
- Act openers — the Act bumper already resets the viewer's attention
- Groups longer than ~10 seconds — at that length the viewer benefits from fresh reveals

**Schema:**

- `reveal_group: "<name>"` on each chunk in the group. Freeform string; adjacent chunks sharing the value form one group.
- Non-adjacent chunks with the same value are an error (validator flags it).
- A `boundary_kind: "bumper"` or `"act-boundary"` chunk cannot be inside a reveal group.
- Typical group size: 2–4 chunks. 5 is the hard cap.
- All chunks in a group must be in the same Act.

**Audit implication:** bridge flags between two beats that share a `reveal_group` are suppressed — visual continuity + tight cadence IS the bridge. The deterministic post-filter in `audit_narration.py` handles this.

### Pause vocabulary

Pause-after values accept either a named alias or an explicit seconds string:

| Alias | Seconds | Use |
|---|---|---|
| `"none"` | 0.0 | Immediate continuation, same image still on screen |
| `"tight"` | 0.15 | Rapid-fire cadence (default inside reveal groups) |
| `"short"` | 0.3 | Normal beat-to-beat rhythm (default) |
| `"medium"` | 0.8 | Breath between angles |
| `"long"` | 1.5 | Punchline landing, high-weight chunk trailing pause |

Explicit values like `"0.5s"` or `"1.2s"` always work if a named alias doesn't fit.

### The closing/conclusion archetype

When the video is pivoting into its wrap-up, core-message restatement, or outro — regardless of where the previous chunk left off — signal it explicitly. The viewer needs to know "we're now tying it together," not "we've jumped to a new subtopic."

Phrases that do this work:
- *"So..."* / *"So where does this leave us?"*
- *"In short."* / *"To recap."* / *"Here's the frame."*
- *"Which brings us back to..."* (explicit callback to the opening)
- *"Zooming out."* / *"Step back."*
- *"All of this means..."* (if the conclusion is earned)

A conclusion chunk without a closing signal lands as an orthogonal jump, even if the content is correct. The same principle applies to Act-closers that lead into the Outro Act.

### Acts are the editorial unit

The editorial unit of a spoolcast video is the Act, not the chapter.

- **Chapters** are YouTube markers only. They exist for the viewer's chapter-picker UI and don't drive pacing.
- **Acts** are the story-structural unit. Each Act is a cohesive section the viewer holds as one mental chunk (e.g., *Cold Open*, *Anatomy*, *Layers*, *Proof*).
- The number of Acts is not fixed. Group chunks into Acts that match the video's natural structure — typically 3–6.
- Every Act after the first begins with an Act bumper + an opener chunk that previews what the Act covers.
- The first Act does NOT get a bumper. The first frames of the video must earn continued watching; a title card before the hook costs retention.

### The four transition sizes

These sizes are descriptive of common transition scales, not prescriptive. The viewer-cognition test determines the actual signal required; these scales are defaults when the test says "acceptable" and the shift is just structural.

| Transition | When it happens | Default signal |
|---|---|---|
| **beat → beat** | Next sentence, same idea | Tiny pause, same image |
| **chunk → chunk, thread continues** | New angle but same sub-topic | Small pause, visually related image, narration continues the thread |
| **chunk → chunk, topic shift** | New topic within the same Act | Longer pause + bridge narration that names what ended and what begins |
| **Act → Act** | Major section shift | 1.5–2s silent bumper + opener narration that previews the new Act |

Any of these transitions can fail the viewer-cognition test even at its default size. A "beat → beat" pair can have a logical jump that needs bridging; a "chunk → chunk" topic-shift can be fine without a verbal bridge if the shared visual language connects them. The structural category is the starting bid; the cognition test makes the final call.

### Visual transition primitives (comic-strip vibe)

Beyond the signal sizes above, the renderer uses named visual transitions from `src/transitions/` — a small library of presentations tuned to the illustrated comic-strip vibe. The editorial rule for which to use where:

| Transition primitive | Use for | Why |
|---|---|---|
| `comicPan` | Inter-chunk within the same act, same thread (`continues-thread` / `continues-from-prev`) | Panel-pan mimics the viewer's eye crossing to the next panel; matches the baseline reading cadence |
| `pageFlip` | Act boundaries only | The biggest transition in the library — signals chapter change. Overuse flattens its signal. |
| `panelSplit` | Adjacent chunks that benefit from being on screen together (setup/payoff pair, adjacent evidence, comparison) | Two panels coexist mid-transition; viewer takes both in before the first collapses out |
| `CUT` | Reveal-group internals, proof inserts, cold-open → Act-1 handoff, deadpan punchline leads | Any soft transition dilutes a deadpan reveal or a proof-style clash; the hard cut is its own signal |

Rules of application:
- **Match transition primitive to signal size.** `comicPan` is a chunk-scale signal, `pageFlip` is an Act-scale signal. Never use a larger primitive than the structural transition actually is.
- **Direction follows reading flow.** `comicPan` defaults to `from-right` (viewer's eye moves left-to-right). Use `from-left` only for deliberate callbacks where the viewer's eye is returning to an earlier panel.
- **`pageFlip` is scarce.** Reserved for `act-boundary` chunks and their preceding bumpers. If every transition is a page-flip, none of them signal anything. Cap: one per Act boundary, no more.
- **`CUT` is the deadpan default.** If a beat's job is deadpan punctuation and you're tempted to add a soft transition to smooth it — don't. The hard cut is what lets a punchline land.

See `src/transitions/README.md` for the implementation-level factory API, default timings, and how to add new primitives.

### Signals by transition, in detail

#### Beat → beat

- **Pause:** 0.3–0.6 seconds default (≥1s for list-item beats inside high-weight chunks)
- **Image:** unchanged from the chunk's scene
- **Test:** viewer-cognition test must pass — if it fails, either insert a bridge beat or rewrite the next line

#### Chunk → chunk, same thread

- **Pause:** 0.8–1.2 seconds
- **Image:** new illustration, visually related family (same characters, same object space)
- **Narration:** flows naturally; no explicit bridge needed because the thread hasn't broken — but the cognition test still runs, and if the logical connection is weak, a bridge is still required

#### Chunk → chunk, topic shift

- **Pause:** 1.2–1.8 seconds
- **Image:** new illustration that may reference the old one transitionally
- **Narration:** first beat of the new chunk must be a bridge matching an archetype above. Examples: *"that's the budget — now the four layers"*, *"even if you have all three, the harder problem is…"*, *"so much for the theory — here's what it looks like in practice."*
- **Why obvious:** the bridge sentence explicitly closes one thought and opens the next. No inference needed.

#### Act → Act

- **Pause before bumper:** 1s silence after the last chunk of the closing Act
- **Bumper:** 1.5–2 seconds. Full-screen title card in hand-drawn-style type (not numbered — just the Act name: *"ANATOMY"*, *"LAYERS"*, *"PROOF"*, etc.). No narration during the bumper.
- **Pause after bumper:** 0.5s before the opener begins
- **Opener chunk:** first chunk of the new Act is its own `act-boundary` chunk. Its narration previews the Act — what the viewer is about to see. The opener is typically flagged `weight: high`. **Preview ≠ enumeration — see "Preview structure" below for what an opener must actually deliver.**
- **Why obvious:** the viewer literally reads the Act name on a full screen, then hears the preview narration.

#### Preview structure — Act openers must name AND explain

An Act-opener chunk must do more than list what's coming — the viewer needs a mental model they can carry through the Act, not a word-list.

**Required structure for any preview / roadmap chunk** (Act openers, explicit previews like "in the next seven minutes...", any chunk whose job is to frame what follows):

1. **Name** — each sub-element (item, layer, rule, step) the Act/section will cover.
2. **One-line job description for each** — what it *does*, in the simplest terms. Not technical details. The smallest possible explanation of why this element exists.
3. **Relationship line** — how the items connect, what they produce together, or what makes them one unit.

Minimum to pass: names **plus** either jobs (2) or relationship (3). Ideal: all three.

**Anti-example** (from V6 at 3:19): *"Four layers. Image. Animation. Voice. Render."* — names only. Viewer has no idea what any layer does or why there are four of them. They'll spend the next two minutes trying to reverse-engineer the map instead of following the argument.

**Good example:** *"Four layers. Image makes the pictures. Animation gives them motion. Voice narrates. Render stitches everything into an mp4. Each one does one thing. Together they make the video."* — names + jobs + relationship. Viewer leaves this chunk with a scaffold that makes every subsequent layer-specific section feel like "here's more on layer N" instead of "wait, which one is this?"

**Why this matters beyond Act openers:** any chunk that says "here's what we'll cover" or "here are the N things" is making a promise to the viewer. Delivering only names breaks the promise — the viewer was told a preview was coming and got a bullet list instead. If a chunk can't meet the name+job(+relationship) bar, it shouldn't be framed as a preview in the first place.

**Audit implication (pending wire-up):** a future pass in `scripts/audit_narration.py` should flag any chunk that either (a) is a `boundary_kind: act-boundary` opener, or (b) contains preview-signal phrases (*"four layers"*, *"three things"*, *"here's what we'll cover"*, *"in the next N minutes"*), and check that the narration includes at least name + (job OR relationship). Flag if not. For now, the check runs at review time, manually, against this rule.

#### First Act exception

The first Act has NO bumper. The video opens directly on content (Cold Open). Reasoning: the opening seconds are the most attention-fragile part of the video; a label before the hook delays the hook and costs retention. The video's YouTube title + thumbnail already do the top-level framing.

### Bumper rendering

Bumper chunks are rendered by Remotion as full-screen text title cards, not kie.ai images. Why: $0 per card, instant iteration when Act names change, deterministic, and a hand-lettering Google font (Caveat / Kalam / Gochi Hand) matches the notebook-doodle aesthetic closely enough.

The `act_title` field on the bumper chunk drives the card. The card appears centered, black-on-white (or white-on-black — visually consistent with the Act's surrounding chunks), with a simple hand-drawn underline stroke below the text.

If a future video wants an Act card to include a doodle / stick figure / decorative element, swap that single card to kie.ai without changing the schema: drop an image at a known path, Composition.tsx falls back to the image if it exists, else renders text from `act_title`.

#### Act-title naming rule — don't expose the craft

Act titles are what the viewer sees on bumpers. They must describe the *content* of the Act the viewer is about to watch — not the *narrative function* the Act serves. Exposing the function ("PAYOFF", "THE HOOK", "THE REVEAL", "THE SETUP") reads as behind-the-curtain craft vocabulary; the viewer feels the machinery working on them and trusts the video less.

**Avoid function-name labels:**
- "PAYOFF" / "THE PAYOFF"
- "THE HOOK"
- "THE REVEAL"
- "THE SETUP"
- "THE PROBLEM" (generic function-label; fine if the video genuinely reveals the problem IS named "the problem" in-world)
- "THE FIX" (same caveat — OK when "the fix" is the in-world name, not just narrative role)
- "PART N" / "ACT N" / "CHAPTER N" — numbering with no content is worst of all; tells the viewer nothing + exposes structure

**Prefer content-describing labels:**
- A noun phrase for the thing the Act is actually about — "THE INCIDENT" (the specific event the Act covers), "THE DIAGNOSIS" (what's wrong), "WHAT CHANGED", "THE ANSWER", "CONCLUSION"
- A question the Act answers — "NOW WHAT?"
- The in-world name for the moment — "THE TURN", "SESSION 12"

Test: replace the act_title with "THE [random-role]" and see if the viewer learns less. If function-label > content-label on "does this tell me what the Act is about?", the label is wrong.

Example fixes:
- "PAYOFF" → "CONCLUSION" / "THE ANSWER" / a content noun ("THE PROTOCOL", "THE FIX THAT STUCK")
- "THE HOOK" → drop the bumper entirely (first Act has none anyway) or replace with the content noun
- "THE SETUP" → the name of what's being set up ("THE PROJECT", "THE RULES FILE")

### High-weight chunks

Certain chunks carry disproportionate weight for their size:
- **The promise** — the moment that tells the viewer why to watch ("in the next seven minutes…")
- **The preview** — the roadmap of what the video covers
- **The thesis** — the core-message articulation
- **A punchline** — a deadpan capstone where the frame drop is the rhythm
- **An Act opener** — the first narration after a bumper

These are flagged `weight: high` in the shot-list. High-weight means:
- ≥1.0 seconds of silence after the chunk ends
- The illustration LINGERS on screen during the silence — no hurried wipe-in to the next chunk
- Camera doesn't move during the chunk (hold the frame still)
- Within the chunk, beats that are list items get ≥1s pause instead of 0.3–0.6s so each item can register

### Lean away from on-screen text

Default: the narration carries the words, the illustration carries the feeling. On-screen text is a spike, not a running device. Before putting text on the frame, check whether the narration already says the same thing — if it does, the on-screen text is usually decorative and the chunk works better without it.

Lean toward text only when it does a job the narration alone can't:
- a **rule**, **quote**, or **protocol** the viewer should register as authoritative (title card, pinned note, rule card)
- a **label** that names a specific thing in the scene (a filename tag, a signage caption, a calendar or date marker, a product name)
- a **punchline stamp** or deadpan reaction (a single-word stamp or exclamation) where the word IS the beat
- an intentional **wall-of-text** whose density is itself the joke

Strong lean away from long strings unless the wall of text is the point:
- a paragraph-length quote rendered full-frame is rarely worth the read-time cost unless the quote itself is the beat
- multi-line lists (numbered protocols, rule files, bulleted cards) must be budgeted against the read-time floor below — a 40-word card needs ~14 seconds of screen-time to be readable, and dense cards often land faster as a narrated voiceover with a simpler illustration
- when in doubt, replace the text card with a single-word stamp or a labeled diagram

The cost of text that can't be read: the viewer registers "there were words but I couldn't read them" as noise, which dilutes the beat instead of reinforcing it. Text the viewer *can't* read is worse than no text.

### On-screen text read-time (required)

Any chunk whose `on_screen_text` field declares visible text — a rule on a page, a caption, a chart label, a document, a title card, a meme with caption — must hold on screen long enough for the viewer to finish reading.

Floor: **readable window ≥ visible-text-word-count × 0.35 seconds**, where the readable window = chunk duration minus the paint-on animation (if the chunk's entrance is `paint-on`). During paint-on the text isn't fully legible, so that time doesn't count toward the budget. Crossfade and cut entrances count fully toward the readable window.

If a chunk is 2s long with a 0.5s paint-on, the readable window is 1.5s — a 9-word card (~3.15s floor) is under-timed. Extend `pause_after`, set `hold_duration_sec`, or reduce the on-screen text.

Most chunks inside an act use crossfade (not paint-on), so the full chunk duration is the readable window for those. Only scene-opener chunks take the paint-on hit. See VISUALS.md § Inter-chunk transition vocabulary.

0.35s per word is a floor (roughly 170 wpm reading speed for short bursts of on-screen text, with a buffer). Longer for text that uses unfamiliar words, stylized typography the viewer has to parse, or handwriting. Shorter only if the text is a single recognizable word (*"NO"*, *"OUCH!"*, *"WAIT"*) where the viewer doesn't read so much as recognize.

The rule applies regardless of whether the beat narration is short or long. The constraint is *the viewer reading the frame*, which is independent of *the viewer hearing the narration*. A common failure: narration is a one-line 2-second beat, the illustration shows a full rules page with eight bullets, the chunk ends at 2s — the viewer saw the page but can't read it.

**Authoring-time read-time budget (primary enforcement).** The read-time check belongs in the authoring step, not the audit step. When writing a chunk that carries on-screen text, do the math inline before setting `pause_after`:

1. Write the literal words into `on_screen_text` as an array of strings.
2. Count the words (including headings, labels, punctuation-separated items). Call this `W`.
3. Floor = `W × 0.35` seconds.
4. Estimate chunk duration = `narration_word_count / 2.5` + `pause_after` tier. Pause tiers: tight=0.15s, short=0.3s, medium=0.6s, long=1.2s.
5. Subtract paint-on time if this chunk is a scene-opener (first chunk of a new scene, cold-open, or first chunk of the video): paint-on = `max(0.5, min(chunk_sec × 0.2, 1.5))` seconds. Readable window = duration − paint-on. For chunks inside an act (crossfade or cut entrance), readable window = full duration.
6. If readable window < floor, choose the fix in this order:
   - **(a)** promote the `pause_after` tier (short → medium → long)
   - **(b)** set an explicit `hold_duration_sec` on the same chunk — the chunk plays its narration, then holds the frame silently for the remainder. This is the preferred pattern for dense text cards: one chunk, one image, explicit hold time. No second chunk to manage.
   - **(c)** split into two chunks only when the editorial beat genuinely has two moments (narration + later reveal). Use `image_source: reuse` with `silent_hold: true` on the follow-on chunk. This is rare — most cases are (b).

Worked example: `on_screen_text` is a 28-word block. Floor = `28 × 0.35 = 9.8s`. Narration is a short 5-word line. Narration-duration ≈ 2s. `pause_after: long` adds 1.2s → 3.2s. Paint-on eats 0.64s → readable 2.56s. Not enough. Preferred fix: set `hold_duration_sec: 11` on the same chunk. Narrator plays the line at the top (2s), then the frame holds silently for ~9 more seconds. Paint-on only fires once at the start, so total readable window comfortably clears the floor.

The rule: compute the floor *when you write the chunk*, not after validation catches it. The validator is the backstop for drift — ideally it never fires because the authoring step already budgeted correctly.

**Enforcement (backstop).** `validate_shot_list.py` computes `on_screen_text` word-count × 0.35 and compares against the estimated chunk duration. Any chunk whose estimated duration falls below the floor is a validation error and blocks render. See PIPELINE.md § `on_screen_text` field.

**Author opt-out — `readtime_override: true`.** The floor is a safety net, not a mandate. By-ear tuning can legitimately pick a shorter hold when:
- the card was already seen recently (continuation of recognition — viewer doesn't re-read)
- the text is scannable at a glance (headings + short labels, not paragraph prose)
- the viewer is meant to glance/absorb pattern, not read word-for-word

Set `readtime_override: true` on the chunk to bypass the validator check. The flag is explicit so intent is recorded — never silently lower a hold_duration_sec without flagging. See PIPELINE.md § `readtime_override`.

### Deadpan punchlines

Short beats that carry comedic weight — one-word reactions, deadpan capstones, understated asides like *"Obviously."*, *"You know, casually."*, *"Structurally, it was."*, *"That's the whole trick."* — need their own chunk so the image changes at the exact moment the line lands. Burying a one-word punchline as the middle beat of a multi-beat chunk kills the gag; the image doesn't switch, so the word lands on the same frame as the lead-in, and the deadpan is lost.

When a punchline beat is split into its own chunk, mark `punchline: true` on the chunk. That unlocks two forms of meme/stamp substitution (VISUALS.md § Punchline Chunk Carve-Out):

- **full-frame substitution** — the meme/reaction replaces the prior scene entirely. Use when the punchline resets / erases the prior moment. `image_source: meme`.
- **overlay on reused scene** — a stamp or reaction artifact drops onto the prior scene as an overlay, the scene stays visible underneath. Use when the punchline reacts to the scene rather than replacing it. `image_source: reuse` pointing at the prior chunk, plus an `overlays` entry for the artifact.

Pick based on intent. A REJECTED stamp smacking a desk scene reads as a reaction TO the scene — use overlay. A SpongeBob "9 attempts later" card reads as "time passes, reset" — use full-frame.

Enforcement: `validate_shot_list.py` flags any beat whose narration is ≤3 words and lives inside a multi-beat chunk. Those beats almost always belong in their own `punchline: true` chunk with `image_source: meme`.

Suppressions the validator applies automatically:
- **List-enumeration openers** — beats that begin with ordinal/enumeration markers ("One.", "First.", "Step 1.", "1.") are list items, not deadpan punchlines. The marker itself is the structural signal; the short length is expected.
- **Closing-conclusion bridges** — beats that begin with wrap-up markers ("So.", "In short.", "Zooming out.") are outro bridges, not deadpan capstones.

Author opt-out: if a short beat is structurally NOT a deadpan (typical case: a short setup line that previews an enumerated list the following chunks expand) and the automatic suppressions don't catch it, set `not_a_punchline: true` on the beat or chunk. Use sparingly — most overrides indicate the beat should actually be split. See PIPELINE.md § `not_a_punchline`.

### Multi-panel chunks

Default: one chunk = one full-frame illustration. Alternate pattern: a chunk whose illustration is composed of two or three panels laid out together in the same frame, like a page in a comic strip. The viewer's eye moves across the panels within the chunk; the renderer applies a slow pan or held wide shot to let each panel register.

When this pattern fits:
- **Parallel options / choices** — e.g. three cards side-by-side showing three distinct actions.
- **Before/after pairs** — left panel is the before state, right panel is the after; holding both visible lets the viewer register the change.
- **Tricolons** — three rhythmically parallel lines of narration ("*different skills / different time / different energy*") land cleanly as a three-panel strip with one micro-image per clause.
- **Condensed lists** — when a narration beat names three things the viewer should take in together, not sequentially.

When this pattern doesn't fit:
- Sequential story beats. If the narration is "first X, then Y," that's two chunks, not two panels in one.
- Abstract / emotional moments where the viewer should dwell on one image. Multi-panel splits attention; a single full-frame holds it.
- Payoff moments. Final beats should be one-image-one-feeling — don't multi-panel the payoff.

Generation: multi-panel chunks are a prompt pattern, not a schema change. The chunk's `beat_description` explicitly specifies the panel layout (*"Three side-by-side hand-drawn cards in the wojak-comic style, each showing one option: …"*). Style anchor logic is unchanged — if the chunk has `references`, it uses them as image-ref; otherwise prompt-only per the anchor rule.

Rendering: the preprocessor reveals the composite frame as one image. Optionally, `Composition.tsx` can apply a slow horizontal pan across the panel strip during the chunk's screen-time, letting the viewer's eye read the panels in order. Use a `panelSplit` transition when a multi-panel chunk hands off to another multi-panel chunk (e.g., the second "after" state in a before/after sequence).

Budget note: one multi-panel illustration costs one kie generation (same as a full-frame single-subject chunk). No cost increase vs. splitting into multiple chunks — and in fact cheaper if it replaces what would otherwise be three chunks.

### Ending sequence (required)

The final chunk of the video must do more than land the last narrated line and cut. A video that ends on the last spoken word with no deliberate outro structure feels abrupt — the viewer hasn't had time to finish processing, or isn't sure whether the video is actually over.

Every video must end with a **deliberate ending sequence**. The exact shape depends on the video's goal, but the rule is: the end must be chosen, not accidental. Several archetypes qualify. Pick the one that fits what the video is trying to do.

**Declare the archetype BEFORE drafting the final Act** — not after the shot-list is written. The choice drives which final chunks get written, not the other way around. The declared archetype is recorded in `session.json`'s `ending_archetype` field (new) AND referenced in the shot-list `notes` on the final chunk. Deciding post-hoc tends to produce endings that "just happen" rather than endings designed to land a specific feeling.

**Ending archetypes (any one of these satisfies the rule):**

1. **Settle-and-hold.** For standalone videos that land a thesis. Final narrated beat is `weight: high`, followed by ≥2.5s of silent visual hold (normal post-beat silence + extra linger). Ideal final frame is a resolution of the cold open — same element, resolved form, viewer's eye completes a loop.

2. **Cliffhanger.** For multi-part series, pilots, or any video deliberately handing off to a sequel. The final beat does NOT resolve — it raises a new question, teases a follow-up, or drops on an unresolved image. Required for validity: the cliffhanger is *signaled* (viewer can tell this is intentional, not truncation). Signals include a "to be continued" card, a direct address like *"next time,"* a visual that points forward (arrow, portal, door opening), or an explicit beat naming the follow-up. A cliffhanger without a signal reads as the upload getting cut off — not an ending.

3. **Call-to-action.** Ends with a direct viewer ask: *"watch the V2,"* *"read the source,"* *"try it,"* *"subscribe."* Valid when the CTA is earned by the thesis (the viewer is being asked to do the thing the video was about) and the ask is brief enough not to overwhelm the thesis payoff.

4. **Circular callback.** The last chunk returns literally to the cold open's frame — same image, same composition — but now meaning something different because of what happened in between. Often paired with a closing verbal callback to the cold-open line.

5. **Open question.** Ends on a question posed to the viewer. Valid when the question is load-bearing (the video doesn't need to answer it because the viewer now has the frame to answer it themselves) and when the question lands on a weighted, held beat.

6. **Quiet payoff.** Minimal or no final narration — just a held visual, possibly with a single word or short phrase. Valid when the thesis has already been landed verbally and the final frame functions as a resolution in itself.

7. **Coda / reframe.** After the thesis has apparently landed, an additional short beat recontextualizes everything — the viewer realizes the video was actually about X, not what they thought. Valid when the reframe is earned (the setup supports both readings) and the coda doesn't exceed ~10s.

8. **Punch-and-cut.** A fast hard stop on the sharpest possible line — no extended silence, no outro card, the cut IS the punctuation. Valid when the final line is strong enough to stand alone and the hard stop is editorially deliberate (not truncation). Skips the ≥2.5s held silence requirement of the universal floor — a declared punch-and-cut opts out of the silence rule specifically. The agent must justify the choice in the shot-list `notes` (e.g. *"punch-and-cut: closing line is strong enough to pierce; silence would dilute"*).

**Opting out of the archetype list.** If none of the eight archetypes fit what the video is trying to do, the agent may decline to declare one — but must record a **one-line editorial justification** in `session.json`'s `ending_archetype` field (e.g. `"none: <reason>"`). An undeclared ending with no justification defaults back to settle-and-hold and will be audited against that archetype. Declining-with-reason is rare and meant for experimental formats; most videos fit one of the eight.

**Universal floor across all archetypes:**

- The final narrated beat (or final silent beat, for quiet payoff) has `weight: high` — frame holds, no camera move during the beat.
- At least **2.5s of held silence** between the final narrated word and the video ending (the cut to black / end card / YouTube auto-advance). This is the post-beat silence + extra linger on the final frame; implement via `pause_after: "long"` on the final beat (and add an outro hold chunk if more is needed).
- The shape of the ending is *declared* in the shot-list `notes` field on the final chunk — e.g. `"ending: settle-and-hold"`, `"ending: cliffhanger-to-V3"`, `"ending: CTA-to-tracker"`. The validator can later check that one of the allowed archetypes is declared.

**Failure mode this prevents:** the video ends with a final line, a hard cut, and the YouTube player auto-advances before the viewer has processed anything. Abrupt endings undercut whatever the thesis was trying to do. This applies to every archetype — even a cliffhanger fails if it just cuts off without a signal, because the viewer will read it as a broken upload.

A video without a declared ending-sequence archetype is not a finished video. Pick one. Hold the frame. Let it land.

**Editorial rules that apply to every archetype:**

1. **Emotional coherence beats logical coherence.** An ending can be structurally correct and emotionally flat. The rule: every ending archetype must leave the viewer with a feeling, not just a conclusion. If the final beat lands the thesis intellectually but the viewer doesn't feel anything shift, the ending hasn't worked — regardless of whether the mechanics are right.

2. **The final frame is for feeling, not work.** The last held image should not require the viewer to read, decode, or piece together. If a payoff depends on cognitive work, resolve it before the final frame and let the last image be simple and emotional.

3. **Any transformation shown in the ending has to be set up.** If the payoff depends on a change (register, character, setting, tone), the change must have been foreshadowed earlier. First-and-last appearances in the final beats read as *"who is this"* instead of landing the arc.

4. **Don't break the visual world in the final Act.** Foreign-style assets in the last beats snap the emotional thread. Any cross-reference callbacks belong earlier — before the final turn, not inside it.

**Preferred shape above the minimum floor:** a **dedicated silent outro hold chunk** after the final narrated chunk — no narration, visual continuation of the final frame (or a simple final card), 1.5–3s additional held silence. Implemented as a non-bumper chunk with empty beats and `image_source: "generated"` (or reuse of the final frame via `image_source: "reuse"`). `pause_after: "long"` on the final narrated beat is the floor — a dedicated hold chunk is the form that actually lets the ending settle. Use this whenever budget allows.

### Broll requires obvious viewer context

**"Broll" covers everything that isn't an anchor-style illustration.** This includes: raw video clips, saga-montage clips, meme stills, meme gifs, reaction clips, cultural-reference images, short archival clips, screenshot captures. The rules in this section and the next (*Broll earns attention*) apply uniformly across sub-types. The punchline "meme" carve-out earlier in this document (STORY.md § 10a) is one sub-type of broll — it inherits every rule here. Do not split memes out as a separate category with its own editorial logic.

**Upstream gate — the Concrete-reference check.** The decision of *which chunks get broll vs illustration* is made upstream at Stage 2 (shot-list drafting), not at Stage 4. See rules.md § Non-Negotiable System Defaults ("Concrete-reference check") and PIPELINE.md § Pipeline Stages (Stage 1.5 asset inventory + Stage 2 check). The rules below govern *how broll earns its place on screen once it's been picked*. They are not the upstream gate that decides broll-vs-illustration per chunk — that's the Concrete-reference check.

B-roll is never played without context. The viewer must know *why the clip is playing* and *what they should see in it* within 2 seconds of it starting.

Context can come from any of these mechanisms:
1. **Spoken setup** — the narration immediately before names what's about to play ("watch this — here's the previous video we're reverse-engineering")
2. **Visual continuity** — an illustration of the thing just appeared abstractly; now the real thing plays
3. **Recognition** — the clip is a culturally known artifact (this-is-fine dog, Wall-E, etc.)
4. **Topical match** — narration names the exact thing as the clip plays, and the clip IS that thing
5. **On-broll label** — a caption overlaid on the broll itself ("the pilot video, April 2026")
6. **Callback** — an earlier clearly-established moment the viewer will recognize

Forms that DON'T work (cut the broll instead):
- Playing a clip because we have it handy
- Hoping the viewer will "figure it out from context" when no concrete context mechanism is present
- Generic proof (*"look, the thing works"*) with no pointed reason
- Broll with narration about a different topic playing over it

#### Broll also has to earn attention

Context (the 6 mechanisms above) is about *comprehension* — the viewer knows why the clip is playing. Earning attention is a separate requirement. A clip that the viewer understands but has no reason to look at still bleeds interest.

Broll earns attention via ONE of:

- **(a) Contrast with the host video** — the clip is visually / stylistically / tonally different from the video it's embedded in, so the viewer's eye registers a delta. Real footage inside an illustrated video. A cultural-reference meme inside an anchor-style sequence. A raw terminal capture inside a polished explainer.
- **(b) Specificity — a specific thing inside the clip the viewer is being pointed at** — a named moment, a punchline, a recognizable artifact, a concrete thing the narration just said ("*watch the timestamp at 0:42*", "*the eraser here is the wrong version*"). The viewer has been given something to look for.

If the clip has neither — same style as the host video AND no specific moment being pointed at — cut it. Playing "random clips" under narration is never the move, regardless of whether a comprehension mechanism is technically satisfiable.

Special case, cold-open broll: same-style broll from a sibling video (e.g. V1 clips inside a V2 dev-log about the same project) is disallowed as a cold-open device. It fails both (a) and (b) by construction. Save sibling-video broll for mid-video callbacks where the viewer is being pointed at a specific shipped moment being reverse-engineered, and lead with a setup line that names the thing to watch for.

#### Saga-montage carve-out for spacing

The no-back-to-back-within-~30s guardrail (see § 10a Punchline visual options for the original meme spacing rule, which generalizes to all broll) treats each broll moment as one unit. A **saga-montage** — several broll clips played contiguously that together tell one story (*"here's attempt one, here's attempt two, here's attempt three — all rejected"*) — counts as ONE unit for spacing, not N. Spacing to the next broll moment is measured from the end of the montage, not from each clip inside it.

Why: the viewer experiences a saga-montage as one continuous comedic/narrative beat, not three spikes. Applying the spacing rule per-clip inside a montage would force artificial padding between clips that are supposed to feel continuous, defeating the montage.

Required for saga-montage classification:
- Clips are contiguous in the timeline (no illustrated chunk between them)
- They tell one rhetorical unit together (a list of attempts, a catalog of failures, a parade of reactions)
- Shared framing or caption treatment that visually groups them (consistent caption placement, consistent length, consistent edit rhythm)

Concrete example: V2's chalkboard-saga clips at 0:55–1:23 — three rejected chalkboard renders in a row, each ~9 seconds, all framed the same way. Treated as one unit; spacing to the SpongeBob time card at 1:23 measures from the montage's end, not from any individual clip.

#### Format default: lean toward motion

When a broll slot can be filled by a still image OR a short video/gif clip, **default to the clip**. Motion registers as a stronger attention spike than a held frame, especially in a video whose baseline is illustrated stills that reveal over time. Breaking that rhythm with motion is cleaner than breaking it with another still.

A still only earns the slot when:
- (a) The still is the canonical form of the reference — the meme or artifact is more recognized as a single frame than animated (e.g., an anime-panel meme like *"is this a pigeon?"* is a drawn still; there's no better animated version), OR
- (b) The beat needs a held silent punctuation where motion would over-read (e.g., a deadpan thesis card where a pan or zoom would compete with the silence).

Pipeline difficulty is NOT a valid reason to default to still. Trimming, muting, and compositing a video clip is craft cost, not an editorial veto. The schema term `meme` is a punchline *role*, not a file-format constraint — animated meme gifs / short clips route through the broll pipeline without penalty (see PIPELINE.md § Shot-List Spec).

Concrete effect: in a V2-style sequence with three meme slots, defaulting to clips might yield 2 animated + 1 still, not 3 stills. If every slot defaults to a still, re-audit — the still-default bias is leaking through.

#### Additive framing — not subtractive

When auditing a beat for broll, ask: *"does adding this add engagement without costing the beat?"* — NOT *"does removing this weaken the beat?"*

The two framings look symmetric but produce very different videos:

- **Subtractive default** (*"does removing hurt?"*) — treats illustration as the baseline and makes every broll earn its existence against the question *"but would plain illustration work?"* Because plain illustration often does work, subtractive framing cuts broll aggressively. You end up with a minimum-broll video that the per-beat test can defend but that bleeds engagement on long illustrated stretches.
- **Additive default** (*"does adding help?"*) — treats engagement as a first-class goal and cuts broll only when it actively competes with the beat (thesis moments, deadpan punctuation, abstract principle sections where no concrete subject exists to point at). You end up with a texture-rich video where the broll count emerges from actual per-beat benefit, not from clearing a subtract-to-cut bar.

All existing guardrails still apply (no repeats, spacing, contrast + specificity, audio). The additive framing changes the *starting stance*, not the constraints.

The test failure mode this fixes: an agent auditing broll under subtractive framing keeps saying *"illustration would work fine here, so cut the broll"* and produces videos that are technically on-rule but dry. The same agent under additive framing catches slots the subtractive pass missed.

Applies to all broll sub-types — raw video clips, meme stills, meme gifs, reaction clips, saga montages.

Additional broll rules:
- Two audio tracks never play simultaneously. Narration OR broll-audio, never both. Broll audio defaults to muted unless the clip's audio IS the point.
- Payoff-preview broll (an early "here's the output") must play ≥5 seconds with ≥1 second silent pause before and after. Does not apply to narrative / dev-log videos where the output *is* the story itself — see "Payoff preview in the cold open" earlier in this file.

### Audio-first re-timing

Timing from shot-list estimates (word count × assumed speaking rate) is acceptable during drafting, but becomes stale the moment TTS mp3s exist. After TTS generation, a re-timing pass runs that:

1. Reads every mp3's real duration
2. Recomputes beat durations from the real audio
3. Applies the pause tiers above based on each chunk's `boundary_kind` field
4. Inserts Act bumpers per `act-boundary` chunks
5. Writes the result into `preview-data.json`

The pipeline never renders a video from estimated timing once real audio exists.

### Shot-list schema additions

Six new fields support the rules above:

- **`boundary_kind`** (required on every chunk): one of `continues-thread`, `topic-shift`, `act-boundary`, `bumper`. Drives which pause tier and which signal the builder emits.
- **`weight`** (required on every chunk): `normal` or `high`. Normal gets default pause-after. High gets ≥1.0s silence + linger behavior.
- **`context_justification`** (required on broll chunks only): one sentence naming the context mechanism and what makes this broll obvious to a cold viewer.
- **`act_title`** (required on `act-boundary` and `bumper` chunks): the text rendered on the bumper card. No prefix, no number.
- **`act_opener_line`** (required on `act-boundary` chunks): the narration line that previews the Act's contents.
- **`broll_audio`** (optional on broll chunks): `mute` | `duck` | `full`. Default `mute`.

Full schema definitions live in PIPELINE.md § Shot-List Spec.

### Pairwise narration audit (the automated durability layer)

A structural schema catches missing fields. It can't catch an unbridged logical jump inside a thread (the C1 → C1B failure) or an overloaded beat that glazes the viewer. Those require semantic judgment.

Every shot-list runs through `scripts/audit_narration.py` before preview-data is built. The audit:

1. Iterates every adjacent beat pair across the entire shot-list (not just chunk boundaries — every pair, inside and across chunks)
2. For each pair, applies the viewer-cognition test via a small LLM pass (Claude Haiku): *"what is the viewer likely thinking after beat N? does beat N+1 answer that, or is it a jump?"*
3. Separately for each beat: applies the overweight test — *"is this beat load-bearing for the core message? is the density appropriate for its position in the video (dense cold open, relaxed middle, slow proof moments)? could half be cut without losing the argument?"*
4. Outputs a structured report: one line per beat pair flagged + one line per beat flagged, each with a proposed fix (bridge text, cut suggestion, simplification).

The agent or author reviews the report, either accepts the proposed fix, writes their own, or explicitly marks the pair as acceptable with a justification field. Then re-runs the audit. The build refuses to proceed until every flag is resolved.

The audit is the layer that catches the failures the structural schema misses. Without it, a bot following only the schema will file C1 → C1B as "continues-thread" and ship the unbridged jump.

### Two-layer enforcement, restated

**Layer 1 — structural (deterministic).** `scripts/validate_shot_list.py` refuses to pass any shot-list where:
- a chunk is missing a required field (`boundary_kind`, `weight`, or `context_justification` where applicable)
- an `act-boundary` chunk lacks `act_title` or `act_opener_line`
- a `bumper` chunk lacks `act_title`
- a broll chunk has empty `context_justification`
- a `high` weight chunk's post-chunk pause would fall below 1.0s

**Layer 2 — semantic (LLM).** `scripts/audit_narration.py` refuses to pass any shot-list where:
- a beat pair fails the viewer-cognition test and has no bridge or no author-marked acceptance
- a beat fails the overweight test and has no resolution

**Layer 3 — human review (xlsx).** The assets tab surfaces `boundary_kind`, `weight`, `context_justification`, and the audit report inline, so a reviewer scans the sheet and catches quality issues the auditors couldn't — a bridge that technically exists but doesn't actually connect, a context justification that reads well but wouldn't land with a cold viewer, a density that's technically load-bearing but still feels heavy.

### Why these rules, concrete cases

These rules were written against specific V1–V4 failures in the spoolcast-explainer video. Each rule maps to an observed failure:

- **Rule: Act bumpers + high-weight Act openers** — fixes the 0:27 moment where the video jumped from "this is spoolcast" to a roadmap preview with no signal. Transition was Act 1 → Act 2 but was treated as a regular beat boundary.

- **Rule: pairwise viewer-cognition test + bridge archetypes** — fixes the V4 miss where C1 → C1B (*"You build things." → "Getting attention is a separate job."*) was logged as "continues-thread" and shipped without a bridge. The rule is explicitly altitude-shifted from "chunk-level topic shifts" to "every adjacent beat pair," so the failure can be caught automatically.

- **Rule: overweight test + density curve** — fixes the complementary failure (sections that feel packed with context the viewer doesn't care about). Pairwise audit flags candidates; author cuts or simplifies.

- **Rule: High-weight chunks linger** — fixes the 3:00 four-layers preview that rushed past because it got the same pacing as any other beat. The preview chunk is now Act-boundary opener + high-weight, so there's a bumper before, a progressive reveal during, and a silent linger after.

- **Rule: Broll requires context (6 mechanisms)** — fixes the V1 broll at 0:27, 3:48, 4:08 that played with no viewer setup or with clashing narration. Unjustified broll is cut entirely; pointed-critique broll gets its narration moved to a separate setup chunk BEFORE the broll plays, with the broll running in silence.

### Relationship to Part 1

Part 1 rules govern what the narration says. Part 2 rules govern how it's paced and whether the viewer has enough context to absorb it — without being so packed with context that they zone out. A video that passes Part 1 (honest source-grounded narration, declared core message, beat-sized lines) but fails Part 2 (no Act structure, rushed previews, context-free broll, unbridged logical jumps, overweight decorative beats) reads as a well-written essay being read too fast with random video clips cut in.

Both parts are required.
