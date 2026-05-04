#!/usr/bin/env python3
"""Audit an illustration-chunk-remotion session's current stage.

This is the machine gate for the generic image-chunk / Remotion adapter.
It does not render, generate, upload, or call paid/LLM services. It only
inspects files that should already exist and reports the next allowed step.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

SKIP_PREPROCESS_SOURCES = {
    "broll",
    "broll_image",
    "meme",
    "external_screenshot",
    "external_xlsx",
    "external_json",
    "external_terminal",
    "external_audio",
    "reuse",
    "composite_pilot",
}


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


def read_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text()), None
    except Exception as e:
        return None, str(e)


def add(checks: list[Check], name: str, status: str, detail: str) -> None:
    checks.append(Check(name=name, status=status, detail=detail))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def chunk_ids(shot_list: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for chunk in shot_list.get("chunks") or []:
        cid = (chunk.get("id") or "").strip()
        if cid:
            ids.append(cid)
    return ids


def chunks_for_scene_generation(shot_list: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for chunk in shot_list.get("chunks") or []:
        cid = (chunk.get("id") or "").strip()
        if not cid:
            continue
        source = (chunk.get("image_source") or "generated").strip()
        if source == "generated":
            ids.append(cid)
    return ids


def chunks_for_preprocess(shot_list: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for chunk in shot_list.get("chunks") or []:
        cid = (chunk.get("id") or "").strip()
        if not cid:
            continue
        boundary = (chunk.get("boundary_kind") or "").strip()
        source = (chunk.get("image_source") or "generated").strip()
        if boundary != "bumper" and source in SKIP_PREPROCESS_SOURCES:
            continue
        ids.append(cid)
    return ids


def missing_files(root: Path, ids: list[str], suffix: str) -> list[str]:
    return [cid for cid in ids if not (root / f"{cid}{suffix}").exists()]


def missing_frame_dirs(session_dir: Path, ids: list[str]) -> list[str]:
    missing: list[str] = []
    for cid in ids:
        frame_dir = session_dir / "frames" / cid
        if not frame_dir.exists() or not any(frame_dir.glob("frame_*.png")):
            missing.append(cid)
    return missing


def run_shot_list_validation(session: str, shot_list: dict[str, Any]) -> list[tuple[str, str]]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import validate_shot_list  # type: ignore

    return validate_shot_list.validate(shot_list, session=session)


def narration_audit_failures(audit: dict[str, Any]) -> int:
    keys = (
        "alignment_flags",
        "bridge_flags",
        "layman_flags",
        "overweight_flags",
        "preview_flags",
    )
    total = 0
    for key in keys:
        value = audit.get(key)
        if isinstance(value, list):
            total += len(value)
    return total


def scene_audit_failures(audit: dict[str, Any]) -> int:
    summary = audit.get("summary") or {}
    for key in ("flags", "failed", "failures", "mobile_unsafe"):
        value = summary.get(key)
        if isinstance(value, int):
            return value
    results = audit.get("results") or []
    if isinstance(results, list):
        return sum(1 for item in results if item.get("flagged") or item.get("mobile_unsafe"))
    return 0


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


def find_widescreen_mp4(session_dir: Path) -> list[Path]:
    renders = session_dir / "renders"
    if not renders.exists():
        return []
    return sorted(p for p in renders.glob("*.mp4") if "/mobile/" not in str(p))


def mobile_outputs(session_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
    mobile_dir = session_dir / "renders" / "mobile"
    if not mobile_dir.exists():
        return [], [], []
    mp4s = sorted(mobile_dir.glob("*.mp4"))
    srts = sorted(mobile_dir.glob("*.srt"))
    thumbs = sorted(mobile_dir.glob("*thumb*.png"))
    return mp4s, srts, thumbs


def build_report(session: str, target: str) -> Report:
    checks: list[Check] = []
    blockers: list[str] = []
    warnings: list[str] = []
    session_dir = CONTENT_ROOT / "sessions" / session

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

    if not session_dir.exists():
        add(checks, "session directory", "fail", f"not found at {session_dir}")
        blockers.append("Session has not been scaffolded.")
        return report(
            "Stage 0 - scaffold",
            "Create the session directory and session.json.",
            f"scripts/init_session.py --id {session}",
        )
    add(checks, "session directory", "pass", str(session_dir))

    session_json = session_dir / "session.json"
    cfg, cfg_err = read_json(session_json)
    if cfg_err:
        add(checks, "session.json", "fail", cfg_err)
        blockers.append("session.json is missing or invalid.")
        return report("Stage 0 - scaffold", "Fix or create session.json.", None)
    add(checks, "session.json", "pass", rel(session_json))

    shot_path = session_dir / "shot-list" / "shot-list.json"
    shot_list, shot_err = read_json(shot_path)
    if shot_err:
        add(checks, "shot-list", "fail", shot_err)
        blockers.append("Canonical shot-list JSON is missing or invalid.")
        return report(
            "Stage 1-2 - screenplay / shot-list",
            "Build the screenplay and canonical shot-list before generating assets.",
            None,
        )

    ids = chunk_ids(shot_list)
    if not ids:
        add(checks, "shot-list chunks", "fail", "no chunks found")
        blockers.append("Shot-list has no chunks.")
        return report(
            "Stage 1-2 - screenplay / shot-list",
            "Author chunks in shot-list.json, then validate it.",
            f"scripts/validate_shot_list.py --session {session}",
        )
    add(checks, "shot-list chunks", "pass", f"{len(ids)} chunk(s)")

    render_passed = (session_dir / "working" / "render-audit.passed").exists()

    validation_errors = run_shot_list_validation(session, shot_list)
    if validation_errors:
        add(checks, "shot-list validation", "fail", f"{len(validation_errors)} error(s)")
        blockers.append("Shot-list schema/structure validation is failing.")
        return report(
            "Stage 2 - shot-list",
            "Fix shot-list validation errors before audits, generation, or render.",
            f"scripts/validate_shot_list.py --session {session}",
        )
    add(checks, "shot-list validation", "pass", "validate_shot_list.py = 0")

    narration_path = session_dir / "working" / "narration-audit.json"
    narration, narration_err = read_json(narration_path)
    if narration_err:
        add(checks, "narration audit", "fail", narration_err)
        blockers.append("Narration audit has not passed.")
        return report(
            "Stage 4a - narration audit",
            "Run narration audit and fix any flags before scene generation.",
            f"scripts/audit_narration.py --session {session}",
        )
    narration_flags = narration_audit_failures(narration)
    if narration_flags:
        if render_passed:
            add(
                checks,
                "narration audit",
                "warn",
                f"{narration_flags} flag(s); downstream render already passed",
            )
            warnings.append(
                "Narration audit has flags, but render-audit.passed exists from a downstream gate."
            )
        else:
            add(checks, "narration audit", "fail", f"{narration_flags} flag(s)")
            blockers.append("Narration audit has unresolved flags.")
            return report(
                "Stage 4a - narration audit",
                "Fix narration audit flags before scene generation.",
                f"scripts/audit_narration.py --session {session}",
            )
    else:
        add(checks, "narration audit", "pass", rel(narration_path))

    scene_ids = chunks_for_scene_generation(shot_list)
    scenes_root = session_dir / "source" / "generated-assets" / "scenes"
    missing_scenes = missing_files(scenes_root, scene_ids, ".png")
    if missing_scenes:
        sample = ", ".join(missing_scenes[:8])
        add(checks, "scene PNGs", "fail", f"{len(missing_scenes)} missing ({sample})")
        blockers.append("Generated scene PNGs are missing.")
        return report(
            "Stage 4c - scene generation",
            "Generate only the missing scene chunks.",
            f"scripts/batch_scenes.py --session {session}",
        )
    add(checks, "scene PNGs", "pass", f"{len(scene_ids)} generated scene(s)")

    widescreen_mp4s = find_widescreen_mp4(session_dir)

    scene_audit_path = session_dir / "working" / "scene-audit.json"
    scene_audit, scene_audit_err = read_json(scene_audit_path)
    if scene_audit_err:
        detail = "missing; downstream render already passed" if render_passed else scene_audit_err
        status = "warn" if render_passed else "fail"
        add(checks, "scene audit", status, detail)
        if render_passed:
            warnings.append("scene-audit.json is missing, but render-audit.passed exists from a downstream gate.")
        else:
            blockers.append("Scene audit has not passed.")
            return report(
                "Stage 4d - scene audit",
                "Run scene audit and regenerate flagged chunks before preprocessing.",
                f"scripts/audit_scenes.py --session {session}",
            )
    else:
        scene_flags = scene_audit_failures(scene_audit)
        if scene_flags:
            add(checks, "scene audit", "fail", f"{scene_flags} flag(s)")
            blockers.append("Scene audit has unresolved flags.")
            return report(
                "Stage 4d - scene audit",
                "Regenerate flagged chunks, then rerun scene audit.",
                f"scripts/audit_scenes.py --session {session}",
            )
        add(checks, "scene audit", "pass", rel(scene_audit_path))

    frame_ids = chunks_for_preprocess(shot_list)
    missing_frames = missing_frame_dirs(session_dir, frame_ids)
    if missing_frames:
        sample = ", ".join(missing_frames[:8])
        add(checks, "preprocessed frames", "fail", f"{len(missing_frames)} missing ({sample})")
        blockers.append("Reveal frame sequences are missing.")
        return report(
            "Stage 5 - preprocess",
            "Build reveal frames before review/render.",
            f"scripts/batch_preprocess.py --session {session}",
        )
    add(checks, "preprocessed frames", "pass", f"{len(frame_ids)} frame dir(s)")

    review_path = session_dir / "review" / "shot-review.html"
    if not review_path.exists():
        status = "warn" if render_passed else "fail"
        add(checks, "review board", status, "missing")
        if render_passed:
            warnings.append("Review board is missing, but render-audit.passed exists from a downstream gate.")
        else:
            blockers.append("Review board has not been built.")
            return report(
                "Stage 6 - review board",
                "Build the human review board before final render.",
                f"scripts/build_review_board.py --session {session}",
            )
    else:
        add(checks, "review board", "pass", rel(review_path))

    if not widescreen_mp4s:
        add(checks, "widescreen render", "fail", "no mp4 in renders/")
        blockers.append("Widescreen render is missing.")
        return report(
            "Stage 7 - render",
            "Render widescreen through render_with_audit.sh.",
            f"scripts/render_with_audit.sh {session}",
        )
    add(checks, "widescreen render", "pass", f"{len(widescreen_mp4s)} mp4(s)")

    if not render_passed:
        add(checks, "render audit sentinel", "fail", "working/render-audit.passed missing")
        blockers.append("Render audit has not passed.")
        return report(
            "Stage 7 - render audit",
            "Run render audit and fix flagged frames.",
            f"scripts/render_with_audit.sh {session}",
        )
    add(checks, "render audit sentinel", "pass", "working/render-audit.passed")

    srt_files = sorted((session_dir / "renders").glob("*.srt"))
    if not srt_files:
        add(checks, "widescreen SRT", "fail", "no .srt in renders/")
        blockers.append("Widescreen SRT is missing.")
        return report(
            "Stage 8b - captions SRT",
            "Generate the shipped-rate SRT.",
            f"scripts/generate_srt.py --session {session}",
        )
    add(checks, "widescreen SRT", "pass", f"{len(srt_files)} SRT file(s)")

    thumb_prompt = session_dir / "working" / "thumbnail-prompt.md"
    if not thumb_prompt.exists():
        add(checks, "thumbnail prompt", "warn", "missing; mobile thumbnails must not invent a replacement")
        warnings.append("working/thumbnail-prompt.md is missing; create/persist it before mobile thumbnails.")
    else:
        add(checks, "thumbnail prompt", "pass", rel(thumb_prompt))

    wants_mobile = target == "mobile"
    if target == "auto":
        mobile_dir = session_dir / "renders" / "mobile"
        mobile_audit_path = session_dir / "working" / "mobile-crop-audit.json"
        mobile_scenes = scenes_root / "mobile"
        wants_mobile = mobile_dir.exists() or mobile_audit_path.exists() or mobile_scenes.exists()

    if not wants_mobile:
        return report(
            "Stage 8 - widescreen shipped/render-ready",
            "Ask the user whether to ship mobile variants. If yes, rerun the audit with --target mobile.",
            f"scripts/spoolcast_audit.py --session {session} --target mobile",
        )

    mobile_scene_root = scenes_root / "mobile"
    missing_mobile = missing_files(mobile_scene_root, ids, "-mobile.png")
    if missing_mobile:
        sample = ", ".join(missing_mobile[:8])
        add(checks, "mobile scene PNGs", "fail", f"{len(missing_mobile)} missing ({sample})")
        blockers.append("Mobile scene PNGs are missing.")
        return report(
            "A.1-2 - smart-crop mobile scenes",
            "Run smart-crop first; regenerate only chunks that fail the crop audit later.",
            f"scripts/smart_crop_mobile.py --session {session}",
        )
    add(checks, "mobile scene PNGs", "pass", f"{len(ids)} mobile PNG(s)")

    mobile_audit_path = session_dir / "working" / "mobile-crop-audit.json"
    mobile_audit, mobile_audit_err = read_json(mobile_audit_path)
    if mobile_audit_err:
        add(checks, "mobile crop audit", "fail", mobile_audit_err)
        blockers.append("Mobile crop audit is missing or invalid.")
        return report(
            "A.1-3 - mobile crop audit",
            "Run the mobile crop audit before export.",
            f"scripts/audit_mobile_crops.py --session {session}",
        )
    broken, skipped, total = mobile_audit_counts(mobile_audit)
    if broken:
        add(checks, "mobile crop audit", "fail", f"{broken} broken, {skipped} skipped, {total} total")
        blockers.append("Mobile crop audit has broken chunks; export is blocked.")
        return report(
            "A.1-4 - fix failed crops only",
            "Fix only chunks flagged by mobile-crop-audit.json, then rerun the audit.",
            f"scripts/audit_mobile_crops.py --session {session}",
        )
    add(checks, "mobile crop audit", "pass", f"0 broken, {skipped} skipped, {total} total")

    mobile_mp4s, mobile_srts, mobile_thumbs = mobile_outputs(session_dir)
    if not mobile_mp4s:
        add(checks, "mobile mp4s", "fail", "none found")
        blockers.append("Mobile export is missing.")
        return report(
            "A.1-6 - mobile stitch/export",
            "Export mobile MP4s after crop audit passes.",
            f"scripts/mobile_export.py --session {session}",
        )
    add(checks, "mobile mp4s", "pass", f"{len(mobile_mp4s)} mp4(s)")

    if not mobile_srts:
        add(checks, "mobile SRTs", "fail", "none found")
        blockers.append("Per-part mobile SRTs are missing.")
        return report(
            "A.1-10 - per-part SRTs",
            "Rerun mobile export in split/final mode so per-part SRTs are produced.",
            f"scripts/mobile_export.py --session {session}",
        )
    add(checks, "mobile SRTs", "pass", f"{len(mobile_srts)} SRT file(s)")

    if not mobile_thumbs:
        add(checks, "mobile thumbnails", "fail", "none found")
        blockers.append("Mobile thumbnails are missing.")
        return report(
            "A.1-9 - thumbnail per part",
            "Generate mobile thumbnails from working/thumbnail-prompt.md.",
            f"scripts/mobile_thumbnails.py --session {session}",
        )
    add(checks, "mobile thumbnails", "pass", f"{len(mobile_thumbs)} thumbnail file(s)")

    publish_audit = REPO_ROOT / "scripts" / "audit_mobile_publish.py"
    if not publish_audit.exists():
        add(checks, "mobile publish audit", "warn", "scripts/audit_mobile_publish.py not implemented")
        warnings.append("A.1 final publish gate is still planned, not enforced.")
        return report(
            "A.1-11 - final audit missing implementation",
            "Implement audit_mobile_publish.py before trusting final mobile publish readiness.",
            None,
        )

    publish_audit_path = session_dir / "working" / "mobile-publish-audit.json"
    publish_payload, publish_err = read_json(publish_audit_path)
    if publish_err:
        add(checks, "mobile publish audit", "fail", publish_err)
        blockers.append("Final mobile publish audit has not passed.")
        return report(
            "A.1-11 - final audit",
            "Run the final mobile publish audit before platform upload.",
            f"scripts/audit_mobile_publish.py --session {session}",
        )
    if not publish_payload.get("passed"):
        failures = publish_payload.get("failure_count", "?")
        add(checks, "mobile publish audit", "fail", f"{failures} failure(s)")
        blockers.append("Final mobile publish audit is failing.")
        return report(
            "A.1-11 - final audit",
            "Fix mobile publish audit failures.",
            f"scripts/audit_mobile_publish.py --session {session}",
        )
    add(checks, "mobile publish audit", "pass", "working/mobile-publish-audit.json")

    return report(
        "A.1-12 - ready to publish per part",
        "Upload the audited mobile parts to the target platforms.",
        None,
    )


def print_report(report: Report) -> None:
    print(f"=== illustration-chunk-remotion audit: {report.session} ===")
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
    parser = argparse.ArgumentParser(
        description="Audit current stage for illustration-chunk-remotion sessions under spoolcast-content/sessions/<id>."
    )
    parser.add_argument("--session", required=True)
    parser.add_argument(
        "--target",
        choices=("auto", "widescreen", "mobile"),
        default="auto",
        help="Which branch to evaluate after widescreen render passes.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON for UI/tools.")
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
