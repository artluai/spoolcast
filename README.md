# Spoolcast

Turn chat, content, and ideas into short illustrated video.

Each narration chunk becomes one AI-generated scene in a per-session locked visual style. A deterministic preprocessor reveals each scene over time as a numbered PNG sequence. Remotion plays the sequences against narration audio. No overlays, no compositing, no renderer improvisation.

**First end-to-end pilot shipped 2026-04-20:** [https://youtu.be/hqbmHuEtayM](https://youtu.be/hqbmHuEtayM) — a 5-minute illustrated explainer on Meta's TRIBE brain-prediction AI, fully AI-generated (44 scenes, AI voice, OpenCV reveal animations, AI-written title/description/thumbnail) and rendered headless via Remotion.

This repository contains:
- reusable workflow rules
- shot-list and session-config schemas
- a Remotion scaffold
- preprocessor and generation script locations

This repository does not contain:
- a finished video
- session-specific media
- session-specific working files
- generated review artifacts or renders

Keep session-specific content in the separate content directory:
- `../spoolcast-content/`

## How It Works

1. Write a shot list with narration per beat.
2. Group adjacent beats into chunks.
3. Generate one illustration per chunk via the kie.ai provider, locked to a per-session style anchor.
4. Run the preprocessor — each scene PNG becomes a numbered frame folder showing the reveal.
5. Remotion plays the frame folders in chunk order, synced to narration audio.
6. Output is an MP4 in the session's `renders/` directory.

## Commands

Install dependencies:

```bash
npm install
```

Open Remotion Studio:

```bash
npm run dev
```

Bundle the project:

```bash
npm run build
```

Render the template composition:

```bash
npx remotion render spoolcast-template renders/spoolcast-template.mp4
```

Render a still for inspection:

```bash
npx remotion still spoolcast-template renders/frame.png --frame=0
```

## Project Shape

- `src/` — Remotion renderer scaffold
- `scripts/` — project-specific tooling (kie.ai client, scene generator, preprocessor)
- `rules.md` + `*_RULES.md` + `*_SPEC.md` — workflow specification
- `../spoolcast-content/` — session configs, shot lists, generated scenes, frame sequences, review boards, renders

## Working Rule

Keep shared repo docs path-agnostic when possible.

Use:
- relative paths
- generic folder names
- workflow descriptions

Avoid:
- hardcoded personal local machine paths unless a path is truly required to make something work

## Runtime

Node 22 is required. Node 24 has caused repeated Rspack / Remotion native-binding failures on development machines. See `RENDER_RULES.md`.

## Current State

The repo is a reusable scaffold:

- background-only illustrated-scene workflow defined across the rules files
- Remotion template composition only (no bundled session example)
- scripts directory ready for the kie.ai client and preprocessor

## Next Work

- implement the kie.ai client in `scripts/`
- implement the scene preprocessor in `scripts/` (Python, deterministic, no AI tokens)
- replace the template composition with a chunk-driven composition that plays preprocessor frame folders
- generate the first end-to-end illustrated session
