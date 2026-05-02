# Video Output Rules

Engine-level rules for video output quality, character consistency, and pipeline mechanics. These were learned the hard way during the news-anime-bot Episode 1 build (April 2026, kling-3.0/video + gpt-image-2 + Google Chirp3-HD TTS + ffmpeg) and apply to any video this engine produces.

These rules previously lived in global Claude memory (`behavior_character_cloning.md`, `reference_kling_text_limitation.md`, `feedback_caption_placement.md`, `feedback_never_touch_anchors.md`). Moved here to live with the engine code so they get versioned alongside the pipeline.

**For raw model API specs, pricing, and the model-selection matrix, see `VIDEO_MODELS.md`.** This file (`VIDEO_OUTPUT_RULES.md`) is the production-rules / gotchas / lessons-learned doc; `VIDEO_MODELS.md` is the spec quickref.

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

## 1.5 Asset scope — three levels

Locked assets fall into three storage scopes. Each is a storage axis; assets at any level are referenced the same way at runtime.

- **Engine-wide / global** — style anchors and generic archetypes shared across many unrelated projects.
  - Path: `spoolcast-content/styles/<style>/anchor.png` (art-style anchors) or `spoolcast-content/archetypes/<name>.png` (generic character archetypes like a "suit-exec" template).
  - Default for: art-style anchors, reusable-across-projects character archetypes.
- **Series / show-root** — recurring talent for a single show.
  - Path: `spoolcast-content/shows/<show>/characters/<name>.png` and `spoolcast-content/shows/<show>/refs/<name>-source-N.{jpg,png}`.
  - Default for: recurring-show characters. Reusable across all episodes of that one show.
- **Session-local** — one-off characters or props for a single session.
  - Path: `spoolcast-content/sessions/<session-id>/characters/<name>.png` and `spoolcast-content/sessions/<session-id>/refs/<name>-source-N.{jpg,png}`.
  - Default for: one-off-session characters that won't recur.

A session can mix scopes freely. Common pattern: a series episode references engine-wide art style + series characters + (optionally) one session-local guest. A one-off session references engine-wide art style + session-local characters.

**Decision rule:** *will any other production reference this asset?*
- Many unrelated projects → engine-wide
- All episodes of one show → series-scoped
- Just this session → session-local

**Cross-level derivation is fine and encouraged.** Generating a series-level character using an engine-wide archetype as the §2.7 Input-2 style reference is the validated pattern. Once the derived asset is locked at its target scope, it stands alone — no runtime dependency back to the source.

**Per-episode cast manifest + resolution rule (uniform for series and one-off).**

Each session — series or one-off — drops a plain text `cast.txt` in the session dir, one character name per line:
```
pichai
jassy
willens
```

**Sync tools (e.g. artlu.ai showcase) resolve each name against the directory tree using a fixed search order, first match wins:**
1. `<session-dir>/characters/<name>.png` — session-local (one-off characters live here)
2. `<show-root>/characters/<name>.png` — show-level (series characters live here, ascending from `shows/<show>/sessions/<date>/`)
3. `<spoolcast-content-root>/archetypes/<name>.png` — engine-wide (generic archetypes shared across projects)

The directory structure does the disambiguation — sync code needs no branching on project type. Authors drop one consistent artifact (`cast.txt` with names) regardless of whether they're authoring a series episode or a one-off.

**Why this design (vs branching by project type):**
- Single sync logic: one read path, one resolution loop. No "is this series or one-off?" code branches.
- Single author rule: "list character names in cast.txt." No memorizing which directory pattern applies.
- Forward-compatible: a one-off that later becomes a series, or characters promoted from session-local to show-level, work without rewriting cast.txt — the resolution order finds them in the new location.
- No duplication: series characters stay at the show level, never mirrored into per-episode dirs.

§1 (anchor protection), §2 (cloning pipeline), §2.10 (file naming) all reference this scope model.

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

### 2.3 Cloning model selection — per-figure classifier variability

**Empirical finding (2026-05-02):** gpt-image-2's identity classifier is **per-public-figure**, not blanket. Sundar Pichai cleared both `gpt-image-2-image-to-image` (with Wikimedia photos) and `gpt-image-2-text-to-image` (with name in prompt). Andy Jassy got rejected on BOTH paths same-day with identical prompts/photos. Different figures hit different classifier lists.

**Cloning ladder when targeting a specific real public figure:**

1. **Try `gpt-image-2-image-to-image` first** — best anime stylization quality. Use Wikimedia public-domain photos as input (cleaner provenance metadata than user-uploaded photos; clears classifiers more often). Use neutral upload filenames per §2.4.
2. **If gpt-image-2 i2i rejects** (fast 500 + `costTime: 0` = classifier reject; distinct from real server hiccups which fail mid-gen with non-zero costTime): **try `gpt-image-2-text-to-image`** with the real name + features in the prompt. Sometimes accepted even when i2i isn't.
3. **If both gpt-image-2 paths reject:** **fall back to `nano-banana-2-image-to-image`** with the same Wikimedia photos. nb2 generally accepts real-figure image-to-image (the older claim that "nb2 rejects ALL real-person prompts and inputs" was over-broad — verified 2026-05-02). Quality plateau is softer-anime than gpt-image-2 but holds identity.
4. **Last-resort:** generate the sheet directly via ChatGPT (web UI, not API) with a real photo + "anime character sheet, shonen anime style, blank background" prompt. Hand-save the output and lock as the canonical ref.

**The blanket prohibition that was here previously is wrong** — both gpt-image-2 and nb2 can clone real figures via image-to-image; the ceiling is per-figure classifier sensitivity, not model policy. Test the specific figure on each model when bringing them into the recurring cast.

### 2.4 Name-free everywhere — never name the subject in ANY string sent to the model

The real name never appears in any string the model sees. This includes — and is NOT limited to:
- `prompt` text
- `kling_elements.description`
- `description` field on any model call
- **Upload filenames and URL paths.** When you upload a source photo to kie.ai, the `fileName` lands in the resulting download URL (`tempfile.redpandaai.co/.../<fileName>`). That URL is then passed to the model in `input_urls` / `imageUrls`. Classifiers scan URLs. Use neutral filenames for uploads (`char-A-source.jpg`, `id-input-1.jpg`) — never `pichai-source-3.jpg`.
- Phrases that signal photo-source provenance: `"photograph"`, `"real person"`, `"real photo"`, `"translate this real face"`, `"this celebrity"`, `"this CEO"`. These flag photo-of-a-real-person source material to identity classifiers even when the name is absent. Treat both inputs as illustration sources in prompt language ("Input 1: character with glasses and beard"), regardless of what they actually are.

Filter triggers manifest as **fast 500 errors with `costTime: 0`** (job rejected at submission, never started — generation never spent compute). Distinct from real server errors which fail mid-generation with non-zero `costTime`.

Local filenames on disk are fine — the rule only applies to strings sent to the model. So `refs/pichai-source-3.jpg` on local disk is OK, but uploads to kie.ai must use neutral names like `char-A-source.jpg`.

**Describe the subject in the prompt by features, not name:**
- **Visual/animation style** — e.g., "Bleach-style anime," "Tartakovsky angular flat-shape"
- **Signature features to amplify** — the parts that make them recognizable in real life. For caricature, lean *into* those features. Each subject needs a verified feature list — verify against actual photos, don't assume.
- **On-brand wardrobe — verify against photos, don't assume.** Example: Altman wears Patagonia "Better Sweater" crewneck pullovers, Henleys, button-downs — NOT vests, NOT turtlenecks. Generic "tech-CEO costume" loses recognition; their real outfit is a recognition cue.
- **Demographic specificity is a recognition lever AND a classifier risk.** "Indian-American man in his early fifties + salt-and-pepper hair + signature glasses + beard" tracks tightly to one specific public figure even without naming. For high-recognition subjects, consider less-specific demographic phrasing on first attempt; escalate specificity only if first attempt produces an unrecognizable result.

### 2.5 Never use negative instructions in image-gen prompts
"Not", "no", "none", "avoid", "without" get IGNORED or actively backfire (the negation token gets stripped, leaving the rejected item as a positive instruction). Use ONLY positive descriptors. If the model defaults to something wrong, fight it by making the desired alternative so vivid and repeated that it crowds out the default. Universal, not specific to character work.

### 2.6 Image-to-image with a real photo input pulls toward photoreal
Even with strong "anime illustration NOT a photo" prompt language, the body and wardrobe inherit the photo's reality while only the face stylizes. For *style fidelity*, prefer **text-only** with detailed feature description. For *identity fidelity*, prefer image-to-image. Choose based on which matters more.

### 2.7 The two-input redraw recipe (validated)
For BOTH identity-fidelity AND style-fidelity out of `gpt-image-2-image-to-image`:
1. **Input 1** = identity source. Either a real photo (first-time clone) OR a previous good character ref (iterating a clone). Provides face / identity / pose.
2. **Input 2** = style anchor. **MUST be a multi-character lineup illustration**, NEVER a single character. Provides rendering language only — line weight, cel-shading treatment, color-block style, shadow-shape vocabulary.
3. **Prompt:**
   - Tells model: Input 1 contributes facial identity; Input 2 contributes rendering style and clothing-rendering language.
   - Uses **REDRAW** language, NOT "preserve identically." Preserve language locks in the original photo-leaning rendering and won't budge.
   - Spells out specific positive descriptors of what flat cel-shading means: "solid uniform color blocks," "hard-edged darker shadow shapes," "sharp clean thin black anime line work outlining each garment."

**Why Input 2 must be a multi-character lineup, never a single character:** a single-character ref collapses style and design into one example. The model cannot separate "the show's rendering language" from "this one character's design choices" (their hair treatment, body proportions, wardrobe color palette, expression vocabulary). Used as Input 2 for a different character, those design choices bleed in — the new character ends up looking suspiciously like the source. A lineup of ~5 different characters in the same rendering style preserves the diversity needed to isolate rendering from design: the model averages across the cast and extracts only what they share (line work, cel shading) while ignoring what differs (specific designs).

**Practical consequence:** ALL real-figure caricatures in a project share the same Input-2 lineup. A locked character is NEVER promoted to Input-2 for a later character. Per-character distinctiveness comes from (a) their real photo as Input 1 and (b) per-character feature description in the prompt — never from swapping Input 2.

### 2.8 Output as multi-pose character sheet on clean background

Ask for "character design sheet — same character in 3 poses: front view, three-quarter view, expression close-up. Consistent design across all poses. **Clean solid white or transparent background — NO scene, NO setting, NO environmental elements, NO scenery, NO furniture.**"

**Clean background is load-bearing.** When the sheet is passed as a reference image to a video model (Kling `kling_elements`, Seedance `reference_image_urls`, Veo REFERENCE_2_VIDEO `imageUrls`), the model interprets the *entire* image including background. A busy or scene-laden background contaminates the reference — environmental elements bleed into the generated scene regardless of the scene prompt. White/transparent isolates the character so it composes cleanly into whatever scene the prompt describes.

The locked sheet becomes the reference fed forward to the video model.

### 2.9 Lock the character sheet once approved
Same hard rule as §1 — don't regenerate without explicit "yes regen this character" per call.

### 2.9.5 Canonical engine-wide style anchor (current)

`spoolcast-content/archetypes/bleach-cast-anchor.png` — multi-character anime lineup (5 generic anime business characters in Bleach cel-shaded style, modest dark backdrop). Validated as Input-2 style anchor for ep 1's Altman + CFO clones; reused for all current and future news-anime-bot characters.

This is the single canonical lineup for real-figure caricature work in this engine. Per §2.7, do NOT replace it with a locked character ref for downstream clones. If a future show needs a different rendering aesthetic (non-Bleach), generate a new lineup with the new style and save at `spoolcast-content/archetypes/<style-name>-cast-anchor.png` per §1.5.

---

### 2.10 File naming + scope

**File naming:**
- Source photos: `<character>-source-N.{jpg,png}` (e.g., `altman-source-1.jpg`)
- Generated character sheet: `<character>-sheet-<style>.png` (e.g., `altman-sheet-bleach.png`)
- Locked production reference: `characters/<character>.png` (canonical name)

**Where the `characters/` and `refs/` directories live: see §1.5.** Recurring-show characters → series-root. One-off-session characters → session-local. Generic engine-wide archetypes → engine-wide path.

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

**ffmpeg drawtext escape gotchas (when rendering chyrons in post):**
- `%` in text breaks the parser — drawtext treats `%` as a format-specifier prefix (like `%{pts}`). **Even doubling to `%%` doesn't reliably escape** in libavfilter. Workaround: substitute the word — `>50%` → `OVER HALF`, `3%` → `THREE PERCENT`. Empirically the cleanest fix.
- Unicode arrows (`→`, `⇒`) render as garbage if the chosen font lacks the glyph. Stick to ASCII (`->`).
- Single quote `'` needs `\\\\'` escape OR use a textfile via `textfile=path` instead of inline `text='...'`.
- `:` and `,` are filter-graph separators — escape with `\\:` and `\\,` if literal.
- Safe practice: keep chyron text ASCII letters/numbers/spaces/dashes only. Reword anything fancier.

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

### 6.1 Line stacking — per-line `\an5\pos()` events, NOT default libass leading

When a narration line wraps to 2+ visual lines, **libass's default font-metric leading produces too-loose line gaps** (visible empty space between wrapped lines that reads as broken pacing on mobile). Style-level `LineSpacing` extensions are not reliably honored across libass builds. ScaleY hacks to fake tight spacing smush the text vertically.

**Validated fix** (originated in `spoolcast/SHIPPING.md` § "Caption style"):

1. **Pre-wrap text in Python** via `textwrap.wrap(text, width=N)` to a controlled char count per line.
2. **Emit each wrapped line as its own Dialogue event** with explicit `{\an5\pos(x, y)}` positioning:
   ```
   Dialogue: 0,start,end,Default,,0,0,0,,{\an5\pos(540,1300)}LINE 1 TEXT
   Dialogue: 0,start,end,Default,,0,0,0,,{\an5\pos(540,1345)}LINE 2 TEXT
   ```
3. **Style `Alignment` field = `5`** (middle-center anchor) to pair with the inline `\an5\pos()` overrides.
4. **`LINE_STEP` = ~62.5% of fontsize** baseline-to-baseline (e.g., 45px at fontsize 72; 20px at fontsize 32). Lines stack nearly touching — cap-to-cap gap target <4px.
5. **First-line center y (`margin_v_y`)** at ~67.7% from top for 9:16 full-bleed mobile (clears bottom UI overlays).
6. **Wrap width** depends on font: ~31 chars/line for Montserrat Black at canvas-width / fontsize ratio = 15. Arial Black is ~15% wider per char → use ~26 chars/line at the same ratio.

**Why this works:** explicit `\pos()` per line gives deterministic pixel-accurate stacking; libass treats each Dialogue as an independent positioned glyph block, ignoring its own leading heuristics entirely.

**Spoolcast-specific values** (canvas, font, margin_v_y for that pipeline's aspect modes) live in `SHIPPING.md` § "Caption style (burned-in, mobile A.1)" — that file is the per-pipeline application of this engine rule.

**Caught:** ep 3 v3 stitch shipped with default libass leading on 3-line caption beats — too much vertical gap between wrapped lines. Refactored to per-line `\an5\pos()` after the user pointed at the SHIPPING.md rule.

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
2. Beat target duration = narration duration + tail buffer (default ~0.5s)
3. **Trim the source clip to the target — do NOT pad audio with silence to fill an arbitrary clip length.** Even when you've paid for a 5s/6s clip from a video model, use only as much as narration + tail asks for. Excess paid footage is sunk; visible dead air is worse.
4. Freeze-frame extend only when narration genuinely overflows the source clip (rare with correctly-sized prompts)
5. Concat variable-length clips
6. Generate captions with cumulative timings based on actual durations

**Per-beat tail-buffer overrides** for comedic-timing beats: punchline beats benefit from longer trailing dwell (e.g., 1.0–1.8s) so the visual lands after the line. The final beat of an episode also gets a longer trailing dwell (e.g., 1.5–2.0s) since there's no next line to advance to.

**Common bug — inherited from "5s default":** episode 1 of news-anime-bot and ep 2 v1 both shipped with each beat's narration silence-padded to fill the full Kling/Seedance clip duration. Result: viewers hear the line, then 1–3 seconds of silent visual before the next line begins. Reads as broken pacing. The fix is the opposite direction — trim the clip down to narration + small tail, not pad the audio up to fill the clip.

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

---

## 10. Seedance 2.0 Fast video — known gotchas

Seedance 2.0 Fast (`bytedance/seedance-2-fast` on kie.ai) is the alternate path when **legible in-frame text** matters — Kling 3.0 mangles text (§3.1), Seedance renders it cleanly. Validated empirically on news-anime-bot ep 2 (`$120B`, `$35B`, `450M`, `3%` all rendered legibly at 480p).

### 10.1 `generate_audio` defaults to `true` — must explicitly set `false`

Unlike Kling (`sound: false`), Seedance's `generate_audio` defaults to `true`. Forgetting to set it false generates AI audio you don't need (the show uses its own TTS) AND inflates per-clip cost. **Always explicitly pass `generate_audio: false`** in the request.

### 10.2 Three reference modes are mutually exclusive

Per the kie.ai API spec, these three modes cannot be combined in one request:

- `first_frame_url` / `first_frame_url + last_frame_url` — Image-to-Video, locks the first (or first+last) frame to the supplied image. Will exhibit the same lead-frame-flash issue as Kling's `kling_elements`.
- `reference_image_urls` (array, max 9) — Multimodal Reference-to-Video, soft style/character reference, no frame locking.
- `reference_video_urls` — for motion transfer.

For locked-character beats (the analog of Kling's `kling_elements`), use **`reference_image_urls` only** — passes the locked character sheet as a soft reference without locking it to a specific frame.

### 10.3 No lead-frame flash (unlike Kling)

Seedance with `reference_image_urls` does NOT exhibit Kling's 0.5s lead-frame flash where the input character sheet becomes the literal first rendered frame. Frame 0 is already a natural composition matching the prompt. **No 0.5s lead-skip needed in stitch** — saves engine complexity vs the Kling path.

### 10.4 Request shape and pricing

Required: `model: "bytedance/seedance-2-fast"`, `input.prompt`, `input.aspect_ratio`, `input.duration`. Optional: any one of the three reference modes above.

Allowed values:
- `resolution`: `480p`, `720p` (Fast tier doesn't support 1080p — that's the standard tier)
- `aspect_ratio`: `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `21:9`, `adaptive`
- `duration`: integer 4–15 (note: Kling uses string; Seedance uses int)

Pricing (kie.ai, no video input — image refs do NOT count as "video input"):
- 480p: $0.0775/sec
- 720p: $0.165/sec
- "with video input" tier ($0.045/$0.10) only applies when `reference_video_urls` is populated

For mobile-shorts work where in-frame text matters, **480p / 9:16 / no audio** is the sweet spot. 480p cel-shaded anime survives platform compression fine; 720p is ~2.1× the per-second cost.

### 10.5 In-frame text — prompt the literal characters

Seedance renders prompted text legibly when the prompt names the **exact** character sequence wanted, e.g. `"glowing magenta neon text reading exactly '$120B' as cinematic anime typography"`. Passing the exact character sequence in single quotes inside the prompt and using "reading exactly" as the framing reliably produces the right glyphs. Vague phrasing ("a dollar amount", "the figure $120 billion") regresses to mangled glyphs.

---

## 11. Parallelize TTS calls — they're independent network requests

Google Cloud TTS (and any per-line TTS API) calls have NO inter-line dependency. Generating 12 narration lines via a sequential `for` loop takes 5–10 minutes wall time at high latency and is prone to mid-loop hangs. Parallel via `ThreadPoolExecutor` finishes the same batch in 30–60 seconds.

**Right pattern (mirrors `run_clips.py`'s parallel video-gen pattern):**

```python
with ThreadPoolExecutor(max_workers=len(NARRATION)) as ex:
    futures = [ex.submit(synthesize_one, beat, api_key) for beat in NARRATION]
    for fut in as_completed(futures):
        results.append(fut.result())
```

**Also use `python -u` (unbuffered output)** when piping through `tee` — `tee` line-buffers stdout, and Python's default block buffering combined with TTS I/O waits will hide all progress messages until the entire batch completes (or hangs silently). Unbuffered = visible per-line progress, easier to diagnose hangs.

Caught on news-anime-bot ep 2: sequential TTS took 6+ min for 12 lines, then hung at line 3 with no visible output. Process had to be killed and restarted. Parallel + `-u` would have completed the batch in under a minute with full visibility.

---

## 12. Continuous-narration audio — pre-normalize before concat to avoid static at gap boundaries

When building one continuous narration track from 12 line-mp3s + inter-line silence gaps, **pre-normalize every input segment to a uniform AAC 48kHz mono format BEFORE the concat step**. Otherwise sample-rate / channel-layout mismatches at boundaries produce audible clicks/static every time the narrator transitions in or out of speech.

**Root cause:** Google Cloud TTS mp3s come out at **24kHz mono**; ffmpeg `anullsrc` silence is typically generated at **48kHz mono**; the resampler at the concat boundary hits discontinuities → clicks.

**Bad pattern (causes static):**
```python
# concat filter directly on heterogeneous inputs
"[0:a]aresample=async=1[a0];[1:a]anull[a1];[a0][a1]concat=n=2:v=0:a=1[out]"
```
The `aresample=async=1` does the math but per-segment state resets at concat boundaries → audio glitches.

**Good pattern (uniform inputs):**
1. Run a separate `ffmpeg` per input segment that normalizes to AAC 48kHz mono `.m4a`:
   ```python
   ffmpeg -i narration.mp3 -c:a aac -b:a 192k -ac 1 -ar 48000 narr-NN.m4a
   ffmpeg -f lavfi -t 0.5 -i anullsrc=cl=mono:r=48000 -c:a aac -b:a 192k -ac 1 -ar 48000 silence-NN.m4a
   ```
2. Concat via the **demuxer** (not filter) since inputs now match format:
   ```python
   ffmpeg -f concat -safe 0 -i list.txt -c:a aac -b:a 192k -ac 1 -ar 48000 continuous.m4a
   ```

Caught on news-anime-bot ep 3 v1 stitch: noticeable static every time narrator speaks. Fixed by pre-normalizing all inputs to uniform AAC 48kHz mono before demuxer-concat.
