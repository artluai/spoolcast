#!/usr/bin/env python3
"""Audit a news-anime-bot episode's current stage."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
SHOW_ROOT = CONTENT_ROOT / "shows" / "news-anime-bot"

REQUIRED_EPISODE_FILES = (
    "script.md",
    "run_clips.py",
    "run_tts_schedar.py",
    "run_stitch.py",
)


@dataclass
class Check:
    name: str
    status: str
    detail: str


@dataclass
class Report:
    session: str
    session_dir: str
    current_stage: str
    next_step: str
    command: str | None
    blockers: list[str]
    warnings: list[str]
    checks: list[Check]


def add(checks: list[Check], name: str, status: str, detail: str) -> None:
    checks.append(Check(name=name, status=status, detail=detail))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def newest_prior_session(session: str) -> str | None:
    sessions_root = SHOW_ROOT / "sessions"
    if not sessions_root.exists():
        return None
    candidates = sorted(
        p.name for p in sessions_root.iterdir() if p.is_dir() and p.name < session
    )
    return candidates[-1] if candidates else None


def nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return len(list(root.glob(pattern)))


def build_report(session: str, target: str = "auto") -> Report:
    checks: list[Check] = []
    blockers: list[str] = []
    warnings: list[str] = []
    session_dir = SHOW_ROOT / "sessions" / session
    episode_dir = session_dir / "episode"

    def report(stage: str, next_step: str, command: str | None = None) -> Report:
        return Report(
            session=session,
            session_dir=str(session_dir),
            current_stage=stage,
            next_step=next_step,
            command=command,
            blockers=blockers,
            warnings=warnings,
            checks=checks,
        )

    owner_rules = SHOW_ROOT / "rules.md"
    if owner_rules.exists():
        add(checks, "owner rules", "pass", rel(owner_rules))
    else:
        add(checks, "owner rules", "fail", f"missing at {owner_rules}")
        blockers.append("news-anime-bot/rules.md is missing.")
        return report("Stage 0 - format setup", "Restore the show rules before producing an episode.", None)

    if not session_dir.exists() or not episode_dir.exists():
        add(checks, "episode directory", "fail", f"missing at {episode_dir}")
        blockers.append("Episode directory has not been bootstrapped from a prior episode.")
        prior = newest_prior_session(session)
        command = None
        if prior:
            command = (
                f"mkdir -p {session_dir} && "
                f"cp -R {SHOW_ROOT / 'sessions' / prior / 'episode'} {episode_dir}"
            )
        return report(
            "Stage 0 - bootstrap episode",
            "Copy the most recent prior episode directory, then edit the four stable files.",
            command,
        )
    add(checks, "episode directory", "pass", rel(episode_dir))

    missing_required = [name for name in REQUIRED_EPISODE_FILES if not nonempty_file(episode_dir / name)]
    if missing_required:
        add(checks, "stable episode files", "fail", ", ".join(missing_required))
        blockers.append("One or more stable episode files are missing or empty.")
        return report(
            "Stage 0 - bootstrap episode",
            "Restore script.md, run_clips.py, run_tts_schedar.py, and run_stitch.py.",
            None,
        )
    add(checks, "stable episode files", "pass", ", ".join(REQUIRED_EPISODE_FILES))

    script = episode_dir / "script.md"
    script_text = script.read_text(errors="replace")
    if "## Sources" not in script_text:
        add(checks, "script sources", "fail", "missing ## Sources section")
        blockers.append("script.md does not expose sources for the episode.")
        return report(
            "Stage 4 - screenplay / production plan",
            "Finish script.md with narration, sources, and audit notes before TTS.",
            None,
        )
    add(checks, "script sources", "pass", "## Sources present")

    if "## Audit" not in script_text and "## Audit notes" not in script_text:
        add(checks, "script audit notes", "warn", "missing ## Audit notes section")
        warnings.append("script.md should include audit notes for the artlu.ai guidebook.")
    else:
        add(checks, "script audit notes", "pass", "audit notes present")

    audio_count = count_files(episode_dir / "audio", "*.mp3")
    if audio_count < 12:
        add(checks, "narration mp3s", "fail", f"{audio_count}/12 mp3(s)")
        blockers.append("Narration TTS is incomplete.")
        return report(
            "Stage 6 - audio plan / generation",
            "Run TTS and ffprobe durations before clip generation.",
            f"cd {episode_dir} && python3 run_tts_schedar.py",
        )
    add(checks, "narration mp3s", "pass", f"{audio_count} mp3(s)")

    clip_count = count_files(episode_dir / "clips", "*.mp4")
    if clip_count < 12:
        add(checks, "visual clips", "fail", f"{clip_count}/12 mp4 clip(s)")
        blockers.append("Generated visual clips are incomplete.")
        return report(
            "Stage 7 - visual asset generation",
            "Generate or regenerate missing clips before stitching.",
            f"cd {episode_dir} && python3 run_clips.py",
        )
    add(checks, "visual clips", "pass", f"{clip_count} mp4 clip(s)")

    out_dir = episode_dir / "out"
    out_mp4s = sorted(out_dir.glob("*.mp4")) if out_dir.exists() else []
    out_srts = sorted(out_dir.glob("*.srt")) if out_dir.exists() else []
    if not out_mp4s or not out_srts:
        add(checks, "stitched outputs", "fail", f"{len(out_mp4s)} mp4(s), {len(out_srts)} srt(s)")
        blockers.append("Final stitched MP4/SRT is missing.")
        return report(
            "Stage 9 - assembly / stitch",
            "Run stitch after audio and clips exist.",
            f"cd {episode_dir} && python3 run_stitch.py",
        )
    add(checks, "stitched outputs", "pass", f"{len(out_mp4s)} mp4(s), {len(out_srts)} srt(s)")

    cast = session_dir / "cast.txt"
    if not nonempty_file(cast):
        add(checks, "cast manifest", "fail", "missing or empty cast.txt")
        blockers.append("cast.txt is required after stitch so sync tools can resolve show characters.")
        return report(
            "Stage 9 - post-stitch manifest",
            "Write one character name per line to the episode cast manifest.",
            None,
        )
    add(checks, "cast manifest", "pass", rel(cast))

    add(checks, "manual output audit", "warn", "not mechanically recorded")
    warnings.append(
        "news-anime-bot output audit is still manual: review final MP4 for pacing, captions, watermark, disclosure, chyrons, and audio."
    )

    return report(
        "Stage 10/12 - assembled; manual output audit / publish checklist",
        "Review the final MP4, then complete platform disclosure, SRT upload, and account-status checks.",
        None,
    )


def print_report(report: Report) -> None:
    print(f"=== news-anime-bot audit: {report.session} ===")
    print(f"Session dir: {report.session_dir}")
    print(f"Current stage: {report.current_stage}")
    print(f"Next step: {report.next_step}")
    if report.command:
        print(f"Command: {report.command}")
    if report.blockers:
        print("\nBlockers:")
        for blocker in report.blockers:
            print(f"- {blocker}")
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"- {warning}")
    print("\nChecks:")
    for check in report.checks:
        print(f"[{check.status}] {check.name}: {check.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a news-anime-bot episode.")
    parser.add_argument("--session", required=True, help="Episode date, e.g. 2026-05-03.")
    parser.add_argument("--target", default="auto")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.session, args.target)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print_report(report)
    return 2 if report.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
