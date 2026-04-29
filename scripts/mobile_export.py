#!/usr/bin/env python3
"""mobile_export.py — A.1 mobile export pipeline (1080x1920).

Replaces the v1 simple-crop `export_mobile.py` with the full Part 4 pipeline
per SHIPPING.md. For each chunk, resolves a mobile-native visual asset
(scenes/mobile/<chunk>-mobile.png for generated/meme/broll; PIL-rendered
title card for bumpers), concatenates per-chunk video clips at the
durations from preview-data.json, mixes the widescreen master's audio
track, and burns captions + watermarks + optional part badge via libass.

Supports split-into-parts mode for TikTok/Reels/Shorts.

Usage:
  scripts/.venv/bin/python scripts/mobile_export.py \\
      --session spoolcast-dev-log-02 \\
      [--split-duration 100] \\
      [--title "How I caught AI lying"]

Outputs under sessions/<session>/renders/mobile/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: scripts/.venv/bin/pip install Pillow", file=sys.stderr)
    sys.exit(3)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
FONTS_DIR = REPO_ROOT / "scripts" / "assets" / "fonts"

# Canvas + paper-color constants shared across bumper render + letterbox pad.
MOBILE_W = 1080
MOBILE_H = 1920
PAPER_BG = (240, 225, 202)     # off-white paper sampled from wojak-gpt2 bumpers
PAPER_INK = (30, 28, 26)       # near-black ink


# ---------- asset resolution -------------------------------------------------

def chunk_mobile_png(session_dir: Path, chunk_id: str) -> Path:
    return session_dir / "source" / "generated-assets" / "scenes" / "mobile" / f"{chunk_id}-mobile.png"


def render_bumper_card(title: str, out_path: Path) -> None:
    """PIL-render a clean text-only title card at 1080x1920.

    Off-white paper background + centered bold text in Caveat Bold.
    Used for bumper chunks per SHIPPING Part 4 (mobile bumpers need their
    own render — widescreen bumper cropped to 9:16 clips title text).
    """
    img = Image.new("RGB", (MOBILE_W, MOBILE_H), PAPER_BG)
    draw = ImageDraw.Draw(img)

    # Caveat Bold scales well. Aim for title width ~75% of canvas.
    font_path = FONTS_DIR / "Caveat-Bold.ttf"
    # Auto-size: start big, shrink until fits.
    fontsize = 360
    min_size = 120
    max_width = int(MOBILE_W * 0.8)
    while fontsize > min_size:
        font = ImageFont.truetype(str(font_path), fontsize)
        bbox = draw.textbbox((0, 0), title, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_width:
            break
        fontsize -= 10
    else:
        font = ImageFont.truetype(str(font_path), min_size)
        bbox = draw.textbbox((0, 0), title, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

    x = (MOBILE_W - w) // 2 - bbox[0]
    y = (MOBILE_H - h) // 2 - bbox[1]
    draw.text((x, y), title, fill=PAPER_INK, font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")


def resolve_chunk_asset(chunk: dict[str, Any], session_dir: Path, tmp_dir: Path) -> Path:
    """Return a 1080x1920 PNG for the chunk's mobile visual.

    - boundary_kind=bumper  → PIL-render title card
    - everything else       → scenes/mobile/<chunk>-mobile.png (must exist)
    """
    cid = chunk.get("id", "?")
    if chunk.get("boundary_kind") == "bumper":
        title = chunk.get("act_title") or (chunk.get("on_screen_text") or [""])[0] or cid
        out = tmp_dir / f"{cid}-bumper.png"
        render_bumper_card(title, out)
        return out
    mobile_png = chunk_mobile_png(session_dir, cid)
    if not mobile_png.exists():
        raise FileNotFoundError(f"{cid}: mobile asset missing at {mobile_png}")
    return mobile_png


# ---------- clip build + concat ---------------------------------------------

def build_clip(asset_png: Path, duration_sec: float, out_mp4: Path, fps: int = 30) -> None:
    """Loop a still PNG for duration_sec, write a silent mp4 at 1080x1920."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", f"{duration_sec:.3f}",
        "-i", str(asset_png),
        "-vf", f"scale={MOBILE_W}:{MOBILE_H}:force_original_aspect_ratio=decrease,pad={MOBILE_W}:{MOBILE_H}:(ow-iw)/2:(oh-ih)/2:color=black",
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-an",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def build_paint_clip(
    asset_png: Path,
    duration_sec: float,
    out_mp4: Path,
    work_dir: Path,
    chunk_id: str,
    fps: int = 30,
    reveal_dur_sec: float = 1.5,
) -> None:
    """Paint-on reveal then hold. Extracts 1:1 content from a 1080x1920
    letterboxed mobile PNG, runs stroke_reveal to produce a paint-on
    sequence, then ffmpeg builds the chunk clip with the reveal followed
    by a held final frame for the remaining duration. Black letterbox
    bars are added back at composite time so the final frame is 1080x1920.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    chunk_work = work_dir / "reveal" / chunk_id
    chunk_work.mkdir(parents=True, exist_ok=True)

    # 1. Extract the 1080x1080 1:1 content from the 1080x1920 mobile PNG.
    content_png = chunk_work / "content.png"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(asset_png),
         "-vf", "crop=1080:1080:0:420",
         "-frames:v", "1", "-update", "1", str(content_png)],
        check=True, capture_output=True,
    )

    # 2. Generate paint-on frames via stroke_reveal.py at 1080x1080.
    frames_dir = chunk_work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(REPO_ROOT / "scripts" / ".venv" / "bin" / "python"),
         str(REPO_ROOT / "scripts" / "stroke_reveal.py"),
         "--input", str(content_png),
         "--output", str(frames_dir),
         "--fps", str(fps),
         "--duration", f"{reveal_dur_sec}",
         "--strategy", "center-out"],
        check=True, capture_output=True,
    )

    # 3. Build chunk mp4: paint frames at the start + tpad-cloned final frame
    #    extending to the chunk's full duration. Pad each frame from 1080x1080
    #    to 1080x1920 with black bars.
    hold_dur = max(0.0, duration_sec - reveal_dur_sec)
    vf = (
        f"pad={MOBILE_W}:{MOBILE_H}:0:420:color=black,"
        f"tpad=stop_mode=clone:stop_duration={hold_dur:.3f}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%04d.png"),
        "-vf", vf,
        "-t", f"{duration_sec:.3f}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-an",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_clips(clip_paths: list[Path], out_mp4: Path) -> None:
    """Concat a list of mp4 clips via ffmpeg concat demuxer."""
    list_file = out_mp4.parent / "concat-list.txt"
    list_file.write_text("".join(f"file '{p}'\n" for p in clip_paths))
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def mux_audio_from_master(video_mp4: Path, master_mp4: Path, out_mp4: Path) -> None:
    """Copy the master widescreen's audio track onto the mobile video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_mp4),
        "-i", str(master_mp4),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def burn_ass(in_mp4: Path, ass_path: Path, out_mp4: Path) -> None:
    """Burn an ASS file (captions + watermarks + part badge) onto a video."""
    vf = f"subtitles={ass_path}:fontsdir={FONTS_DIR}"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_mp4),
        "-vf", vf,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


# ---------- split-into-parts helpers ----------------------------------------


def compute_chunk_ranges(preview: dict[str, Any]) -> list[dict[str, Any]]:
    """Return [{id, start, end, is_meme}] in seconds, in chunk order."""
    fps = int(preview["fps"])
    out: list[dict[str, Any]] = []
    t = 0.0
    for c in preview["chunks"]:
        dur = c["durationFrames"] / fps
        is_meme = (c.get("imageSource") or c.get("image_source") or "") == "meme"
        out.append({"id": c["id"], "start": t, "end": t + dur, "is_meme": is_meme})
        t += dur
    return out


def find_split_indexes(ranges: list[dict[str, Any]], target_sec: float) -> list[int]:
    """Find chunk-end indexes to split AFTER. Returns list of indexes in `ranges`.

    Walks forward, splits at the first chunk whose end ≥ accumulated target.
    Skips splits that land on a meme or immediately before a meme (must keep
    meme + its setup-narration chunk in the same part — see SHIPPING.md
    Part 4 § Split mode + part badge).
    """
    splits: list[int] = []
    next_target = target_sec
    final_end = ranges[-1]["end"]
    for i, r in enumerate(ranges):
        if i == len(ranges) - 1:
            break  # never split on the final chunk's end
        if r["end"] >= next_target:
            # Skip if this chunk is a meme (split would land on/cut the meme)
            # or if the NEXT chunk is a meme (split would orphan the meme from setup).
            nxt = ranges[i + 1] if i + 1 < len(ranges) else None
            if r["is_meme"] or (nxt and nxt["is_meme"]):
                continue
            splits.append(i)
            next_target = r["end"] + target_sec
            if next_target > final_end:
                break
    return splits


def cut_mp4(in_mp4: Path, start_sec: float, end_sec: float, out_mp4: Path) -> None:
    """Cut a clean segment via re-encode (keyframe-accurate)."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-to", f"{end_sec:.3f}",
        "-i", str(in_mp4),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "18",
        "-c:a", "aac",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _parse_srt_ts(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _fmt_srt_ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms >= 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def window_srt(in_srt: Path, start_sec: float, end_sec: float, out_srt: Path) -> int:
    """Filter cues to [start, end] window and rebase to start at 00:00:00.

    Cues straddling the boundary are clipped to the window edges. Returns
    cue count.
    """
    text = in_srt.read_text()
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out_cues: list[str] = []
    out_n = 1
    for b in blocks:
        lines = b.splitlines()
        if len(lines) < 2:
            continue
        # First line is index, second is timestamps "HH:MM:SS,mmm --> HH:MM:SS,mmm"
        ts_line_idx = 1 if "-->" in lines[1] else 0
        ts_line = lines[ts_line_idx]
        body = "\n".join(lines[ts_line_idx + 1:]).strip()
        try:
            t1_str, t2_str = [p.strip() for p in ts_line.split("-->")]
            t1 = _parse_srt_ts(t1_str)
            t2 = _parse_srt_ts(t2_str)
        except (ValueError, IndexError):
            continue
        # Skip cues entirely outside the window.
        if t2 <= start_sec or t1 >= end_sec:
            continue
        # Clip to window, then rebase.
        nt1 = max(0.0, t1 - start_sec)
        nt2 = min(end_sec - start_sec, t2 - start_sec)
        if nt2 <= nt1:
            continue
        out_cues.append(f"{out_n}\n{_fmt_srt_ts(nt1)} --> {_fmt_srt_ts(nt2)}\n{body}")
        out_n += 1
    out_srt.write_text("\n\n".join(out_cues) + ("\n" if out_cues else ""))
    return len(out_cues)


# ---------- pipeline driver --------------------------------------------------

def find_widescreen_master(session_dir: Path, session_id: str) -> Path:
    """Resolve the latest widescreen mp4 for audio mux."""
    renders = session_dir / "renders"
    # Prefer highest-numbered v* render.
    candidates = sorted(renders.glob(f"{session_id}-v*.mp4"))
    if not candidates:
        raise FileNotFoundError(f"no widescreen master found in {renders}")
    return candidates[-1]


def load_preview_data() -> dict[str, Any]:
    path = REPO_ROOT / "src" / "data" / "preview-data.json"
    if not path.exists():
        raise FileNotFoundError(f"preview-data not found at {path}. Run build_preview_data.py first.")
    return json.loads(path.read_text())


def load_shot_list(session_dir: Path) -> dict[str, Any]:
    path = session_dir / "shot-list" / "shot-list.json"
    return json.loads(path.read_text())


def build_unsplit(session_id: str, work_dir: Path, reveal: str = "none") -> Path:
    session_dir = CONTENT_ROOT / "sessions" / session_id
    preview = load_preview_data()
    shot_list = load_shot_list(session_dir)
    shot_by_id = {c["id"]: c for c in shot_list["chunks"]}

    fps = int(preview["fps"])
    master = find_widescreen_master(session_dir, session_id)
    print(f"[mobile] widescreen master: {master}")

    clip_dir = work_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    tmp_assets = work_dir / "tmp-assets"
    tmp_assets.mkdir(parents=True, exist_ok=True)

    clip_paths: list[Path] = []
    for chunk in preview["chunks"]:
        cid = chunk["id"]
        shot_chunk = shot_by_id.get(cid, {})
        merged = {**shot_chunk, **chunk}
        duration_sec = chunk["durationFrames"] / fps
        asset = resolve_chunk_asset(merged, session_dir, tmp_assets)
        clip_path = clip_dir / f"{cid}.mp4"
        # Brush-paint reveal applies to chunks with line-art on white bg
        # (image_source: generated). Skip for proof/SVG charts (16:9 letterbox)
        # and bumpers — those stay static.
        img_src = (shot_chunk.get("image_source") or chunk.get("imageSource") or "generated").strip()
        use_paint = (reveal == "brush-paint" and img_src == "generated")
        if use_paint:
            build_paint_clip(asset, duration_sec, clip_path, work_dir, cid, fps=fps)
            print(f"[mobile] {cid}: {duration_sec:.2f}s  asset={asset.name}  reveal=brush-paint")
        else:
            build_clip(asset, duration_sec, clip_path, fps=fps)
            print(f"[mobile] {cid}: {duration_sec:.2f}s  asset={asset.name}")
        clip_paths.append(clip_path)

    concat_mp4 = work_dir / "concat-silent.mp4"
    concat_clips(clip_paths, concat_mp4)
    print(f"[mobile] concat: {concat_mp4}")

    with_audio = work_dir / "concat-audio.mp4"
    mux_audio_from_master(concat_mp4, master, with_audio)
    print(f"[mobile] muxed audio: {with_audio}")

    return with_audio


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--work-dir", default=None, help="tmp work dir (default: session working/mobile-build/)")
    p.add_argument("--out", default=None, help="final mp4 path (default: session renders/mobile/<session>-mobile.mp4)")
    # Phase 1 scope: no captions, no split, no watermarks yet — deliver the raw concat+audio first for review.
    p.add_argument("--skip-captions", action="store_true", help="write the unsplit concat+audio mp4 without burning captions (for intermediate review)")
    p.add_argument("--title", default=None, help="video title for thumbnails + badges (phase 3)")
    p.add_argument("--split-duration", type=int, default=None, help="split into parts every N seconds at chunk boundaries")
    p.add_argument("--caption-margin-v", type=int, default=None, help="override caption margin_v (top-of-first-line in 1080x1920 px). Default 1300 for 9:16 full-bleed; 1558 for 1:1 / 16:9 mobile letterbox.")
    p.add_argument("--reveal", default="none", choices=["none", "brush-paint"], help="per-chunk entrance reveal. 'brush-paint' runs stroke_reveal.py on the 1:1 content and prepends a 1.5s paint-on animation to each generated chunk before the static hold.")
    p.add_argument("--skip-audit", action="store_true", help="bypass the pre-flight mobile-crop comprehension audit. Use only for intentional preview-only runs; final mobile exports must pass the audit per PIPELINE.md § Audit-gated stage outputs.")
    args = p.parse_args()

    session_dir = CONTENT_ROOT / "sessions" / args.session
    if not session_dir.exists():
        print(f"ERROR: session dir not found: {session_dir}", file=sys.stderr)
        return 2

    # Pre-flight: mobile-crop comprehension audit must pass before producing
    # the mp4. PIPELINE.md § Audit-gated stage outputs.
    if not args.skip_audit:
        audit_path = session_dir / "working" / "mobile-crop-audit.json"
        if not audit_path.exists():
            print(
                f"ERROR: no mobile-crop audit found at {audit_path}.\n"
                f"  Run: scripts/audit_mobile_crops.py --session {args.session}\n"
                f"  Or pass --skip-audit for an intentional preview-only run.",
                file=sys.stderr,
            )
            return 2
        try:
            audit = json.loads(audit_path.read_text())
        except Exception as e:
            print(f"ERROR: could not read mobile-crop audit at {audit_path}: {e}", file=sys.stderr)
            return 2
        broken = [c for c in audit.get("chunks", []) if c.get("broken")]
        if broken:
            print(
                f"ERROR: mobile-crop audit shows {len(broken)} broken chunk(s) — refusing to produce mp4.",
                file=sys.stderr,
            )
            for c in broken:
                cid = c.get("id") or "<unnamed>"
                sev = c.get("severity") or "?"
                reason = c.get("broken_reason") or ""
                print(f"  [{sev:6}] {cid}: {reason}", file=sys.stderr)
            print(
                f"\n  Fix the chunks (regenerate at 9:16 native via batch_scenes.py --mobile-variant\n"
                f"  for illustrations, or re-render produced broll natively), re-run the audit, then\n"
                f"  re-run mobile_export.py. Or pass --skip-audit for an intentional preview-only run.",
                file=sys.stderr,
            )
            return 2

    work_dir = Path(args.work_dir) if args.work_dir else (session_dir / "working" / "mobile-build")
    work_dir.mkdir(parents=True, exist_ok=True)

    out_dir = session_dir / "renders" / "mobile"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else (out_dir / f"{args.session}-mobile.mp4")

    print(f"[mobile] session={args.session} work={work_dir} out={out_path}")

    with_audio = build_unsplit(args.session, work_dir, reveal=args.reveal)

    if args.skip_captions:
        subprocess.run(["cp", str(with_audio), str(out_path)], check=True)
        print(f"\n[mobile] PHASE 1 DELIVERABLE (no captions, no watermarks, no split): {out_path}")
        return 0

    # Phase 2: burn captions + watermarks onto the concat+audio video.
    import sys as _sys
    _sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from caption_assets import srt_to_ass  # type: ignore
    from generate_srt import generate_srt  # type: ignore

    # Generate narration-only SRT (mobile burn-in excludes bracketed on-screen cues).
    srt_path = work_dir / f"{args.session}-burn.srt"
    generate_srt(args.session, srt_path, exclude_onscreen_cues=True)
    print(f"[mobile] wrote burn SRT: {srt_path}")

    # Convert to ASS with mobile layout. margin_v depends on aspect mode:
    #   9:16 full-bleed: 1300 (over-content, above platform UI)
    #   1:1 / 16:9 letterboxed: 1568 (just below image, 25px gap)
    # See SHIPPING.md § Caption position by mobile aspect.
    caption_margin_v = args.caption_margin_v if args.caption_margin_v is not None else 1300

    # Split mode — produce per-part mp4 + SRT, each with its own part badge.
    if args.split_duration is not None:
        preview = load_preview_data()
        ranges = compute_chunk_ranges(preview)
        split_idxs = find_split_indexes(ranges, float(args.split_duration))
        # Build [start, end] for each part using chunk boundaries.
        part_ranges: list[tuple[float, float]] = []
        last_start = 0.0
        for idx in split_idxs:
            split_t = ranges[idx]["end"]
            part_ranges.append((last_start, split_t))
            last_start = split_t
        part_ranges.append((last_start, ranges[-1]["end"]))
        total = len(part_ranges)
        print(f"[mobile] split: {total} parts at {[f'{e:.1f}s' for _, e in part_ranges[:-1]]}")

        for i, (start, end) in enumerate(part_ranges):
            n = i + 1
            label = f"Part {n} of {total}"

            # Window the SRT for this part (also shipped as accessibility caption file).
            per_part_srt = out_dir / f"{args.session}-mobile-pt{n}of{total}.srt"
            cues = window_srt(srt_path, start, end, per_part_srt)
            print(f"[mobile] pt{n}of{total}: {start:.2f}s–{end:.2f}s  ({cues} cues)  srt={per_part_srt.name}")

            # Cut the unburned video to this part's window (re-encoded for clean cut).
            cut_path = work_dir / f"part-{n}of{total}-cut.mp4"
            cut_mp4(with_audio, start, end, cut_path)

            # Build per-part ASS with its own Part N badge, captions windowed/rebased.
            per_part_ass = work_dir / f"{args.session}-pt{n}of{total}.ass"
            srt_to_ass(
                per_part_srt, per_part_ass,
                play_res_x=MOBILE_W, play_res_y=MOBILE_H,
                font_size=72, margin_v=caption_margin_v,
                watermark=True,
                part_label=label,
            )

            # Burn captions + chrome onto this part.
            part_out = out_dir / f"{args.session}-mobile-pt{n}of{total}.mp4"
            burn_ass(cut_path, per_part_ass, part_out)
            print(f"[mobile] pt{n}of{total} -> {part_out}")

        print(f"\n[mobile] SPLIT DELIVERABLE: {total} parts in {out_dir}")
        print(f"[mobile] caption margin_v={caption_margin_v}")
        return 0

    # Single-output mode (no split).
    ass_path = work_dir / f"{args.session}-burn.ass"
    part_label = args.part_label if getattr(args, "part_label", None) else None
    srt_to_ass(
        srt_path, ass_path,
        play_res_x=MOBILE_W, play_res_y=MOBILE_H,
        font_size=72, margin_v=caption_margin_v,
        watermark=True,
        part_label=part_label,
    )
    print(f"[mobile] caption margin_v={caption_margin_v}")
    print(f"[mobile] wrote burn ASS: {ass_path}")

    burn_ass(with_audio, ass_path, out_path)
    print(f"\n[mobile] PHASE 2 DELIVERABLE (captions + watermarks + audio): {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
