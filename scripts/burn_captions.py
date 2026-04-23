#!/usr/bin/env python3
"""burn_captions.py — burn styled captions into a spoolcast master MP4.

Reads the session's rendered master, regenerates the SRT with
`--exclude-onscreen-cues` (so the burned captions don't duplicate text
already rendered in the frame), converts it to an ASS file with an explicit
PlayResX/PlayResY matching the target frame (so MarginV values are in frame
pixel space, not libass's SRT-default coordinate space), and invokes
ffmpeg's `ass` filter.

Why ASS not SRT: when you pass an SRT through the `subtitles` filter with
`force_style`, libass uses its internal default reference resolution
(~288 tall). MarginV=80 in that space projects to ~27% up from the bottom
of a 1080 frame, not the intended 7%. Writing a real ASS file with
`PlayResY=<frame_height>` puts MarginV in frame-pixel units directly.

Fonts are bundled at `scripts/assets/fonts/` and loaded via `fontsdir=`.

Usage:
  scripts/.venv/bin/python scripts/burn_captions.py \\
      --session spoolcast-dev-log
  # -> writes renders/spoolcast-dev-log-1.0x-captioned.mp4

  scripts/.venv/bin/python scripts/burn_captions.py \\
      --session spoolcast-dev-log --rate 1.15 --margin-v 250 \\
      --frame-size 1080x1920
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


def burn(in_mp4: Path, ass_path: Path, out_mp4: Path) -> None:
    # The `ass` filter (not `subtitles`) consumes our ASS file directly with
    # its embedded PlayResX/Y; no coordinate remapping or force_style needed.
    vf = f"ass=filename='{ass_path}':fontsdir='{FONTS_DIR}'"
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
    print(f"[burn] {in_mp4.name} + captions -> {out_mp4.name}")
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Burn styled captions into a spoolcast master MP4.")
    p.add_argument("--session", required=True, help="session id")
    p.add_argument("--rate", default="1.0", help="playback rate of the master to burn (1.0 or 1.15)")
    p.add_argument("--srt", default=None, help="override: use this pre-existing SRT instead of regenerating")
    p.add_argument("--in-mp4", default=None, help="override: input mp4 path")
    p.add_argument("--out", default=None, help="override: output mp4 path")
    p.add_argument("--font-size", type=int, default=80, help="caption Fontsize (default 80 — bumped from 56 for mobile legibility)")
    p.add_argument(
        "--margin-v",
        type=int,
        default=80,
        help="MarginV in pixels from bottom (default 80 for 1920x1080; use 250 for 1080x1920 mobile)",
    )
    p.add_argument(
        "--frame-size",
        default="1920x1080",
        help="target frame WxH — drives ASS PlayResX/PlayResY (default 1920x1080; use 1080x1920 for 9:16 mobile)",
    )
    args = p.parse_args()

    session_dir = CONTENT_ROOT / "sessions" / args.session
    renders_dir = session_dir / "renders"
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

    out_mp4 = Path(args.out) if args.out else renders_dir / f"{args.session}-{args.rate}x-captioned.mp4"

    if not FONTS_DIR.exists() or not (FONTS_DIR / "Caveat-Bold.ttf").exists():
        print(
            f"ERROR: Caveat-Bold.ttf missing at {FONTS_DIR}. "
            "Re-run the font bundling step (see SHIPPING.md § Part 3 Prerequisites).",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        play_res_x_str, play_res_y_str = args.frame_size.lower().split("x")
        play_res_x = int(play_res_x_str)
        play_res_y = int(play_res_y_str)
    except Exception:
        print(f"ERROR: --frame-size must be WxH (e.g. 1920x1080), got {args.frame_size!r}", file=sys.stderr)
        sys.exit(1)

    ass_path = working_dir / f"{args.session}-{args.rate}x-burn.ass"
    cue_count = srt_to_ass(
        srt_path=srt_path,
        ass_path=ass_path,
        play_res_x=play_res_x,
        play_res_y=play_res_y,
        font_size=args.font_size,
        margin_v=args.margin_v,
    )
    print(f"[ass] wrote {cue_count} cues to {ass_path} (PlayRes {play_res_x}x{play_res_y}, MarginV {args.margin_v})")

    burn(in_mp4=in_mp4, ass_path=ass_path, out_mp4=out_mp4)
    print(f"[burn] wrote {out_mp4}")


if __name__ == "__main__":
    main()
