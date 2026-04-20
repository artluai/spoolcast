"""
estimate_overlay_timings.py — update overlay timing_start_s / timing_end_s in
the shot list based on proportional word-position estimates.

For each overlay with a `mark_on_word` field:
  1. Find the beat whose narration contains that word (case-insensitive match).
  2. Compute that beat's start time within its chunk using the real mp3
     durations (ffprobe on source/audio/<beat-id>.mp3) plus pause-after
     values between beats.
  3. Compute the word's fractional position in the beat's narration
     (word_index / total_words).
  4. Estimate the word's absolute time in the chunk as:
        beat_start_in_chunk + (word_fraction * beat_duration)
  5. Overwrite timing_start_s to that value; keep the original
     (timing_end_s - timing_start_s) duration.

This is a cheap approximation. Accurate to ~±0.3s. Will be replaced by
real word-level timestamps when Whisper alignment is wired in for V2+.

Usage:
    scripts/.venv/bin/python scripts/estimate_overlay_timings.py \\
        --session spoolcast-explainer
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

PAUSE_SECONDS = {
    "":      0.3,
    "none":  0.0,
    "short": 0.5,
    "medium":1.0,
    "long":  2.0,
}


def _parse_pause(s: str) -> float:
    s = (s or "").strip().lower()
    # numeric suffix like "1.0s" or "0.5s"
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


def _fallback_duration_from_text(text: str) -> float:
    # ~14 chars-per-sec at 1.0x. At 1.2x, ~17 cps.
    return max(0.5, len(text) / 17.0)


def _find_word_position(narration: str, target: str) -> tuple[int, int] | None:
    """Return (word_index, total_words) if target found in narration, else None."""
    words = re.findall(r"\S+", narration)
    if not words:
        return None
    # Match whole-word, case-insensitive. Also handle trailing punctuation.
    target_l = target.lower()
    for i, w in enumerate(words):
        w_clean = re.sub(r"[^\w.@-]", "", w).lower()
        if w_clean == target_l or target_l in w_clean:
            return (i, len(words))
    return None


def update_shot_list(session_id: str, verbose: bool = True) -> dict:
    session_dir = CONTENT_ROOT / "sessions" / session_id
    shot_list_path = session_dir / "shot-list" / "shot-list.json"
    data = json.loads(shot_list_path.read_text())

    total_overlays = 0
    updated = 0
    skipped = []

    for chunk in data["chunks"]:
        overlays = chunk.get("overlays") or []
        if not overlays:
            continue

        beats = chunk.get("beats", [])
        # Build (beat_id, narration, duration, pause_after) table
        beat_info: list[tuple[str, str, float, float]] = []
        for b in beats:
            bid = b.get("id", "")
            narr = (b.get("narration") or "").strip()
            dur = _audio_duration(session_id, bid)
            if dur is None and narr:
                dur = _fallback_duration_from_text(narr)
            elif dur is None:
                dur = 0.0
            pause = _parse_pause(b.get("pause_after", ""))
            beat_info.append((bid, narr, dur, pause))

        # Compute running starts within the chunk
        beat_starts: dict[str, float] = {}
        t = 0.0
        for bid, narr, dur, pause in beat_info:
            beat_starts[bid] = t
            t += dur + pause

        for ov in overlays:
            total_overlays += 1
            target = ov.get("mark_on_word")
            if not target:
                continue

            # Find the beat containing the target word
            hit = None
            for bid, narr, dur, pause in beat_info:
                pos = _find_word_position(narr, target)
                if pos is not None:
                    hit = (bid, narr, dur, pause, pos)
                    break

            if hit is None:
                skipped.append((chunk["id"], target, "word not found in any beat"))
                continue

            bid, narr, dur, pause, (wi, wn) = hit
            # Fraction: mid-word if word is >1 char, otherwise beat_fraction
            frac = (wi + 0.1) / wn if wn > 0 else 0.0
            word_t = beat_starts[bid] + frac * dur

            old_start = ov.get("timing_start_s", 0.0)
            old_end = ov.get("timing_end_s", 0.0)
            dur_overlay = max(0.8, old_end - old_start)

            # Anchor overlay slightly before the word and keep duration
            new_start = max(0.0, word_t - 0.1)
            new_end = new_start + dur_overlay

            ov["timing_start_s"] = round(new_start, 2)
            ov["timing_end_s"] = round(new_end, 2)
            updated += 1

            if verbose:
                print(f"  {chunk['id']:5} overlay→{Path(ov['source']).name:28} "
                      f"mark={target:12} word#{wi+1}/{wn} beat={bid:5} "
                      f"→ {old_start:5.2f}→{new_start:5.2f}s (d={dur_overlay:.2f})")

    shot_list_path.write_text(json.dumps(data, indent=2))

    print(f"\nSummary:")
    print(f"  {updated} / {total_overlays} overlays updated")
    if skipped:
        print(f"  {len(skipped)} skipped (word not found):")
        for cid, word, reason in skipped:
            print(f"    {cid} '{word}': {reason}")

    return {"updated": updated, "total": total_overlays, "skipped": skipped}


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    update_shot_list(args.session, verbose=not args.quiet)


if __name__ == "__main__":
    _cli()
