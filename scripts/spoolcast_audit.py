#!/usr/bin/env python3
"""Universal spoolcast audit router."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
NEWS_SHOW_ROOT = CONTENT_ROOT / "shows" / "news-anime-bot"


@dataclass
class Route:
    format: str
    owner_rules: str
    session: str


@dataclass
class UnknownReport:
    session: str
    session_dir: str
    current_stage: str
    next_step: str
    command: str | None
    blockers: list[str]
    warnings: list[str]
    checks: list[Any]


def normalize_session(value: str) -> str:
    path = Path(value).expanduser()
    if path.exists():
        return path.name if path.name != "episode" else path.parent.name
    return value.strip().rstrip("/")


def route_session(session: str, forced_format: str) -> tuple[Route | None, UnknownReport | None]:
    generic_dir = CONTENT_ROOT / "sessions" / session
    news_dir = NEWS_SHOW_ROOT / "sessions" / session

    if forced_format == "illustration-chunk-remotion":
        return (
            Route(
                format="illustration-chunk-remotion",
                owner_rules=str(REPO_ROOT / "rules.md"),
                session=session,
            ),
            None,
        )
    if forced_format == "news-anime-bot":
        return (
            Route(
                format="news-anime-bot",
                owner_rules=str(NEWS_SHOW_ROOT / "rules.md"),
                session=session,
            ),
            None,
        )

    generic_exists = generic_dir.exists()
    news_exists = news_dir.exists()
    if generic_exists and news_exists:
        return None, UnknownReport(
            session=session,
            session_dir=str(CONTENT_ROOT),
            current_stage="Format conflict",
            next_step="Rerun with --format illustration-chunk-remotion or --format news-anime-bot.",
            command=None,
            blockers=[
                f"Both generic session and news-anime-bot session exist for {session}; choose the owner explicitly."
            ],
            warnings=[],
            checks=[],
        )
    if news_exists:
        return (
            Route(
                format="news-anime-bot",
                owner_rules=str(NEWS_SHOW_ROOT / "rules.md"),
                session=session,
            ),
            None,
        )
    if generic_exists:
        return (
            Route(
                format="illustration-chunk-remotion",
                owner_rules=str(REPO_ROOT / "rules.md"),
                session=session,
            ),
            None,
        )

    return None, UnknownReport(
        session=session,
        session_dir=str(CONTENT_ROOT),
        current_stage="Unknown format/session",
        next_step=(
            "Choose an existing adapter with --format, or run PIPELINE.md Stage 0 "
            "New Format Definition Pass before production."
        ),
        command=None,
        blockers=[
            f"No generic session at {generic_dir}",
            f"No news-anime-bot session at {news_dir}",
            "No registered adapter owns this session yet.",
        ],
        warnings=[
            "If this video needs a new style/format, define the adapter before making assets."
        ],
        checks=[],
    )


def build_report(route: Route, target: str) -> Any:
    if route.format == "illustration-chunk-remotion":
        from auditors import illustration_chunk_remotion

        return illustration_chunk_remotion.build_report(route.session, target)
    if route.format == "news-anime-bot":
        from auditors import news_anime_bot

        return news_anime_bot.build_report(route.session, target)
    raise ValueError(f"Unsupported format: {route.format}")


def print_report(route: Route | None, report: Any) -> None:
    print(f"=== spoolcast audit: {report.session} ===")
    if route:
        print(f"Format: {route.format}")
        print(f"Owner rules: {route.owner_rules}")
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
    if report.checks:
        print("\nChecks:")
        for check in report.checks:
            print(f"[{check.status}] {check.name}: {check.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a spoolcast session and route to the owning format.")
    parser.add_argument("--session", required=True, help="Session id, show episode date, or path.")
    parser.add_argument(
        "--format",
        choices=("auto", "illustration-chunk-remotion", "news-anime-bot"),
        default="auto",
        help="Force a format when creating a new session or resolving ambiguity.",
    )
    parser.add_argument(
        "--target",
        choices=("auto", "widescreen", "mobile"),
        default="auto",
        help="Optional target branch for formats that support variants.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = normalize_session(args.session)
    route, unknown = route_session(session, args.format)
    report = unknown if unknown else build_report(route, args.target)  # type: ignore[arg-type]
    if args.json:
        payload = {
            "format": route.format if route else None,
            "owner_rules": route.owner_rules if route else None,
            "report": asdict(report),
        }
        print(json.dumps(payload, indent=2))
    else:
        print_report(route, report)
    return 2 if report.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
