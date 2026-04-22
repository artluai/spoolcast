# spoolcast roadmap

Planned-but-not-built work. This file is the backlog for features that don't fit into DESIGN_NOTES (which is the why-log of what's already been tried) and aren't urgent enough to be in-flight on the current session.

Items here may become real or get killed. Nothing here is a commitment.

## 1. artlu.ai video showcase — per-video "how it was made" guidebook

**What:** add a dedicated Videos category to artlu.ai's homepage showcase. Clicking a video expands into a guidebook that renders everything that went into making it: anchor reference images, character/object style library entries, the prompt used for every generated scene, the shot-list chunk list with narration beats, render audit results.

**Why:** the point is to show *how* each video was made, not just that it shipped. Turns the video itself into a learning artifact — readers see the source material, the editorial decisions, the style lock, and the scene-by-scene prompts. Distinct from watching the video: this is "peek under the hood."

**Spoolcast side:**
- Per-session export that bundles the artifacts a guidebook would need: `shot-list.json`, the session's style library entries + anchor image URLs, `manifests/scenes.manifest.json`, `working/narration-audit.json`, `working/render-audit.json`, and the final transcript.
- All of these already exist in `spoolcast-content/sessions/<id>/` — the work is packaging them into a clean JSON payload + a canonical fetch URL that artlu.ai can pull.
- Open question: auto-generated from the session dir at build time (always fresh, needs a build step), or hand-curated per video (more editorial control, more work)?

**Artlu.ai side:**
- New showcase category for videos, sibling to existing project categories.
- Detail-expand component that reads the bundled artifacts and renders them: anchor refs as thumbnails, prompt text as code blocks, chunk list with narration + per-chunk image, audit result summary, embedded video player.
- Canonical URL pattern (e.g. `artlu.ai/video/<session-id>`) with its own React route.

**Depends on:** nothing blocking. Can start whenever. Best done after at least 3-4 videos are shipped so the guidebook component has variety to render.

**Not in scope (yet):** comments, likes, remix, "fork this video's shot-list as a template."

---

## 2. Text-to-video for prompt-only chunks

**What:** for chunks currently generated as a single AI still (and with no character reference), optionally generate them as short video clips instead. The clips play natively through the existing broll pipeline; the chunk metadata just switches from `image_source: generated` to `image_source: generated_video` or similar.

**Why:** some chunks are purely symbolic and static (a bumper title card, a spotlit empty page, a mood-establishing scene). Motion can make these feel less flat without adding editorial weight. Prompt-only chunks are good candidates because we're not trying to preserve character consistency across them — which is where video models struggle.

**Cost landscape** (per ~3-5 second clip, approximate, kie.ai hosted):
- `seedance/1-lite` — ~$0.10-0.15 — weak character consistency, cheap experiment tier
- `kling/2.1` — ~$0.35-0.50 — moderate consistency
- `veo3-fast` — ~$0.20-0.35 — good consistency, strong value
- `veo3` — ~$1.50-2.50 — top-tier quality
- (for reference) still image via `nano-banana-2` — ~$0.05-0.08

So per-chunk cost goes up ~3-10x relative to a still. Budget-aware default: cheap tier (`seedance/1-lite`) for video candidates, hard cap on how many video chunks per video.

**Good candidates (prompt-only, symbolic):**
- Bumpers / title cards — motion could drift / pulse / accent the chapter break
- Purely symbolic scenes (spotlights, lens pans across blank pages, atmospheric moments)
- Mood-establishing pre-narration moments

**Bad candidates:**
- Anything with the recurring characters (builder/chad/etc.) — video models handle character consistency worse than still models, and we'd lose the style-library anchor path
- Anything with readable on-screen text — video models smear text. Same class of failure we already documented for stills (see VISUALS.md § "empty text slots get invented"), but worse because the text gets animated
- Scenes that reuse a prior chunk's image (the `reuse` pattern) — the whole point is consistency with the prior still

**Spoolcast side:**
- New image_source value (`generated_video` or `ai_video`) with its own field set (prompt, model, duration, aspect, seed).
- `generate_scene.py` sibling or extension that hits the kie.ai video endpoint (probably already exposed via kie_client, check).
- Chunk-level opt-in flag (`video_candidate: true`) so authors mark which prompt-only chunks are worth trying as video.
- Budget cap enforced at validator: no more than N video chunks per session, configurable in session.json.
- Preprocessor doesn't run for video chunks (they play as video, not as stroke-revealed frames).
- Remotion side: these already work — they route through the existing broll-video render path (`OffthreadVideo`).

**Out of scope (to avoid bloat):**
- Character-consistent video generation (save for when veo3-class model's character lock is reliable enough)
- Video editing / trimming inside the pipeline (the clip is the clip; if it's wrong, regen)
- Video-to-video (animating a still into a motion clip) — different beast; revisit separately

**Depends on:** nothing blocking.

---

## How this file gets updated

When an item here becomes in-flight, move the relevant details into DESIGN_NOTES (for rationale that will persist) + into the actual code / rule files (for current-state rules). Delete the item from here once it's shipped. Add new items as they come up.

Items should be scoped — "what, why, depends on, not in scope" at minimum. Anything more structured than that graduates to its own doc.
