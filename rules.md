# Session To Video Rules Index

Start here.

This file tells any new agent or app:
- which rules files exist
- what each file is for
- what order to read them in

Read repo-local rules before making suggestions, writing workflow docs, or changing implementation details.

## Read Order

Read these files in this exact order:

1. [WORKFLOW_RULES.md](./WORKFLOW_RULES.md)
2. [SHOT_LIST_SPEC.md](./SHOT_LIST_SPEC.md)
3. [ASSET_RULES.md](./ASSET_RULES.md)
4. [REVIEW_BOARD_RULES.md](./REVIEW_BOARD_RULES.md)
5. [RENDER_RULES.md](./RENDER_RULES.md)

## What Each File Does

### WORKFLOW_RULES.md
Use this first.

It defines:
- the global system model
- source-of-truth rules
- pipeline stages
- regeneration rules
- failure conditions
- validation rules

### SHOT_LIST_SPEC.md
Use this when reading, creating, validating, or editing the shot list.

It defines:
- what the shot list is
- required headers
- field meanings
- required vs optional fields
- allowed values and formatting expectations
- how shot-list fields map to downstream outputs

### ASSET_RULES.md
Use this when sourcing, fetching, validating, reusing, or generating assets.

It defines:
- sourcing order
- Google Images / Google Videos usage
- reuse rules
- asset validation
- fetch pipeline
- AI budget rules

### REVIEW_BOARD_RULES.md
Use this when building or validating the HTML review board.

It defines:
- what the review board must show
- what must be visible
- what counts as failure
- layout expectations
- review-board validation rules

### RENDER_RULES.md
Use this when generating preview data, building Remotion behavior, or rendering video.

It defines:
- preview/render expectations
- background-run behavior
- motion rules
- what must never be improvised
- regeneration requirements for video outputs

## Non-Negotiable System Defaults

These apply everywhere unless explicitly replaced by a future system rewrite:

- The shot list is the source of truth.
- Videos use one visual layer per beat: the background.
- Do not create, preserve, or read a second visual layer.
- If an asset cannot be visibly reviewed, it is not done.
- When the shot list changes, downstream artifacts must be regenerated.
- If a legacy sheet still contains removed columns, delete them before continuing.
- Shared docs should avoid absolute local paths unless a path is truly required to make something work.

## If There Is A Conflict

If two files appear to conflict:

1. `SHOT_LIST_SPEC.md` wins for shot-list structure and field meaning.
2. `ASSET_RULES.md` wins for asset sourcing and validation.
3. `REVIEW_BOARD_RULES.md` wins for HTML review-board behavior.
4. `RENDER_RULES.md` wins for preview/render behavior.
5. `WORKFLOW_RULES.md` wins for pipeline-level behavior, source of truth, and regeneration rules.

If a real conflict still remains:
- do not guess
- report the conflict clearly
- stop before making a silent assumption

## Expected Agent Behavior

A new agent should:

1. read this file
2. read the rule files in the required order
3. identify the current pipeline stage
4. make changes only within that stage unless regeneration is required
5. validate downstream outputs after any upstream change

## Expected App Behavior

A standalone app should:

- model the workflow as explicit stages
- keep the shot list as the root data source
- enforce regeneration after upstream edits
- never silently carry stale downstream data
- use only background visuals per beat
- delete legacy removed columns before processing a sheet
