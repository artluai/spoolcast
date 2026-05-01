#!/usr/bin/env python3
"""Mechanical audit of overlay declarations in a spoolcast shot-list.

Checks per overlay:
  1. `meme_type` is a valid value.
  2. Effective duration (timing_end_s - timing_start_s) matches the type range.
  3. `width` >= 0.30 (canvas fraction).
  4. `mark_on_word` is declared.
  5. If `mark_on_word` is not "chunk-start", the word appears in some beat
     narration of the host chunk.
  6. Overlay `source` basename is not reused from the prior 2 sibling sessions
     of the same series (prefix match, lexicographic sort).

Usage:
  scripts/.venv/bin/python scripts/audit_overlays.py --session <session-id>

Writes: ../spoolcast-content/sessions/<session>/working/overlay-audit.json
Exit codes:
  0 = no flags
  2 = any flag raised
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"

MEME_TYPE_RANGES: dict[str, tuple[float, float]] = {
    "quick-react-static": (0.0, 1.0),
    "quick-react-animated": (1.2, 1.8),
    "sustained-punchline": (1.5, 2.5),
    "saga-item": (0.6, 1.0),
}

MIN_WIDTH = 0.30
SIBLING_LOOKBACK = 2


def _series_stem(session_id: str) -> str:
    # Strip trailing "-NN" if present so dev-log-04 → dev-log.
    return re.sub(r"-\d+$", "", session_id)


def _prior_siblings(session_id: str) -> list[str]:
    stem = _series_stem(session_id)
    sessions_dir = CONTENT_ROOT / "sessions"
    if not sessions_dir.exists():
        return []
    candidates = sorted(
        d.name for d in sessions_dir.iterdir()
        if d.is_dir() and _series_stem(d.name) == stem and d.name != session_id
    )
    # Lexicographic sort works for zero-padded numeric suffixes.
    return candidates[-SIBLING_LOOKBACK:]


def _load_overlay_sources(session_id: str) -> set[str]:
    shot_list = CONTENT_ROOT / "sessions" / session_id / "shot-list" / "shot-list.json"
    if not shot_list.exists():
        return set()
    data = json.loads(shot_list.read_text())
    sources: set[str] = set()
    for c in data.get("chunks", []):
        for ov in (c.get("overlays") or []):
            src = ov.get("source", "")
            if src:
                sources.add(Path(src).name)
    return sources


def _word_in_beats(word: str, beats: list[dict[str, Any]]) -> bool:
    pat = re.compile(r"\b" + re.escape(word.strip().lower()) + r"\b")
    for b in beats:
        if pat.search((b.get("narration") or "").lower()):
            return True
    return False


def audit(session_id: str) -> dict[str, Any]:
    shot_list = CONTENT_ROOT / "sessions" / session_id / "shot-list" / "shot-list.json"
    data = json.loads(shot_list.read_text())

    siblings = _prior_siblings(session_id)
    reused_pool: set[str] = set()
    for s in siblings:
        reused_pool |= _load_overlay_sources(s)

    flags: list[dict[str, Any]] = []

    for chunk in data.get("chunks", []):
        cid = chunk.get("id", "?")
        beats = chunk.get("beats", [])
        for i, ov in enumerate(chunk.get("overlays") or []):
            src = ov.get("source", "")
            basename = Path(src).name
            mt = ov.get("meme_type", "")
            ts = float(ov.get("timing_start_s", 0))
            te = float(ov.get("timing_end_s", 0))
            dur = max(0.0, te - ts)
            width = float(ov.get("width", 0))
            mark = ov.get("mark_on_word", "")

            def flag(kind: str, detail: str) -> None:
                flags.append({
                    "chunk": cid, "overlay_index": i, "source": basename,
                    "kind": kind, "detail": detail,
                })

            # 1 + 2: meme_type valid and duration matches
            if mt not in MEME_TYPE_RANGES:
                flag("invalid-meme-type", f"got {mt!r}; valid: {sorted(MEME_TYPE_RANGES)}")
            else:
                lo, hi = MEME_TYPE_RANGES[mt]
                # ±0.05s tolerance for floating-point drift from word-anchoring.
                if dur < lo - 0.05 or dur > hi + 0.05:
                    flag("duration-out-of-range",
                         f"meme_type={mt} requires {lo}-{hi}s, got {dur:.2f}s")

            # 3: width
            if width < MIN_WIDTH:
                flag("width-below-minimum",
                     f"width={width:.2f} < {MIN_WIDTH}")

            # 4 + 5: mark_on_word
            if not mark:
                flag("mark-on-word-missing",
                     "every overlay must declare mark_on_word (or 'chunk-start' with reason)")
            elif mark != "chunk-start":
                if not _word_in_beats(mark, beats):
                    flag("mark-on-word-not-found",
                         f"word {mark!r} not in any beat of {cid}")

            # 6: series freshness — suppressed by editorial_rerun_reason
            if basename in reused_pool and not ov.get("editorial_rerun_reason"):
                flag("series-reuse-stale",
                     f"{basename} also appears in {siblings}; add editorial_rerun_reason to suppress")

    out = {
        "session_id": session_id,
        "siblings_checked": siblings,
        "flags": flags,
        "flag_count": len(flags),
    }

    out_path = CONTENT_ROOT / "sessions" / session_id / "working" / "overlay-audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    args = p.parse_args()
    out = audit(args.session)

    if not out["flags"]:
        print(f"[overlays] {args.session}: clean ({len(out['siblings_checked'])} siblings checked)")
        return 0

    print(f"[overlays] {args.session}: {out['flag_count']} flag(s)")
    for f in out["flags"]:
        print(f"  {f['chunk']:5} ov[{f['overlay_index']}] {f['source']:40} {f['kind']:25} {f['detail']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
