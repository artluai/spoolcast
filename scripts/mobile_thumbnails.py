#!/usr/bin/env python3
"""mobile_thumbnails.py — generate per-part mobile thumbnails for an A.1 export.

Per SHIPPING.md § Mobile thumbnail (A.1):
  - 1080×1920 full-screen, no letterbox
  - Per-part (split into N parts → N thumbnails)
  - Title baked in: Caveat Bold ~140px
  - Part indicator baked in: Montserrat Black ~60px
  - File naming: renders/mobile/<session>-mobile-thumb-pt<n>of<total>.png

Default flow (option a per spec): generate ONE 9:16 base via kie.ai, composite
title + part badge for each part. Use `--base <path>` to skip the kie call and
re-use an existing image.

Usage:
  scripts/.venv/bin/python scripts/mobile_thumbnails.py \\
      --session spoolcast-dev-log-04 \\
      --title "The bug an AI couldn't catch"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ImportError:
    print("[mobile-thumb] PIL not available. Install: pip install Pillow", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kie_client import KieClient, build_input_for_model  # noqa: E402

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"
FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

W, H = 1080, 1920
TITLE_SIZE = 140
PART_SIZE = 60
TITLE_FONT = FONTS_DIR / "Caveat-Bold.ttf"
PART_FONT = FONTS_DIR / "Montserrat-Black.ttf"

# Mobile prompt suffix appended to the persisted widescreen prompt. Forces 9:16
# aspect + grid-safe composition + no baked headline (PIL composites the title).
MOBILE_SUFFIX = (
    "\n\nMOBILE ADAPTATION: render this in 9:16 vertical portrait composition "
    "(not 16:9 widescreen). The figure + central focal element occupy the upper "
    "70% of the frame (grid-safe area). DO NOT bake any headline text into the "
    "image — the title overlay is composited separately. Skip the brush-lettering "
    "headline and red brushstroke underline that the widescreen prompt requests."
)

# Fallback prompt — used only when working/thumbnail-prompt.md does not exist.
# Real sessions should persist their widescreen prompt; this is the safety net.
DEFAULT_PROMPT = (
    # noir-debug template (verbatim from SHIPPING.md registry):
    "Gritty black-and-white graphic novel / ink illustration. Heavy "
    "crosshatching, bold shadows, high contrast, sharp ink lines, cinematic "
    "desk lighting, dramatic noir atmosphere. Mostly pure black and white "
    "with only selective red accents. Bold distressed brush-lettering "
    "headline across the top; red brushstroke underline beneath the headline. "
    "Composition clean and thumbnail-readable, central subject, slightly "
    "ominous tone. STYLE NOTES: this is a stark zine / woodcut / graphic-"
    "novel aesthetic with thick distressed ink lines and dramatic dark "
    "shadows — NOT soft cel-shading, NOT realistic illustration, NOT anime "
    "rendering. Heavy black areas dominate; whites are bright; mid-tones "
    "are minimal. "
    # Scene-specific block (this video):
    "Scene: 9:16 vertical portrait composition. A tired hooded programmer "
    "sits at a cluttered desk in a dark debugging room, staring forward "
    "with a serious exhausted expression. He holds a magnifying glass in "
    "both hands at chest height; inside the lens is a vivid bright red "
    "cartoon bug — the focal point. Cluttered desk with code-filled "
    "monitor, desk lamp, open notebook with handwritten code, coffee mug, "
    "sticky notes, programming books. The figure + magnifying glass occupy "
    "the upper 70% of the frame (grid-safe area). NO baked-in headline "
    "text — title overlay is composited separately. Punchy, engaging, "
    "slightly ominous."
)


def detect_num_parts(session_id: str) -> int:
    """Count existing mobile parts from renders/mobile/."""
    mobile_dir = CONTENT_ROOT / "sessions" / session_id / "renders" / "mobile"
    if not mobile_dir.exists():
        raise FileNotFoundError(f"no mobile renders dir at {mobile_dir}")
    parts: set[int] = set()
    for f in mobile_dir.glob(f"{session_id}-mobile-pt*of*.mp4"):
        m = re.search(r"-pt(\d+)of(\d+)\.mp4$", f.name)
        if m:
            parts.add(int(m.group(2)))
    if not parts:
        raise FileNotFoundError(f"no mobile parts found in {mobile_dir}")
    if len(parts) > 1:
        raise RuntimeError(f"inconsistent part totals found: {parts}")
    return parts.pop()


def _session_anchor_url(session_id: str) -> str | None:
    cfg_path = CONTENT_ROOT / "sessions" / session_id / "session.json"
    if not cfg_path.exists():
        return None
    style_name = (json.loads(cfg_path.read_text()).get("style") or "").strip()
    if not style_name:
        return None
    style_path = CONTENT_ROOT / "styles" / style_name / "style.json"
    if not style_path.exists():
        return None
    return (json.loads(style_path.read_text()).get("anchor") or {}).get("image_url")


def generate_base(session_id: str, prompt: str, out_path: Path, *, use_anchor: bool = False) -> None:
    """Call kie.ai for a 9:16 base image. Default prompt-only per spec; pass
    use_anchor=True to also pass the session style anchor as image_ref."""
    client = KieClient()
    if use_anchor:
        anchor_url = _session_anchor_url(session_id)
        if not anchor_url:
            print("[mobile-thumb] WARN: --use-anchor requested but no session anchor found; falling back to prompt-only", flush=True)
            use_anchor = False
    if use_anchor:
        model = "gpt-image-2-image-to-image"
        input_dict = build_input_for_model(
            model,
            prompt=prompt,
            quality="1K",
            image_refs=[anchor_url],
            aspect_ratio="9:16",
            output_format="png",
        )
        print(f"[mobile-thumb] submitting kie model={model} aspect=9:16 anchor=on", flush=True)
    else:
        model = "gpt-image-2-text-to-image"
        input_dict = build_input_for_model(
            model,
            prompt=prompt,
            quality="1K",
            aspect_ratio="9:16",
            output_format="png",
        )
        print(f"[mobile-thumb] submitting kie model={model} aspect=9:16 (prompt-only)", flush=True)
    task_id = client.submit_task(model=model, input_dict=input_dict)
    print(f"[mobile-thumb] task: {task_id}", flush=True)
    result = client.poll_task(task_id)
    if not result.result_urls:
        raise RuntimeError(f"kie returned no urls (failCode={result.fail_code} failMsg={result.fail_msg})")
    req = urllib.request.Request(
        result.result_urls[0],
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
        f.write(resp.read())
    print(f"[mobile-thumb] base -> {out_path} ({out_path.stat().st_size} bytes)", flush=True)


def scale_to_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize + center-crop to fill (target_w, target_h)."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = round(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = round(target_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def composite_part(
    base: Image.Image,
    title: str,
    part_n: int,
    total: int,
    out_path: Path,
) -> None:
    canvas = base.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(str(TITLE_FONT), TITLE_SIZE)
    part_font = ImageFont.truetype(str(PART_FONT), PART_SIZE)

    # Title positioning: lower portion of grid-safe area (top ~70% = upper 1344px).
    # Place title with bottom edge ~y=1300 so it sits inside grid-safe.
    # Wrap title if it exceeds canvas width.
    margin_x = 60
    max_text_w = W - 2 * margin_x

    def wrap(text: str, font: ImageFont.FreeTypeFont) -> list[str]:
        words = text.split()
        lines: list[str] = []
        cur: list[str] = []
        for w in words:
            trial = (" ".join(cur + [w])).strip()
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] > max_text_w and cur:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))
        return lines

    title_lines = wrap(title, title_font)
    line_h = TITLE_SIZE + 10
    title_block_h = line_h * len(title_lines)
    part_text = f"PART {part_n} OF {total}"
    part_bbox = draw.textbbox((0, 0), part_text, font=part_font)
    part_h = part_bbox[3] - part_bbox[1]
    part_w = part_bbox[2] - part_bbox[0]

    # Position part badge above the title block. Anchor block bottom at y=1280.
    block_bottom_y = 1280
    spacing = 24
    title_top_y = block_bottom_y - title_block_h
    part_y = title_top_y - spacing - part_h

    # Translucent dark band behind the text for legibility regardless of base.
    band_padding_y = 30
    band_top = part_y - band_padding_y
    band_bottom = block_bottom_y + band_padding_y
    band = Image.new("RGBA", (W, band_bottom - band_top), (0, 0, 0, 140))
    canvas.paste(band, (0, band_top), band)

    # Draw part badge (centered).
    draw.text(((W - part_w) // 2, part_y), part_text, font=part_font, fill="#ff3b3b")

    # Draw title (centered, multi-line).
    y = title_top_y
    for line in title_lines:
        bb = draw.textbbox((0, 0), line, font=title_font)
        line_w = bb[2] - bb[0]
        draw.text(((W - line_w) // 2, y), line, font=title_font, fill="white")
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    print(f"[mobile-thumb] pt{part_n}of{total} -> {out_path}", flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--num-parts", type=int, default=None,
                   help="default: auto-detect from existing renders/mobile/*.mp4")
    p.add_argument("--base", default=None,
                   help="path to existing base image (skip kie call)")
    p.add_argument("--prompt", default=None,
                   help="override prompt (default: read working/thumbnail-prompt.md)")
    p.add_argument("--use-anchor", action="store_true",
                   help="pass session style anchor as image_ref (default: prompt-only)")
    args = p.parse_args()

    session_dir = CONTENT_ROOT / "sessions" / args.session
    mobile_dir = session_dir / "renders" / "mobile"

    n = args.num_parts or detect_num_parts(args.session)
    print(f"[mobile-thumb] {args.session}: {n} parts")

    # Resolve prompt: CLI override > persisted widescreen prompt > fallback.
    if args.prompt:
        prompt_body = args.prompt
        prompt_src = "--prompt"
    else:
        persisted = session_dir / "working" / "thumbnail-prompt.md"
        if persisted.exists():
            text = persisted.read_text()
            # Strip a top markdown heading block + its intro paragraph: take the
            # last "---" separated section as the actual prompt body.
            sections = [s.strip() for s in text.split("---") if s.strip()]
            prompt_body = sections[-1] if sections else text.strip()
            prompt_src = "working/thumbnail-prompt.md"
        else:
            prompt_body = DEFAULT_PROMPT
            prompt_src = "DEFAULT_PROMPT (fallback)"
    full_prompt = prompt_body + MOBILE_SUFFIX
    print(f"[mobile-thumb] prompt source: {prompt_src}")

    # Resolve base.
    if args.base:
        base_path = Path(args.base)
        if not base_path.is_absolute():
            base_path = session_dir / base_path
    else:
        base_path = mobile_dir / f"{args.session}-mobile-thumb-base.png"
        if not base_path.exists():
            generate_base(args.session, full_prompt, base_path, use_anchor=args.use_anchor)
        else:
            print(f"[mobile-thumb] reusing existing base: {base_path.name}")

    base_img = Image.open(base_path)
    base_img = scale_to_cover(base_img, W, H)

    for i in range(1, n + 1):
        out = mobile_dir / f"{args.session}-mobile-thumb-pt{i}of{n}.png"
        composite_part(base_img, args.title, i, n, out)

    print(f"[mobile-thumb] done. {n} thumbnails in {mobile_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
