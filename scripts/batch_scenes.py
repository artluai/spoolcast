#!/usr/bin/env python3
"""Batch-generate scenes for every 'generated' chunk in a session's shot-list.

Reads the shot-list, iterates non-broll/meme chunks, calls generate_scene.generate()
once per chunk with the chunk's references list. Continues past individual
failures and prints a summary at the end.

Usage:
    scripts/.venv/bin/python scripts/batch_scenes.py --session <session-id>
    scripts/.venv/bin/python scripts/batch_scenes.py --session <id> --force  # regenerate
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from generate_scene import generate

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


SKIP_SOURCES = {
    "broll", "broll_image", "meme", "external_screenshot", "external_xlsx",
    "external_json", "external_terminal", "external_audio", "reuse",
    "composite_pilot", "proof",
}

# Sources that require a verification sidecar file per VISUALS.md § Asset
# Verification Enforcement. Video/audio assets where the agent can't directly
# inspect motion.
SOURCES_REQUIRING_SIDECAR = {
    "broll", "external_terminal", "external_audio",
}


def preflight_external_assets(
    session_dir: Path, chunks: list[dict]
) -> list[str]:
    """Walk chunks, verify every external asset is on disk with required sidecars.

    Returns a list of blocker messages. Empty list = pre-flight passes.
    Enforces PIPELINE.md § Stage 4 ordering rule mechanically: externals must
    be sourced and verified before any paid kie.ai call runs.
    """
    blockers: list[str] = []
    for c in chunks:
        cid = c.get("id", "<unnamed>")
        isrc = c.get("image_source", "generated")
        if isrc not in SKIP_SOURCES:
            continue  # generated/bumper handled by the batch itself
        rel_path = c.get("image_path", "")
        if not rel_path:
            blockers.append(f"{cid}: image_source={isrc} but no image_path set")
            continue
        abs_path = session_dir / rel_path
        if not abs_path.exists():
            blockers.append(f"{cid}: {isrc} image_path missing on disk: {abs_path}")
            continue
        if isrc in SOURCES_REQUIRING_SIDECAR:
            sidecar = abs_path.with_suffix(abs_path.suffix + ".verified.json")
            if not sidecar.exists():
                blockers.append(
                    f"{cid}: {isrc} missing verification sidecar: {sidecar} "
                    f"(per VISUALS.md § Asset Verification Enforcement)"
                )
    return blockers


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--only", default=None,
                   help="comma-separated chunk ids to generate (default: all eligible)")
    p.add_argument(
        "--skip-external-check",
        action="store_true",
        help=(
            "BYPASS the pre-flight external-asset check. Use only when you "
            "intentionally want to generate scenes before externals are sourced "
            "(e.g. for a preview). Normally externals must be on disk first per "
            "PIPELINE.md § Stage 4 ordering rule."
        ),
    )
    args = p.parse_args()

    shot_list_path = CONTENT_ROOT / "sessions" / args.session / "shot-list" / "shot-list.json"
    d = json.loads(shot_list_path.read_text())
    chunks = d["chunks"]

    # Pre-flight: externals must be sourced + verified before any paid kie call.
    # Enforces PIPELINE.md § Stage 4 ordering rule mechanically.
    if not args.skip_external_check:
        session_dir = CONTENT_ROOT / "sessions" / args.session
        blockers = preflight_external_assets(session_dir, chunks)
        if blockers:
            print(
                "[batch] PRE-FLIGHT FAILED — external assets missing or unverified.\n"
                "        Per PIPELINE.md § Stage 4 ordering rule, externals must "
                "be sourced + verified before kie.ai generations run.\n",
                file=sys.stderr,
            )
            for b in blockers:
                print(f"  - {b}", file=sys.stderr)
            print(
                "\n[batch] To bypass (intentional preview-only): re-run with --skip-external-check.",
                file=sys.stderr,
            )
            return 2

    only = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}

    todo = []
    for c in chunks:
        cid = c["id"]
        if only and cid not in only:
            continue
        isrc = c.get("image_source", "generated")
        bk = c.get("boundary_kind", "")
        # Bumpers are generated (title cards); broll/meme/external are skipped.
        if bk != "bumper" and isrc in SKIP_SOURCES:
            continue
        # Bumpers don't have beats; non-bumpers must.
        if bk != "bumper" and not c.get("beats"):
            continue
        todo.append(c)

    print(f"[batch] session={args.session} todo={len(todo)} chunks "
          f"(force={args.force})")
    successes, failures = [], []
    for i, c in enumerate(todo, 1):
        cid = c["id"]
        bk = c.get("boundary_kind", "")
        references = c.get("references") or []
        beat = c.get("beat_description") or ""
        narration_all = " ".join(b.get("narration", "") for b in c.get("beats") or [])
        # For bumpers, narration is "" and beat describes the title card.
        narration = narration_all or beat or ""
        # Structured slots (PIPELINE.md § visual_direction / on_screen_text /
        # motion_notes). When present, generate_scene.compose_prompt uses these
        # instead of the legacy beat_description blob; motion_notes is
        # deliberately discarded before reaching the image model.
        visual_direction = c.get("visual_direction") or None
        on_screen_text_field = c.get("on_screen_text")
        on_screen_text = (
            list(on_screen_text_field)
            if isinstance(on_screen_text_field, list)
            else None
        )
        motion_notes = c.get("motion_notes") or None
        print(f"\n[batch] ({i}/{len(todo)}) {cid} (bk={bk}, refs={references})")
        try:
            dest = generate(
                session_id=args.session,
                chunk_id=cid,
                narration=narration,
                beat=beat,
                force=args.force,
                references=references or None,
                visual_direction=visual_direction,
                on_screen_text=on_screen_text,
                motion_notes=motion_notes,
            )
            successes.append((cid, str(dest)))
        except Exception as e:
            print(f"[batch] {cid} FAILED: {e}")
            failures.append((cid, str(e)))
            # brief pause before next to avoid hammering on errors
            time.sleep(2)

    print(f"\n[batch] done. {len(successes)} succeeded, {len(failures)} failed.")
    if failures:
        print("[batch] failures:")
        for cid, err in failures:
            print(f"  {cid}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
