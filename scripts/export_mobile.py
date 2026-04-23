#!/usr/bin/env python3
"""export_mobile.py — produce a 9:16 mobile variant of a shipped 16:9 master.

v1 scope (Process A.1, simple path): center-crop the widescreen master to
9:16, scale to 1080x1920, burn captions in a single ffmpeg pass. No
per-chunk `mobile_focal` cropping, no regenerated mobile-variant scenes,
no split-into-parts. Those are later v1 steps that build on this one.

Captions follow the caption-styling reference (SHIPPING.md § Part 3) via
the shared `caption_assets.srt_to_ass` helper — MarginV defaults to 250
for the 1080x1920 frame, which lands text in the mobile thumb zone.

Usage:
  scripts/.venv/bin/python scripts/export_mobile.py \\
      --session spoolcast-dev-log \\
      --in-mp4 .../renders/spoolcast-dev-log-v4e-1.0x.mp4
  # -> writes .../renders/spoolcast-dev-log-v4e-1.0x-mobile-9x16.mp4

Upscale note: widescreen masters today are rendered at 1920x1080, so the
9:16 center-crop (608x1080) has to be upscaled to 1080x1920. Quality is
acceptable for iteration but noticeably softer than native-resolution
mobile output. Rendering the master at 3840x2160 would give a 9:16 crop
of 1215x2160 that downscales cleanly — tracked separately as a future
render-config tweak.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from caption_assets import srt_to_ass

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
FONTS_DIR = REPO_ROOT / "scripts" / "assets" / "fonts"

# 9:16 at the canonical mobile master resolution.
MOBILE_W = 1080
MOBILE_H = 1920


def generate_burn_srt(session: str, srt_out: Path) -> None:
    """Invoke generate_srt.py with --exclude-onscreen-cues."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "generate_srt.py"),
        "--session",
        session,
        "--out",
        str(srt_out),
        "--exclude-onscreen-cues",
    ]
    subprocess.run(cmd, check=True)


def export(
    in_mp4: Path,
    ass_path: Path,
    out_mp4: Path,
) -> None:
    # Crop 16:9 → 9:16 at source height. Width = source height * 9 / 16.
    # Expressed via ffmpeg's filter variables so this adapts to any input
    # resolution (1080, 2160, etc.) without a hardcoded crop-width.
    # crop=W:H:X:Y — W rounded to even (h264 demands even dims).
    # The scale after crop brings us to the canonical 1080x1920 mobile frame.
    # ass consumes our PlayResY=1920 subtitle file with MarginV in frame px.
    vf = (
        "crop=trunc(ih*9/16/2)*2:ih:trunc((iw-ih*9/16)/2):0"
        f",scale={MOBILE_W}:{MOBILE_H}:flags=lanczos"
        f",ass=filename='{ass_path}':fontsdir='{FONTS_DIR}'"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(in_mp4),
        "-vf",
        vf,
        "-c:a",
        "copy",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        str(out_mp4),
    ]
    print(f"[export-mobile] {in_mp4.name} -> {out_mp4.name} (9:16 center-crop + captions)")
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Produce a 9:16 mobile variant of a shipped 16:9 master.")
    p.add_argument("--session", required=True, help="session id")
    p.add_argument("--rate", default="1.0", help="playback rate of the master (1.0 or 1.15)")
    p.add_argument("--srt", default=None, help="override: use this pre-existing burn SRT instead of regenerating")
    p.add_argument("--in-mp4", default=None, help="override: input 16:9 master path")
    p.add_argument("--out", default=None, help="override: output mp4 path")
    p.add_argument("--font-size", type=int, default=110, help="caption Fontsize (default 110 scaled for 1080x1920 mobile)")
    p.add_argument(
        "--margin-v",
        type=int,
        default=250,
        help="MarginV in px from bottom (default 250 — lands captions in mobile thumb zone on 1080x1920)",
    )
    args = p.parse_args()

    session_dir = CONTENT_ROOT / "sessions" / args.session
    renders_dir = session_dir / "renders"
    # A.1 mobile outputs land under renders/mobile/ so they stay conceptually
    # "renders" but are isolated from the A (widescreen) deliverables.
    mobile_renders_dir = renders_dir / "mobile"
    mobile_renders_dir.mkdir(parents=True, exist_ok=True)
    working_dir = session_dir / "working"
    working_dir.mkdir(parents=True, exist_ok=True)

    in_mp4 = Path(args.in_mp4) if args.in_mp4 else renders_dir / f"{args.session}-{args.rate}x.mp4"
    if not in_mp4.exists():
        print(f"ERROR: master mp4 not found at {in_mp4}", file=sys.stderr)
        sys.exit(1)

    if args.srt:
        srt_path = Path(args.srt)
        if not srt_path.exists():
            print(f"ERROR: --srt path does not exist: {srt_path}", file=sys.stderr)
            sys.exit(1)
    else:
        srt_path = working_dir / f"{args.session}-{args.rate}x-burn.srt"
        generate_burn_srt(args.session, srt_path)

    out_mp4 = Path(args.out) if args.out else mobile_renders_dir / f"{args.session}-{args.rate}x-mobile-9x16.mp4"

    if not (FONTS_DIR / "Caveat-Bold.ttf").exists():
        print(
            f"ERROR: Caveat-Bold.ttf missing at {FONTS_DIR}. "
            "Re-run the font bundling step (see SHIPPING.md § Part 3 Prerequisites).",
            file=sys.stderr,
        )
        sys.exit(1)

    ass_path = working_dir / f"{args.session}-{args.rate}x-mobile-9x16.ass"
    cue_count = srt_to_ass(
        srt_path=srt_path,
        ass_path=ass_path,
        play_res_x=MOBILE_W,
        play_res_y=MOBILE_H,
        font_size=args.font_size,
        margin_v=args.margin_v,
    )
    print(f"[ass] wrote {cue_count} cues to {ass_path} (PlayRes {MOBILE_W}x{MOBILE_H}, MarginV {args.margin_v})")

    export(in_mp4=in_mp4, ass_path=ass_path, out_mp4=out_mp4)
    print(f"[export-mobile] wrote {out_mp4}")


if __name__ == "__main__":
    main()
