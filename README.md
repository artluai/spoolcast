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

## Your first video

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

Two optional but recommended passes before render:

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
