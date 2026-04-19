# Design Notes

Why the rules are the way they are. What was tried and abandoned. Constraints discovered in real builds.

This file is not a rule file. It is context for agents and humans who need to understand *why* the rules look the way they do, and what failure modes the current design is protecting against.

Rules tell you what to do. Design notes tell you why. If you're thinking about changing a rule, read the relevant design note first.

## When To Update This File

Update DESIGN_NOTES when:

- A rule is being challenged or reconsidered — document the challenge and the decision, even if the decision is "keep it."
- A feature or approach is tried and abandoned — record what failed, how we knew it failed, and what replaced it.
- A major design decision lands — capture the reasoning so future agents don't undo it.
- A rule changes — move the old rationale to a "History" block, write the new one.
- A post-build retrospective exposes a gap in the rules — capture the learning here first, then update rules if needed.
- A new external constraint shows up (API pricing change, provider behavior shift, tooling break) — record it so we don't silently forget why we chose what we chose.
- A question or real use of the rules exposes a gap — if someone asks "don't we already have X?" and the rules can't answer that, that's a missing piece. Capture the gap here, then update the rules.
- A rule is being worked around instead of followed — either the rule is wrong or the practice is wrong. Analyze which before deciding what to change.

Do **not** update DESIGN_NOTES for:

- Minor rule wording changes.
- Style preferences.
- Speculation about things that haven't been tried yet.
- "What if we wanted to do X" hypotheticals.

The test: *if someone read the rules without this file and would be tempted to undo a good decision, this file is missing context.*

## Current Design Decisions And Their Reasons

### One visual layer per frame (no overlays, no compositing)

Rule source: `WORKFLOW_RULES.md`, `RENDER_RULES.md`.

Reason: Remotion cannot reliably place, size, or time floating foreground elements. Every attempt to put "a small thing on top of a background" produced drift — wrong position, wrong size, wrong timing, ugly transitions. The renderer improvises, and its improvisations are bad. We removed the entire second-layer concept to close that failure mode.

If you are tempted to add back a foreground layer: don't. Change the background instead, or generate a new full-frame illustration that has the emphasis built in.

### AI-illustrated scenes as the primary visual source

Rule source: `ASSET_RULES.md` (Primary Visual Pipeline).

Reason: We tried stock-footage-per-beat first (see killed approaches below). It was brittle, drift-prone, and required AI to judge visual fit — which AI can't do reliably. Switching to per-chunk AI-generated illustrations in a locked style removed two failure modes at once: no more stock-matching judgment, no more per-beat sourcing logistics.

If you are tempted to go back to stock-per-beat as the default: read the "Killed: stock footage per beat" note below first.

### Script is the atomic driver, not the shot-list row

Rule source: `SHOT_LIST_SPEC.md` (Chunk field), `WORKFLOW_RULES.md`.

Reason: Real-world narration flows don't map cleanly to per-row images. One image often needs to cover several beats. Forcing one image per row produced redundant illustrations and broke narrative pacing. Chunks let the narration shape the visual rhythm instead of the spreadsheet structure.

### Preprocessor owns reveal animation, not Remotion

Rule source: `PREPROCESSOR_RULES.md`, `RENDER_RULES.md`.

Reason: Remotion improvises when asked to animate. A deterministic script producing numbered PNG frames removes all improvisation from the reveal. Frame N is always the same frame. Same image in, same frames out. The renderer just plays them.

This also means: no AI tokens are spent on animation. The preprocessor is dumb, deterministic, local.

### Node 22 for Remotion

Rule source: `RENDER_RULES.md` (Runtime Requirements).

Reason: Node 24 caused repeated Rspack / Remotion native-binding failures on development machines (`ERR_DLOPEN_FAILED`, code-signature load failures). Node 22 was the first fallback that worked across projects. Treat as a cross-project runtime compatibility issue, not a one-off repo quirk.

### Google Cloud TTS (Chirp3-HD) over ElevenLabs

Rule source: not yet in rules. Belongs in a session config default.

Reason: ElevenLabs at daily-video pace is $99-330/month (Pro or Scale tier). Google Cloud Chirp3-HD has a 1M chars/month free tier that comfortably covers ~20 minutes of narration per day. Quality on Chirp3-HD is genuinely close to ElevenLabs for narrator-over-illustrations work. The provider is wrapped in a swap-friendly client so OpenAI TTS or CosyVoice can replace it with a small code change if the free tier ever stops fitting.

### Kie.ai as the image provider

Rule source: `ASSET_RULES.md` (Kie Provider Spec).

Reason: Already set up, working, supports all the models we want to try (nano-banana-2, nano-banana-pro, seedream, wan). No reason to switch providers mid-build. If Kie changes pricing or model availability unfavorably, revisit.

### Script extraction (source-to-script stage) is externally owned

Rule source: `WORKFLOW_RULES.md` (Stage 1: Source-to-Script). When `SCRIPT_EXTRACTION_RULES.md` is written, that becomes the primary reference.

Reason: Turning a raw session package into a screenplay, scene plan, and shot list is an editorially-driven stage, not a mechanical one. It requires judgment about story arc, turning points, what to cut and keep, where humor lands without becoming gimmicky, and how dense to make the narration.

An earlier pass (Codex executing the brief in `spoolcast-content/shared/video-generation-skill-spec.md`) produced high-quality output because of that judgment, not because the process was rigorous. The brief exists; the "how" does not.

Decision: this stage is owned by a capable agent with the full session package in context — typically Codex or Claude in a dedicated session with the raw transcript and logs loaded. The spoolcast repo provides the brief and the output contract, not the code. A more detailed `SCRIPT_EXTRACTION_RULES.md` will be written by the agent who actually ran the stage, as a self-documentation pass.

If you are tempted to "automate" script extraction with a general-purpose LLM loop: don't, yet. Mechanized script-writing is how spoolcast becomes AI slop. The quality bar is "feel like following real work" — that comes from judgment on the raw material, not from a pipeline.

### Rule files live in the repo; session content lives in the content dir

Rule source: `WORKFLOW_RULES.md` (Canonical Directory Contract).

Reason: The repo is the reusable scaffold. Session-specific content (media, data, scripts, working files) doesn't belong in the repo — it bloats history and conflates "the workflow" with "one specific video." The split lets the repo stay small, public-friendly, and reusable across sessions.

## What We Tried And Killed

### Killed: foreground overlays (cutouts on top of backgrounds)

Tried in tribe-session-001. Approximately 15 beats had generated foreground elements meant to float over backgrounds. Every overlay needed manual fixup — drift in placement, wrong sizing, half-broken AI-generated transparency. The renderer couldn't improvise positioning reliably. Abandoned in favor of illustrated full-frame scenes.

What would make this reconsider-able: a real breakthrough in how Remotion handles per-beat positional data AND a reliable way to judge AI-generated transparency. Neither condition is met.

### Killed: AI-judged stock footage selection

Tried: prompt an AI to pick matching stock videos or images per beat. Failure mode: AI couldn't judge visual fit, transparency, or quality. It kept choosing bad matches with confident-sounding rationale. Abandoned.

This is why `ASSET_RULES.md` lists stock sourcing as an "alternate mode" rather than "primary with AI picker."

### Killed: stock footage per beat as the default

Tried first, as the original tribe-session-001 workflow. Brittle in multiple ways:
- sourcing logistics were heavy (per beat, sometimes per retry)
- stale generated files drifted from the shot list constantly
- the "Remotion can't place overlays" problem showed up here too
- the visual result felt like stock-cut-and-paste, not a told story

Abandoned as the default. Kept as an optional alternate mode for sessions that genuinely need real footage (e.g. real screenshots from the source session).

### Killed: ElevenLabs as the TTS provider

Initial TTS provider (wired up by codex). At daily-video pace, ElevenLabs requires the Scale tier (~$330/month). Not worth it when Google Cloud TTS Chirp3-HD hits the same quality for $0 at our volume. ElevenLabs-specific env vars (`ELEVENLABS_*`) are safe to remove from `.env` — they're dead config.

### Killed: tribe-specific baked into the repo

Original setup had tribe-specific media, data, and scripts in the repo. Made the repo heavy, single-use, and confusing for anyone trying to understand "what is this system." Separated into repo (scaffold) + content dir (session-specific) to fix this. Old assets kept in `spoolcast-content/sessions/tribe-session-001/` for reference, not for pipeline use.

## Lessons Learned

- Remotion is not good at improvising layout, placement, or timing. Keep it as a dumb playback engine.
- AI image models can't reliably judge whether a sourced image works for a given beat. Don't rely on AI curation of assets.
- Stale generated files are a major failure mode. Regeneration must be explicit, not silent.
- Script and narration are more reliable atomic units than shot-list rows for image generation.
- Fragile visual systems should be simplified, not preserved.
- Provider choice matters at daily-video pace. A tier that "works for one video" can be 50x too expensive at 30 videos.
- When a complex system has drift across layers (shot list / review / preview / render), the fix is usually fewer layers, not better sync.
- Rule files written from a long working session always have gaps. The gaps surface when the rules are used or questioned — treat "don't we already have a system for X?" as a trigger to update, not as pushback. The questioner is usually right.
- Editorial stages (story, voice, pacing, humor) are hard to mechanize without making everything feel generic. Leave them to agents with full context and judgment. Mechanize the downstream plumbing (images, preprocessor, render) where determinism helps quality.
