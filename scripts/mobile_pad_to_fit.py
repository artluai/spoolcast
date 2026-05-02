#!/usr/bin/env python3
"""mobile_pad_to_fit.py — scale a widescreen scene to fit 9:16 with per-chunk
sampled pad color.

For each chunk:
  1. Resolve the source PNG (chunk's image_path in shot-list).
  2. Sample the source's edge pixels (4 corners + 4 mid-edges, 5x5 block each)
     and pick the median color.
  3. Scale source to fit 1080-wide inside a 1080x1920 canvas, pad top/bottom
     with the sampled color.
  4. Write to source/generated-assets/scenes/mobile/<chunk>-mobile.png.

Free — PIL + ffmpeg, no kie.ai spend. Use when audit_mobile_crops.py flags a
chunk for "edges clipped" (composition is sound, just doesn't fit the crop box).
For composition-failure flags, use batch_scenes.py --mobile-variant instead.

Usage:
  scripts/.venv/bin/python scripts/mobile_pad_to_fit.py \\
      --session spoolcast-dev-log-04 \\
      --only C7,C23,C28,C49,C50,C58
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except ImportError:
    print("[pad-to-fit] PIL not available. Install: pip install Pillow", file=sys.stderr)
    sys.exit(1)

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"
MOBILE_W = 1080
MOBILE_H = 1920


def _sample_edge_color(png_path: Path) -> str:
    """Return a hex color string sampled from the image's edges."""
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    # 5x5 block at each of 8 edge positions: 4 corners + 4 mid-edges.
    block = 5
    positions = [
        (0, 0), (w - block, 0), (0, h - block), (w - block, h - block),
        (w // 2 - 2, 0), (w // 2 - 2, h - block),
        (0, h // 2 - 2), (w - block, h // 2 - 2),
    ]
    pixels: list[tuple[int, int, int]] = []
    for x, y in positions:
        crop = img.crop((x, y, x + block, y + block))
        for px in crop.getdata():
            pixels.append(px)
    # Median per channel — robust to one-off bright pixels.
    r = int(statistics.median(p[0] for p in pixels))
    g = int(statistics.median(p[1] for p in pixels))
    b = int(statistics.median(p[2] for p in pixels))
    return f"#{r:02x}{g:02x}{b:02x}"


def _resolve_source(session_id: str, chunk: dict) -> Path | None:
    """Find the source PNG for a chunk: image_path > scenes/<id>.png fallback."""
    session_dir = CONTENT_ROOT / "sessions" / session_id
    img_path = chunk.get("image_path", "")
    if img_path:
        p = session_dir / img_path
        if p.exists():
            return p
    fallback = session_dir / "source" / "generated-assets" / "scenes" / f"{chunk['id']}.png"
    if fallback.exists():
        return fallback
    return None


def _fit_height(src_path: Path) -> int:
    """Compute the scaled height when source is fit to MOBILE_W width."""
    img = Image.open(src_path)
    w, h = img.size
    return round(MOBILE_W * h / w)


def pad_to_fit(session_id: str, chunk_ids: list[str]) -> int:
    session_dir = CONTENT_ROOT / "sessions" / session_id
    shot_list = json.loads((session_dir / "shot-list" / "shot-list.json").read_text())
    chunks_by_id = {c["id"]: c for c in shot_list.get("chunks", [])}

    out_dir = session_dir / "source" / "generated-assets" / "scenes" / "mobile"
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for cid in chunk_ids:
        chunk = chunks_by_id.get(cid)
        if not chunk:
            print(f"  {cid:5} → MISSING chunk in shot-list")
            failures += 1
            continue
        src = _resolve_source(session_id, chunk)
        if not src:
            print(f"  {cid:5} → MISSING source PNG")
            failures += 1
            continue

        color = _sample_edge_color(src)
        fit_h = _fit_height(src)
        pad_y = (MOBILE_H - fit_h) // 2
        out = out_dir / f"{cid}-mobile.png"

        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf",
            f"scale={MOBILE_W}:{fit_h}:force_original_aspect_ratio=decrease,"
            f"pad={MOBILE_W}:{MOBILE_H}:0:{pad_y}:{color}",
            str(out),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  {cid:5} → resized | pad={color} | src={src.name}")
        else:
            print(f"  {cid:5} → ffmpeg FAILED | {r.stderr.strip().splitlines()[-1]}")
            failures += 1
    return failures


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--only", required=True, help="comma-separated chunk ids")
    args = p.parse_args()
    chunk_ids = [c.strip() for c in args.only.split(",") if c.strip()]
    failures = pad_to_fit(args.session, chunk_ids)
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
