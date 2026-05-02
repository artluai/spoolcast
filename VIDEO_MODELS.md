# Video Models — Reference

Quick reference for video-generation models the engine can target. Pricing and base URLs are **provider-specific** (currently kie.ai); the model APIs themselves are mostly stable upstream.

For production lessons, gotchas, and rules learned the hard way, see `VIDEO_OUTPUT_RULES.md`. This file is the spec quickref — read both.

---

## Provider abstraction

Schema field names (`first_frame_url`, `imageUrls`, `aspect_ratio`, etc.) are **model-side** — they come from the upstream provider (ByteDance, Kuaishou, Google) and stay the same regardless of which API gateway we hit.

What changes per provider:
- Base URL
- Auth header format / API key
- Pricing
- Endpoint paths (e.g., kie.ai uses `/api/v1/jobs/createTask` for most models, `/api/v1/veo/generate` for Veo)

If we switch from kie.ai (to fal.ai, replicate, direct upstream APIs, etc.):
- Re-fetch pricing for the new provider
- Update base URL + auth in run_clips.py
- Schema params should mostly carry over

---

## Pricing comparison

All numbers normalized to a **5-second clip** for fair comparison across per-second and per-clip pricing.

Provider: **kie.ai**. Last verified: 2026-05-02.

| Model | Tier | Resolution | Pricing model | 5s clip cost | Notes |
|---|---|---|---|---|---|
| Kling 3.0 | std | 720p | $0.07/sec | **$0.35** | text-to-video, mode `std` |
| Kling 3.0 | pro | 1080p | $0.09/sec | $0.45 | mode `pro` |
| Kling 3.0 | 4K | 4K | $0.335/sec | $1.68 | mode `4K` |
| Seedance 2.0 Fast | — | 480p | $0.0775/sec | **$0.39** | what ep 2 used |
| Seedance 2.0 Fast | — | 720p | $0.165/sec | $0.83 | ~2.1× cost vs 480p |
| Seedance 2.0 | — | 480p | TBD | TBD | not yet validated |
| Seedance 2.0 | — | 720p | TBD | TBD | — |
| Seedance 2.0 | — | 1080p | TBD | TBD | only on full 2.0, not Fast |
| Veo 3.1 Lite | — | 720p | $0.15/clip | **$0.15** | cheapest video option |
| Veo 3.1 Lite | — | 1080p | $0.175/clip | $0.175 | — |
| Veo 3.1 Lite | — | 4K | $0.75/clip | $0.75 | — |
| Veo 3.1 Fast | — | 720p | $0.30/clip | **$0.30** | mid-tier, REFERENCE_2_VIDEO mode supported |
| Veo 3.1 Fast | — | 1080p | $0.325/clip | $0.325 | — |
| Veo 3.1 Fast | — | 4K | $0.90/clip | $0.90 | — |
| Veo 3.1 Quality | — | 720p | $1.25/clip | $1.25 | top-tier |
| Veo 3.1 Quality | — | 1080p | $1.275/clip | $1.275 | — |
| Veo 3.1 Quality | — | 4K | $1.85/clip | $1.85 | — |

**Veo prices are flat per clip** (max 8s per clip). Kling and Seedance are per-second. For our typical 4–6s beats, Veo's flat structure can win on cost.

**Image-to-video pricing on Veo matches text-to-video at all tiers.**

---

## Model selection matrix

Pick model based on the **episode profile**, not per-beat (style drift is bad — see rules.md §9).

| Episode profile | Recommended | Why |
|---|---|---|
| Heavy characters, low in-frame text | Kling 3.0 std | `kling_elements` is most battle-tested for multi-character scenes |
| Light characters, heavy in-frame text | Seedance 2.0 Fast 480p | renders prompted text legibly (§10.5 of `VIDEO_OUTPUT_RULES.md`) |
| Heavy characters AND heavy text | Kling 3.0 std + ffmpeg drawtext post-overlay for text | pushes text out of model prompts entirely |
| Cost-sensitive daily output, mid quality OK | Veo 3.1 Fast 720p (REFERENCE_2_VIDEO) | cheapest with char-refs + 720p + native 9:16 |
| Top quality matters (one-off, longer-form) | Veo 3.1 Quality 1080p | best fidelity, cost prohibitive for daily |
| Ultra-cheap, lowest priority | Veo 3.1 Lite 720p | $0.15/clip; quality risk on a daily-shipping show |

**Always burn one test clip before committing all 12** when swapping models. ~$0.30 of insurance.

---

## Model API quickrefs

### Kling 3.0

- **Model string:** `kling-3.0/video` (text-to-video) | `kling-3.0/motion-control` (motion transfer)
- **Provider:** kie.ai
- **Endpoint:** `POST https://api.kie.ai/api/v1/jobs/createTask`
- **Required:** `prompt`, `sound`, `duration`, `aspect_ratio`, `mode`, `multi_shots`, `multi_prompt`
- **Optional:** `image_urls`, `kling_elements`, `callBackUrl`
- **Allowed values:**
  - `mode`: `std`, `pro`, `4K` (NOT `standard`)
  - `duration`: string `'3'` through `'15'` (note: STRING, not int)
  - `aspect_ratio`: `'1:1'`, `'9:16'`, `'16:9'`
- **Character refs:** `kling_elements` (array of element objects with `element_input_urls` + `description`). Requires **2–4 input images per element** (single-image returns 422). When prompt has `@role` references, `image_urls` field must also be populated (first ref's URL works).
- **Gotchas:** in-frame text mangles (§3.1 of `VIDEO_OUTPUT_RULES.md`); `kling_elements` causes 0.5s lead-frame flash (§3.2 — stitch must skip first 0.5s of each char beat)
- **Pricing:** see chart above

---

### Seedance 2.0 / Seedance 2.0 Fast

- **Model string:** `bytedance/seedance-2-fast` | `bytedance/seedance-2`
- **Provider:** kie.ai
- **Endpoint:** `POST https://api.kie.ai/api/v1/jobs/createTask`
- **Required:** `model`, `input.prompt` (3–20000 chars), `input.aspect_ratio`, `input.duration`
- **Optional:** `callBackUrl`, `input.first_frame_url`, `input.last_frame_url`, `input.reference_image_urls`, `input.reference_video_urls`, `input.reference_audio_urls`, `input.generate_audio`, `input.resolution`, `input.web_search`, `input.nsfw_checker`
- **Allowed values:**
  - `resolution`: Fast = `480p` | `720p`. Full 2.0 = `480p` | `720p` | `1080p`
  - `aspect_ratio`: `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `21:9`, `adaptive`
  - `duration`: integer 4–15 (note: INT, not string — different from Kling)
  - `generate_audio`: boolean, **defaults to `true` — must explicitly set `false`** to avoid extra cost
- **Three mutually exclusive reference modes** (cannot combine in one request):
  1. `first_frame_url` (+ optional `last_frame_url`) — Image-to-Video, locks first/last frame
  2. `reference_image_urls` (array, max 9) — Multimodal Reference, **soft style/character ref, no frame-lock, no lead-frame flash** ← preferred for char beats
  3. `reference_video_urls` — motion transfer
- **Character refs:** use `reference_image_urls` for character continuity (validated by ep 2, no special stitch handling needed). Supports up to 9 refs per beat — multi-character beats work natively.
- **Image constraints (any ref field):** jpeg/png/webp/bmp/tiff/gif, aspect 0.4–2.5, 300–6000px, ≤30MB
- **Gotchas:** `generate_audio` default-true (§10.1 of `VIDEO_OUTPUT_RULES.md`); for in-frame text, prompt the literal characters in single quotes with "reading exactly" framing (§10.5)
- **Pricing:** see chart. **No video-input tier** unless `reference_video_urls` is populated; image refs do not trigger the higher tier.

---

### Veo 3.1

- **Model strings:** `veo3` (Quality) | `veo3_fast` (Fast) | `veo3_lite` (Lite)
- **Provider:** kie.ai
- **Endpoint:** `POST https://api.kie.ai/api/v1/veo/generate` (note: separate path from Seedance/Kling)
- **Status endpoint:** `GET https://api.kie.ai/api/v1/veo/record-info?taskId=<id>` (also separate)
- **1080P upgrade endpoint** (16:9 only): `GET https://api.kie.ai/api/v1/veo/get-1080p-video?taskId=<id>`
- **Required:** `prompt`
- **Optional:** `imageUrls` (array, 1–3 depending on mode), `model`, `generationType`, `aspect_ratio`, `callBackUrl`, `enableTranslation`, `watermark`, `resolution`
- **Allowed values:**
  - `model`: `veo3`, `veo3_fast`, `veo3_lite`
  - `generationType`: `TEXT_2_VIDEO`, `FIRST_AND_LAST_FRAMES_2_VIDEO`, `REFERENCE_2_VIDEO`
  - `aspect_ratio`: `16:9`, `9:16`, `Auto`
  - `resolution`: `720p`, `1080p`, `4k`
- **Three generation modes:**
  1. `TEXT_2_VIDEO` — text only, no image input
  2. `FIRST_AND_LAST_FRAMES_2_VIDEO` — 1 image (animate from it) or 2 images (transition from first to last). Supports all 3 model tiers.
  3. `REFERENCE_2_VIDEO` — 1–3 reference images (style/character). **Fast tier only.** Supports 16:9 and 9:16.
- **Character refs:** use `REFERENCE_2_VIDEO` mode with up to 3 images in `imageUrls`. Fast model only — Quality and Lite cannot do reference-based character work.
- **Hard limits:**
  - Max clip length: **8 seconds** per clip (anything longer = external concat)
  - **English prompts only** — `enableTranslation: true` (default) auto-translates other languages
  - Always ships with audio by default (no `generate_audio: false` toggle exists)
  - All videos default include audio; in rare sensitive scenes upstream may suppress it
- **Pricing:** see chart. **Flat per clip** regardless of clip duration (different from Kling/Seedance).
- **Status flags (`successFlag`):** `0` generating | `1` success | `2` failed | `3` upstream generation failed
- **Gotchas:** content review is strict — content-policy flags return `code: 400`; minor uploads, prominent-people uploads, and unsafe images are auto-rejected. Veo 3.1's appetite for real-figure caricatures is unknown — **test before committing on a real-figure-heavy episode**.

---

## Shared kie.ai endpoints

### Submit a job (Kling, Seedance)
```
POST https://api.kie.ai/api/v1/jobs/createTask
Authorization: Bearer $KIE_API_KEY
Content-Type: application/json
```

### Poll a job (Kling, Seedance)
```
GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<id>
Authorization: Bearer $KIE_API_KEY
```
Response contains `data.state` (`success` / `fail` / in-progress states) and on success `data.resultJson` containing `resultUrls` (parse as JSON, then read array).

### Veo job submission
```
POST https://api.kie.ai/api/v1/veo/generate
GET  https://api.kie.ai/api/v1/veo/record-info?taskId=<id>
GET  https://api.kie.ai/api/v1/veo/get-1080p-video?taskId=<id>   # 1080P upgrade for 16:9
```

### File upload (for character refs / first-frame images)
```
POST https://kieai.redpandaai.co/api/file-stream-upload
Authorization: Bearer $KIE_API_KEY
Content-Type: multipart/form-data
Form fields: file (binary), uploadPath (e.g., "images/news-anime-bot"), fileName
Response: data.downloadUrl
```
Files expire in **3 days**. Re-upload before each batch run.

### Common error codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 401 | Auth missing/invalid |
| 402 | Insufficient credits |
| 404 | Resource not found |
| 422 | Validation error (or fallback failure for Veo) |
| 429 | Rate limited |
| 433 | Sub-key usage exceeded (Kling/Seedance only) |
| 451 | Image fetch failed (Veo only) |
| 455 | Service unavailable (maintenance) |
| 500 | Server error |
| 501 | Generation failed |
| 505 | Feature disabled |

---

## Image generation models

The pipeline also uses image-gen models for character archetypes, keyframes, and style anchors. Pricing is per-image (no per-second analog).

### gpt-image-2

- **Model strings:** `gpt-image-2-text-to-image` (no input image) | `gpt-image-2-image-to-image` (1–16 input images)
- **Provider:** kie.ai (OpenAI upstream)
- **Endpoint:** `POST https://api.kie.ai/api/v1/jobs/createTask` (same submit + poll pattern as Kling/Seedance)
- **Required:** `model`, `input.prompt` (1–20000 chars). For image-to-image: also `input.input_urls` (array of public URLs or `asset://` refs).
- **Optional:** `callBackUrl`, `input.aspect_ratio`, `input.resolution`
- **Allowed values:**
  - `aspect_ratio`: `auto`, `1:1`, `9:16`, `16:9`, `4:3`, `3:4` (default: `auto`)
  - `resolution`: `1K`, `2K`, `4K`. **Note: `auto` aspect_ratio + no resolution → forces 1K.** `1:1` aspect cannot be 4K.
- **Constraint:** `input_urls` array max 16 images for image-to-image.
- **Pricing (kie.ai, last verified 2026-05-02):**

| Tier | Per image | Use case |
|---|---|---|
| 1K | **$0.03** | internal style anchors, throwaway tests |
| 2K | **$0.05** | **default for locked production assets** (character refs, keyframes) |
| 4K | $0.08 | overkill for video pipeline (downstream models read at 480p–720p) |

- **Pricing applies to BOTH text-to-image and image-to-image** at the same per-resolution rate.
- **No `nsfw_checker` field** on this spec (older scripts may pass it; gets ignored).
- **Gotchas / production rules:** see `VIDEO_OUTPUT_RULES.md` §2 for the full character-cloning recipe (name-free prompts §2.4, no negatives §2.5, two-input redraw §2.7, multi-pose sheet on clean BG §2.8).

### nano-banana-2

- **Model string:** `nano-banana-2`
- **Provider:** kie.ai (Google upstream)
- **DO NOT USE for real-figure caricatures.** Per `VIDEO_OUTPUT_RULES.md` §2.3: Google's strict identity policy rejects ALL real-person prompts and inputs. Confirmed empirically.
- **Pricing (kie.ai, last verified 2026-05-02):**

| Tier | Per image | Notes |
|---|---|---|
| 1K | $0.04 | |
| 2K | $0.06 | ~20% more than gpt-image-2 2K |
| 4K | $0.09 | |

- Use for: non-real-figure work (generic archetypes, environments, props) where its style might beat gpt-image-2's. For real-figure caricatures, gpt-image-2 is the only option.

### seedream 5.0 Lite

- **Model strings:** `seedream/5-lite-text-to-image`, `seedream/5-lite-image-to-image`
- **Provider:** kie.ai (ByteDance upstream)
- **Pricing (kie.ai, last verified 2026-05-02):** **$0.0275 per image** flat, both modalities. **Cheapest image-gen on kie.ai** (~9% cheaper than gpt-image-2 1K, ~31% cheaper than nano-banana-2 1K).
- Resolution tiering not visible in pricing list — assume single tier.
- **Identity policy:** unknown. Not yet tested with real-figure photos in this pipeline. If you want a cheaper path than gpt-image-2 for non-real-figure work (engine-wide style anchors, generic archetypes, environments), seedream is the cheapest candidate. Test once before adopting.

### wan 2.7 image

Listed on kie.ai per memory, not yet validated. Add specs when first used.

---

## Last verified

| Source | Date | Notes |
|---|---|---|
| Kling 3.0 spec + pricing | 2026-04 | from `VIDEO_OUTPUT_RULES.md` §3 + §9; not re-fetched against kie.ai/pricing |
| Seedance 2.0 + Fast OpenAPI | 2026-05-02 | full spec pasted, both variants |
| Veo 3.1 docs + pricing | 2026-05-02 | quickstart docs + pricing list pasted |
| kie.ai endpoints | 2026-04-30 | last seen working in news-anime-bot ep 2 production run |

When pricing or fields change, update the relevant section + bump its row in this table. Don't silently re-quote stale numbers.
