"""
preprocess_scene.py — deterministic reveal animation.

Takes one generated scene PNG and produces a numbered frame sequence that
reveals the scene over `reveal_duration_seconds`. No AI tokens spent here.

v1 supports two reveal styles:
- `fade`  — linear alpha ramp from neutral background to the scene
- `paint` — soft-edged left-to-right wipe

See PREPROCESSOR_RULES.md for the full contract.

Usage:
    scripts/.venv/bin/python scripts/preprocess_scene.py \\
        --session <session-id> --chunk <chunk-id>
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

ALLOWED_REVEAL_STYLES = {"fade", "paint"}  # edge-skeleton is v2
DEFAULT_REVEAL_STYLE = "fade"
DEFAULT_REVEAL_DURATION = 1.5
DEFAULT_SCENE_FPS = 30
NEUTRAL_BACKGROUND = (252, 250, 245)  # warm off-white, paper-like


# ---- paths -------------------------------------------------------------

def session_dir(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id


def scene_path(session_id: str, chunk_id: str) -> Path:
    return (
        session_dir(session_id)
        / "source"
        / "generated-assets"
        / "scenes"
        / f"{chunk_id}.png"
    )


def frames_dir(session_id: str, chunk_id: str) -> Path:
    return session_dir(session_id) / "frames" / chunk_id


def session_config_path(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"


def load_session_config(session_id: str) -> dict[str, Any]:
    path = session_config_path(session_id)
    with open(path) as f:
        return json.load(f)


# ---- hashing & cache ---------------------------------------------------

def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _existing_frames_valid(
    frames_out: Path,
    input_hash: str,
    reveal_style: str,
    duration: float,
    fps: int,
    expected_count: int,
) -> bool:
    meta = frames_out / "frames.json"
    if not meta.exists():
        return False
    try:
        data = json.loads(meta.read_text())
    except Exception:
        return False
    if data.get("input_hash") != input_hash:
        return False
    if data.get("reveal_style") != reveal_style:
        return False
    if abs(float(data.get("reveal_duration_seconds", 0)) - duration) > 1e-6:
        return False
    if int(data.get("scene_fps", 0)) != fps:
        return False
    if int(data.get("frame_count", 0)) != expected_count:
        return False
    actual = len(list(frames_out.glob("frame_*.png")))
    return actual == expected_count


# ---- reveal styles -----------------------------------------------------

def _render_fade_frames(scene: Image.Image, frame_count: int) -> list[Image.Image]:
    """Fade-in over frame_count frames.

    Frame 1 = pure neutral background. Frame N = full scene, pixel-for-pixel.
    """
    scene_rgb = scene.convert("RGB")
    bg = Image.new("RGB", scene_rgb.size, NEUTRAL_BACKGROUND)

    frames: list[Image.Image] = []
    for i in range(frame_count):
        alpha = 1.0 if frame_count == 1 else i / (frame_count - 1)
        frames.append(Image.blend(bg, scene_rgb, alpha))

    # Enforce: last frame equals the scene pixel-for-pixel.
    frames[-1] = scene_rgb.copy()
    return frames


def _render_paint_frames(scene: Image.Image, frame_count: int) -> list[Image.Image]:
    """Soft-edged left-to-right wipe.

    Frame 1 = neutral background. Frame N = full scene.
    """
    scene_rgb = scene.convert("RGB")
    w, h = scene_rgb.size
    scene_arr = np.array(scene_rgb, dtype=np.float32)
    bg_arr = np.full_like(scene_arr, np.array(NEUTRAL_BACKGROUND, dtype=np.float32))
    x_coords = np.arange(w, dtype=np.float32)
    soft_edge = max(32.0, w / 40.0)

    frames: list[Image.Image] = []
    for i in range(frame_count):
        if frame_count == 1:
            t = 1.0
        else:
            t = i / (frame_count - 1)
        # edge sweeps from -soft_edge (off left) to w + soft_edge (off right)
        edge_x = t * (w + 2 * soft_edge) - soft_edge
        alpha_row = np.clip(
            (edge_x - x_coords + soft_edge) / (2 * soft_edge), 0.0, 1.0
        ).astype(np.float32)
        alpha_2d = np.tile(alpha_row.reshape(1, w, 1), (h, 1, 3))
        blended = bg_arr * (1.0 - alpha_2d) + scene_arr * alpha_2d
        frames.append(
            Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "RGB")
        )

    # Enforce final-frame equality.
    frames[-1] = scene_rgb.copy()
    return frames


# ---- preprocess --------------------------------------------------------

def preprocess(
    session_id: str,
    chunk_id: str,
    *,
    force: bool = False,
    reveal_style: str | None = None,
    reveal_duration_seconds: float | None = None,
    scene_fps: int | None = None,
) -> Path:
    scene = scene_path(session_id, chunk_id)
    if not scene.exists():
        raise FileNotFoundError(f"scene png not found: {scene}")

    cfg = load_session_config(session_id)
    style = reveal_style or cfg.get("reveal_style", DEFAULT_REVEAL_STYLE)
    if style not in ALLOWED_REVEAL_STYLES:
        raise ValueError(
            f"reveal_style {style!r} not in allowed set "
            f"{sorted(ALLOWED_REVEAL_STYLES)} (see PREPROCESSOR_RULES.md)"
        )
    duration = (
        reveal_duration_seconds
        if reveal_duration_seconds is not None
        else cfg.get("reveal_duration_seconds", DEFAULT_REVEAL_DURATION)
    )
    fps = scene_fps if scene_fps is not None else cfg.get("scene_fps", DEFAULT_SCENE_FPS)
    frame_count = max(1, round(duration * fps))

    input_hash = _file_hash(scene)
    out_dir = frames_dir(session_id, chunk_id)

    if out_dir.exists() and not force:
        if _existing_frames_valid(out_dir, input_hash, style, duration, fps, frame_count):
            print(f"[pre] cache hit: {out_dir}")
            return out_dir

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(scene)

    if style == "fade":
        frames = _render_fade_frames(img, frame_count)
    elif style == "paint":
        frames = _render_paint_frames(img, frame_count)
    else:
        raise RuntimeError(f"unreachable: style={style}")

    for i, f in enumerate(frames, start=1):
        f.save(out_dir / f"frame_{i:04d}.png", "PNG")

    meta = {
        "chunk_id": chunk_id,
        "scene_src": str(scene.relative_to(CONTENT_ROOT)),
        "reveal_style": style,
        "reveal_duration_seconds": duration,
        "scene_fps": fps,
        "frame_count": frame_count,
        "input_hash": input_hash,
        "created_at": _dt.datetime.now(_dt.UTC).isoformat(),
    }
    (out_dir / "frames.json").write_text(json.dumps(meta, indent=2))

    # Validation: last frame must equal the scene pixel-for-pixel
    # (PREPROCESSOR_RULES.md § Final-frame rule).
    last = Image.open(out_dir / f"frame_{frame_count:04d}.png").convert("RGB")
    if list(last.getdata()) != list(img.convert("RGB").getdata()):
        raise RuntimeError(
            "preprocessor validation failed: last frame != scene "
            "(see PREPROCESSOR_RULES.md)"
        )

    print(f"[pre] {chunk_id}: {frame_count} frames @ {fps}fps -> {out_dir}")
    return out_dir


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Preprocess one scene into a reveal frame sequence"
    )
    parser.add_argument("--session", required=True)
    parser.add_argument("--chunk", required=True)
    parser.add_argument(
        "--reveal-style", default=None, choices=sorted(ALLOWED_REVEAL_STYLES)
    )
    parser.add_argument("--reveal-duration-seconds", type=float, default=None)
    parser.add_argument("--fps", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        preprocess(
            session_id=args.session,
            chunk_id=args.chunk,
            force=args.force,
            reveal_style=args.reveal_style,
            reveal_duration_seconds=args.reveal_duration_seconds,
            scene_fps=args.fps,
        )
    except Exception as e:
        print(f"[pre] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
