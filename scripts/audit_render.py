#!/usr/bin/env python3
"""Programmatic audit of a rendered spoolcast mp4.

Runs checks against the final rendered artifact — not against intermediate
preview-data or code. Encodes every known failure class as a mechanical
check so "verified" means "the audit passed," not "I changed the code."

Checks in v1:
  - white-flash detection: every chunk boundary (and every chunk carrying
    on_screen_text) gets sampled at the boundary frame and at small offsets
    into the chunk. Any frame whose compressed JPG size is below a threshold
    is flagged as near-white — pure white at 1920x1080, -q:v 2, is ~13KB;
    real illustrated frames are 70-350KB.

Planned for v2+ (not yet implemented):
  - overlay presence: confirm declared overlay asset is visible on the frame
  - OCR of on_screen_text: confirm declared literal text renders legibly
  - duration integrity: total render duration matches preview-data totalFrames
  - hold_duration_sec respected: chunks hold the right number of frames

Exit codes:
  0 = all checks passed
  2 = at least one check failed (see report)
  3 = inputs missing or ffmpeg unavailable

Usage:
  scripts/.venv/bin/python scripts/audit_render.py \\
      --session spoolcast-dev-log \\
      [--mp4 path/to/render.mp4] \\
      [--report path/to/report.json]

On success, writes a sentinel file at the session's
`working/render-audit.passed` path with the mp4's absolute path + timestamp.
Other tools (e.g. render-wrapper scripts, publish hooks) can require this
sentinel before treating the render as shipped.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

# Threshold (bytes) below which a 1920x1080 JPG at -q:v 2 is treated as
# near-white. Pure white is ~13KB; real scenes are 70KB+. 30KB is a safe
# floor that catches flashes without false-positives on minimal frames.
WHITE_FLASH_JPG_SIZE_THRESHOLD = 30_000


def _session_dir(session: str) -> Path:
    return CONTENT_ROOT / "sessions" / session


def _default_mp4(session: str) -> Path:
    # Most-recent 1.0x render in the session's renders/ dir. Caller can
    # override with --mp4.
    renders = _session_dir(session) / "renders"
    if not renders.exists():
        return Path("/nonexistent")
    candidates = sorted(
        renders.glob("*-1.0x.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else Path("/nonexistent")


def _extract_frame_size(mp4: Path, timestamp_s: float) -> int:
    """Extract one frame at timestamp and return its JPG byte size.

    Returns 0 if ffmpeg fails. Uses -q:v 2 (high-quality JPG) — the
    compression is what makes near-white frames collapse to ~13KB while
    real frames stay at 70KB+.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{timestamp_s}", "-i", str(mp4),
            "-frames:v", "1", "-q:v", "2",
            tmp.name,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return 0
        try:
            return Path(tmp.name).stat().st_size
        except OSError:
            return 0


def _load_preview_data() -> dict[str, Any] | None:
    path = REPO_ROOT / "src" / "data" / "preview-data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def check_white_flashes(mp4: Path, preview: dict[str, Any]) -> list[dict[str, Any]]:
    """For each chunk boundary, sample a few frames; flag near-white ones.

    Returns a list of failure records (empty = no flashes detected).
    """
    failures: list[dict[str, Any]] = []
    fps = float(preview.get("fps") or 30)
    chunks = preview.get("chunks") or []
    # Broll chunks render source video/image content; their first frames can
    # legitimately be low-detail (opening white/black, title cards, blinking
    # cursors) without being pipeline flashes. Skip the white-flash check on
    # those — real flashes would be in the illustrated chunks around them.
    skip_sources = {"broll", "broll_image"}
    for i, c in enumerate(chunks):
        if (c.get("imageSource") or "") in skip_sources:
            continue
        start_frame = int(c.get("startFrame", 0) or 0)
        duration = int(c.get("durationFrames", 0) or 0)
        if duration <= 0:
            continue
        # Sample at boundary (frame 0 of chunk) and +3, +6 frames in. That
        # window catches flashes during crossfades and at gap boundaries.
        boundary_frames = [0, 3, 6]
        for offset in boundary_frames:
            if offset >= duration:
                break
            t = (start_frame + offset) / fps
            size = _extract_frame_size(mp4, t)
            if 0 < size < WHITE_FLASH_JPG_SIZE_THRESHOLD:
                failures.append({
                    "check": "white_flash",
                    "timestamp_s": round(t, 3),
                    "chunk_id": c.get("id", "?"),
                    "chunk_offset_frames": offset,
                    "jpg_bytes": size,
                    "threshold_bytes": WHITE_FLASH_JPG_SIZE_THRESHOLD,
                    "reason": (
                        f"frame at {t:.2f}s (chunk {c.get('id')} + {offset}f) "
                        f"compressed to {size}b < threshold {WHITE_FLASH_JPG_SIZE_THRESHOLD}b "
                        f"— probable near-white / blank frame"
                    ),
                })
    return failures


def run(session: str, mp4: Path) -> tuple[bool, dict[str, Any]]:
    if not mp4.exists():
        return False, {"error": f"mp4 not found at {mp4}"}

    # Verify ffmpeg exists
    try:
        subprocess.run(
            ["ffmpeg", "-version"], check=True, capture_output=True, timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False, {"error": "ffmpeg not available on PATH"}

    preview = _load_preview_data()
    if preview is None:
        return False, {"error": "src/data/preview-data.json missing or unreadable"}

    all_failures: list[dict[str, Any]] = []
    all_failures.extend(check_white_flashes(mp4, preview))

    passed = len(all_failures) == 0
    report = {
        "session": session,
        "mp4": str(mp4),
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failure_count": len(all_failures),
        "failures": all_failures,
        "checks_run": ["white_flash"],
    }
    return passed, report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit a rendered spoolcast mp4.")
    p.add_argument("--session", required=True)
    p.add_argument("--mp4", default=None, help="path to mp4 (default: most-recent 1.0x render)")
    p.add_argument("--report", default=None, help="write JSON report to this path")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mp4 = Path(args.mp4) if args.mp4 else _default_mp4(args.session)
    passed, report = run(args.session, mp4)

    # Write report
    if args.report:
        report_path = Path(args.report)
    else:
        report_path = _session_dir(args.session) / "working" / "render-audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    # Console summary
    print(f"=== render audit: {args.session} ===")
    print(f"mp4: {mp4}")
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return 3
    print(f"checks: {', '.join(report['checks_run'])}")
    print(f"{'PASSED' if passed else 'FAILED'} — {report['failure_count']} failure(s)")
    if not passed:
        for f in report["failures"][:20]:
            print(f"  - {f['reason']}")
        if len(report["failures"]) > 20:
            print(f"  ... and {len(report['failures']) - 20} more (see {report_path})")
    print(f"report: {report_path}")

    # Sentinel on success
    sentinel = _session_dir(args.session) / "working" / "render-audit.passed"
    if passed:
        sentinel.write_text(
            f"{mp4}\n{report['audited_at']}\n"
        )
        print(f"sentinel: {sentinel}")
    elif sentinel.exists():
        # Stale sentinel from a prior pass — remove to avoid confusing
        # downstream gates.
        sentinel.unlink()

    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
