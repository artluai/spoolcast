#!/usr/bin/env python3
"""Final mechanical audit for A.1 mobile publish packages.

This implements PIPELINE.md A.1-11 / SHIPPING.md "Pre-upload checklist (A.1)"
for checks that can be deterministic: mobile crop audit status, MP4 dimensions
and duration, per-part SRT presence/duration/content, thumbnail dimensions, and
part numbering consistency.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
MOBILE_W = 1080
MOBILE_H = 1920


@dataclass
class Check:
    name: str
    status: str
    detail: str
    path: str | None = None


def add(checks: list[Check], name: str, status: str, detail: str, path: Path | None = None) -> None:
    checks.append(Check(name=name, status=status, detail=detail, path=str(path) if path else None))


def read_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text()), None
    except Exception as e:
        return None, str(e)


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        sig = f.read(24)
    if len(sig) < 24 or sig[:8] != b"\x89PNG\r\n\x1a\n" or sig[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return struct.unpack(">II", sig[16:24])


def ffprobe(path: Path) -> tuple[int, int, float]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height:format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    payload = json.loads(result.stdout)
    stream = (payload.get("streams") or [{}])[0]
    duration = float((payload.get("format") or {}).get("duration") or 0.0)
    return int(stream.get("width") or 0), int(stream.get("height") or 0), duration


SRT_TS_RE = re.compile(
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})"
)


def srt_time_to_sec(text: str) -> float:
    m = SRT_TS_RE.fullmatch(text.strip())
    if not m:
        raise ValueError(f"invalid SRT timestamp: {text!r}")
    return (
        int(m.group("h")) * 3600
        + int(m.group("m")) * 60
        + int(m.group("s"))
        + int(m.group("ms")) / 1000.0
    )


def srt_duration(path: Path) -> tuple[int, float]:
    text = path.read_text()
    cues = 0
    last_end = 0.0
    for line in text.splitlines():
        if "-->" not in line:
            continue
        cues += 1
        try:
            end = line.split("-->", 1)[1].strip().split()[0]
            last_end = max(last_end, srt_time_to_sec(end))
        except Exception:
            pass
    return cues, last_end


def mobile_audit_counts(audit: dict[str, Any]) -> tuple[int, int, int]:
    summary = audit.get("summary") or {}
    broken = summary.get("broken")
    skipped = summary.get("skipped")
    total = summary.get("total")
    if all(isinstance(v, int) for v in (broken, skipped, total)):
        return int(broken), int(skipped), int(total)
    rows = audit.get("chunks")
    if rows is None:
        rows = audit.get("results", [])
    if not isinstance(rows, list):
        return 0, 0, 0
    return (
        sum(1 for row in rows if row.get("broken")),
        sum(1 for row in rows if row.get("skipped")),
        len(rows),
    )


def discover_parts(session: str, mobile_dir: Path) -> tuple[list[tuple[int, int, Path]], list[str]]:
    warnings: list[str] = []
    part_re = re.compile(rf"^{re.escape(session)}-mobile-pt(\d+)of(\d+)\.mp4$")
    parts: list[tuple[int, int, Path]] = []
    for path in sorted(mobile_dir.glob("*.mp4")):
        m = part_re.match(path.name)
        if m:
            parts.append((int(m.group(1)), int(m.group(2)), path))
        elif path.name == f"{session}-mobile.mp4":
            parts.append((1, 1, path))
        else:
            warnings.append(f"Ignoring unrecognized mobile MP4 name: {path.name}")
    return parts, warnings


def audit(session: str, max_duration: float, tolerance: float) -> tuple[list[Check], list[str], list[str]]:
    checks: list[Check] = []
    failures: list[str] = []
    warnings: list[str] = []
    session_dir = CONTENT_ROOT / "sessions" / session
    mobile_dir = session_dir / "renders" / "mobile"

    if not session_dir.exists():
        add(checks, "session directory", "fail", "missing", session_dir)
        failures.append("Session directory is missing.")
        return checks, failures, warnings
    add(checks, "session directory", "pass", str(session_dir), session_dir)

    crop_audit_path = session_dir / "working" / "mobile-crop-audit.json"
    crop_audit, crop_err = read_json(crop_audit_path)
    if crop_err:
        add(checks, "mobile crop audit", "fail", crop_err, crop_audit_path)
        failures.append("Mobile crop audit is missing or invalid.")
    else:
        broken, skipped, total = mobile_audit_counts(crop_audit)
        if broken:
            add(checks, "mobile crop audit", "fail", f"{broken} broken, {skipped} skipped, {total} total", crop_audit_path)
            failures.append("Mobile crop audit has broken chunks.")
        else:
            add(checks, "mobile crop audit", "pass", f"0 broken, {skipped} skipped, {total} total", crop_audit_path)

    prompt_path = session_dir / "working" / "thumbnail-prompt.md"
    if not prompt_path.exists():
        add(checks, "thumbnail prompt", "fail", "missing", prompt_path)
        failures.append("working/thumbnail-prompt.md is missing; mobile thumbnails must reuse the persisted prompt.")
    else:
        add(checks, "thumbnail prompt", "pass", "persisted prompt exists", prompt_path)

    if not mobile_dir.exists():
        add(checks, "mobile renders directory", "fail", "missing", mobile_dir)
        failures.append("renders/mobile/ is missing.")
        return checks, failures, warnings
    add(checks, "mobile renders directory", "pass", str(mobile_dir), mobile_dir)

    parts, name_warnings = discover_parts(session, mobile_dir)
    warnings.extend(name_warnings)
    if not parts:
        add(checks, "mobile MP4 parts", "fail", "none found", mobile_dir)
        failures.append("No mobile MP4 parts found.")
        return checks, failures, warnings

    totals = {total for _, total, _ in parts}
    part_nums = sorted(n for n, _, _ in parts)
    expected_total = max(totals) if totals else len(parts)
    expected_nums = list(range(1, expected_total + 1))
    if len(totals) != 1 or part_nums != expected_nums:
        add(checks, "part numbering", "fail", f"found parts={part_nums}, totals={sorted(totals)}")
        failures.append("Mobile part numbering is inconsistent or non-contiguous.")
    else:
        add(checks, "part numbering", "pass", f"{expected_total} contiguous part(s)")

    for part_n, total, mp4 in parts:
        label = f"pt{part_n}of{total}"
        try:
            w, h, dur = ffprobe(mp4)
        except Exception as e:
            add(checks, f"{label} video probe", "fail", str(e), mp4)
            failures.append(f"{mp4.name} could not be probed.")
            continue
        if (w, h) != (MOBILE_W, MOBILE_H):
            add(checks, f"{label} video dimensions", "fail", f"{w}x{h}", mp4)
            failures.append(f"{mp4.name} is not {MOBILE_W}x{MOBILE_H}.")
        else:
            add(checks, f"{label} video dimensions", "pass", f"{w}x{h}", mp4)
        if dur <= 0:
            add(checks, f"{label} video duration", "fail", f"{dur:.3f}s", mp4)
            failures.append(f"{mp4.name} has invalid duration.")
        elif dur > max_duration + tolerance:
            add(checks, f"{label} video duration", "fail", f"{dur:.3f}s > {max_duration:.3f}s cap", mp4)
            failures.append(f"{mp4.name} exceeds the configured platform cap.")
        else:
            add(checks, f"{label} video duration", "pass", f"{dur:.3f}s", mp4)

        srt = mobile_dir / f"{session}-mobile-pt{part_n}of{total}.srt"
        if total == 1 and not srt.exists():
            srt = mobile_dir / f"{session}-mobile.srt"
        if not srt.exists():
            add(checks, f"{label} SRT", "fail", "missing", srt)
            failures.append(f"{label} SRT is missing.")
        else:
            text = srt.read_text()
            cues, srt_dur = srt_duration(srt)
            if cues <= 0:
                add(checks, f"{label} SRT cues", "fail", "0 cues", srt)
                failures.append(f"{srt.name} has no cues.")
            elif "[on-screen:" in text.lower():
                add(checks, f"{label} SRT content", "fail", "contains [on-screen:] cue", srt)
                failures.append(f"{srt.name} contains on-screen cues; upload SRT should be narration-only.")
            elif abs(srt_dur - dur) > 2.0:
                add(checks, f"{label} SRT duration", "warn", f"SRT ends {srt_dur:.3f}s, MP4 {dur:.3f}s", srt)
                warnings.append(f"{srt.name} duration differs from MP4 by more than 2 seconds.")
            else:
                add(checks, f"{label} SRT", "pass", f"{cues} cue(s), ends {srt_dur:.3f}s", srt)

        thumb = mobile_dir / f"{session}-mobile-thumb-pt{part_n}of{total}.png"
        if total == 1 and not thumb.exists():
            thumb = mobile_dir / f"{session}-mobile-thumb.png"
        if not thumb.exists():
            add(checks, f"{label} thumbnail", "fail", "missing", thumb)
            failures.append(f"{label} thumbnail is missing.")
        else:
            try:
                tw, th = png_size(thumb)
            except Exception as e:
                add(checks, f"{label} thumbnail dimensions", "fail", str(e), thumb)
                failures.append(f"{thumb.name} could not be read as PNG.")
            else:
                if (tw, th) != (MOBILE_W, MOBILE_H):
                    add(checks, f"{label} thumbnail dimensions", "fail", f"{tw}x{th}", thumb)
                    failures.append(f"{thumb.name} is not {MOBILE_W}x{MOBILE_H}.")
                else:
                    add(checks, f"{label} thumbnail dimensions", "pass", f"{tw}x{th}", thumb)

    return checks, failures, warnings


def print_report(session: str, checks: list[Check], failures: list[str], warnings: list[str]) -> None:
    print(f"=== mobile publish audit: {session} ===")
    print(f"Result: {'FAIL' if failures else 'PASS'}")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")
    print("\nChecks:")
    for check in checks:
        suffix = f" ({check.path})" if check.path else ""
        print(f"[{check.status}] {check.name}: {check.detail}{suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit A.1 mobile publish artifacts.")
    parser.add_argument("--session", required=True)
    parser.add_argument(
        "--max-duration",
        type=float,
        default=180.0,
        help="Max seconds per mobile part. Default 180 for Reels-friendly cap; pass 60 for Shorts/TikTok-strict packages.",
    )
    parser.add_argument("--tolerance", type=float, default=0.5)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    parser.add_argument(
        "--out",
        default=None,
        help="Audit JSON path. Default: working/mobile-publish-audit.json.",
    )
    parser.add_argument("--no-write", action="store_true", help="Do not write audit JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks, failures, warnings = audit(args.session, args.max_duration, args.tolerance)
    payload = {
        "session": args.session,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "warnings": warnings,
        "checks": [asdict(check) for check in checks],
        "settings": {"max_duration": args.max_duration, "tolerance": args.tolerance},
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_report(args.session, checks, failures, warnings)

    if not args.no_write:
        out_path = (
            Path(args.out)
            if args.out
            else CONTENT_ROOT / "sessions" / args.session / "working" / "mobile-publish-audit.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
        if not args.json:
            print(f"\nwrote {out_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
