#!/usr/bin/env python3
"""Fetch a meme gif from a URL, convert to mp4, save to a session's memes dir.

Usage:
    fetch_meme_clip.py --session <id> --url <gif-url> --name <basename>

Example:
    fetch_meme_clip.py --session spoolcast-dev-log-04 \\
        --url https://media.tenor.com/.../picard-face-palm.gif \\
        --name meme-picard

Result: source/fetched-assets/memes/<name>.mp4 with libx264 / yuv420p / faststart,
even-pixel scaling (Remotion-friendly).

Why this exists: animated memes deliver the meme experience; static screenshots
of animated memes don't. behavior.md §0a + STORY.md § 5b-2 (when sourcing memes,
prefer animated when the canonical form is animated). This script collapses the
download+convert friction so animated stays the default, not the exception.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--url", required=True, help="direct .gif (or .mp4) URL — tenor / giphy / kym CDN")
    p.add_argument(
        "--name",
        required=True,
        help="basename WITHOUT extension. Final file: source/fetched-assets/memes/<name>.mp4",
    )
    args = p.parse_args()

    session_dir = CONTENT_ROOT / "sessions" / args.session
    if not session_dir.exists():
        print(f"ERROR: session {args.session} not found at {session_dir}", file=sys.stderr)
        return 2
    out_dir = session_dir / "source" / "fetched-assets" / "memes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"{args.name}.mp4"

    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    print(f"[fetch-meme] downloading {args.url}")
    req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tmp_path.write_bytes(resp.read())
    except Exception as e:
        print(f"[fetch-meme] download failed: {e}", file=sys.stderr)
        return 1

    if tmp_path.stat().st_size < 1024:
        print(f"[fetch-meme] downloaded file is suspiciously small ({tmp_path.stat().st_size} bytes)", file=sys.stderr)
        return 1

    # Probe the filetype — accept gif, mp4, webm. Reject HTML.
    head = tmp_path.read_bytes()[:8]
    if head[:3] == b"GIF":
        kind = "gif"
    elif head[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c", b"\x00\x00\x00 "):
        kind = "mp4"
    elif head[:4] == b"\x1aE\xdf\xa3":
        kind = "webm"
    else:
        # Likely HTML / 404 page
        print(f"[fetch-meme] downloaded file is not a recognized media format (first 8 bytes: {head!r}); URL probably returned HTML/404", file=sys.stderr)
        return 1

    print(f"[fetch-meme] detected {kind}, converting → mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(tmp_path),
        "-movflags", "faststart",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        str(out_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[fetch-meme] ffmpeg failed:\n{result.stderr[-500:]}", file=sys.stderr)
        return 1

    tmp_path.unlink(missing_ok=True)
    size = out_mp4.stat().st_size
    print(f"[fetch-meme] wrote {out_mp4} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
