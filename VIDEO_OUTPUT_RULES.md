# Video Output Rules

Engine-level rules for video output quality, character consistency, and pipeline mechanics. These were learned the hard way during the news-anime-bot Episode 1 build (April 2026, kling-3.0/video + gpt-image-2 + Google Chirp3-HD TTS + ffmpeg) and apply to any video this engine produces.

These rules previously lived in global Claude memory (`behavior_character_cloning.md`, `reference_kling_text_limitation.md`, `feedback_caption_placement.md`, `feedback_never_touch_anchors.md`). Moved here to live with the engine code so they get versioned alongside the pipeline.

---

## 1. Style anchors are load-bearing — never overwrite without explicit per-call permission

Style library anchors (`styles/<name>/anchor.png`) and locked character references (`characters/<name>.png` once committed) are NEVER to be regenerated, overwritten, or mutated without an explicit per-call "yes, regenerate the anchor" from the user. Ambiguous approvals ("yes", "sounds good", "try it", "I love that artstyle") do NOT authorize anchor regeneration.

**Why:** Every session that inherits the style references them, every character reference aliases them, overwriting one cascades downstream. The kie.ai temp-URL recovery path is luck — tempfile URLs expire in ~24h, and the local file is instant-irrecoverable without recovery.

**How to apply:**
- Default for any "test the style" ask: regen a *test scene* (`generate_scene.py --force` on one chunk) with prompt override. Does not touch the anchor or style.json's anchor metadata.
- OR draft a prompt revision for user to approve textually BEFORE any generation.
- When proposing anchor regeneration specifically: phrase the ask unambiguously: *"This will overwrite the library anchor file at `<path>`. The old file will be gone (recoverable only from kie's temp URL for ~24h). Confirm?"* — not bundled with other actions. Wait for explicit yes.

Applies to any reference image in a library that other sessions depend on.

---

## 2. Recurring real-person caricature pipeline

For projects that need a recurring caricature of a real public figure (news-anime-bot, satirical content, editorial illustration):

### 2.1 Source 2–4 reference photos
Variety matters. Different angles (front, three-quarter), expressions (neutral, smile, animated), settings (casual, formal). Single-photo refs over-fit to whatever expression / hair-day was in that frame.

### 2.2 Upload to kie.ai temp storage
- `POST https://kieai.redpandaai.co/api/file-stream-upload`
- Multipart form: `file` (binary), `uploadPath` (e.g., `images/<project-name>`), `fileName`
- Auth: `Authorization: Bearer $KIE_API_KEY`
- Response gives `data.downloadUrl` — that's the URL for `input_urls` / `image_input` / `kling_elements.element_input_urls`. Files expire in 3 days.

### 2.3 Use `gpt-image-2-image-to-image` only
nano-banana-2 has Google's strict identity policy — rejects ALL real-person prompts and inputs. Confirmed empirically. Don't waste a run.

### 2.4 Name-free prompt — never name the subject anywhere in the request
- Filter triggers in **both** `prompt` AND `kling_elements.description`. Naming the subject in `description` ("Sam Altman, OpenAI CEO character") triggers content rejection (manifests as repeated 500 errors) even when prompt text is name-free.
- Keep `description` purely role-based: "the tech CEO character", "the CFO character".
- Describe the subject in the prompt by features, not name:
  - **Visual/animation style** — e.g., "Bleach-style anime," "Tartakovsky angular flat-shape"
  - **Signature features to amplify** — the parts that make them recognizable in real life. For caricature, lean *into* those features. Each subject needs a verified feature list — verify against actual photos, don't assume.
  - **On-brand wardrobe — verify against photos, don't assume.** Example: Altman wears Patagonia "Better Sweater" crewneck pullovers, Henleys, button-downs — NOT vests, NOT turtlenecks. Generic "tech-CEO costume" loses recognition; their real outfit is a recognition cue.

### 2.5 Never use negative instructions in image-gen prompts
"Not", "no", "none", "avoid", "without" get IGNORED or actively backfire (the negation token gets stripped, leaving the rejected item as a positive instruction). Use ONLY positive descriptors. If the model defaults to something wrong, fight it by making the desired alternative so vivid and repeated that it crowds out the default. Universal, not specific to character work.

### 2.6 Image-to-image with a real photo input pulls toward photoreal
Even with strong "anime illustration NOT a photo" prompt language, the body and wardrobe inherit the photo's reality while only the face stylizes. For *style fidelity*, prefer **text-only** with detailed feature description. For *identity fidelity*, prefer image-to-image. Choose based on which matters more.

### 2.7 The two-input redraw recipe (validated)
For BOTH identity-fidelity AND style-fidelity out of `gpt-image-2-image-to-image`:
1. **Input 1** = a previous good character ref (image-to-image-derived from a real photo) — provides face/identity/pose/background
2. **Input 2** = a separate fully-text-to-image-generated illustration with the desired clothing-rendering style (e.g., a cast lineup with flat cel-shaded outfits) — provides the rendering language we want applied
3. **Prompt:**
   - Tells model: input 1 = identity, pose, background; input 2 = clothing-rendering style
   - Uses **REDRAW** language, NOT "preserve identically." Preserve language locks in the original photo-leaning rendering and won't budge.
   - Spells out specific positive descriptors of what flat cel-shading means: "solid uniform color blocks," "hard-edged darker shadow shapes," "sharp clean thin black anime line work outlining each garment."

### 2.8 Output as multi-pose character sheet
Ask for "character design sheet — same character in 3 poses: front view, three-quarter view, expression close-up. Consistent design across all poses." This locked sheet becomes the reference fed forward to Kling video via `kling_elements`.

### 2.9 Lock the character sheet once approved
Same hard rule as §1 — don't regenerate without explicit "yes regen this character" per call.

### 2.10 File naming convention
- Source photos: `<character>-source-N.{jpg,png}` (e.g., `altman-source-1.jpg`)
- Generated character sheet: `<character>-sheet-<style>.png` (e.g., `altman-sheet-bleach.png`)
- Locked production reference: `characters/<character>.png` (canonical name)

---

## 3. Kling 3.0 video — known gotchas

### 3.1 In-frame text mangles
Kling 3.0 cannot reliably render legible text in scenes. Examples from Episode 1:
- `OPENAI` → "OAENIAI" / "OENIAI"
- `GOOGLE` → "GOGLE"
- `PAST DUE` → "PASST DURE"
- `$40,000,000,000` → "$40,00,00,000"

**Rule for Kling prompts:**
- Don't ask Kling to render literal text. Building names, banner copy, sign text, dollar amounts, document text, screen displays — all garbled.
- Convey brand identity via visual cues: color (Google = primary palette; Amazon = bold orange; OpenAI = neon green), distinctive silhouette, iconography (Amazon arrow, etc.).
- For required in-frame text: render in **post via ffmpeg `drawtext`** as an overlay between Kling output and audio-mux/concat. Produces perfect typography.

This applies to Kling 3.0. Other video models (Veo 3.1, Sora 2) may handle text differently — re-test before assuming.

### 3.2 `kling_elements` lead-frame flash
The very first ~0.3–0.5s of any clip generated with `kling_elements` is the literal input character-sheet image — Kling starts on the reference and animates from there. In a 5s clip this flash is visible and reads as a "wrong frame" to the viewer.

**Mitigation in stitch pipeline:** skip the lead 0.5s of any clip that used `kling_elements`. Effective usable clip length is 4.5s (vs 5.0s nominal). Plan beat durations and freeze-frame extensions accordingly.

### 3.3 `kling_elements` requires 2–4 input images per element
Single-image element refs return a 422. Provide 2-4 distinct images per character.

### 3.4 `image_urls` is mandatory when prompt has `@role` references
Even when using `kling_elements`, the `image_urls` field must also be populated when the prompt contains `@role` references. The first character ref's URL works as a stand-in.

---

## 4. ffmpeg concat — `-c copy` mangles timestamps on variable-duration mp4s

When concatenating multiple variable-duration mp4 clips that came from re-encoded sources, `-c copy` produces a final video where timestamps drift and clips render out of sync with their position (clip N's caption appears over clip N-1's video, etc.).

**Fix:** re-encode during concat (`-c:v libx264 -c:a aac` instead of `-c copy`). Adds maybe 5s of CPU time but produces correct output.

---

## 5. ASS subtitle rendering — set `PlayResX` / `PlayResY` to match video resolution

libass defaults its script resolution to 384×288. If the actual video is e.g. 720×1280, fontsize values in the SSA Style get scaled up proportionally — a `Fontsize=18` becomes ~80px in the final video, producing giant captions.

**Fix:** generate the captions as an ASS file (not SRT + force_style) with `[Script Info] PlayResX: <video_w>` and `PlayResY: <video_h>` set. Then fontsize values render in natural pixels at the actual video resolution.

---

## 6. Caption placement must avoid covering on-screen text and important imagery

Burned-in captions should be positioned in the area of the frame with the LEAST visually important content. They must not cover:
- In-frame text (signage, banners, document content, ticker text)
- Character faces in close-ups
- Action focal points
- Brand logos / decorative elements (e.g., Japanese kanji that's part of the aesthetic)
- Any element specifically prompted into the visual

**Default for 9:16 mobile video:** captions in the bottom-third zone (around 18-22% from bottom) — sits ABOVE social-platform overlays but doesn't crowd central visual. **However**, this is a starting position, not a guarantee. Each beat's visual must be checked.

**Per-beat overrides:** when a specific beat has on-screen content in the default caption zone (a "PAST DUE" notice on a door, kanji watermarks down the side, important text on a screen), the caption for that beat must be moved out of the way:
- Top-zone captions if the bottom is busy
- Higher-than-default bottom captions
- Smaller fontsize for that beat to reduce footprint

**Pipeline implication:** the stitch step should support per-beat caption positioning — either a per-beat `MarginV` override or a check-and-warn step that flags beats where the caption likely overlaps prompted visual content.

**Authoring implication for prompts:** when designing scene prompts, KEEP important on-screen text/imagery in the upper-middle of the frame so the default caption placement doesn't block them.

---

## 7. SSML pacing — `<break>` works, `<emphasis>` distorts in Chirp3-HD

For comedic timing on punchline beats, Google Chirp3-HD voices respond cleanly to `<break time="...ms"/>` tags but render `<emphasis level="strong">word</emphasis>` with a distorted/mangled output on the emphasized word.

**Use:** `It missed <break time="400ms"/> every one.`
**Avoid:** `It missed <break time="400ms"/> every <emphasis level="strong">one</emphasis>.`

The pause itself gives the comedic timing without distortion.

---

## 8. Variable beat durations driven by narration > fixed-grid clips with padding

When stitching multi-clip videos with TTS narration, do not pad each clip to a uniform fixed duration (e.g., always 5s). Short narration lines get awkward trailing silence; long lines get truncated mid-word.

**Right pattern:**
1. Probe each narration mp3 for duration via ffprobe
2. Beat target duration = narration duration + tail buffer (default ~0.35s)
3. Trim or extend the source clip to match the target (freeze-frame extend if narration > clip)
4. Concat variable-length clips
5. Generate captions with cumulative timings based on actual durations

**Per-beat tail-buffer overrides** for comedic-timing beats: punchline beats benefit from longer trailing dwell (e.g., 1.0–1.4s) so the visual lands after the line.

---

## 9. Kling 3.0 model name and request shape

Model: `kling-3.0/video` (text-to-video) — also `kling-3.0/motion-control` for motion-transfer.

Required request fields: `prompt`, `sound`, `duration`, `aspect_ratio`, `mode`, `multi_shots`, `multi_prompt`. Optional: `image_urls`, `kling_elements`, `callBackUrl`.

Allowed values:
- `mode`: `std`, `pro`, `4K` (NOT "standard")
- `duration`: string `'3'` through `'15'`
- `aspect_ratio`: `'1:1'`, `'9:16'`, `'16:9'`

Pricing (kie.ai, no audio):
- 720P (std): $0.07/sec
- 1080P (pro): $0.09/sec
- 4K: $0.335/sec

For mobile-shorts work, std/720p/no-audio is the sweet spot.
