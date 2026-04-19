"""
chalkboard_wipe.py — back-and-forth eraser reveal.

Motion model (from spec):
  - Each stroke covers a band ~10% of perpendicular dimension (eraser diameter).
  - One back-and-forth = 2 strokes (forward, then back offset by half-eraser),
    covering ~15% with 50% overlap between the two strokes.
  - 6-7 back-and-forths stacked to cover the whole canvas = 90-100% coverage.
  - Total strokes: 12-14.
  - Overall travel direction: diagonal.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2
import numpy as np


ERASER_DIAM_FRAC = 0.10          # eraser diameter = 10% of perp extent
N_BACK_FORTHS_MIN = 6
N_BACK_FORTHS_MAX = 7
INNER_OFFSET_FRAC = 0.5          # back stroke offset = 0.5 * eraser diameter
STROKE_OVERLAP = 0.15            # time overlap between consecutive strokes


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"could not load image: {path}")
    if img.ndim == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3:4] / 255.0
        bgr = img[:, :, :3].astype(np.float32)
        white = np.full_like(bgr, 255)
        img = (bgr * alpha + white * (1 - alpha)).astype(np.uint8)
    elif img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def build_reveal_map(
    H: int, W: int, seed: int | None
) -> tuple[np.ndarray, int, int]:
    if seed is None:
        seed = int(time.time() * 1000) % 2**32
    rng = np.random.default_rng(seed)

    # Overall diagonal angle
    angle_deg = float(rng.choice([45, -45, 135, -135]))
    angle = np.radians(angle_deg)
    mdx, mdy = float(np.cos(angle)), float(np.sin(angle))
    pdx, pdy = -mdy, mdx

    # Canvas extent along motion / perpendicular axes
    corners = [(0.0, 0.0), (W, 0.0), (0.0, H), (W, H)]
    along_p = [x * mdx + y * mdy for x, y in corners]
    perp_p = [x * pdx + y * pdy for x, y in corners]
    along_min, along_max = min(along_p), max(along_p)
    perp_min, perp_max = min(perp_p), max(perp_p)
    perp_span = perp_max - perp_min

    eraser_diam = perp_span * ERASER_DIAM_FRAC
    eraser_r = eraser_diam / 2.0
    inner_offset = eraser_diam * INNER_OFFSET_FRAC

    n_bf = int(rng.integers(N_BACK_FORTHS_MIN, N_BACK_FORTHS_MAX + 1))

    # Center each back-and-forth evenly across perp extent
    bf_centers = [
        perp_min + (i + 0.5) * (perp_span / n_bf) for i in range(n_bf)
    ]

    # Build stroke list: forward & back per back-and-forth
    # Timing: sequential with slight overlap
    strokes: list[dict] = []
    for bf_idx, center in enumerate(bf_centers):
        fwd_perp = center - inner_offset / 2
        back_perp = center + inner_offset / 2
        # Alternate which one comes first based on bf_idx for zigzag feel
        if bf_idx % 2 == 0:
            strokes.append({"perp": fwd_perp, "forward": True})
            strokes.append({"perp": back_perp, "forward": False})
        else:
            strokes.append({"perp": back_perp, "forward": False})
            strokes.append({"perp": fwd_perp, "forward": True})

    n_strokes = len(strokes)
    # Correct timing: want last stroke to end at t=1.0 with overlap f between
    # consecutive strokes. Start stride = per_stroke * (1 - f). Total length:
    # (n-1) * stride + per_stroke = per_stroke * ((n-1)(1-f) + 1) = 1.0
    per_stroke = 1.0 / max((n_strokes - 1) * (1.0 - STROKE_OVERLAP) + 1.0, 1e-6)

    reveal = np.full((H, W), 1.0, dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    along = xx * mdx + yy * mdy
    perp = xx * pdx + yy * pdy

    pad = eraser_r + 4.0
    r_sq = eraser_r * eraser_r

    for i, st in enumerate(strokes):
        t0 = i * per_stroke * (1.0 - STROKE_OVERLAP)
        t1 = t0 + per_stroke
        t0 = max(0.0, t0)
        t1 = min(1.0, t1)

        p_off = st["perp"]
        forward = st["forward"]
        if forward:
            a_start, a_end = along_min - pad, along_max + pad
        else:
            a_start, a_end = along_max + pad, along_min - pad
        dz = a_end - a_start

        dp = perp - p_off
        dp_sq = dp * dp
        in_band = dp_sq <= r_sq
        sqrt_term = np.sqrt(np.clip(r_sq - dp_sq, 0.0, None))

        if forward:
            first_contact = (along - a_start - sqrt_term) / max(dz, 1e-6)
        else:
            first_contact = (a_start - along - sqrt_term) / max(-dz, 1e-6)
        first_contact = np.clip(first_contact, 0.0, 1.0)

        pixel_t = t0 + first_contact * (t1 - t0)
        new_t = np.where(in_band, pixel_t, 1.0).astype(np.float32)
        reveal = np.minimum(reveal, new_t)

    return reveal, seed, n_strokes


def generate_frames(
    original: np.ndarray,
    reveal_map: np.ndarray,
    num_frames: int,
    output_dir: Path,
    feather: float = 0.010,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    white = np.full_like(original, 255)

    def _ease(x: float) -> float:
        return float(0.5 - 0.5 * np.cos(np.pi * x))

    for i in range(1, num_frames + 1):
        t = _ease(i / num_frames)
        alpha = np.clip((t - reveal_map) / feather + 0.5, 0.0, 1.0).astype(np.float32)
        frame = (
            original.astype(np.float32) * alpha[..., None]
            + white.astype(np.float32) * (1.0 - alpha[..., None])
        ).astype(np.uint8)
        cv2.imwrite(str(output_dir / f"frame_{i:04d}.png"), frame)

    cv2.imwrite(str(output_dir / f"frame_{num_frames:04d}.png"), original)


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--direction", default="random", help="unused")
    parser.add_argument("--feather", type=float, default=0.010)
    args = parser.parse_args()

    img = load_image(Path(args.input))
    H, W = img.shape[:2]
    reveal_map, seed, n = build_reveal_map(H, W, args.seed)
    print(f"[chalkboard-wipe] seed={seed} n_strokes={n}")
    num_frames = max(1, int(args.fps * args.duration))
    generate_frames(img, reveal_map, num_frames, Path(args.output), feather=args.feather)
    print(f"[chalkboard-wipe] wrote {num_frames} frames to {args.output}")


if __name__ == "__main__":
    _cli()
