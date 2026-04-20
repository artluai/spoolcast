# spoolcast

Turn a script into a short illustrated video. Each narration sentence maps to one AI-generated scene, locked to a per-session visual style. A deterministic Python script paints the scene in stroke-by-stroke. Remotion renders everything headless into an mp4. No editor, no overlays, no renderer improvisation.

## What it produces

Watch an 8-minute example — [**I don't make videos. My AI pipeline does.**](https://artlu.ai/project/what-is-spoolcast) — fully rendered via this pipeline. ~$3 in generation costs, four Acts, 61 chunks, 14,686 frames.

Earlier 5-minute pilot: [https://youtu.be/hqbmHuEtayM](https://youtu.be/hqbmHuEtayM)

## Who it's for

People who build things and don't want marketing to be a second job. If you ship code, write posts, or run a side project and want explainer-style videos that match the cadence of your work (not a weekend of editing per video), this is the pipeline.

## Repo layout

```
spoolcast/                    # this repo — reusable pipeline
├── rules.md                  # index — read first
├── PIPELINE.md               # workflow, session config, shot-list schema, render
├── STORY.md                  # script extraction + pacing + viewer context
├── VISUALS.md                # asset generation + preprocessor + transitions
├── SHIPPING.md               # review + publish
├── DESIGN_NOTES.md           # why log — lessons learned, approaches killed
├── src/                      # Remotion composition
├── scripts/                  # pipeline scripts (generate, preprocess, render, audit, publish)
└── public/                   # Remotion static-file mount (symlinks to the active session)

../spoolcast-content/         # session content — kept in a separate directory
└── sessions/
    └── <session-id>/
        ├── session.json      # per-session config (style, budget, voice, rate)
        ├── shot-list/
        │   └── shot-list.json   # the editorial artifact — one row per sentence
        ├── source/
        │   ├── audio/        # TTS mp3s per beat
        │   ├── generated-assets/scenes/   # kie.ai-rendered PNGs per chunk
        │   ├── external-assets/           # logos, memes, broll stills
        │   └── box/          # optional drop folder for user-supplied files
        ├── working/          # drafts, source analysis, audit reports
        ├── frames/<chunk>/   # preprocessor-generated reveal frame sequences
        ├── manifests/        # scene generation manifests (provenance)
        └── renders/          # output mp4s
```

The repo and content dirs are **separate** so the pipeline is portable across projects. One clone of `spoolcast/` can drive many sessions.

## Prerequisites

- **Node 22** (not 24 — native-binding failures with Remotion)
- **Python 3.14+** (the venv at `scripts/.venv` handles dependencies)
- **ffmpeg** (for Remotion render — `brew install ffmpeg`)
- API keys (all loaded from `spoolcast/.env`):
  - **`KIE_API_KEY`** — kie.ai image generation (required)
  - **`GOOGLE_CLOUD_TTS_API_KEY`** — Google Cloud text-to-speech (required)
  - **`OPENROUTER_API_KEY`** — optional, for the Qwen narration auditor path (~$0.03/run)
  - **`ANTHROPIC_API_KEY`** — optional, for the Claude Haiku narration auditor path (~$0.25/run, cleaner output)
  - **`YOUTUBE_CLIENT_SECRETS_PATH`** — optional, path to Google OAuth client_secret.json if you want to auto-upload to YouTube

## Setup

```bash
# 1. Clone the pipeline and create the sibling content directory
git clone https://github.com/<you>/spoolcast.git
mkdir spoolcast-content
cd spoolcast

# 2. Python venv + dependencies
python3.14 -m venv scripts/.venv
scripts/.venv/bin/pip install -r scripts/requirements.txt

# 3. Node deps
npm install

# 4. Configure .env
cp .env.example .env   # if available, else create from scratch
# Add your API keys to .env

# 5. Read the rules (at minimum rules.md + PIPELINE.md + STORY.md)
```

## Real scenarios

Most people don't start with a blank shot-list. The actual entry points are usually **"I have a long Claude conversation about something I built"** or **"I want to explain this repo"**. Both work the same way: give your coding agent raw source material + point it at the spoolcast rule files, and let it do the editorial stages before you touch production.

### Scenario A: from a Claude Code / Cursor / chat session → video

You just spent hours with an AI agent building something. You want a video that explains what you built + the decisions that went into it.

```bash
# 1. Scaffold a new session
scripts/.venv/bin/python scripts/init_session.py --id my-project-explainer --activate

# 2. Drop your raw source material in source/
# For a Claude Code session, export the conversation:
#   - copy the full chat transcript to source/transcript.md
#   - grab any relevant commits: git log --patch > source/commits.txt
#   - drop screenshots, diagrams, mockups in source/box/

# 3. In your coding agent, point it at the rule files:
#    "read spoolcast/rules.md, STORY.md Part 1, and PIPELINE.md.
#     then read ../spoolcast-content/sessions/my-project-explainer/source/
#     and do a source analysis per STORY.md § 3 (Jobs A–E).
#     confirm the core message with me before writing anything."

# 4. The agent proposes 2–3 candidate core messages. You pick one (or rephrase).
#    From there, it drafts screenplay v1 (short version only — just the spine),
#    you confirm, it writes the full prose, iterates through v2 + v3 with the
#    viewer-orientation and concept-inventory gates from STORY.md.

# 5. The agent converts the final screenplay into shot-list.json
#    (one row per sentence the narrator says, grouped into chunks).

# 6. Run the narration auditor before production:
scripts/.venv/bin/python scripts/audit_narration.py \
    --session my-project-explainer --provider openrouter
# Fix any bridge/overweight flags the auditor surfaces.

# 7. Production (same as the mechanical walkthrough below) — generate images,
#    TTS, preprocess, render.
```

The editorial work (steps 3–5) is where the quality comes from, and it's what the rules in `STORY.md` Part 1 exist to guide. You're not asking the agent to summarize — you're asking it to **extract a story** from the session, with a declared core message, a specific turning point, and lines that can survive as independent narration beats.

### Scenario B: from a codebase → "what is this repo?" video

You have a repo (yours or someone else's) and want an explainer.

```bash
# 1. Scaffold a session
scripts/.venv/bin/python scripts/init_session.py --id repo-explainer --activate

# 2. Instead of a transcript, the source is the repo itself:
#    - cp the README to source/readme.md
#    - drop key source files / architecture diagrams in source/
#    - git log --oneline --stat > source/commits.txt  (the evolution story)
#    - any existing docs → source/

# 3. Point your coding agent at spoolcast rules + the source/ dir:
#    "read rules.md, STORY.md, PIPELINE.md. then read the source material in
#     ../spoolcast-content/sessions/repo-explainer/source/. do a source analysis.
#     find the practical question the repo answers. propose 2–3 candidate
#     core messages. don't write anything until I confirm one."

# 4. Same screenplay → shot-list → audit → production path as Scenario A.
```

**Meta-example:** the 8-minute video this repo ships with (*I don't make videos. My AI pipeline does.*) was itself produced this way — the "repo" was spoolcast itself, the core message was confirmed in chat, the screenplay iterated from the architecture and decisions documented in the rule files. See [`spoolcast-content/sessions/spoolcast-explainer/`](https://artlu.ai/project/ai-generated-video-what-is-spoolcast) for the actual working directory, or watch the build log at the same URL.

### How the rules collaborate with the agent

The key insight is that `STORY.md` and `PIPELINE.md` are written **for agent consumption**. Every rule is explicit, every anti-pattern is named, every archetype has examples. When you say "read STORY.md Part 1 then do a source analysis," the agent has a concrete procedure — not vibes.

Two specific hooks:
- **STORY.md § Review-Artifact Policy** — the agent only shows you two things: a short version in chat, and the final shot-list xlsx. Everything else (source-analysis.md, screenplay drafts) exists on disk for traceability but isn't handed to you for review. Saves you from reading prose drafts.
- **STORY.md § 3 Job E** — the core message MUST be confirmed with you in chat before any writing starts. The agent proposes 2–3 candidates; you pick one (or rephrase). This is the most load-bearing editorial decision in the whole pipeline.

---

## Mechanical walkthrough — if you want to skip the editorial stages

If you already have narration written (your own script, a blog post, a transcript you're using verbatim), you can go straight to production.

```bash
# 1. Scaffold a new session
scripts/.venv/bin/python scripts/init_session.py --id my-video-v1 --activate

# 2. Edit the shot-list — replace the example chunk with real narration
open ../spoolcast-content/sessions/my-video-v1/shot-list/shot-list.json
# Each chunk has one image and one or more beats (sentences).
# See PIPELINE.md § Shot-List Spec for all fields.

# 3. Generate illustrations (one per chunk) — costs ~$0.04 per image
scripts/.venv/bin/python scripts/generate_scene.py \
    --session my-video-v1 --chunk C1 \
    --narration "<your first beat narration>"
# ... repeat for each chunk

# 4. Generate TTS (one per beat) — free within Google Cloud monthly tier
scripts/.venv/bin/python scripts/tts_client.py \
    --text "<beat narration>" \
    --out ../spoolcast-content/sessions/my-video-v1/source/audio/01A.mp3 \
    --voice Puck

# 5. Preprocess reveal frames (one per chunk) — local, deterministic, free
scripts/.venv/bin/python scripts/stroke_reveal.py \
    --input ../spoolcast-content/sessions/my-video-v1/source/generated-assets/scenes/C1.png \
    --output ../spoolcast-content/sessions/my-video-v1/frames/C1/ \
    --fps 30 --duration 1.5 --strategy auto

# 6. Build the Remotion preview data
scripts/.venv/bin/python scripts/build_preview_data.py --session my-video-v1

# 7. Preview in Remotion Studio
npm run dev

# 8. Render
npx remotion render spoolcast-pilot \
    ../spoolcast-content/sessions/my-video-v1/renders/my-video-v1.mp4
```

## Quality gates

One optional but recommended pass before render:

**Narration audit** — LLM reviews every adjacent beat pair for missing bridges and every beat for overweight density.
```bash
scripts/.venv/bin/python scripts/audit_narration.py \
    --session my-video-v1 --provider openrouter   # or --provider anthropic
```

**Publish to YouTube** — once your video is rendered, upload + set thumbnail + description via one command.
```bash
scripts/.venv/bin/python scripts/publish_youtube.py \
    --video ../spoolcast-content/sessions/my-video-v1/renders/my-video-v1.mp4 \
    --title "..." \
    --description-file ../spoolcast-content/sessions/my-video-v1/working/youtube-description.txt \
    --thumbnail ../spoolcast-content/sessions/my-video-v1/source/generated-assets/thumbnail.png
```
First run opens a browser for Google OAuth consent; the refresh token is cached so subsequent runs are silent.

## The rule files

Six files describe the whole pipeline. Read them in order:

1. **[rules.md](rules.md)** — index + global agent rules (pre-pass, substance-before-form, no-offloading)
2. **[PIPELINE.md](PIPELINE.md)** — workflow stages, session.json schema, shot-list schema, render config
3. **[STORY.md](STORY.md)** — script extraction (Part 1) + pacing and viewer context (Part 2). This is where the editorial discipline lives: Acts, bumpers, bridge archetypes, reveal groups, overweight/underweight calibration.
4. **[VISUALS.md](VISUALS.md)** — kie.ai generation, style anchor, preprocessor, reveal-animation math, transitions
5. **[SHIPPING.md](SHIPPING.md)** — review contract, title/thumbnail rules (including the zero-prior-context and anti-self-hedge rules), description structure
6. **[DESIGN_NOTES.md](DESIGN_NOTES.md)** — why log. What we tried and killed, lessons learned. Read this before challenging any rule.

## Agents & LLMs

Any coding agent (Claude Code, Cursor, Windsurf, Codex) that walks into this repo should read `rules.md` first, then follow the per-file headers. The rules are written for agent consumption as much as human — explicit schema, explicit failure modes, explicit "do / don't" patterns.

The repo includes one LLM-driven quality-check script (`audit_narration.py`) that runs against the shot-list and reports pacing/density issues. All other scripts are deterministic.

## Troubleshooting

- **"ERROR: anthropic SDK not installed"** — run `scripts/.venv/bin/pip install anthropic`
- **"ERROR: ANTHROPIC_API_KEY not set"** — either add the key to `.env`, or use `--provider openrouter` with `OPENROUTER_API_KEY`
- **Remotion fails with native-binding errors** — verify `node --version` prints `v22.x`. Node 24 has Rspack/Remotion native-binding regressions.
- **Kie.ai returns 403 on image download** — Kie's CDN blocks default Python-urllib User-Agent. `generate_scene.py` and `generate_thumbnail.py` both set a browser UA; if you wrote custom code, include `User-Agent: Mozilla/5.0 ...` on the download request.
- **Composition.tsx shows "cannot find module preview-data.json"** — run `scripts/build_preview_data.py` first. The file is auto-generated and gitignored.

## Current state

Shipped: V1 pilot (Meta TRIBE explainer, 5 min) and V2 (*I don't make videos. My AI pipeline does.*, 8 min).

The pipeline is in active use — see [DESIGN_NOTES.md](DESIGN_NOTES.md) for the rolling log of what we've learned and killed.

## Contributing

This started as a personal pipeline, open-sourced so others can run it. If you use it, a link back is appreciated but not required. Issues and PRs welcome — especially rule-file clarifications and new narration auditor checks.
