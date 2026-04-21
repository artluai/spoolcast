#!/usr/bin/env python3
"""Structural validator for a spoolcast shot-list.

Layer 1 of the two-layer durability gate described in STORY.md § Part 2
"Two-layer enforcement". This is the deterministic schema check that runs
before build_preview_data.py. The semantic layer (viewer-cognition,
overweight, preview-structure) lives in audit_narration.py.

Usage:
    scripts/.venv/bin/python scripts/validate_shot_list.py \\
        --session spoolcast-explainer

Reads: ../spoolcast-content/sessions/<session>/shot-list/shot-list.json

Exit codes:
    0 = no errors
    1 = at least one validation error
    3 = shot-list missing / unreadable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

ALLOWED_BOUNDARY_KIND = {"continues-thread", "topic-shift", "act-boundary", "bumper"}
ALLOWED_WEIGHT = {"normal", "high"}
ALLOWED_IMAGE_SOURCE = {
    "generated",
    "proof",
    "reuse",
    "meme",
    "broll",
    "broll_image",
    "external_screenshot",
    "external_xlsx",
    "external_json",
    "external_terminal",
    "external_audio",
    "composite_pilot",
}
BROLL_SOURCES = {"broll", "broll_image"}
REVEAL_GROUP_MAX = 5


def load_shot_list(session: str) -> dict[str, Any]:
    path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: shot-list not found at {path}", file=sys.stderr)
        sys.exit(3)
    with path.open() as f:
        return json.load(f)


def validate(shot_list: dict[str, Any]) -> list[tuple[str, str]]:
    """Returns a list of (chunk_id, error_message). Empty list = pass."""
    errors: list[tuple[str, str]] = []
    chunks = shot_list.get("chunks", [])
    if not chunks:
        errors.append(("<shot-list>", "no chunks found"))
        return errors

    # Per-chunk field checks
    for c in chunks:
        cid = c.get("id") or "<unnamed>"
        bk = (c.get("boundary_kind") or "").strip()
        w = (c.get("weight") or "").strip()
        isrc = (c.get("image_source") or "generated").strip()

        if bk not in ALLOWED_BOUNDARY_KIND:
            if bk == "":
                errors.append((cid, "missing boundary_kind"))
            else:
                errors.append((cid, f"invalid boundary_kind: {bk!r}"))
        if w not in ALLOWED_WEIGHT:
            if w == "":
                errors.append((cid, "missing weight"))
            else:
                errors.append((cid, f"invalid weight: {w!r}"))
        if isrc not in ALLOWED_IMAGE_SOURCE:
            errors.append((cid, f"invalid image_source: {isrc!r}"))

        if bk == "act-boundary":
            if not (c.get("act_title") or "").strip():
                errors.append((cid, "act-boundary missing act_title"))
            if not (c.get("act_opener_line") or "").strip():
                errors.append((cid, "act-boundary missing act_opener_line"))
        if bk == "bumper":
            if not (c.get("act_title") or "").strip():
                errors.append((cid, "bumper missing act_title"))
            if c.get("beats"):
                errors.append((cid, "bumper has beats (should be empty)"))
        else:
            # Non-bumper chunks must have at least one beat.
            # Broll chunks may use a silent placeholder beat (empty narration)
            # because the clip plays its own audio — see build_preview_data.py.
            beats = c.get("beats") or []
            if not beats:
                errors.append((cid, "no beats"))
            for b in beats:
                if not (b.get("id") or "").strip():
                    errors.append((cid, "beat missing id"))
                if isrc not in BROLL_SOURCES and not (b.get("narration") or "").strip():
                    bid = b.get("id") or "?"
                    errors.append((cid, f"beat {bid} missing narration"))

        if isrc in BROLL_SOURCES:
            cj = (c.get("context_justification") or "").strip().lower()
            if not cj or cj == "none":
                errors.append((cid, "broll missing context_justification"))

    # Adjacency / structural checks
    prev_nonbumper: dict[str, Any] | None = None
    for i, c in enumerate(chunks):
        cid = c.get("id") or "<unnamed>"
        bk = (c.get("boundary_kind") or "").strip()

        # Scene-change default: crossing a scene boundary cannot be continues-thread
        if bk != "bumper":
            if (
                prev_nonbumper is not None
                and c.get("scene") != prev_nonbumper.get("scene")
                and bk == "continues-thread"
            ):
                errors.append(
                    (
                        cid,
                        f"scene changed ({prev_nonbumper.get('scene')!r} -> "
                        f"{c.get('scene')!r}) but boundary_kind=continues-thread",
                    )
                )
            prev_nonbumper = c

        # Act-boundary must be first chunk OR preceded by a bumper
        if bk == "act-boundary":
            if i == 0:
                pass  # allowed: video can open on an Act
            else:
                prev_bk = (chunks[i - 1].get("boundary_kind") or "").strip()
                if prev_bk != "bumper":
                    errors.append((cid, "act-boundary not preceded by a bumper chunk"))

        # Bumper must be followed by an act-boundary
        if bk == "bumper":
            if i + 1 >= len(chunks):
                errors.append((cid, "bumper is the last chunk (no act-boundary follows)"))
            else:
                next_bk = (chunks[i + 1].get("boundary_kind") or "").strip()
                if next_bk != "act-boundary":
                    errors.append((cid, "bumper not immediately followed by act-boundary"))

    # Reveal-group checks (adjacency, size, scene containment, bumper exclusion)
    group_indices: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        rg = (c.get("reveal_group") or "").strip()
        if rg:
            group_indices.setdefault(rg, []).append(i)

    for rg, idxs in group_indices.items():
        head_id = chunks[idxs[0]].get("id") or "<unnamed>"
        # Adjacency: consecutive indices
        for a, b in zip(idxs, idxs[1:]):
            if b != a + 1:
                errors.append(
                    (chunks[b].get("id") or "<unnamed>",
                     f"reveal_group {rg!r} non-adjacent "
                     f"(prev at index {a}, this at index {b})")
                )
        # Size cap
        if len(idxs) > REVEAL_GROUP_MAX:
            errors.append(
                (head_id, f"reveal_group {rg!r} size {len(idxs)} > {REVEAL_GROUP_MAX}")
            )
        # Scene containment (same Act)
        scenes = {chunks[i].get("scene") for i in idxs}
        if len(scenes) > 1:
            errors.append(
                (head_id, f"reveal_group {rg!r} spans scenes {sorted(s or '' for s in scenes)}")
            )
        # No bumper/act-boundary inside a group
        for i in idxs:
            bk = (chunks[i].get("boundary_kind") or "").strip()
            if bk in ("bumper", "act-boundary"):
                errors.append(
                    (chunks[i].get("id") or "<unnamed>",
                     f"reveal_group contains {bk!r} chunk (not allowed)")
                )

    return errors


def print_report(session: str, errors: list[tuple[str, str]]) -> None:
    print(f"=== validate_shot_list: {session} ===")
    if not errors:
        print("OK — no structural errors.")
        return
    # Group by chunk id, preserving first-seen order
    by_chunk: dict[str, list[str]] = {}
    for cid, msg in errors:
        by_chunk.setdefault(cid, []).append(msg)
    print(f"{len(errors)} errors across {len(by_chunk)} chunks:")
    print()
    for cid, msgs in by_chunk.items():
        print(f"  {cid}")
        for m in msgs:
            print(f"    - {m}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Structural validator for a spoolcast shot-list (Layer 1).",
    )
    p.add_argument("--session", required=True, help="Session ID, e.g. spoolcast-explainer")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    shot_list = load_shot_list(args.session)
    errors = validate(shot_list)
    print_report(args.session, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
