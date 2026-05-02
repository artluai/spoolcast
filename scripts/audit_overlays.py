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
  7. Runway: chunk has enough time after timing_start_s for the meme_type's
     minimum duration to play before chunk-end.

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
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"

PAUSE_SECONDS = {
    "":      0.3,
    "none":  0.0,
    "short": 0.5,
    "medium":1.0,
    "long":  2.0,
}


def _parse_pause(s: str) -> float:
    s = (s or "").strip().lower()
    m = re.match(r"^([0-9.]+)s?$", s)
    if m:
        return float(m.group(1))
    return PAUSE_SECONDS.get(s, 0.3)


def _audio_duration(session_id: str, beat_id: str) -> float | None:
    path = CONTENT_ROOT / "sessions" / session_id / "source" / "audio" / f"{beat_id}.mp3"
    if not path.exists():
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=5,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def _chunk_duration_sec(session_id: str, chunk: dict[str, Any], playback_rate: float) -> float:
    """Estimate chunk duration: sum(audio/playback_rate) + sum(pauses)."""
    total = 0.0
    for b in chunk.get("beats", []):
        bid = b.get("id", "")
        d = _audio_duration(session_id, bid)
        if d is None:
            continue
        total += d / playback_rate
        total += _parse_pause(b.get("pause_after", ""))
    return total

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
    for ov in (data.get("cross_chunk_overlays") or []):
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

    session_json = CONTENT_ROOT / "sessions" / session_id / "session.json"
    playback_rate = 1.0
    if session_json.exists():
        playback_rate = float(json.loads(session_json.read_text()).get("tts_playback_rate", 1.0))

    siblings = _prior_siblings(session_id)
    reused_pool: set[str] = set()
    for s in siblings:
        reused_pool |= _load_overlay_sources(s)

    flags: list[dict[str, Any]] = []

    for chunk in data.get("chunks", []):
        cid = chunk.get("id", "?")
        beats = chunk.get("beats", [])
        chunk_dur = _chunk_duration_sec(session_id, chunk, playback_rate) if (chunk.get("overlays") or []) else 0.0
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

            # 7: runway — meme_type min duration must fit between timing_start_s and chunk end
            if mt in MEME_TYPE_RANGES and chunk_dur > 0:
                lo, _ = MEME_TYPE_RANGES[mt]
                runway = chunk_dur - ts
                if runway < lo - 0.05:
                    flag("insufficient-runway",
                         f"chunk has {runway:.2f}s after timing_start_s={ts:.2f}s; "
                         f"meme_type={mt} needs ≥{lo}s. mark_on_word lands too late in chunk.")

    # Cross-chunk overlay audit. Same 7 checks adapted for spans + 3 new.
    chunk_ids_in_order = [c["id"] for c in data.get("chunks", [])]
    chunks_by_id = {c["id"]: c for c in data.get("chunks", [])}

    for i, ov in enumerate(data.get("cross_chunk_overlays") or []):
        src = ov.get("source", "")
        basename = Path(src).name
        mt = ov.get("meme_type", "")
        ts = float(ov.get("timing_start_s", 0))
        dur_s = float(ov.get("duration_s", 0))
        width = float(ov.get("width", 0))
        mark = ov.get("mark_on_word", "")
        start_id = ov.get("start_chunk_id", "")
        mark_id = ov.get("mark_chunk_id", start_id)

        def cflag(kind: str, detail: str) -> None:
            flags.append({
                "chunk": f"cross[{start_id}]", "overlay_index": i,
                "source": basename, "kind": kind, "detail": detail,
            })

        # 1: meme_type valid
        if mt not in MEME_TYPE_RANGES:
            cflag("invalid-meme-type", f"got {mt!r}; valid: {sorted(MEME_TYPE_RANGES)}")
        else:
            lo, hi = MEME_TYPE_RANGES[mt]
            if dur_s < lo - 0.05 or dur_s > hi + 0.05:
                cflag("duration-out-of-range",
                      f"meme_type={mt} requires {lo}-{hi}s, got {dur_s:.2f}s")

        # 2: width
        if width < MIN_WIDTH:
            cflag("width-below-minimum", f"width={width:.2f} < {MIN_WIDTH}")

        # 3: mark_on_word + mark_chunk_id
        if not mark:
            cflag("mark-on-word-missing", "cross-chunk overlay requires mark_on_word")
        if not start_id or start_id not in chunks_by_id:
            cflag("invalid-start-chunk-id", f"start_chunk_id={start_id!r} not in shot-list")
            continue
        if mark_id not in chunks_by_id:
            cflag("invalid-mark-chunk-id", f"mark_chunk_id={mark_id!r} not in shot-list")
            continue

        # 4: span ≤ 2 adjacent chunks (mark must be start or the next chunk)
        si = chunk_ids_in_order.index(start_id)
        mi = chunk_ids_in_order.index(mark_id)
        if mi != si and mi != si + 1:
            cflag("span-too-wide",
                  f"mark_chunk_id={mark_id} is not start_chunk_id={start_id} or its immediate next; "
                  "cross-chunk overlays span ≤2 adjacent chunks")

        # 5: mark_on_word exists in mark_chunk's narration
        if mark and mark != "chunk-start":
            if not _word_in_beats(mark, chunks_by_id[mark_id].get("beats", [])):
                cflag("mark-on-word-not-found", f"word {mark!r} not in any beat of {mark_id}")

        # 6: runway across the span
        start_dur = _chunk_duration_sec(session_id, chunks_by_id[start_id], playback_rate)
        if mark_id == start_id:
            total_span = start_dur
        else:
            total_span = start_dur + _chunk_duration_sec(session_id, chunks_by_id[mark_id], playback_rate)
        if mt in MEME_TYPE_RANGES and total_span > 0:
            lo, _ = MEME_TYPE_RANGES[mt]
            runway = total_span - ts
            if runway < lo - 0.05:
                cflag("insufficient-runway",
                      f"span has {runway:.2f}s after timing_start_s={ts:.2f}s; "
                      f"meme_type={mt} needs ≥{lo}s")

        # 7: series freshness
        if basename in reused_pool and not ov.get("editorial_rerun_reason"):
            cflag("series-reuse-stale",
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
