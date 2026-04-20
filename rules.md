# Spoolcast Rules Index

Start here.

Spoolcast turns chat, content, and ideas into illustrated videos. Each narration chunk becomes one AI-generated scene in a per-session locked style; a deterministic preprocessor reveals it over time; Remotion plays the resulting PNG sequences against audio.

This file tells any new agent or app:
- which rule files exist
- what each file is for
- what order to read them in

Read repo-local rules before making suggestions, writing workflow docs, or changing implementation details.

## Read Order

Read these files in this exact order:

1. [PIPELINE.md](./PIPELINE.md) — workflow, session config, shot-list spec, render config
2. [STORY.md](./STORY.md) — script extraction, pacing, viewer context
3. [VISUALS.md](./VISUALS.md) — assets, preprocessor, transitions
4. [SHIPPING.md](./SHIPPING.md) — review board, publishing

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

## Expected Agent Behavior

A new agent should:

1. read this file
2. read the rule files in the required order
3. identify the current pipeline stage
4. make changes only within that stage unless regeneration is required
5. validate downstream outputs after any upstream change

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
