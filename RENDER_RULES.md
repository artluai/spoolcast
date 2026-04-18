# Render Rules

## Purpose

This file defines how preview-data generation and Remotion rendering should behave.

## Preview Rule

The preview should act like a rough cut.

It should not act like:
- a debug export
- a diagnostics page
- a review board converted directly into a video

## Required Render Behavior

The preview should:
- use real video backgrounds when available
- use image backgrounds when video is not available
- use full scene/chapter audio correctly
- remove debug text from frame
- reflect the current shot list exactly

## Background Rules

Backgrounds are the only visual layer.

If adjacent beats use the same background:
- treat them as one continuous background run
- do not restart the media
- do not restart the camera move

One reused background run should feel like one shot.

If the source media is vertical:
- render it as a full-height background
- do not turn it into a floating element

## Removed Columns Rule

The render pipeline must not read, preserve, or recreate data from removed legacy columns.

If a legacy shot list still contains those columns:
- delete them upstream first
- then regenerate preview data
- then rerender

## Motion Rules

Motion must be:
- simple
- justified
- consistent with the shot list

Allowed:
- hold
- slow push
- gentle pan
- continuous run-level motion

Not allowed by default:
- impact shake
- micro zoom on impact
- arbitrary camera pops
- repeated reset motion on reused backgrounds
- decorative transitions between every beat

## Visual Effect Rules

Do not apply global visual effects by default that darken or stylize the whole frame unnecessarily.

Disallowed by default:
- global gradient overlays
- decorative darkening layers that are not explicitly needed

## Preview-Data Rules

Preview-data generation must:
- read from the current shot list
- read from current validated asset data
- export only the layers allowed by the current system

Current rule:
- preview data must contain background-only beats

## Render Regeneration Rule

When any of these change:
- shot list
- asset resolution
- preview-data generation logic
- composition logic

Then the video must be rerendered.

Do not trust an older MP4 if any upstream layer has changed.

## Validation Rules

The render fails if:
- it shows deleted elements
- it uses stale preview data
- reused backgrounds reset when they should be continuous
- audio plays incorrectly across the planned duration
- motion is arbitrary or visually distracting

## Long-Running Render Rule

When starting a render:
- start it
- let it run
- avoid noisy polling unless explicitly requested

For reliability:
- prefer stable direct terminal renders over fragile detached launch patterns
