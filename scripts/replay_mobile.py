#!/usr/bin/env python3
"""replay_mobile.py — re-submit a manifest prompt at a new aspect ratio.

STRICT REPLAY semantics: reads the exact `prompt` and `image_input` from the
widescreen scene manifest entry (role='scene') and submits them to kie.ai
with a single override — aspect_ratio. No prompt re-composition via
compose_prompt. No shot-list reads. No preamble injection.

Why this exists: the shot-list is mutable on-disk state. Between the
original widescreen generation and any later run, fields can be
normalized / backfilled / cleaned up in ways that silently change what
compose_prompt produces. If the goal is "produce the same scene I got
before, just at a different aspect", replaying the manifest entry is the
only byte-faithful way. Going through compose_prompt again uses the
CURRENT shot-list and can drift.

Usage:
  scripts/.venv/bin/python scripts/replay_mobile.py \\
      --session spoolcast-dev-log \\
      --chunks C4,C20,C23,C24,C25,C34,C36,C37,C38 \\
      --aspect 1:1 \\
      --dry-run

  # real run (costs kie.ai credits — one call per chunk):
  scripts/.venv/bin/python scripts/replay_mobile.py \\
      --session spoolcast-dev-log \\
      --chunks C20 \\
      --aspect 1:1 --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

from kie_client import KieClient, KieError, build_input_for_model

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


def manifest_path(session: str) -> Path:
    return CONTENT_ROOT / "sessions" / session / "manifests" / "scenes.manifest.json"


def scenes_dir(session: str) -> Path:
    return CONTENT_ROOT / "sessions" / session / "source" / "generated-assets" / "scenes"


def find_entry(manifest: dict[str, Any], chunk_id: str, role: str) -> dict[str, Any] | None:
    for item in manifest.get("items", []):
        if item.get("chunk_id") == chunk_id and item.get("role") == role:
            return item
    return None


def dry_run_diff(session: str, chunk_ids: list[str]) -> int:
    """Compare widescreen prompt vs current scene-mobile prompt. No API calls."""
    manifest = json.load(open(manifest_path(session)))
    print(f"=== dry-run diff for session {session} ===")
    print()
    for cid in chunk_ids:
        ws = find_entry(manifest, cid, "scene")
        mobile = find_entry(manifest, cid, "scene-mobile")
        if ws is None:
            print(f"  {cid}: NO widescreen entry (cannot replay)")
            continue
        if mobile is None:
            print(f"  {cid}: no current scene-mobile entry (replay would create fresh)")
            continue
        ws_prompt = ws.get("prompt", "")
        mb_prompt = mobile.get("prompt", "")
        if ws_prompt == mb_prompt:
            print(f"  {cid}: MATCH — widescreen prompt == current mobile prompt")
        else:
            print(f"  {cid}: DIFFERS — replay would change the prompt")
            # Show the differing section in context of "Scene:".
            ws_s = ws_prompt.find("Scene:")
            mb_s = mb_prompt.find("Scene:")
            ws_sect = ws_prompt[ws_s : ws_s + 300] if ws_s >= 0 else "(no Scene: section)"
            mb_sect = mb_prompt[mb_s : mb_s + 300] if mb_s >= 0 else "(no Scene: section)"
            print(f"    WIDESCREEN Scene: {ws_sect}")
            print(f"    CURRENT Scene:    {mb_sect}")
        # Also note image_input differences (reference URL churn).
        ws_refs = ws.get("image_input") or []
        mb_refs = mobile.get("image_input") or []
        if ws_refs != mb_refs:
            print(f"    image_input DIFFERS:")
            print(f"      WIDESCREEN: {ws_refs}")
            print(f"      CURRENT:    {mb_refs}")
        print()
    return 0


def replay_chunk(
    session: str,
    chunk_id: str,
    target_aspect: str,
    force: bool = False,
) -> Path | None:
    manifest = json.load(open(manifest_path(session)))
    entry = find_entry(manifest, chunk_id, "scene")
    if entry is None:
        print(f"[replay] {chunk_id}: no widescreen manifest entry — cannot replay", file=sys.stderr)
        return None

    mobile_scenes = scenes_dir(session) / "mobile"
    mobile_scenes.mkdir(parents=True, exist_ok=True)
    dest = mobile_scenes / f"{chunk_id}-mobile.png"
    if dest.exists() and not force:
        print(f"[replay] {chunk_id}: {dest} exists; pass --force to overwrite")
        return dest

    prompt = entry["prompt"]
    image_input = list(entry.get("image_input") or [])
    model = entry["model"]

    input_dict = build_input_for_model(
        model,
        prompt=prompt,
        image_refs=image_input,
        aspect_ratio=target_aspect,
        quality=entry.get("resolution", "1K"),
        output_format=entry.get("output_format", "png"),
    )

    print(f"[replay] {chunk_id}: model={model} target_aspect={target_aspect}")
    print(f"[replay] {chunk_id}: image_input={image_input}")

    client = KieClient()
    try:
        result = client.submit_and_download(
            model=model,
            input_dict=input_dict,
            dest_path=dest,
        )
    except KieError as e:
        print(f"[replay] {chunk_id} FAILED: {e}", file=sys.stderr)
        return None

    new_item = {
        "id": f"{chunk_id}-mobile",
        "chunk_id": chunk_id,
        "role": "scene-mobile",
        "replay_source_task_id": entry.get("task_id"),
        "model": model,
        "prompt": prompt,
        "task_id": result.task_id,
        "result_url": result.result_urls[0] if result.result_urls else "",
        "local_path": str(dest.relative_to(CONTENT_ROOT)),
        "mime_type": "image/png",
        "status": "success",
        "aspect_ratio": target_aspect,
        "resolution": entry.get("resolution", "1K"),
        "output_format": entry.get("output_format", "png"),
        "image_input": image_input,
    }

    # Replace any existing scene-mobile entry for this chunk.
    manifest["items"] = [
        i
        for i in manifest["items"]
        if not (i.get("chunk_id") == chunk_id and i.get("role") == "scene-mobile")
    ] + [new_item]

    with open(manifest_path(session), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[replay] wrote {dest}")
    print(f"[replay] manifest updated with scene-mobile entry")
    return dest


def main() -> int:
    p = argparse.ArgumentParser(description="Replay a widescreen manifest entry at a new aspect ratio.")
    p.add_argument("--session", required=True)
    p.add_argument("--chunks", required=True, help="comma-separated chunk ids")
    p.add_argument("--aspect", default="1:1", help="target aspect for the replay (default 1:1)")
    p.add_argument("--force", action="store_true", help="overwrite existing <chunk>-mobile.png")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="diff widescreen vs current scene-mobile prompts per chunk; no API calls, no writes",
    )
    args = p.parse_args()

    chunks = [c.strip() for c in args.chunks.split(",") if c.strip()]

    if args.dry_run:
        return dry_run_diff(args.session, chunks)

    failures = []
    for cid in chunks:
        if replay_chunk(args.session, cid, args.aspect, force=args.force) is None:
            failures.append(cid)

    print()
    print(f"[replay] done. {len(chunks) - len(failures)} succeeded, {len(failures)} failed.")
    if failures:
        print(f"[replay] failed: {failures}", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
