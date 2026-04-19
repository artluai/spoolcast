"""
stroke_reveal.py — multi-stroke parallel reveal for line art.

Approach: per-pixel reveal time map.
Every black pixel gets assigned a reveal time in [0, 1] based on:
- its component's priority (when its component starts drawing)
- its position within the component (intra-component progression)

Multiple components draw in parallel (staggered starts). Fast-painter vibe:
hand appears to be working everywhere at once, with organic ordering.

Strategy controls both:
- component ordering (which components start first)
- intra-component direction (which pixels within a component reveal first)

Usage:
    scripts/.venv/bin/python scripts/stroke_reveal.py \\
        --input <scene>.png \\
        --output <frames_dir>/ \\
        --fps 30 --duration 1.5 \\
        --strategy largest-first
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import cv2
import numpy as np


STRATEGIES = {
    "auto",
    "largest-first",
    "left-to-right",
    "right-to-left",
    "top-to-bottom",
    "bottom-to-top",
    "center-out",
}

# Direction abbreviations → full strategy names
DIRECTION_ALIASES = {
    "": "largest-first",
    "lr": "left-to-right",
    "rl": "right-to-left",
    "tb": "top-to-bottom",
    "bt": "bottom-to-top",
}


# ---- image loading -----------------------------------------------------

def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"could not load image: {path}")
    if img.ndim == 3 and img.shape[2] == 4:
        # Flatten alpha against white
        alpha = img[:, :, 3:4] / 255.0
        bgr = img[:, :, :3].astype(np.float32)
        white = np.full_like(bgr, 255)
        img = (bgr * alpha + white * (1 - alpha)).astype(np.uint8)
    elif img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def binarize(img: np.ndarray, threshold: int = 128) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return binary


def find_components(
    binary: np.ndarray, min_area: int = 40
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    comps: list[dict[str, Any]] = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        cx, cy = centroids[i]
        comps.append(
            {
                "label": int(i),
                "area": int(area),
                "cx": float(cx),
                "cy": float(cy),
                "bbox": (int(x), int(y), int(w), int(h)),
            }
        )
    return labels, comps


def order_components(
    comps: list[dict[str, Any]], strategy: str, canvas_shape: tuple[int, int]
) -> list[dict[str, Any]]:
    H, W = canvas_shape
    s = DIRECTION_ALIASES.get(strategy, strategy)
    if s not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy}")
    if s == "largest-first" or s == "auto":
        return sorted(comps, key=lambda c: -c["area"])
    if s == "left-to-right":
        return sorted(comps, key=lambda c: c["cx"])
    if s == "right-to-left":
        return sorted(comps, key=lambda c: -c["cx"])
    if s == "top-to-bottom":
        return sorted(comps, key=lambda c: c["cy"])
    if s == "bottom-to-top":
        return sorted(comps, key=lambda c: -c["cy"])
    if s == "center-out":
        return sorted(
            comps, key=lambda c: (c["cx"] - W / 2) ** 2 + (c["cy"] - H / 2) ** 2
        )
    return comps


# ---- reveal-time map ---------------------------------------------------

def build_reveal_times(
    labels: np.ndarray,
    ordered: list[dict[str, Any]],
    canvas_shape: tuple[int, int],
    strategy: str,
    # Fraction of total duration dedicated to staggering component starts.
    # E.g., 0.35 means the last-started component begins at t=0.35, and all
    # components have until t=1.0 to finish. Gives lots of parallel drawing.
    stagger_fraction: float = 0.35,
    # Small per-pixel noise amount for organic feel (0-1 as fraction of t).
    pixel_noise: float = 0.05,
    rng_seed: int = 42,
) -> np.ndarray:
    """Return a float32 array (H, W) of reveal times in [0, 1] per pixel.

    White-background pixels are assigned t=1.0 (never revealed by threshold,
    but they're already the background color so this doesn't matter).

    Multiple components are active simultaneously at most frames."""
    H, W = canvas_shape
    reveal = np.full((H, W), 1.0, dtype=np.float32)
    if not ordered:
        return reveal

    s = DIRECTION_ALIASES.get(strategy, strategy)
    n = len(ordered)
    draw_duration = 1.0 - stagger_fraction  # time each component has to draw

    # Precompute coord grids once
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    rng = np.random.default_rng(rng_seed)

    for i, comp in enumerate(ordered):
        mask = labels == comp["label"]
        if not mask.any():
            continue

        comp_start = (i / max(1, n - 1)) * stagger_fraction if n > 1 else 0.0

        # Intra-component progression: which pixels appear first within this component
        # Strategy controls the direction of travel inside the component.
        if s in ("left-to-right", "largest-first", "auto", "center-out"):
            # for auto/largest-first, default intra to center-out from component centroid
            # for left-to-right or center-out, use that direction
            if s == "left-to-right":
                cmask_x = xx[mask]
                intra = (cmask_x - cmask_x.min()) / max(1e-6, (cmask_x.max() - cmask_x.min()))
            elif s == "center-out":
                cmask_x = xx[mask]
                cmask_y = yy[mask]
                d = np.sqrt((cmask_x - comp["cx"]) ** 2 + (cmask_y - comp["cy"]) ** 2)
                intra = d / max(1e-6, d.max())
            else:
                # auto / largest-first → center-out from the component's centroid
                cmask_x = xx[mask]
                cmask_y = yy[mask]
                d = np.sqrt((cmask_x - comp["cx"]) ** 2 + (cmask_y - comp["cy"]) ** 2)
                intra = d / max(1e-6, d.max())
        elif s == "right-to-left":
            cmask_x = xx[mask]
            intra = (cmask_x.max() - cmask_x) / max(1e-6, (cmask_x.max() - cmask_x.min()))
        elif s == "top-to-bottom":
            cmask_y = yy[mask]
            intra = (cmask_y - cmask_y.min()) / max(1e-6, (cmask_y.max() - cmask_y.min()))
        elif s == "bottom-to-top":
            cmask_y = yy[mask]
            intra = (cmask_y.max() - cmask_y) / max(1e-6, (cmask_y.max() - cmask_y.min()))
        else:
            intra = np.zeros_like(xx[mask])

        # Pixel reveal time = component_start + intra * draw_duration + small noise
        noise = (rng.random(intra.shape).astype(np.float32) - 0.5) * 2 * pixel_noise
        pixel_t = comp_start + intra * draw_duration + noise
        pixel_t = np.clip(pixel_t, 0.0, 1.0)

        # Write; in case of overlap, take the earlier reveal time
        existing = reveal[mask]
        reveal[mask] = np.minimum(existing, pixel_t)

    return reveal


def generate_frames(
    original: np.ndarray,
    reveal_times: np.ndarray,
    num_frames: int,
    output_dir: Path,
    ease_in_out: bool = True,
    stroke_dilate: int = 2,
) -> None:
    """Render each frame by revealing pixels where reveal_times <= t."""
    output_dir.mkdir(parents=True, exist_ok=True)
    H, W = reveal_times.shape
    # Dilation kernel slightly widens the strokes so thin lines stay visible
    kernel = np.ones((stroke_dilate * 2 + 1, stroke_dilate * 2 + 1), np.uint8)

    def _ease(t: float) -> float:
        if not ease_in_out:
            return t
        return float(0.5 - 0.5 * np.cos(np.pi * t))

    for frame_idx in range(1, num_frames + 1):
        t = _ease(frame_idx / num_frames)
        visible = (reveal_times <= t).astype(np.uint8) * 255
        if stroke_dilate > 0:
            visible = cv2.dilate(visible, kernel, iterations=1)

        # Compose: where visible, show original; else white
        frame = np.full_like(original, 255)
        m3 = (visible > 0)[:, :, None].astype(np.uint8)
        frame = original * m3 + frame * (1 - m3)

        cv2.imwrite(str(output_dir / f"frame_{frame_idx:04d}.png"), frame)

    # Enforce final frame == original pixel-for-pixel
    cv2.imwrite(str(output_dir / f"frame_{num_frames:04d}.png"), original)


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate multi-stroke parallel reveal frames from a line-art PNG"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=float, default=1.5)
    parser.add_argument(
        "--strategy",
        default="auto",
        help="Strategy or direction alias (auto/largest-first/left-to-right/right-to-left/top-to-bottom/bottom-to-top/center-out/lr/rl/tb/bt)",
    )
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--min-area", type=int, default=40)
    parser.add_argument("--stagger", type=float, default=0.35,
                        help="Fraction of total duration used to stagger component starts (0.0-0.8)")
    parser.add_argument("--noise", type=float, default=0.05,
                        help="Per-pixel noise amount (0-1 fraction of total time)")
    args = parser.parse_args()

    img = load_image(Path(args.input))
    binary = binarize(img, threshold=args.threshold)
    labels, comps = find_components(binary, min_area=args.min_area)
    ordered = order_components(comps, args.strategy, img.shape[:2])

    print(
        f"[stroke-reveal] {len(comps)} components, strategy={args.strategy}, stagger={args.stagger}"
    )

    reveal_times = build_reveal_times(
        labels, ordered, img.shape[:2], args.strategy,
        stagger_fraction=args.stagger, pixel_noise=args.noise,
    )
    num_frames = max(1, int(args.fps * args.duration))
    generate_frames(img, reveal_times, num_frames, Path(args.output))
    print(f"[stroke-reveal] wrote {num_frames} frames to {args.output}")


if __name__ == "__main__":
    _cli()
