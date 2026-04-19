# Session To Video

Workflow and Remotion scaffold for turning real build sessions into reviewable videos.

This repository contains:
- reusable workflow rules
- shot-list schema documentation
- a generic Remotion template composition

This repository does not contain:
- a finished video
- session-specific media
- session-specific working files
- generated review artifacts or renders

Keep session-specific content in the separate content directory, for example:
- `../spoolcast-content/`

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

- `src/` = Remotion renderer scaffold
- `scripts/` = placeholder location for project-specific tooling
- `rules.md` + `*_RULES.md` = workflow specification
- `../spoolcast-content/` = source material, planning docs, generated media, review boards, and renders

## Working Rule

Keep shared repo docs path-agnostic when possible.

Use:
- relative paths
- generic folder names
- workflow descriptions

Avoid:
- hardcoded personal local machine paths unless a path is truly required to make something work

## Current State

The repo is a reusable system scaffold:

- background-only shot-list workflow
- review board and render behavior defined by rules files
- template composition only
- no bundled session-specific example project

## Next Work

- add a clean generic shot-list parser
- add project-specific tooling only through configurable scripts
- keep session data outside the repo
- evolve the renderer from the template into a configurable pipeline
