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

## 3. Mobile export from widescreen (Process A.1)

**What:** post-render optional chain that turns the shipped 16:9 master into polished 9:16 / 1:1 variants for Reels / TikTok / Shorts, with burned captions and — for long videos targeting TikTok — multi-part splits with "to be continued…" cards and per-part badges.

**Why:** platform auto-captions are inadequate (timing drift, no style control, strip off when sound is muted). Professional creators on Reels/TikTok/Shorts burn captions directly into the video and lock the composition to the target aspect. The existing pipeline already produces all the ingredients — rendered master, SRT, per-chunk scenes, style library, audit — so mobile export is the last mile.

**Spoolcast side:**
- Shot-list fields: `mobile_focal`, `mobile_unsafe`, `mobile_image_path`, `mobile_overlays` (all optional, audit-populated — see PIPELINE.md § Mobile-Export Fields).
- `audit_scenes.py` extended with mobile-crop safety check — runs on every session, not just mobile-bound ones, so the data is on disk when needed.
- `generate_scene.py --mobile-variant` for regenerating portrait-native scenes for `mobile_unsafe` chunks.
- `generate_srt.py --exclude-onscreen-cues` for burn-in captions (strips the `[on-screen: …]` bracketed cues since the frame already shows the text).
- `scripts/burn_captions.py` — ffmpeg libass burn-in using the Caveat Bold caption style.
- `scripts/export_mobile.py` — crop, caption burn, optional split, part badge.
- `generate_thumbnail.py` extended with `--aspect 9:16|1:1 --part-badge "1/3"`.
- Caveat-Bold.ttf bundled at `scripts/assets/fonts/`.

**Not in scope (v1):**
- Auto-trim-to-highlights (trimming is manual)
- Per-platform distinct caption styles (one style fits all)
- CapCut-style word-by-word caption highlighting
- YouTube Shorts auto-upload
- Vertical-native Remotion composition (that's Process B below)

**Depends on:** ffmpeg with libass (homebrew-ffmpeg tap, not default brew formula — see SHIPPING.md § Part 3 Prerequisites).

---

## 4. Mobile-first authoring (Process B)

**What:** a parallel pipeline where sessions are composed at 9:16 (or 1:1) from chunk 1 — Remotion canvas is mobile, every scene is AI-generated at mobile aspect, captions burn in natively at mobile dimensions, no 16:9 master ever exists. Not a mode switch on the existing pipeline; a sibling pipeline that shares atoms (caption style, font, libass prereq, publish logic) but owns its own composition, audit, and render configs.

**Why:** some content is natively mobile-first — TikTok-style explainers, phone-screen walkthroughs, vertical demos. Deriving these from a widescreen master (Process A.1) forces compromises in composition, leaves ~40% of the pixel budget unused after a 9:16 crop, and requires regen passes that mobile-first authoring avoids entirely.

**Spoolcast side (sketch — design when the work starts):**
- Session config: `aspect_ratio: "9:16"` or `"1:1"` drives canvas dimensions everywhere downstream.
- Scene generation: passes the mobile aspect to kie.ai from the first chunk; no `--mobile-variant` flag needed.
- Remotion: a sibling composition for the mobile canvas.
- Audit: existing scene audits run; the mobile-crop audit (A.1's) is inapplicable and skipped.
- Publish: reuses the caption-styling atoms from SHIPPING.md § Part 3; skips the crop + focal + regen chain. Split-into-parts may still be useful for long TikTok uploads and can reuse A.1's split implementation.

**Not in scope (B v1 when it lands):**
- Cross-compiling a mobile session back into a 16:9 master. If both are needed, run A.1 and B as separate sessions.
- Shared session metadata between A.1 and B renders (they're independent sessions with independent shot-lists).

**Depends on:** A.1 shipped first (to prove the caption / font / libass atoms work end-to-end), then B takes over the composition + scene-gen aspect plumbing.

---

## 6. Meme / reaction SFX + non-voice audio per chunk

**What:** extend the audio pipeline so meme / reaction / broll chunks can carry non-voice audio — sound effects (a thud, a ding, a vinyl scratch, a facepalm slap, a laugh track), short music stingers, or burned audio from a broll clip. Currently every chunk expects TTS narration tied to its beats; silent-hold meme chunks pause the video awkwardly (caught on dev-log-02 — silent meme beats felt like dead air).

**Why:** memes and reactions land harder with accompanying audio than with silence. A Surprised Pikachu meme with a brief "huh?!" SFX delivers more than the same image played over silence for 1.5s. The current workaround — consolidating memes into neighboring narration chunks so the meme plays during its topical narration — works but limits where memes can go (they have to piggy-back on a narration beat). Independent punchline timing needs independent audio.

**Spoolcast side:**
- New chunk field (schema addition): `sfx` (or `punchline_audio`) — path to a short audio file in `source/fetched-assets/sfx/` or `source/generated-assets/sfx/`.
- Audio source options: (a) manually sourced SFX library (freesound.org and similar), (b) ElevenLabs / Google Cloud TTS for scripted punchline voice lines, (c) extracted audio from broll mp4 clips. Each source category gets its own convention.
- Validator: chunk with `silent_hold: true` and no narration must have either `sfx` set OR a documented exception.
- Preview-data + Remotion composition: play `sfx` audio during the chunk's duration alongside (or instead of) narration audio; mix volumes.

**Editorial rules (to codify when this ships):**
- One SFX per chunk maximum — no stacked audio.
- SFX duration ≤ chunk duration. Trim or loop appropriately.
- SFX should serve the meme's register — no generic "cartoon boing" on a doomer beat.

**Not in scope:**
- Full music tracks / background score. Short stingers only.
- AI-generated SFX via audio-gen models (deferred; a curated SFX library is cheaper).
- Mixing multiple SFX per chunk.

**Depends on:** nothing blocking. Sourcing a starter SFX library (20–30 clips covering common reaction registers) is the first step.

---

## 7. Split-focus camera tricks for mobile re-framing

**What:** when a widescreen scene has 2+ subjects laid out horizontally (builder + ai-figure across desk, side-by-side panels, before/after composites) and the chunk's duration is long enough (≥6s), the mobile re-frame animates a Ken-Burns-style pan from subject A in the first half to subject B in the second half — instead of cropping both into a single 9:16 frame and losing comprehension.

**Why:** the mobile-crop comprehension audit (SHIPPING.md § Mobile-crop audit) flags chunks where 2-subject horizontal compositions get gutted by the 9:16 crop (caught broadly on dev-log-03 mobile — C13 side-by-side, C17 builder+ai-figure, C18 balance scale). Today the only fix is to regenerate at 9:16 native with vertical compositions, which sometimes fights the editorial intent. A timed pan keeps the original framing and uses chunk duration as the editorial unit.

**Spoolcast side:**
- New chunk field (schema addition): `mobile_pan` (or similar) — `{from: "left", to: "right", ease: "smooth"}` or `{focus_a_until_sec: 4.0}`.
- Preprocessor extension: when `mobile_pan` is set, generate frame sequences that translate the source 16:9 image across the 9:16 viewport over the chunk's duration.
- Audit recognition: `audit_mobile_crops.py` accepts pan-equipped chunks as a valid alternative to vertical regen — judges comprehension across the full pan, not a single frame.
- Editorial gate: only valid for chunks ≥6s; shorter chunks revert to regen.

**Editorial rules (to codify when this ships):**
- One pan per chunk maximum; no chained pans.
- Pan direction is editorial — left-to-right for "this happened then this," right-to-left rare.
- Pan timing splits chunk duration cleanly — first half on subject A, hold ~0.5s, smooth pan to B for second half.
- Not a fallback for everything — use deliberately on high-impact 2-subject moments. Vertical regen is still the default for crowded compositions, race-line scenes, etc.

**Not in scope:**
- Multi-subject (3+) pans.
- 3D parallax.
- Mid-chunk cuts (use chunk-split instead).

**Depends on:** Remotion composition supporting per-chunk transform animations driven by chunk metadata.

---

## How this file gets updated

## 5. Remotion-native bumper rendering

**What:** bumpers (`boundary_kind="bumper"` chunks) render directly in Remotion as styled text compositions — not as kie.ai-generated PNGs. A "THE INCIDENT" bumper becomes a Remotion component with Caveat Bold at size N on the current canvas, centered; no rasterized image involved.

**Why:** bumpers are pure text cards (e.g. "THE INCIDENT", "THE FIX", "PAYOFF"). Rasterizing them via kie.ai creates two avoidable failure modes:

1. **Aspect-specific clipping** — the rasterized PNG is fixed at one aspect; cropping it for mobile clips the letter edges. This session's B3 "PAYOFF" clipped to "PAYOF" at 4:5.
2. **Stochastic letter-form variance** — kie.ai occasionally produces slight misalignment, uneven letter weight, or artifacts that a text renderer wouldn't.

Remotion-rendered text re-lays-out per aspect automatically, and every character is pixel-perfect. Cost: $0 per bumper vs ~$0.05 at kie. Explicit mobile requirement: when mobile export runs, bumpers compose natively at the mobile canvas (the 1080×1350 4:5 content area centered on the 1080×1920 frame), NOT by scaling a widescreen bumper PNG. Each bumper renders fresh per export-target aspect.

**Fontsize rule (canvas-agnostic):** Caveat Bold, fontsize chosen so the rendered text fits within 85% of canvas width. Formula: `fontsize = min(canvas_safe_max, int((canvas_w * 0.85) / (len(text) * 0.55)))`, where `canvas_safe_max` is a ceiling (e.g. 220 for widescreen, 200 for mobile) and `0.55` is the average Caveat Bold char-width-per-fontsize ratio. For mobile 1080-wide canvas this fits "THE INCIDENT" (12 chars) at ~140 px and shorter titles at up to 200 px. Never hardcode to a specific bumper text.

**A.1 temporary path:** until this lands, the A.1 mobile stitcher uses ffmpeg `drawtext` to live-render bumpers on white background at the mobile canvas, applying the same fontsize formula above. That implementation should migrate to Remotion-native rendering when this item ships, and the `drawtext` fallback removed from the A.1 stitcher.

**Spoolcast side:**
- `boundary_kind: bumper` chunks skip kie.ai generation entirely — no scene PNG written.
- Remotion composition adds a `BumperCard` component that reads the chunk's `on_screen_text` and renders Caveat Bold text sized for the current canvas.
- Preprocessor skips bumpers (no reveal frames; the card just holds).
- `validate_shot_list.py` forbids `image_source: generated` on chunks with `boundary_kind: bumper` (post-migration). Pre-migration, warn-but-accept.

**Not in scope:**
- Bumpers with non-text elements (photos, backgrounds). If a bumper needs imagery beyond text, it stays kie.ai-generated.
- Migrating existing shipped sessions. New sessions start Remotion-native; shipped sessions keep their generated bumper PNGs.

**Depends on:** Caveat font already bundled via `@remotion/google-fonts/Caveat` — no new asset work.

---

When an item here becomes in-flight, move the relevant details into DESIGN_NOTES (for rationale that will persist) + into the actual code / rule files (for current-state rules). Delete the item from here once it's shipped. Add new items as they come up.

Items should be scoped — "what, why, depends on, not in scope" at minimum. Anything more structured than that graduates to its own doc.
