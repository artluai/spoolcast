#!/usr/bin/env python3
"""Batch-preprocess every chunk in a session's shot-list that has a scene PNG.

Calls preprocess_scene.py once per eligible chunk. Skips broll/meme/external_*
chunks (they don't need reveal frames — they play their own video). Skips
chunks whose frames dir already exists unless --force.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
PYTHON = REPO_ROOT / "scripts" / ".venv" / "bin" / "python"
PREPROCESS = REPO_ROOT / "scripts" / "preprocess_scene.py"

SKIP_SOURCES = {
    "broll", "broll_image", "meme", "external_screenshot", "external_xlsx",
    "external_json", "external_terminal", "external_audio", "reuse",
    "composite_pilot",
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    shot_list = CONTENT_ROOT / "sessions" / args.session / "shot-list" / "shot-list.json"
    d = json.loads(shot_list.read_text())
    frames_root = CONTENT_ROOT / "sessions" / args.session / "frames"

    todo = []
    for c in d["chunks"]:
        cid = c["id"]
        bk = c.get("boundary_kind", "")
        isrc = c.get("image_source", "generated")
        if bk != "bumper" and isrc in SKIP_SOURCES:
            continue
        todo.append(cid)

    print(f"[batch-pre] {len(todo)} chunks to preprocess")
    ok = 0
    failed: list[tuple[str, str]] = []
    for i, cid in enumerate(todo, 1):
        target = frames_root / cid
        if target.exists() and not args.force:
            print(f"[batch-pre] ({i}/{len(todo)}) {cid} skip-exists")
            ok += 1
            continue
        cmd = [str(PYTHON), str(PREPROCESS), "--session", args.session, "--chunk", cid]
        if args.force:
            cmd.append("--force")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            ok += 1
            print(f"[batch-pre] ({i}/{len(todo)}) {cid} ✓")
        else:
            failed.append((cid, result.stderr.strip()[-400:]))
            print(f"[batch-pre] ({i}/{len(todo)}) {cid} ✗ {result.stderr.strip()[-200:]}")

    print(f"\n[batch-pre] done. {ok} ok, {len(failed)} failed")
    if failed:
        for cid, err in failed:
            print(f"  {cid}: {err}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
