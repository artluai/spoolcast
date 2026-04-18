# Workflow Rules

## Purpose

These are the global system rules for any agent or app working on this project.

This file defines:
- the system model
- the pipeline stages
- the source of truth
- regeneration rules
- validation rules
- failure conditions

This file is generic.
It must not depend on any specific video.

## System Goal

Turn a shot list into:

1. a reviewable HTML board
2. a renderable preview
3. a reliable final video pipeline

The system should minimize:
- stale data
- arbitrary visual decisions
- hidden assumptions
- unnecessary AI generation

When something is important across chats or tools:
- write it into the repo docs
- do not trust chat memory

## Source Of Truth

The shot list is the source of truth.

The workbook is one implementation of the shot list.

Downstream artifacts may include:
- asset manifests
- review-board HTML
- generated preview-data files
- Remotion render output

None of those may silently override the shot list.

Shared documentation should avoid absolute local paths unless a path is truly required for a working local setup.

## Global Visual Model

All videos use one visual layer per beat: the background.

That means:
- each beat is represented by one background visual
- emphasis comes from changing the background between beats
- vertical source media should be treated as full-height backgrounds
- returning to a prior background later is allowed

This system does not use a second visual layer.

If a legacy sheet still contains removed columns from an older model:
- delete those columns before doing any other work

## Pipeline Stages

The workflow has five separate stages:

1. shot-list editing
2. asset sourcing and validation
3. review-board generation
4. preview-data generation
5. video rendering

Each stage must have:
- a known input
- a known output
- a clear validation step

Do not blur these stages together.

For fragile visual systems:
- validate changes in a prototype or duplicate first when possible
- port the approved version back into the main implementation only after the behavior is clearly correct

## Stage Inputs And Outputs

### 1. Shot-List Editing
Input:
- current shot list

Output:
- updated shot list

### 2. Asset Sourcing And Validation
Input:
- shot list
- source links
- local media files

Output:
- verified local/previewable assets
- asset manifest

### 3. Review-Board Generation
Input:
- shot list
- verified asset manifest

Output:
- HTML review board

### 4. Preview-Data Generation
Input:
- shot list
- validated asset manifest
- audio timing data

Output:
- generated preview-data file(s) for the renderer

### 5. Video Rendering
Input:
- preview-data file(s)
- renderer/composition code
- validated media

Output:
- rendered preview or final video

## Regeneration Rule

When an upstream source changes, every affected downstream artifact must be regenerated.

Examples:

- If the shot list changes:
  - regenerate asset resolution if asset references changed
  - regenerate review board
  - regenerate preview-data files
  - rerender video output

- If assets change:
  - regenerate asset manifest
  - regenerate review board
  - regenerate preview-data files if asset references changed
  - rerender video if the render depends on those assets

Do not assume one rebuilt layer updates the rest.

## Long-Running Job Rule

For long-running jobs:
- start the job
- stop talking
- do not keep polling unless explicitly asked

Applies to:
- renders
- asset fetches
- AI image generation

## Reviewability Rule

If an asset cannot be visibly reviewed, it is not done.

This rule applies before render trust.

An asset is not done if:
- it only exists as a page link
- it cannot be previewed on the review board
- it fails fetch validation
- it is stale compared with the shot list

When building anything meant for external review:
- optimize for proof and clarity over flavor text

## No Improvisation Rule

The renderer must not improvise:
- where something appears
- how large it is
- when it appears
- why it appears

If a visual decision matters, it must come from:
- the shot list
- or a deterministic system rule

## Failure Conditions

A task is not complete if any of these are true:

- the shot list is not correct
- the review board does not match the shot list
- the preview-data file does not match the shot list
- the render is based on stale preview data
- deleted columns still influence downstream output
- the asset manifest contains unresolved required assets
- a background run resets when it should be continuous

## Validation Checklist

Before saying a state is correct, verify:

1. shot list reflects intended plan
2. asset layer reflects shot list
3. review board reflects shot list
4. preview-data files reflect shot list
5. render output reflects current preview-data files

If any one layer is stale:
- the work is not done

## Environment Rule

Use a known-good local render environment.

Render reliability matters more than clever background execution tricks.

Prefer:
- a stable local Node/runtime setup
- direct user-terminal render commands when needed

Avoid:
- fragile detached launch patterns unless proven stable
