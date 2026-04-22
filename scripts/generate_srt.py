"""
generate_srt.py — produce a YouTube-ready SRT caption file for a session.

Reads preview-data.json + the shot-list (for narration text) and writes an
.srt where each beat is one subtitle cue timed to its rendered position in
the video.

Usage:
    scripts/.venv/bin/python scripts/generate_srt.py \\
        --session spoolcast-explainer
    # -> writes ../spoolcast-content/sessions/spoolcast-explainer/renders/
    #    spoolcast-explainer.srt

    scripts/.venv/bin/python scripts/generate_srt.py \\
        --session spoolcast-explainer \\
        --out /abs/path/to/captions.srt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


def fmt_timestamp(sec: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    if sec < 0:
        sec = 0.0
    ms_total = round(sec * 1000)
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(session: str, out_path: Path | None) -> Path:
    preview_path = REPO_ROOT / "src" / "data" / "preview-data.json"
    shot_list_path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    if not preview_path.exists():
        print(
            f"ERROR: preview-data.json not found at {preview_path}. "
            "Run scripts/build_preview_data.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not shot_list_path.exists():
        print(f"ERROR: shot-list not found at {shot_list_path}", file=sys.stderr)
        sys.exit(1)

    with preview_path.open() as f:
        preview = json.load(f)
    with shot_list_path.open() as f:
        shot_list = json.load(f)

    # Build beat-id → narration text map from the shot-list (preview-data has
    # narration too, but the shot-list is authoritative).
    narration_by_beat: dict[str, str] = {}
    # Chunk-level on_screen_text (the literal words that appear on the
    # rendered frame). Included as bracketed cues so deaf/muted-viewer
    # captions reflect everything visible on screen, not just narration.
    on_screen_by_chunk: dict[str, list[str]] = {}
    for chunk in shot_list.get("chunks", []):
        for beat in chunk.get("beats", []):
            narration_by_beat[beat.get("id", "")] = (beat.get("narration") or "").strip()
        osts = chunk.get("on_screen_text") or []
        if isinstance(osts, list):
            cleaned = [s.strip() for s in osts if isinstance(s, str) and s.strip()]
            if cleaned:
                on_screen_by_chunk[chunk.get("id", "")] = cleaned

    fps = preview["fps"]
    cues: list[tuple[float, float, str]] = []
    for chunk in preview["chunks"]:
        chunk_start = chunk["startFrame"]
        chunk_end = chunk_start + chunk["durationFrames"]
        chunk_id = chunk.get("id", "")
        for beat in chunk["beats"]:
            text = narration_by_beat.get(beat["id"], (beat.get("narration") or "").strip())
            if not text:
                continue  # skip broll placeholders / empty beats
            abs_start = (chunk_start + beat["startFrameInChunk"]) / fps
            abs_end = (chunk_start + beat["endFrameInChunk"]) / fps
            cues.append((abs_start, abs_end, text))

        # On-screen text cue: spans the full chunk, bracketed so the viewer
        # reads it as "this is what's visible on the frame" rather than
        # dialogue. Lets sound-off viewers (YouTube mobile, captions
        # dashboards, accessibility readers) see every rendered word.
        osts = on_screen_by_chunk.get(chunk_id)
        if osts:
            abs_start = chunk_start / fps
            abs_end = chunk_end / fps
            label = " / ".join(osts)
            cues.append((abs_start, abs_end, f"[on-screen: {label}]"))

    # Sort cues chronologically. The narration loop adds beat cues in-order
    # then the chunk's on-screen-text cue at the end; without a sort they'd
    # appear in chunk-interleaved rather than strictly time-ordered.
    cues.sort(key=lambda c: (c[0], c[1]))

    # Write SRT.
    if out_path is None:
        out_path = CONTENT_ROOT / "sessions" / session / "renders" / f"{session}.srt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for i, (start, end, text) in enumerate(cues, start=1):
            f.write(f"{i}\n")
            f.write(f"{fmt_timestamp(start)} --> {fmt_timestamp(end)}\n")
            f.write(f"{text}\n\n")

    print(f"[srt] wrote {len(cues)} cues to {out_path}")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(description="Generate an SRT caption file from preview-data + shot-list.")
    p.add_argument("--session", required=True, help="session id")
    p.add_argument("--out", default=None, help="output path (default: sessions/<id>/renders/<id>.srt)")
    args = p.parse_args()
    generate_srt(args.session, Path(args.out) if args.out else None)


if __name__ == "__main__":
    main()
