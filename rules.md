# Spoolcast Rules Index

Start here.

Spoolcast turns chat, content, and ideas into illustrated videos. Each narration chunk becomes one AI-generated scene in a per-session locked style; a deterministic preprocessor reveals it over time; Remotion plays the resulting PNG sequences against audio.

This file tells any new agent or app:
- which rules files exist
- what each file is for
- what order to read them in

Read repo-local rules before making suggestions, writing workflow docs, or changing implementation details.

## Read Order

Read these files in this exact order:

1. [WORKFLOW_RULES.md](./WORKFLOW_RULES.md)
2. [SCRIPT_EXTRACTION_RULES.md](./SCRIPT_EXTRACTION_RULES.md)
3. [SESSION_CONFIG_SPEC.md](./SESSION_CONFIG_SPEC.md)
4. [SHOT_LIST_SPEC.md](./SHOT_LIST_SPEC.md)
5. [ASSET_RULES.md](./ASSET_RULES.md)
6. [PREPROCESSOR_RULES.md](./PREPROCESSOR_RULES.md)
7. [TRANSITION_RULES.md](./TRANSITION_RULES.md)
8. [REVIEW_BOARD_RULES.md](./REVIEW_BOARD_RULES.md)
9. [RENDER_RULES.md](./RENDER_RULES.md)
10. [PUBLISHING_RULES.md](./PUBLISHING_RULES.md)

If you are about to challenge or change a rule, also read [DESIGN_NOTES.md](./DESIGN_NOTES.md) — it captures the reasoning behind current decisions and what was tried and abandoned. The rule files tell you what to do; design notes tell you why.

## What Each File Does

### WORKFLOW_RULES.md
Use this first.

It defines:
- the global system model
- source-of-truth rules
- the directory contract
- pipeline stages
- regeneration rules
- failure conditions
- validation rules

### SESSION_CONFIG_SPEC.md
Use this when reading, creating, or validating a per-session config file.

It defines:
- the canonical `session.json` location
- required and optional fields
- style anchor rules
- model selection
- budget rules

### SHOT_LIST_SPEC.md
Use this when reading, creating, validating, or editing the shot list.

It defines:
- what the shot list is
- required headers (including `Chunk`)
- field meanings
- required vs optional fields
- allowed values and formatting expectations
- how shot-list fields map to downstream outputs

### ASSET_RULES.md
Use this when generating, sourcing, validating, reusing, fetching, or budgeting visual assets.

It defines:
- the primary AI-illustrated scene pipeline
- the style anchor rule
- the scene manifest contract
- the Kie provider spec
- the alternate mode for stock / sourced assets
- AI budget rules

### PREPROCESSOR_RULES.md
Use this when building or modifying the scene preprocessor.

It defines:
- the input/output contract for reveal frame sequences
- supported reveal styles
- determinism and caching rules
- the renderer's restrictions on reveal behavior

### REVIEW_BOARD_RULES.md
Use this when building or validating the HTML review board.

It defines:
- what the review board must show per chunk
- layout expectations
- what counts as failure
- review-board validation rules

### RENDER_RULES.md
Use this when generating preview data, building Remotion behavior, or rendering video.

It defines:
- the preview-data schema (chunk-driven)
- motion mapping
- what must never be improvised
- the rule that the renderer plays preprocessor PNG sequences as-is
- regeneration requirements for video outputs

## Non-Negotiable System Defaults

These apply everywhere unless explicitly replaced by a future system rewrite:

- The shot list is the source of truth for structure and narration.
- The session config is the source of truth for style, reveal behavior, and budget.
- Videos use one primary visual layer per frame: the illustrated scene.
- Overlays (logos, badges, small reference artifacts) are permitted only when every overlay's position, size, entry/exit timing, and duration are explicitly specified per-overlay in the shot list. Renderer-improvised placement, size, or timing is still banned. AI-judged or AI-generated transparency is still banned — overlay sources must be authoritative images with clean alpha (brand logos, official badges, cleanly-cropped real screenshots). See `RENDER_RULES.md` overlay placement schema and `ASSET_RULES.md` overlay sourcing. See `DESIGN_NOTES.md` "Killed: foreground overlays → Reconsidered" for the reasoning behind the carve-out.
- One AI illustration per narration chunk is the default. Stock sourcing is an alternate mode, not the default.
- The preprocessor owns reveal animation; the renderer plays PNG sequences as-is.
- If a scene cannot be visibly reviewed, it is not done.
- When the shot list, session config, or scene manifest changes, downstream artifacts must be regenerated.
- If a legacy sheet still contains removed columns, delete them before continuing.
- Shared docs should avoid absolute local paths unless a path is truly required to make something work.

## If There Is A Conflict

If two files appear to conflict:

1. `SESSION_CONFIG_SPEC.md` wins for session config structure and fields.
2. `SHOT_LIST_SPEC.md` wins for shot-list structure and field meaning.
3. `ASSET_RULES.md` wins for scene generation, asset sourcing, and validation.
4. `PREPROCESSOR_RULES.md` wins for reveal animation behavior and frame output.
5. `REVIEW_BOARD_RULES.md` wins for HTML review-board behavior.
6. `RENDER_RULES.md` wins for preview/render behavior.
7. `WORKFLOW_RULES.md` wins for pipeline-level behavior, source of truth, and regeneration rules.

If a real conflict still remains:
- do not guess
- report the conflict clearly
- stop before making a silent assumption

### Diagnostic anti-pattern: pipe-buffering

Do NOT pipe long-running commands through `head` / `tail` / `grep` when
you need to see progress. These tools buffer their input until the
upstream process exits (or until N lines accumulate, in head's case).
A working process can look completely hung because no output reaches
your terminal until it finishes.

This caused ~30 minutes of false debugging where a working API wrapper
was repeatedly killed mid-flight under the false belief it was hanging.

If you need progress visibility on a long command:
- Run it without any pipe: `python -u script.py` (the `-u` flag is also
  important — disables Python's own stdout buffering)
- If filtering is needed, use `tee file.log | head -30` so the full
  output is captured to disk while head shows the truncated view
- For background tasks, read the output file directly without piping

If you're sure a command is hanging (no output for >2x expected time),
verify with `ps aux | grep <name>` to check if the process is alive
and consuming CPU before killing it.

### User request vs existing rule

If the user asks for something that contradicts a documented rule in any
of the files above, do NOT silently update the rule to justify the new
request. This is how rules get rewritten every session and lose meaning.

Instead, flag the conflict explicitly before acting, using this format:

> ⚠️ **Rule conflict**
> `<FILE.md>` says: "*<quote the specific rule>*"
> You're asking for: *<restate the request>*
> Options:
> - (a) **update the rule** — change the documented rule AND apply the
>   new behavior (both happen)
> - (b) **one-off exception** — apply the behavior for this case only,
>   do not touch the rule
> - (c) **keep the rule** — decline the request

Wait for the user to pick before proceeding. If the user answers with
anything other than "update", do NOT edit the rule file.

This applies specifically to: `TRANSITION_RULES.md` (reveal type / camera
/ pauses), `SHOT_LIST_SPEC.md` (shot-list structure), `ASSET_RULES.md`
(image generation), and any other documented rule. Obvious clarifications
or typo fixes in the rule itself do not need this ceremony.

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
- use only illustrated scenes per chunk (or documented alternate-mode backgrounds)
- delete legacy removed columns before processing a sheet
- never generate reveal animation inside the renderer
