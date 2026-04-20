"""
init_session.py — scaffold a new spoolcast session.

Creates the full content-side directory structure for a new session under
`../spoolcast-content/sessions/<session-id>/` with a minimal valid
`session.json`, an empty `shot-list.json`, and all the subdirectories the
pipeline expects (source/, working/, renders/, frames/, manifests/).

Optionally re-points the Remotion `public/` symlinks (frames + source) at
the new session so `npm run dev` and renders pick it up immediately.

Usage:
    scripts/.venv/bin/python scripts/init_session.py --id my-video-v1
    scripts/.venv/bin/python scripts/init_session.py --id my-video-v1 --activate
    scripts/.venv/bin/python scripts/init_session.py --id my-video-v1 \\
        --style "loose hand-drawn ink sketches, flat earth tones" \\
        --ai-budget 60 \\
        --model nano-banana-2
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
PUBLIC_DIR = REPO_ROOT / "public"


def make_session_json(
    session_id: str, ai_budget: int, model: str, style: str | None
) -> dict[str, object]:
    cfg: dict[str, object] = {
        "session_id": session_id,
        "ai_budget": ai_budget,
        "preferred_model": model,
        "reveal_style": "paint",
        "reveal_duration_seconds": 1.5,
        "scene_fps": 30,
        "resolution": "1K",
        "aspect_ratio": "16:9",
        "output_format": "png",
        "tts_voice": "Puck",
        "tts_playback_rate": 1.1,
        "notes": f"session created {_dt.datetime.now().strftime('%Y-%m-%d')}",
    }
    if style:
        cfg["style_reference"] = style
    else:
        cfg["default_style_prompt"] = (
            "loose hand-drawn black ink line art on white background, "
            "simple stick-figure characters, basic flat fill colors, "
            "no shading, no gradients. notebook-doodle vibe."
        )
    return cfg


def make_shot_list_json(session_id: str) -> dict[str, object]:
    """Produce a minimal valid shot-list.json with one example chunk.

    The example chunk is intentionally obvious placeholder content so the
    author sees the schema in action and can edit or delete it."""
    return {
        "session_id": session_id,
        "canvas": {"aspect_ratio": "16:9", "fps": 30},
        "notes": (
            "draft shot-list — replace the example chunk below with real "
            "narration. Each chunk = one illustration; chunk.beats = one row "
            "per sentence the narrator will say."
        ),
        "chunks": [
            {
                "id": "C1",
                "scene": "01",
                "scene_title": "Cold Open",
                "summary": "example chunk — replace this",
                "continuity": "standalone",
                "image_source": "generated",
                "boundary_kind": "continues-thread",
                "weight": "normal",
                "beats": [
                    {
                        "id": "01A",
                        "narration": "Replace this sentence with your first line of narration.",
                        "pause_after": "short",
                    }
                ],
                "beat_description": "Describe what this scene illustration should show.",
                "image_path": "source/generated-assets/scenes/C1.png",
                "reveal_type": "paint-auto",
            }
        ],
    }


def scaffold_session(
    session_id: str, ai_budget: int, model: str, style: str | None, force: bool
) -> Path:
    session_dir = CONTENT_ROOT / "sessions" / session_id
    if session_dir.exists() and not force:
        print(
            f"ERROR: session directory already exists at {session_dir}. "
            "Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    # All subdirectories the pipeline expects.
    subdirs = [
        "source",
        "source/audio",
        "source/generated-assets",
        "source/generated-assets/scenes",
        "source/external-assets",
        "source/box",
        "shot-list",
        "working",
        "renders",
        "frames",
        "manifests",
    ]
    for sub in subdirs:
        (session_dir / sub).mkdir(parents=True, exist_ok=True)
        # .gitkeep so empty dirs survive git (content repo is typically
        # committed for portability / session reproducibility).
        gitkeep = session_dir / sub / ".gitkeep"
        if not gitkeep.exists() and not any((session_dir / sub).iterdir()):
            gitkeep.touch()

    # session.json
    session_json_path = session_dir / "session.json"
    with session_json_path.open("w") as f:
        json.dump(make_session_json(session_id, ai_budget, model, style), f, indent=2)

    # shot-list/shot-list.json
    sl_path = session_dir / "shot-list" / "shot-list.json"
    with sl_path.open("w") as f:
        json.dump(make_shot_list_json(session_id), f, indent=2)

    print(f"[init] scaffolded session {session_id!r} at {session_dir}")
    print(f"[init]   session.json: {session_json_path.relative_to(CONTENT_ROOT)}")
    print(f"[init]   shot-list:    {sl_path.relative_to(CONTENT_ROOT)}")
    return session_dir


def activate_session(session_id: str) -> None:
    """Point the Remotion public/ symlinks at this session so renders and
    `npm run dev` pick it up. Replaces any existing links."""
    session_dir = CONTENT_ROOT / "sessions" / session_id
    if not session_dir.exists():
        print(f"ERROR: cannot activate — session dir missing: {session_dir}", file=sys.stderr)
        sys.exit(1)

    PUBLIC_DIR.mkdir(exist_ok=True)
    links = {
        "frames": session_dir / "frames",
        "source": session_dir / "source",
    }
    # Optional "pilot" symlink — only created if a pilot session exists,
    # since some sessions reference a sibling pilot's assets.
    pilot_dir = CONTENT_ROOT / "sessions" / "pilot"
    if pilot_dir.exists():
        links["pilot"] = pilot_dir

    for name, target in links.items():
        link_path = PUBLIC_DIR / name
        # Replace whatever is there.
        if link_path.is_symlink() or link_path.exists():
            link_path.unlink()
        # Use relative symlink so the repo is portable between machines.
        rel_target = os.path.relpath(target, PUBLIC_DIR)
        link_path.symlink_to(rel_target)
        print(f"[activate] public/{name} -> {rel_target}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Scaffold a new spoolcast session (content-side directory + templates)."
    )
    p.add_argument("--id", required=True, help="session id (folder name), e.g. my-video-v1")
    p.add_argument(
        "--ai-budget",
        type=int,
        default=60,
        help="max kie.ai image generations for this session (default 60)",
    )
    p.add_argument(
        "--model",
        default="nano-banana-2",
        help="kie.ai preferred model (default nano-banana-2)",
    )
    p.add_argument(
        "--style",
        default=None,
        help="optional style_reference string or image URL for the session anchor",
    )
    p.add_argument(
        "--activate",
        action="store_true",
        help="re-point public/ symlinks at this session so Remotion picks it up",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing session dir (careful — destroys session.json / shot-list)",
    )
    args = p.parse_args()

    scaffold_session(args.id, args.ai_budget, args.model, args.style, args.force)
    if args.activate:
        activate_session(args.id)
    print()
    print("Next steps:")
    print(f"  1. Edit ../spoolcast-content/sessions/{args.id}/shot-list/shot-list.json")
    print(f"     — write real narration per chunk.")
    print(f"  2. scripts/.venv/bin/python scripts/generate_scene.py \\")
    print(f"         --session {args.id} --chunk C1 \\")
    print(f"         --narration \"<your first beat narration>\"")
    print(f"  3. scripts/.venv/bin/python scripts/tts_client.py \\")
    print(f"         --text \"<same narration>\" \\")
    print(f"         --out ../spoolcast-content/sessions/{args.id}/source/audio/01A.mp3")
    print(f"  4. scripts/.venv/bin/python scripts/stroke_reveal.py \\")
    print(f"         --input ../spoolcast-content/sessions/{args.id}/source/generated-assets/scenes/C1.png \\")
    print(f"         --output ../spoolcast-content/sessions/{args.id}/frames/C1/ \\")
    print(f"         --fps 30 --duration 1.5 --strategy auto")
    print(f"  5. scripts/.venv/bin/python scripts/build_preview_data.py --session {args.id}")
    print(f"  6. npm run dev   # open Remotion Studio to preview")
    print(f"  7. npx remotion render spoolcast-pilot \\")
    print(f"         ../spoolcast-content/sessions/{args.id}/renders/{args.id}-v1.mp4")


if __name__ == "__main__":
    main()
