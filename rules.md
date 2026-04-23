# Spoolcast Rules Index

Start here.

Spoolcast turns chat, content, and ideas into illustrated videos. Each narration chunk becomes one AI-generated scene in a per-session locked style; a deterministic preprocessor reveals it over time; Remotion plays the resulting PNG sequences against audio.

This file tells any new agent or app:
- which rule files exist
- what each file is for
- what order to read them in

Read repo-local rules before making suggestions, writing workflow docs, or changing implementation details.

## First Turn Protocol — what to do when you open this repo

Before writing any editorial content, generating any assets, or running any script:

1. **Identify the current pipeline stage** (see table below). Don't assume — check the session directory state.
2. **Read the stage-specific rule file(s)** named in § What Each File Does. At minimum, read the file that owns the stage you're in.
3. **Confirm with the user what they want you to do.** If source/ exists but the shot-list is empty and the user says "make a video," you're at Stage 1 (script extraction), not Stage 7 (render). Don't skip ahead.
4. **Before drafting any editorial content, read STORY.md § 3 Jobs A–E.** Core-message confirmation (Job E) is the most load-bearing decision in the whole pipeline — skip it and every downstream decision drifts.
5. **Propose your first step in chat. Wait for confirmation. Then work.**

Violating this protocol is how iteration loops get born — the agent runs ahead, the user catches misses in review, expensive re-renders happen. The protocol is cheaper.

### Stage identification

| Session state | Stage | Primary rule file |
|---|---|---|
| No `session.json` in `sessions/<id>/` | Stage 0 — scaffold | PIPELINE.md § Workflow |
| Raw source in `source/`, shot-list empty | Stage 1 — script extraction | STORY.md Part 1 |
| Shot-list has narration, no images generated | Stage 3–4 — asset generation | VISUALS.md § Assets |
| Images exist, no `frames/` | Stage 5 — preprocessing | VISUALS.md § Preprocessor |
| `frames/` + audio + shot-list all present | Stage 7 — render | PIPELINE.md § Render Config |
| Rendered mp4 exists | Stage 8 — shipping | SHIPPING.md |
| Rendered 16:9 mp4 exists, mobile variants requested | Post-Stage 8 — mobile export from widescreen (A.1, optional) | SHIPPING.md § Mobile Export from Widescreen |

Run `scripts/validate_shot_list.py --session <id>` at any point to confirm the shot-list is schema-valid before proceeding. `build_preview_data.py` runs the validator automatically before emitting preview-data.

## Read Order

Read these files in this exact order:

1. [PIPELINE.md](./PIPELINE.md) — workflow, session config, shot-list spec, render config
2. [STORY.md](./STORY.md) — script extraction, pacing, viewer context
3. [VISUALS.md](./VISUALS.md) — assets, preprocessor, transitions
4. [SHIPPING.md](./SHIPPING.md) — review board, publishing

Delivery modes (agent-skill vs standalone-app, autopilot) are covered inside this file — see § Delivery Modes below.

If you are about to challenge or change a rule, also read [DESIGN_NOTES.md](./DESIGN_NOTES.md) — it captures the reasoning behind current decisions and what was tried and abandoned. The rule files tell you what to do; design notes tell you why.

## What Each File Does

### PIPELINE.md

The procedural reference. Read top-to-bottom as you move through stages.

Contains:
- the global system model and pipeline stages (Part 1)
- session.json spec, style anchor rules, budget (Part 2)
- shot-list schema, required fields, the `boundary_kind` / `weight` / `context_justification` fields that drive pacing (Part 3)
- preview-data schema, Remotion composition rules, canvas dims (Part 4)

### STORY.md

Everything editorial. Read when drafting narration, pacing, or the viewer's arc.

Contains:
- Part 1 — script extraction: source analysis, story spine, screenplay v1/v2/v3 workflow, gates, heuristics, planned-vs-shipped rule, core-message confirmation rule
- Part 2 — pacing and viewer context: Acts as the editorial unit, Act bumpers, the four transition sizes and their signals, bridge narration, high-weight chunks, broll context rule (6 mechanisms + 2-second gut-check), audio-first re-timing

### VISUALS.md

Everything on-screen and how it animates. Read during asset generation or when modifying the preprocessor/transitions.

Contains:
- Part 1 — assets: primary AI-illustrated scene pipeline, style anchor rule, scene manifest contract, kie.ai provider spec, overlay sourcing, AI budget, alternate (stock) mode
- Part 2 — preprocessor: reveal frame contract, supported reveal styles, determinism, caching
- Part 3 — transitions: reveal-type vocabulary, camera targets, inter-chunk behavior

### SHIPPING.md

End-of-pipeline: review and publish.

Contains:
- Part 1 — review board HTML contract, per-chunk display rules, layout, validation
- Part 2 — publishing: title, thumbnail, description rules, YouTube metadata, core-message test

### DESIGN_NOTES.md

The "why" log. Lessons learned, approaches killed, decisions and their reasoning.

Not a rules file. Read it when you want to understand why something is the way it is, or before challenging an existing rule.

## Non-Negotiable System Defaults

These apply everywhere unless explicitly replaced by a future system rewrite:

- The shot list is the source of truth for structure and narration.
- The session config is the source of truth for style, reveal behavior, and budget.
- Videos use one primary visual layer per frame: the illustrated scene.
- Overlays (logos, badges, small reference artifacts) are permitted only when every overlay's position, size, entry/exit timing, and duration are explicitly specified per-overlay in the shot list. Renderer-improvised placement, size, or timing is banned. AI-judged or AI-generated transparency is banned — overlay sources must be authoritative images with clean alpha (brand logos, official badges, cleanly-cropped real screenshots). See PIPELINE.md § Render Config overlay placement schema and VISUALS.md § Assets overlay sourcing. See DESIGN_NOTES.md "Killed: foreground overlays → Reconsidered" for the reasoning.
- One AI illustration per narration chunk is the default **for abstract/conceptual beats**. When a chunk's narration references a specific real thing that exists (a shipped video, a real file, a real screenshot, a real quote, a real asset), the default visual flips to broll of the real artifact. Illustration over broll in that case requires a one-line per-chunk justification recorded in the shot list. See *Concrete-reference check* below; stock/broll context rules still live in STORY.md § Part 2.
- **Concrete-reference check.** During shot-list drafting (Stage 2), scan each chunk's narration for a reference to a specific real thing. Match the reference against the asset inventory produced in Stage 1d. When a match exists, the cell default is the real artifact, not an AI redraw. Without this check, "illustration by default" silently turns every concrete reference into a lossy re-creation of something the viewer could be seeing directly. The inventory makes the check a lookup, not a search — so the cost of *"is there a real artifact?"* collapses to near-zero at shot-list time.
- **Recurring-reference check.** When building the shot-list, scan for (a) characters/objects with stable visual identity that appear in 2+ chunks, AND (b) style-library registered characters whose register any chunk invokes — even without naming them by key. Both get `references: [...]` tags. Without (b), library characters (e.g. `chad`) get bypassed because no beat names them and the model renders a drifted identity. Chunks with a recurring stable entity but no reference entry need a one-line `context_justification` — typical valid reasons: one-off cameo, intentional drift, stylized variant. **Evolving visuals are not references.** A diagram that builds up across chunks (cloud alone → cloud + box → equals + strike-through), a shape that transforms between beats, a scene state that changes — these are concept sequences, not identities. Tagging them with a reference over-constrains every chunk to the same frozen state and breaks progression. Evolving visuals stay prompt-only per chunk.
- **Test-on-one per beat TYPE before the batch.** If the shot-list spans multiple beat types (text-cards, diagrams, character scenes, composites, bumpers), run ONE of each type through the generator and verify visually BEFORE batching. One character-scene passing is not evidence that text-cards will render correctly. Catches class-of-output drift (e.g. text-cards rendering as split-panel comics instead of typography).
- **Beat-description vocabulary must match the style library.** When writing a beat description for a chunk that uses a style-library character reference, use the exact character name / description terms from the locked style's `characters[].description` field. Do not substitute generic placeholders that describe a different character register (e.g., writing a generic stand-in when the style registers a specific character identity). Mixed vocabulary — the style anchor pulling toward one character register while the prompt pulls toward another — causes silent output drift: the model averages the two signals and the result matches neither. At Stage 2 shot-list build, check every beat description against the session's style library: any character term used in the prompt must correspond to a registered character in `styles/<style>/style.json`, or must be a one-off unregistered entity the beat explicitly treats as outside the style. No session should ship beat descriptions referencing characters the style doesn't know about.

- **Persistent generator output is signal, not noise.** If the generator produces the same element in ≥3 chunks without being named in beat descriptions, that element fits the content's register. Do NOT write `"NO [element]"` to suppress it — tag with the matching library reference instead. `"NO [element]"` is only valid for explicit rule violations, user-directed removals, or literal misreads (e.g. a cardboard box when the beat specified a labeled diagram-box). If Stage 1e roster was done correctly — including library-implied characters, not just script-named ones — this guard-rail rarely fires.
- **Ending-archetype check (two-pass).** STORY.md § "Ending sequence (required)" lists 8 valid archetypes (settle-and-hold, cliffhanger, call-to-action, circular-callback, open-question, quiet-payoff, coda/reframe, punch-and-cut) plus a documented opt-out-with-justification. At pre-render, `audit_narration.py` runs two complementary checks:
  1. **Mechanical pass.** Verify the declared archetype (from `session.json` → `ending_archetype` or shot-list `notes`) is one of the 8 valid values (or a justified opt-out). For the declared archetype, check the structural requirements: `weight: high` on final narrated beat; ≥2.5s held silence via `pause_after: "long"` or a dedicated outro hold chunk (punch-and-cut archetype exempt); matching signals if cliffhanger (`"to be continued"` / `"next time"` / forward-pointing visual); final line tone matches the archetype (no trailing rhetorical questions on settle-and-hold, no hard resolution on open-question, etc.). Red-flag final narrations to catch: *"What's next?"* without a cliffhanger signal, single trailing imperative with no breathing room, unsignaled cliffhanger.
  2. **Emotional-landing LLM pass.** After the mechanical pass, an LLM is given the declared archetype + the final 3–5 chunks' narrations + scene descriptions, and asked: *"does this ending deliver the emotional outcome declared?"* Three verdicts: **landed**, **mismatched** (creates a different feeling than declared), **jarring** (creates no coherent feeling — reads as truncated / cut-off / abrupt). Jarring is a hard block; mismatched surfaces for target-revision or script-rework. This complements the mechanical pass — the structural requirements can all pass while the ending still feels emotionally flat. The LLM question isn't "does it match the archetype structure"; it's *"does the viewer finish this feeling like the story landed?"*
- **Meme / reaction punchline placement check.** During Stage 2 shot-list build, in addition to the Concrete-reference and Recurring-reference checks, scan for *punchline / reveal / reaction / "all-the-same" / "of course this happens" / facepalm* moments in the script. For each, decide whether a meme or reaction-gif/image insert lands the beat harder than an illustrated chunk. Memes are a third category alongside literal-artifact broll and library-character references — and they're not auto-suggested by either of the other two checks. Source per STORY.md § 10a Punchline visual options. Without this check, dev-log register beats land flat where a culturally-recognized reaction could spike them.

  **Meme placement — every meme must have audio playing during its on-screen time. No silent meme beats.** Valid placements:
    1. **Overlay on an existing narration chunk** — the meme is declared as an entry in the host chunk's `overlays` field, sitting on top of the chunk's main illustration. The host chunk's narration is the audio covering the meme. Required per-overlay fields: `source` (path), `position` (x, y as 0–1 canvas fractions), `size` (width as 0–1 fraction, height auto), `entry_time_sec` (offset from chunk start), `duration_sec` (must fit declared `meme_type`), `exit_style` (`cut` or `fade`), `meme_type`. The scene beneath keeps playing; the meme pops in, holds, pops out. Preferred placement — keeps chunk pacing tight without forcing narration compression.
    2. **Its own chunk, with narration audio** — the meme is the chunk's `image_path` (`image_source: broll_image`, `broll_source_kind: meme`, `broll_framing: full-frame`), and the chunk has a normal narration beat whose audio plays over the meme for the full chunk duration. Chunk duration = narration duration; author the narration to fit the declared `meme_type` range. When a meme's type doesn't match the companion narration's duration, shorten the narration — don't leave the meme held past its `meme_type` cap.
    3. **Its own chunk, with SFX audio** — same as (2) but the audio is an SFX file instead of narration. **Blocked until `ROADMAP.md` §6 SFX support ships.** Until then, (1) and (2) are the only valid placements.

  **Banned:** meme as a standalone chunk with no audio (silent-hold meme). Produces dead air (caught on dev-log-02 — silent meme beats felt like dead air; see `ROADMAP.md` §6).

  Regardless of placement, the declared `meme_type` duration rules apply (see § Meme / reaction duration classification below): quick-react ≤1.0s, sustained-punchline 1.5–2.5s, saga-item 0.6–1.0s. Stage 2 audit validates the effective duration matches the declared type.
- **A/B parallel sessions: rare, never default; when used, isolation format is non-negotiable.** Single-session is the default workflow. A/B parallel sessions are a rare exception — only used when there is a genuine editorial question worth comparing under controlled conditions (e.g. two narration registers against the same visual base). Most videos do not need this.

  **When an A/B is run, every one of the following is required (skipping any of them defeats the comparison and creates cross-session contamination — if the format can't be honored, don't run the A/B):**
    1. Two sibling session dirs: `<name>` and `<name>-<variant>`.
    2. Shared style library — both sessions reference the same style by name.
    3. Shot-list built once for A, then copied + narration-overridden for B.
    4. Scene images may be copied A→B *only if* beat descriptions are identical (otherwise regenerate per session — see *Cross-session scene-copy caveat* below).
    5. TTS and render run independently per session.
    6. Each session owns its own `working/preview-data-snapshot.json` so neither depends on the global `src/data/preview-data.json`.
    7. Both sessions stay fully isolated by session ID — downstream stages (mobile export, publish) target one and only one.
    8. Once the A/B is decided, the winner is **promoted to the canonical session name** and the loser is **deleted or archived**. Variant suffixes (`-qwen`, `-v2`, etc.) exist for the duration of the comparison only — never as the long-term state. All `session_id` fields inside the promoted dir (session.json, shot-list.json, manifests, working/ JSONs, per-chunk frames.json) must be updated to the canonical name, and any Remotion `public/` symlinks repointed. Future sibling-video references, mobile-export, and publish targets look up the canonical name — leaving variant suffixes around creates ambiguity for later agents and invites cross-session contamination.
- **Never upload to YouTube (or any public destination) without explicit per-call permission.** `publish_youtube.py` and any other external-publish action (YouTube, Twitter/X, tracker-public-facing updates, channel-facing posts) is a user-only-authorized action. The agent NEVER executes these without an unambiguous per-call *"yes, upload to YouTube"* (or equivalent per platform) from the user. Ambiguous approvals like *"yes,"* *"sounds good,"* *"ship it,"* *"keep going"* do NOT authorize upload — they apply to whatever specific action was just proposed and nothing beyond. Unlisted-privacy default does not change this — the upload itself is the unauthorized action, not the privacy level. When proposing an upload, the ask must be phrased unambiguously: *"Upload <file> to YouTube (<channel>) at <privacy> privacy now? This is a real external publish; it will be visible to <audience>."* — not bundled with other actions. Wait for an explicit yes to that specific question.
- **Silence-accumulation budget.** At Stage 2 (and pre-render audit), aggregate all silent time: `pause_after` values, `hold_duration_sec` overrides, bumper holds, silent-reveal post-beat gaps. Two checks:
  1. **No single silence moment exceeds 2.0s** — outside the declared ending archetype (which has its own ≥2.5s requirement per STORY.md § Ending sequence). A single `pause_after: "long"` (1.2s) + a chunk's `hold_duration_sec` of 2s stacks into 3.2s+ and will flag.
  2. **Rolling 5-second window check** — scan the timeline; any 5-second continuous stretch where ≥80% of the time is silent (pauses, text-card-holds, bumper-holds, post-narration silences) is flagged as dead-air risk. Silences stack quietly — a 1.2s pause + a 2s hold + a 1.75s bumper sum to a 5s dead-air window without any single piece looking problematic.
  3. **Aggregate cap** — total silent time ≤ 8% of runtime for dev-log-style videos, ≤ 12% for explainer-style (where breathing room is editorially deliberate). If over, audit flags the specific silent moments and requires trimming.
- **Meme / reaction duration classification.** Every meme / reaction chunk declares a `meme_type` field. Valid values and their duration ranges:
  - **`quick-react`** — ≤1.0s hold. Reaction faces with no caption to read (Surprised Pikachu, Picard facepalm, Mr. Krabs Blur, wojak reaction crops). The punch lands instantly; holding longer dilutes it.
  - **`sustained-punchline`** — 1.5–2.5s hold. Memes with caption text the viewer must read (Pam "they're the same picture," First Time Franco, Always Has Been astronaut). Reading time is load-bearing.
  - **`saga-item`** — 0.6–1.0s hold, part of a run of ≥3 items where the pattern is the point. Spacing rules per STORY.md § Saga-montage carve-out.
  Stage 2 audit validates the chunk's effective duration matches the declared type. A `quick-react` meme held for 2s is a hard flag; a `sustained-punchline` held for 0.5s is a hard flag. Generalizes: memes have wildly different optimal durations depending on whether the viewer decodes the joke instantly (a face) vs. reads a caption vs. follows a pattern.
- **Meme-narration alignment.** When a meme is the primary visual for a narration chunk, the chunk's narration must have its emotional-peak moment (the joke, the reveal, the reaction trigger) in the **first 40% of the chunk's total duration** (narration + pauses + holds). The meme appears at chunk-start; if the peak lands near the end, the meme stares back at the viewer for seconds before its audio companion arrives, producing off-beat pacing. Fix options when this fails: (a) shorten the narration so the peak lands early, (b) split the chunk — setup-narration on prior chunk, meme with payoff-narration as its own chunk, (c) move the meme to the following chunk where the peak is earlier. Generalizes: a meme on-screen too early without its audio partner reads as the agent dropping the joke before it landed.
- **Contiguous meme/punchline cluster pacing.** If **3+ memes** appear within any **30-second window**, they are a *meme cluster* and get additional constraints:
  1. Each meme in the cluster is shortened to **0.8–1.0s** maximum, regardless of its declared `meme_type`. The cluster's collective effect supplies the comedic weight; individual dwell time drops.
  2. The cluster is ONE spacing unit per STORY.md § Saga-montage carve-out — no cooling-off inside the cluster, but a mandatory **≥15s gap** before the next meme after the cluster ends.
  3. **Caption-heavy memes cannot cluster.** If the 3+ memes in the window each require `sustained-punchline` duration (captions to read), the cluster is over-dense — either space them out or cut one. A cluster's pacing only works when items are visually parallel and readable at a glance.
  Generalizes: a meme works as a spike; 3 spikes in quick succession collapse into a meme-block that reads as the agent overdoing it. Saga-montage format is the only valid way to cluster — and it has constraints.
- **Text-card density cap + visible-action first.** Text cards (*"typography only / clean page / handwritten line / nothing else in frame"*) are the last-resort visual, not the default. At Stage 2 shot-list build, **every `beat_description` must begin with a visible action, subject, or scene** — not typography language. Ban opening phrases like *"typography-only title card,"* *"clean page with text,"* *"handwritten line centered"* except for narrowly justified cases: cold-open hook, the single thesis-landing beat, channel sign-off, Act bumpers. **Cap: ≤10% of non-bumper chunks should be pure text cards.** If the shot-list exceeds the cap, flag it and require a per-chunk justification for each text card beyond the allowance. Text-cards feel weighty in the writer's head and land as dead air in the viewer's eye — reaching for typography for every "important" moment (core message, takeaway, title) is the anti-pattern that produces a video of reading-while-narration-plays. See STORY.md § Visualability test extension.
- **Drift fix: narrow-to-heart, never strip-to-text.** When a chunk's rendered image drifts (model added too much, wrong register, hallucinated content), the correct response is to be *more specific about what should be in the scene* — not to remove all elements until only text remains. Anti-pattern caught on dev-log-02: when a chunk drifted (e.g., model rendered a split-panel doomer-vs-chad comic for a core-message text beat), the fix reached for *"TYPOGRAPHY-ONLY. NO CHARACTERS. NO SCENE. Zero figures."* — stripping out all visual content. This killed the drift AND killed engagement. The correct fix: identify the visual heart (*"narrator at desk realizing X"* / *"cloud diagram with strike-through"* / *"two characters handing a file"*), then tighten the prompt AROUND that heart (*"single panel, narrator alone at desk, no second figure, no split panel"*). The strip-to-text response is defensive — it treats the model's over-generation as the problem when the real fix is better scene specification. Only use text-only as a last resort when visual representation genuinely doesn't fit the beat (very rare — mostly title cards).
- **Cross-session scene-copy caveat.** When scene images are copied from one session to another (e.g. an A/B parallel build), on-screen-text and beat alignment must be re-audited per chunk against the destination session's narration. Identical `beat_description` does not guarantee the rendered image fits the destination's narration — the original was rendered against the source's narration, and any narration drift breaks: text cards (typography mismatch), broll captions, character expressions matching the line being said, anticipation visuals matching the next reveal, etc. Run the conflict-report pass before treating copied scenes as final: for each chunk, compare destination-narration vs the source-rendered visual; flag any drift. Without this audit, a copied set of scenes appears "complete" while every text card and reveal beat silently mismatches what the viewer hears. Caught on dev-log-02-qwen — copied 41 scenes from sibling, then had to regen 14 of them because qwen's narration diverged.
- **Runtime quote format.** Every runtime quote must include the TTS parameters that produced it. Format: `<runtime> at <rate>x <voice> <provider>` — e.g. `3:07 at 1.1x Puck Google TTS`. A bare `3:07` is ambiguous — the same narration runs materially different at 1.0x vs 1.15x, Puck vs a different voice, Google vs ElevenLabs. Compute runtime empirically (words ÷ calibrated wps + pauses + bumpers + hold overrides), and calibrate wps against a shipped sibling session in the same style **at the same rate / voice / provider** — not against a remembered default or a gut estimate. Applies to every runtime quote, including mid-session updates.
- **Chunk-length check.** Every shot-list chunk past the first ~15 seconds targets **7–10 seconds** of runtime per STORY.md § 9a Cold-open visual density. The density curve: 2–3s per chunk in the cold open (0–15s) → 3–5s in the ramp (15–60s) → 7–10s in the body (rest). At Stage 2 shot-list build, estimate each chunk's duration (narration word count ÷ speaking rate + pauses + hold overrides) and flag any post-cold-open chunk under ~4 seconds as over-fragmentation risk. Consolidate neighbors unless the short chunk is an intentional visual build — core-message line-by-line accumulation, takeaway text stack, held punchline beat. Over-fragmentation costs one AI generation per chunk (inflates spend) and creates stuttery visual pacing the viewer registers as "jumpy." The rule is not "shorter is tighter" — shorter is denser, and density is only wanted where attention needs to be worked for (cold open), not throughout.
- **Produced-broll contrast check.** When broll has to be produced (composite, chat-UI render, side-by-side, screenshot mockup), split by the broll's purpose:
   - If the purpose is *"show the literal artifact being named"* (the actual prior video, the literal reference image, the real output being critiqued), the produced asset should match the artifact's own style — even if that style happens to match the host video. The style fidelity IS the point; contrast is carried by framing devices (the `tv-screen` surround for sibling-video broll, labels, side-by-side borders).
   - If the purpose is *"synthesize a representation"* (chat mockup, terminal capture, UI screenshot, generic diagram) — the asset has no pre-existing style it must be faithful to, so it MUST pass STORY.md § Broll earns attention (a) contrast. Use real-UI chrome, a distinct palette, distinct typography, or an obviously-not-anchor visual language. A cream-paper background with hand-lettered text is the wojak-comic anchor — if the produced broll matches that, it has failed (a) and earned no viewer attention.
- The preprocessor owns reveal animation; the renderer plays PNG sequences as-is.
- If a scene cannot be visibly reviewed, it is not done.
- When the shot list, session config, or scene manifest changes, downstream artifacts must be regenerated.
- Every transition needs a context signal proportional to its size (STORY.md § Part 2 meta-rule).
- Shared docs should avoid absolute local paths unless a path is truly required to make something work.
- **The core message is confirmed with the user before any screenplay or narration drafting.** Propose 2–3 candidates in plain language with tradeoffs, wait for the user to pick or rephrase. See STORY.md § 3 Job E. Guessing the core message and proceeding is the single biggest process failure in Stage 1.
- **Review artifacts are exactly two things: the short version in chat, and the final shot-list xlsx.** Source analysis, screenplay v1/v2/v3 prose, voiceover scripts — written to disk for traceability but NEVER linked to the user for review. See STORY.md § Review-Artifact Policy.
- **Lead with the plain-English version when presenting to any viewer — user in chat or YouTube audience.** Before any technical explanation in chat, write the plain-English version first. Do not gate it on "the user seems technical" or "the context is technical." If the user has already asked for the plain version in this session, assume they want it for every technical topic until they explicitly ask for depth. Technical terms are allowed only after the plain version exists, and only with an in-line explanation on first use. See STORY.md § Layman-first explanation rule. Caught repeatedly: jargon-first presentations force the user to ask *"can you explain in layman terms"* when the plain version was one sentence away.
- **Bundle pipeline assets (fonts, small binaries, reference weights) in the repo over brew/apt/system installs**, when license and size allow. A fresh clone should run end-to-end without a shopping list of casks and taps. Prereqs that genuinely can't be vendored (e.g. a libass-enabled ffmpeg) live in the relevant rule file's prerequisites section as a named one-liner, not implicit tribal knowledge.

## If There Is A Conflict

If two files appear to conflict:

1. `PIPELINE.md § Session Config Spec` wins for session config structure and fields.
2. `PIPELINE.md § Shot-List Spec` wins for shot-list structure and field meaning.
3. `VISUALS.md § Assets` wins for scene generation, asset sourcing, and validation.
4. `VISUALS.md § Preprocessor` wins for reveal animation behavior and frame output.
5. `SHIPPING.md § Review Board` wins for HTML review-board behavior.
6. `PIPELINE.md § Render Config` wins for preview/render behavior.
7. `PIPELINE.md § Workflow` wins for pipeline-level behavior, source of truth, and regeneration rules.
8. `STORY.md § Part 2` wins for pacing, transitions between chunks/Acts, and viewer-context requirements.

If a real conflict still remains:
- do not guess
- report the conflict clearly
- stop before making a silent assumption

### Diagnostic anti-pattern: pipe-buffering

Do NOT pipe long-running commands through `head` / `tail` / `grep` when you need to see progress. These tools buffer their input until the upstream process exits (or until N lines accumulate, in head's case). A working process can look completely hung because no output reaches your terminal until it finishes.

This caused ~30 minutes of false debugging where a working API wrapper was repeatedly killed mid-flight under the false belief it was hanging.

If you need progress visibility on a long command:
- Run it without any pipe: `python -u script.py` (the `-u` flag is also important — disables Python's own stdout buffering)
- If filtering is needed, use `tee file.log | head -30` so the full output is captured to disk while head shows the truncated view
- For background tasks, read the output file directly without piping

If you're sure a command is hanging (no output for >2x expected time), verify with `ps aux | grep <name>` to check if the process is alive and consuming CPU before killing it.

### Diagnostic anti-pattern: silent cwd drift

Bash-tool invocations of local scripts must use absolute paths, or `cd <abs> && ...` first. Relative paths like `scripts/.venv/bin/python ...` silently fail with *"no such file or directory"* when the cwd drifted between calls — often because a prior command changed directories or ran without one. Symptom: task exits 0 with a "not found" error on a script you know exists. Defensive default: `cd /absolute/repo/root && <command>`.

### User request vs existing rule

If the user asks for something that contradicts a documented rule in any of the files above, do NOT silently update the rule to justify the new request. This is how rules get rewritten every session and lose meaning.

Instead, flag the conflict explicitly before acting, using this format:

> ⚠️ **Rule conflict**
> `<FILE.md> § <section>` says: "*<quote the specific rule>*"
> You're asking for: *<restate the request>*
> Options:
> - (a) **update the rule** — change the documented rule AND apply the new behavior (both happen)
> - (b) **one-off exception** — apply the behavior for this case only, do not touch the rule
> - (c) **keep the rule** — decline the request

Wait for the user to pick before proceeding. If the user answers with anything other than "update", do NOT edit the rule file.

Obvious clarifications or typo fixes in the rule itself do not need this ceremony.

## Before challenging any rule

Read DESIGN_NOTES.md first. It captures what was tried, what was killed, and why current rules are shaped the way they are. Many "improvements" agents propose are variations of approaches that already got killed — DESIGN_NOTES exists so those don't get re-litigated in every session.

Especially check DESIGN_NOTES for entries dated from recent sessions — those are the failure modes freshest in the pipeline's memory and most likely to recur if an agent doesn't know they've already been addressed.

## Expected Agent Behavior

A new agent should:

1. read this file
2. read the rule files in the required order
3. identify the current pipeline stage
4. make changes only within that stage unless regeneration is required
5. validate downstream outputs after any upstream change

### Verified = mechanical check passed

A fix is not "verified" because the code changed, because the intermediate data looks right, or because a few frames were extracted by eye. Those are proxies for verification, not verification.

"Verified" means: a mechanical, reproducible check ran against the final artifact the user consumes (the rendered mp4, the deployed app, the shipped file) and passed.

Shapes this takes:
- Render pipeline: `scripts/audit_render.py` runs against the mp4 and its sentinel is written. See PIPELINE.md § Render Audit Rule.
- Validator pipeline: `scripts/validate_shot_list.py` exits 0 against the final shot-list.
- Any other stage with known failure classes: encode the class as a check, run the check on the artifact, require it to pass.

Why this matters: causal models of bugs are always partial. A diagnosis that explains N of M user-reported symptoms doesn't mean the other M-N are gone — it just means your model doesn't cover them. The mechanical audit doesn't rely on the diagnosis being complete; it re-checks the artifact from scratch.

Failure mode this prevents: agent fixes the mechanisms it diagnosed, declares done based on diagnostic closure, user points out the symptom is still there, cycle repeats. The audit breaks the cycle because the artifact is either passing or not — independent of what the agent believes about its own fix.

Applies in both human-in-loop and autonomous modes. The only difference is who reads the failure report when the audit fails.

### Empirical verification beats logical inference

When claiming two things are equivalent — prompts, configs, outputs, API calls — produce the comparison artifact. Do not produce a logical argument that they should be equivalent. Code inspection cannot detect drift in shared mutable state (shot-lists, session configs, any on-disk input that may have been edited between runs).

Red-flag phrases to self-censor: *"verified in code"*, *"they go through the same code path so they're the same"*, *"the logic looks identical"*. These upgrade "inferred from reading" to "verified" — a small but real dishonesty, and one that makes the bug this category invisible to the user.

When a fast-path logic argument looks sufficient, name the tradeoff explicitly: *"I can verify by code inspection in X seconds, or by actual output diff in Y seconds"* — let the user pick.

Concrete pattern that caused the rule:
- Widescreen scene generated months ago with `on_screen_text=None`.
- Cleanup script later set `on_screen_text=[]` (empty list) on the same chunk.
- Mobile regen run today went through the "same code path" but took a different branch on `[]` vs `None`, producing a prompt WITHOUT the Scene section.
- Model invented a scene. Checklist said "verified in code." Nothing was actually verified.

Setup-heavy beats workflow-corrupted: a slower, more explicit setup pays off across the whole downstream workflow. Shortcut at setup = drift everywhere downstream.

### Recon before plan, plan before build

For any non-trivial feature: (1) recon pass over the relevant rule files and the scripts the feature touches, (2) write the implementation plan in chat — schema additions, new scripts, build order, rule-file updates — and wait for sign-off, (3) build. Skipping step 2 is how "I thought we agreed on X" cycles start. The recon is cheap; the wrong-code retraction is expensive.

The plan is a contract, not a doc. It states what will change, where, and in what order. If the plan changes mid-build (a constraint is discovered, a design turns out to be wrong), surface the revision in chat before continuing — the user signed off on the old contract, not the new one.

This applies to feature work that touches more than one file, more than one stage, or introduces new fields/scripts. Trivial changes (one-line fix, typo, local edit inside a single function) do not need a recon pass.

### Prompt-engineering stall signal

When a prompt loop stalls after 2–3 iterations producing the same failure mode, stop iterating on the prompt and question whether the INPUT is right. Change the input, not the prompt.

Concrete: four `audit_scenes.py` prompt revisions failed to catch text-clipping in 9:16 center-crops because the model was being asked to imagine the crop (a geometric task Qwen-VL is unreliable at — strong "centered = safe" bias). Inverting the input — pre-crop the image and audit the cropped result — worked on the first try. `scripts/audit_mobile_crops.py`.

### Test on one before the batch

For any paid-per-call operation (kie.ai regen, vision audit, render), run on a single item and visually verify before the full batch. Catches drift, prompt bugs, and composition regressions for the cost of one unit. Pattern: `--only <one>` → inspect → `--only <all>`. Applies whenever the loop body incurs real money or long render time per iteration.

### Pre-Pass Rule

Before presenting anything to the user — a list of options, a single proposed next step, a recommendation, or an action you are about to take — do an internal pre-pass and drop anything that isn't actually beneficial to what the user is trying to accomplish.

This applies to:
- Option lists ("A vs B vs C") — drop the ones that don't serve the goal
- Single proposed next steps ("let's do a dry run", "let me check X") — drop them if they don't prove or change anything that was actually in doubt
- Tool calls about to be made — drop them if their output doesn't inform a real decision
- Intermediate goals — drop them if they don't move the real work forward

Do not surface decoy options to seem thorough. Do not propose actions that look productive but aren't. Do not rationalize that "this at least proves X works" when X wasn't in doubt.

The test: if what you are about to propose would be described as "honestly doesn't prove/serve/matter much for what we're doing," it should have been filtered out before you wrote it. Commit to a better alternative, or ask the user for direction, or do nothing.

Narrow rule-lawyering (e.g., "this is a single action, not an options list, so the rule doesn't apply") is itself a violation. The point is: filter for benefit, regardless of the shape of what's being proposed.

### Describe behaviors, not taxonomies, when writing agent rules

When writing or editing a rule that the agent will later read into working memory, describe the agent's behavior — not the category of thing the behavior applies to. Rules carried in context prime the concepts they name. If a rule names a story shape, an option category, an asset class, or an argument structure as a distinct thing to watch for, that named thing becomes more available in the agent's later decision-making — regardless of whether the rule encourages or discourages it.

Concrete pattern:
- Bad: *"When picking [named category X], run check Y."* This plants category X in attention. Future sessions reach for X more often because X is now a salient option in the ruleset.
- Good: *"Before committing to any plan, run check Y."* Same behavior required, no category planted.

Applies to rules about option lists, creative structures, asset types, visual styles, narrative shapes. The rule should be phrased so the agent cannot infer a menu of named alternatives from reading it. If a rule requires naming a class of thing to be intelligible, the test is: does naming this category narrow the agent's future generation more than the check warrants? If yes, find a phrasing that doesn't name the category.

The test: rewrite the rule without any noun phrase that describes a specific shape-of-thing. If the rewrite still conveys the required behavior, prefer it. If not, the noun is probably load-bearing — keep it, but note that future behavior in that category may be biased by mere mention.

### Don't Offload Production Work To The User

When presenting options for completing a task, **never include "you do it" as an option.** The agent is responsible for all production work. If a genuine tool/network/capability limitation blocks the agent, name the limitation honestly and propose alternatives the agent CAN do — not "or you could record/capture/screenshot it yourself."

Examples of this rule being violated (all real failure modes):
- *"Two options: (a) I can capture the terminal output, or (b) you do a QuickTime recording"* — (b) is offloading. Just do (a), or if (a) doesn't work, propose (a'), (a''), etc.
- *"I can source a low-res logo, or you could drop a better one in box/"* — the `box/` folder exists as an optional *user-initiated* drop point, not as the agent's fallback. Presenting it as a fallback converts an "optional convenience" into "here's work you can do for me."
- *"You'd need to set up credentials, then I can proceed"* — if something is credentialed, that's a real blocker that needs user decision (do we do it or skip it), not an option among options.

The distinction: if the user proactively says *"I'll provide asset X,"* accept it gratefully. But when the agent is building an options list, every option must be something the agent itself executes.

If the agent is genuinely stuck between *"I do it poorly"* and *"the user would do it well,"* surface the quality tradeoff honestly: *"I can do X but the result will be soft/incomplete/Y — acceptable?"* The user decides whether to accept the limitation or provide something better — their choice, not one of the agent's options.

The user already hired the agent specifically to not do this work themselves. Offering their own labor as an option undercuts the whole premise.

### Substance Before Form

When collaborating with the user on any creative or editorial decision — a screenplay section, a camera choice, a thumbnail concept, a reveal style, a visual subject — propose the substance in plain words first. Get agreement on what the thing is trying to do. Only then propose how to show it, phrase it, or execute it.

Jumping to specifics before the substance is agreed is a process failure. It wastes iterations on choices the user doesn't actually want, and it hides the editorial decision behind surface-level options the user can only react to aesthetically.

Applied to review cycles: when the user pushes back on a draft, figure out which layer the objection is at — substance, structure, voice, or form — not just re-polish at the surface.

## Delivery Modes

Spoolcast is delivered in two shapes. The pipeline (Stages 0–8 in PIPELINE.md) is identical in both. What changes is who initiates each step, how decisions are surfaced, where user-confirmation gates fall, and what happens when the user chooses not to decide. Both modes must honor every rule in this file and in PIPELINE.md / STORY.md / VISUALS.md / SHIPPING.md.

### Mode 1 — Agent Skill (conversational)

Spoolcast runs as a skill inside a chat agent. The user drops a raw session package into a working directory; the agent drives the pipeline by asking questions, proposing options, and waiting for user decisions. Currently the only shipped mode (V1 + V2 both produced this way).

**Default interaction shape (user-driven).** At every decision point the agent (1) says what stage we're at in plain terms, (2) proposes 2–3 options or one clear recommendation with tradeoffs, (3) waits for the user to pick / edit / propose their own, (4) only then acts.

**Gate list, in order:**

1. **Stage 0 — scaffold.** Agent confirms session id, budget, style. Runs `init_session.py`.
2. **Stage 1a — core message (Job E).** Agent proposes 2–3 candidates with tradeoffs. User picks or rewrites. Locked before anything else.
3. **Stage 1b — structure.** Agent proposes the Act/chapter shape. User approves or revises.
4. **Stage 1c — screenplay v1 → v2 → v3.** Drafted to disk (working docs). Per STORY.md § Review-Artifact Policy, no chat review between versions — the shot-list xlsx is the consolidated review artifact.
5. **Stage 1d — asset inventory.** Before shot-list drafting, list every real artifact already on disk or easily sourceable that could illustrate a reference in the narration — prior shipped videos / renders / frames, session files, manifests, style anchors, chat transcripts, pre-existing screenshots. Written to `sessions/<id>/working/asset-inventory.md` as one-line entries with paths. Not user-reviewed; exists to make the concrete-reference check at Stage 2 a lookup, not a search. No acquisition or cropping at this stage — inventory is a survey of what already exists.
6. **Stage 1e — character / object roster.** After screenplay is locked and before any beat description is written, the agent enumerates every recurring character and object the *script* names (role-level — *"the narrator," "the AI that lied,"* etc. — not library keys). **The cast = script-named roles AND style-library-registered characters whose register the script invokes.** For every registered character in the style library, ask: does this video have moments/scenes where this character's register (doomer / chad / ai-figure / etc.) naturally applies? If yes, they're in the roster — the script doesn't need to name them. Missing a library character whose register applies is the bug that causes "NO X" prompt suppression later. For each roster entry, consult the session's locked style library: (a) map to an existing registered reference, (b) plan to register a new reference before Stage 4 (session-scoped default per VISUALS.md; promote to library with intent), or (c) mark as one-off, prompt-only. Output: `sessions/<id>/working/character-roster.md` as a short mapping table — one line per entry: `<role or implied-register entity> → <library/session ref key or "one-off">` with the chunks/Acts they appear in. Stage 2 beat descriptions name roster entries by their reference key; every matching chunk carries `references: [...]` tags. If Stage 2 discovers a character not in the roster, the roster is updated and a reference registered FIRST — no beat is written against an unplanned character.

7. **Stage 2 — shot-list.** Agent builds the shot list from the locked screenplay, consulting the Stage 1e roster for every beat. For every chunk, run the Concrete-reference check (rules.md § Non-Negotiable System Defaults): scan the narration for references to specific real things, match against the Stage 1d inventory, default the cell to broll when a match exists. Record a one-line justification on any chunk that picks illustration over broll. User reviews the xlsx directly.
8. **Stage 3 — chunking.** Chunks populated per heuristics. User approves visible boundaries.
9. **Stage 4 — external assets + AI generation.** Externals first (mechanically enforced by `batch_scenes.py` pre-flight per PIPELINE.md § Stage 4 ordering rule), QA pass, re-approval, then AI spend.
10. **Stage 5 — preprocessing.** Deterministic; no user decisions.
11. **Stage 6 — review board.** User reviews the per-chunk board. Regeneration triggered from any flag.
12. **Stage 7 — render + preview.** User watches the preview. Approves or requests revision.
13. **Stage 8 — publish.** Title, thumbnail, description per SHIPPING.md. User final-approves before upload.

The agent communicates in plain terms per STORY.md § Layman-first explanation rule.

### Sub-mode — Autopilot ("you decide everything, I'll wait")

At session start, the agent MUST offer a second path: *"Do you want me to make every decision and surface the final video when it's ready? You'll only be pulled in if I hit something that genuinely needs your judgment."*

If the user picks autopilot:

- The agent makes all Job E / angle / structure / pacing / visual / chunking / publishing decisions itself using the defaults below.
- The agent still writes source analysis + screenplay drafts to disk for traceability.
- The agent surfaces one thing at session end: the finished video plus a short summary of the choices it made (core message locked, structure used, any tradeoffs worth knowing about).
- The agent is allowed to interrupt autopilot only when:
  1. A rule conflict is triggered (rules.md § User request vs existing rule — the 3-option surface).
  2. The AI budget is about to be exhausted.
  3. A hard dependency is missing (source package incomplete, required asset cannot be produced).
  4. The content raises an ethical / factual concern the agent is not confident to resolve alone.

**Defaults the agent uses in autopilot:**

- **Core message:** picks the outcome-focused candidate unless the source material clearly calls for architecture-focused or meta-lesson framing. Documents the choice in source analysis §6.5 with a one-line reason.
- **Structure:** follows the dominant shape the source material suggests. If ambiguous, defaults to the 4-Act shape (cold open → problem → reframe → payoff).
- **Style anchor:** inherits from the most recent sibling session in `sessions/` unless the session notes specify otherwise.
- **Reveal style:** `paint-auto`.
- **Thumbnail/title:** script-first per SHIPPING.md.

Autopilot is NOT a silent bypass — the agent still writes the same artifacts, runs the same validators, honors the rule-conflict protocol. It just doesn't wait at every gate.

**Workflow record.** Kept as a running log at `sessions/<id>/working/agent-workflow-log.md` per session. Entries: which gate, what options were offered, what the user picked, any deviations. For after-the-fact inspection, not realtime review.

### Mode 2 — Standalone App

Spoolcast runs as its own app (web or desktop). The user opens it, creates a session, drops source material into the UI, and drives the pipeline through explicit screens rather than conversation. Each pipeline stage is a discrete screen.

**Status:** not yet built. Planned screens:

- Session dashboard, source-drop, core-message, structure, shot-list editor, asset board, review, render+publish.

Open design questions (resolve when building):

- Whether the app includes the agent conversation as a sidebar or is fully GUI-driven.
- Where Job E confirmation lives — dialog modal, dedicated screen, inline on dashboard.
- How rule conflicts are surfaced without a conversational agent (likely a modal with the same 3-option menu).

### Shared principles across modes

Regardless of mode, every delivery must:

- Honor the core-message confirmation gate (STORY.md § Job E). Never proceed past Stage 1 without it.
- Honor the rule-conflict protocol (rules.md § User request vs existing rule). Silent rule rewrites are banned.
- Lead with plain-English presentation (STORY.md § Layman-first explanation rule). Jargon-first UI copy fails the same test as jargon-first agent chat.
- Write the same canonical artifacts to disk in the same locations (PIPELINE.md § Canonical Content Layout). Mode-specific state (UI drafts, etc.) goes in `working/`.
- Run the same validators (`validate_shot_list.py`, `audit_narration.py`) before any render.

## Expected App Behavior

A standalone app should:

- model the workflow as explicit stages
- keep the shot list and session config as the two per-session sources of truth
- enforce regeneration after upstream edits
- never silently carry stale downstream data
- use only illustrated scenes per chunk (or documented alternate-mode backgrounds with `context_justification`)
- delete legacy removed columns before processing a sheet
- never generate reveal animation inside the renderer
- enforce the pacing schema (STORY.md § Part 2): no broll without `context_justification`, no topic-shift without bridge narration, no Act boundary without bumper + opener
