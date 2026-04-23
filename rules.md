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
- One AI illustration per narration chunk is the default. Stock/broll is an alternate mode that requires `context_justification` (STORY.md § Part 2).
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
5. **Stage 2 — shot-list.** Agent builds the shot list from the locked screenplay. User reviews the xlsx directly.
6. **Stage 3 — chunking.** Chunks populated per heuristics. User approves visible boundaries.
7. **Stage 4 — external assets + AI generation.** Externals first (mechanically enforced by `batch_scenes.py` pre-flight per PIPELINE.md § Stage 4 ordering rule), QA pass, re-approval, then AI spend.
8. **Stage 5 — preprocessing.** Deterministic; no user decisions.
9. **Stage 6 — review board.** User reviews the per-chunk board. Regeneration triggered from any flag.
10. **Stage 7 — render + preview.** User watches the preview. Approves or requests revision.
11. **Stage 8 — publish.** Title, thumbnail, description per SHIPPING.md. User final-approves before upload.

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
