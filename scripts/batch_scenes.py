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
import concurrent.futures as cf
import json
import sys
import threading
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
    p.add_argument(
        "--mobile-variant",
        action="store_true",
        help=(
            "regenerate chunks at portrait aspect (Process A.1). Writes to "
            "<chunk>-mobile.png and records mobile_image_path back to the "
            "shot-list. Skips the pre-flight external check — mobile variants "
            "reuse the widescreen externals. Typically paired with --only to "
            "target just the mobile_unsafe chunks from the latest audit."
        ),
    )
    p.add_argument(
        "--mobile-aspect",
        default="9:16",
        help="aspect for --mobile-variant (default 9:16; alternatives: 4:5, 1:1)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "number of concurrent kie.ai generations (default: 1 = serial). "
            "Each chunk calls generate() independently — no shared mutable state "
            "during generation, so this is safe to parallelize. kie.ai's documented "
            "rate limit is 20 new generation requests per 10s, with 100+ concurrent "
            "running tasks supported per account. For a typical 20-40 chunk batch, "
            "set this to the chunk count (or 20, whichever is smaller) and the "
            "whole batch fires at once — wall-clock time becomes ~one generation, "
            "not N generations. If you hit HTTP 429, reduce. See "
            "https://docs.kie.ai (Rate Limits & Concurrency)."
        ),
    )
    args = p.parse_args()

    shot_list_path = CONTENT_ROOT / "sessions" / args.session / "shot-list" / "shot-list.json"
    d = json.loads(shot_list_path.read_text())
    chunks = d["chunks"]

    # Pre-flight: externals must be sourced + verified before any paid kie call.
    # Enforces PIPELINE.md § Stage 4 ordering rule mechanically.
    # Skipped entirely for --mobile-variant (mobile regens reuse the already-
    # verified widescreen externals; no new external dependencies).
    if not args.skip_external_check and not args.mobile_variant:
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
          f"(force={args.force} workers={args.workers})")
    successes: list[tuple[str, str]] = []
    failures: list[tuple[str, str]] = []
    print_lock = threading.Lock()

    def run_one(idx: int, c: dict) -> tuple[str, bool, str]:
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
        with print_lock:
            print(f"\n[batch] ({idx}/{len(todo)}) {cid} (bk={bk}, refs={references})")
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
                mobile_variant=args.mobile_variant,
                mobile_aspect=args.mobile_aspect,
            )
            return cid, True, str(dest)
        except Exception as e:
            with print_lock:
                print(f"[batch] {cid} FAILED: {e}")
            # brief pause before next to avoid hammering on errors
            time.sleep(2)
            return cid, False, str(e)

    if args.workers <= 1:
        # Serial path — preserves prior log ordering exactly.
        for i, c in enumerate(todo, 1):
            cid, ok, payload = run_one(i, c)
            if ok:
                successes.append((cid, payload))
            else:
                failures.append((cid, payload))
    else:
        # Parallel path — kie.ai accepts concurrent calls; generate() has no
        # shared mutable state across threads.
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {
                ex.submit(run_one, i, c): c["id"]
                for i, c in enumerate(todo, 1)
            }
            for fut in cf.as_completed(futures):
                cid, ok, payload = fut.result()
                if ok:
                    successes.append((cid, payload))
                else:
                    failures.append((cid, payload))

    # After mobile regen, write mobile_image_path back to the shot-list so
    # downstream export_mobile.py knows which chunks have portrait variants.
    if args.mobile_variant and successes:
        shot_list = json.loads(shot_list_path.read_text())
        success_by_cid = dict(successes)
        session_dir_for_rel = CONTENT_ROOT / "sessions" / args.session
        updated = 0
        for chunk in shot_list.get("chunks", []):
            cid = chunk.get("id")
            if cid in success_by_cid:
                dest_abs = Path(success_by_cid[cid])
                rel = dest_abs.relative_to(session_dir_for_rel)
                new_path = str(rel)
                if chunk.get("mobile_image_path") != new_path:
                    chunk["mobile_image_path"] = new_path
                    updated += 1
        if updated:
            with shot_list_path.open("w") as f:
                json.dump(shot_list, f, indent=2)
                f.write("\n")
            print(f"[batch] wrote mobile_image_path on {updated} chunk(s) in shot-list.json")

    print(f"\n[batch] done. {len(successes)} succeeded, {len(failures)} failed.")
    if failures:
        print("[batch] failures:")
        for cid, err in failures:
            print(f"  {cid}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
