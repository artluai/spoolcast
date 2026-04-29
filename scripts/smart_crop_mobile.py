#!/usr/bin/env python3
"""smart_crop_mobile.py — subject-centered 9:16 crop per chunk via Qwen-VL.

For each chunk with a widescreen scene image, ask Qwen-VL to locate the
main subject's center (fractional x, y in [0,1]), then compute a 9:16
crop window that keeps the subject in the middle — clamped to the source
image edges. Writes the cropped+scaled result to
`scenes/mobile/<chunk>-mobile.png` at 1080x1920.

Follow up with `audit_mobile_crops.py` on the output to flag any chunks
where subject-centered cropping still leaves important content clipped;
those are candidates for full 9:16 regen via `replay_mobile.py`.

Usage:
  scripts/.venv/bin/python scripts/smart_crop_mobile.py \\
      --session spoolcast-dev-log-02 \\
      [--only C1,C2] [--parallel 4] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: scripts/.venv/bin/pip install Pillow", file=sys.stderr)
    sys.exit(3)

try:
    import pytesseract
except ImportError:
    pytesseract = None  # OCR optional — falls back to Qwen bbox if unavailable

from audit_scenes import (
    DEFAULT_PROVIDER,
    DEFAULT_MODEL_BY_PROVIDER,
    VisionClient,
    encode_image,
    parse_json_reply,
    load_shot_list,
)

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"

MOBILE_W = 1080
MOBILE_H = 1920
TARGET_ASPECT = 9 / 16  # width / height, portrait. Mutated at startup when --aspect is set.
CONTENT_H = MOBILE_H  # content area height; equals MOBILE_H for 9:16, less for 1:1 (letterboxed)

SYSTEM_PROMPT = """You are a locator for mobile-crop geometry. You find
bounding boxes of the important visual elements in an image so Python
code can compute the best 9:16 crop. Accuracy of the bboxes is critical.
Tightly wrap the actual element — a box covering "the middle of the
image" is wrong when the element is off-center.

Return JSON:

{
  "elements": [
    {
      "bbox": {"x0": <0-1>, "y0": <0-1>, "x1": <0-1>, "y1": <0-1>},
      "face_bbox": {"x0": <0-1>, "y0": <0-1>, "x1": <0-1>, "y1": <0-1>} | null,
      "importance": <int, 1 = primary, 2 = secondary, 3+ = lower>,
      "kind": "character" | "text" | "object",
      "description": "<one short phrase>"
    }
    // ... one entry per important element
  ],
  "confidence": "high" | "medium" | "low"
}

**face_bbox field** (characters only): the TIGHT bounding box of just the
character's face/head region (not the whole body). If the character's
face is visible in frame, provide this — it's what the 10% face-clip
rule is applied to. The body can clip more than 10% as long as the face
stays ≤10% clipped. Set to null if the character's face isn't clearly
visible (back of head, hood obscuring face, etc.). Non-character
elements should omit or null this field.

Coordinates are fractions of image dimensions (x0/x1 for horizontal,
y0/y1 for vertical; 0 is top/left, 1 is bottom/right).

**What counts as an element:**

Anything a viewer must see for the scene to make sense. Common kinds:
- A character (person, figure) — wrap head to waist/feet
- Readable text (speech bubble, label, hand-lettered caption,
  full-frame typography) — wrap the whole text block
- A key object or prop (the thing being held, pointed at, or named
  by an arrow/label)

Do NOT include ambient background clutter, desk props, posters,
decorative elements. Only things that carry the beat's meaning.

**Importance = focal-vs-constraint role:**

The crop has two kinds of elements:
- **FOCAL** — the one element the crop aims to center ON. Visually anchors the scene.
- **CONSTRAINTS & CONTEXT** — other elements that must not be badly clipped or that provide supporting context, but are not the center of attention.

Exactly ONE element has importance=1 (focal). All others get importance 2–4+.

**Focal-selection rule — the alone-crop test (most important):**

Ask, for each element you identify: *"If the final 9:16 crop contained ONLY this element (everything else cropped out), and the viewer also heard the narration line, would the scene still make sense to that viewer?"*

- If YES → this element is a candidate for focal.
- If NO → this element CANNOT be focal, no matter how visually prominent it is.

Among passing candidates, pick the one most tied to the scene's meaning. Tiebreakers:

1. **Prefer characters over objects** as focal, when both pass the alone-crop test. Characters anchor viewer identification; objects need human context to land emotionally.
2. **For handoff / exchange / delivery scenes**: the RECIPIENT (the character on the receiving end of the action, or whose situation is being addressed) is usually the best focal. The recipient's expression / circumstance anchors the scene; the artifact they receive is a symbol; the deliverer is interchangeable.
   - Example: narration is "the fix: AI redraws broken shots." Candidates: the redo note (artifact), the worker receiving it (recipient), the deliverer. Alone-crop test:
     - Worker alone + narration → "struggling worker being helped" — makes sense ✓
     - Note alone + narration → "floating redo note, no subject" — confusing ✗
     - Deliverer alone + narration → "man holding note, no recipient" — confusing ✗
     Only the recipient passes → focal = recipient.
3. **For accusation / confrontation / monologue scenes**: the SPEAKER / ACTOR is the focal. The speaker's expression and body language anchor the accusation / line.
   - Example: narration is "I knew you were lying to me." Candidates: accuser, accused, speech bubble. Alone-crop test:
     - Accuser alone + narration → "angry person, implied accusation" — makes sense ✓
     - Speech bubble alone + narration → "floating text" — confusing ✗
     - Accused alone + narration → "passive person, no accuser" — confusing ✗
     Only the accuser passes → focal = accuser.
4. **For text-only cards** (no characters or objects): text is the focal, because there's nothing else.

Text is NEVER focal when a character or key object is in frame — text cannot anchor a scene on its own (see alone-crop test: "text alone" always fails the test when a character exists).

**Text is never focal when a character or narrative object is present.** Text is always a constraint (importance 2 for the primary line, 3–4 for secondary), never the thing the crop aims at. Even when the text literally carries the line of narration, the character saying it is still the focal — the text goes along as a constraint.

**Importance 2** — key constraint elements. Rank by how much the scene would SUFFER without this element, not by how visually active it is. A passive "receiver" character is often more important than an active "deliverer" because the scene is about the receiver's situation.
  - Current-line text (speech bubble, caption) that carries the narration
  - Receivers / reactors / subjects of the action — the person being accused, the worker whose task is being fixed, the one asking the question
  - Specific key objects in the scene

**Importance 3+** — contextual / interchangeable. The scene still reads if these are dropped.
  - Interchangeable participants — messengers, deliverers, generic bystanders whose specific identity doesn't matter to the scene
  - Background characters not in the primary action
  - Decorative text (book titles, poster slogans, mug inscriptions), ambient props
  - A character who's "doing" something but whose role is mechanical (handing, pointing, delivering) — the THING they deliver is usually importance 1 or 2, but they themselves are often 3

Test for active characters: "if this character were replaced by a different person doing the same action, would the scene still make sense?" If yes → importance 3. If no (their identity / emotion / situation matters) → importance 2.

You will be told the chunk's NARRATION (the line the viewer hears) in the user prompt. Use it to identify who the speaker is and what the scene's action is — but remember: the speaker/actor (a CHARACTER) is focal, not the line itself.

**When two elements are semantically linked** (e.g. a character and
the speech bubble coming from them; a builder and the file they're
handing to another figure), the element bbox should still wrap each
element individually — don't fuse them. Python handles the grouping
via importance order.

**Edge cases:**

- Pure text card (typography-only, no characters): return one
  element with kind="text" and importance=1.
- Pure diagram (labeled shapes, no characters): return the shapes
  and labels as separate elements with importance reflecting the
  reading order.
- Abstract/empty frame: return an empty elements array.

Return ONLY the JSON — no prose."""


USER_PROMPT_TEMPLATE = """Narration (the line the viewer hears during
this moment, ground truth for the message test):
{narration}

Analyze what is actually visible in the image. Trust only the pixels
for locations (some images differ from their brief — e.g. a brief said
"no character" but the image has two). For importance ranking, apply
the message-preservation test against the narration above: which element,
when shown alone, most directly conveys what the narration is about?

Return bounding boxes per the schema. JSON only."""


def _median_bbox(bboxes: list[dict[str, Any]]) -> dict[str, float] | None:
    """Compute per-coordinate median bbox from a list of bboxes."""
    if not bboxes:
        return None
    xs0 = sorted(float(b["x0"]) for b in bboxes if b and "x0" in b)
    ys0 = sorted(float(b["y0"]) for b in bboxes if b and "y0" in b)
    xs1 = sorted(float(b["x1"]) for b in bboxes if b and "x1" in b)
    ys1 = sorted(float(b["y1"]) for b in bboxes if b and "y1" in b)
    if not xs0:
        return None
    n = len(xs0)
    mid = n // 2
    # Odd count: true middle; even count: average of middle two
    def med(arr: list[float]) -> float:
        if len(arr) % 2 == 1:
            return arr[len(arr) // 2]
        return (arr[len(arr) // 2 - 1] + arr[len(arr) // 2]) / 2.0
    return {
        "x0": round(med(xs0), 4),
        "y0": round(med(ys0), 4),
        "x1": round(med(xs1), 4),
        "y1": round(med(ys1), 4),
    }


def _merge_qwen_runs(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Merge N Qwen responses into one with median bboxes per element.

    Elements are matched by INDEX POSITION across runs. If counts or kinds
    disagree across runs, falls back to the first run (no merging).
    """
    if not runs:
        return None
    ref = runs[0]
    ref_elements = ref.get("elements") or []
    if len(runs) == 1:
        return ref

    # Check consistency: all runs same element count + same kinds
    for r in runs[1:]:
        r_el = r.get("elements") or []
        if len(r_el) != len(ref_elements):
            return ref  # fallback — inconsistent, can't merge
        for a, b in zip(ref_elements, r_el):
            if a.get("kind") != b.get("kind"):
                return ref  # fallback

    # Consistent. Median each element's bbox and face_bbox.
    merged_elements: list[dict[str, Any]] = []
    for i in range(len(ref_elements)):
        ref_e = ref_elements[i]
        bboxes_across_runs = [r["elements"][i].get("bbox") for r in runs if r["elements"][i].get("bbox")]
        face_bboxes_across_runs = [r["elements"][i].get("face_bbox") for r in runs if r["elements"][i].get("face_bbox")]
        median_bbox = _median_bbox(bboxes_across_runs) or ref_e.get("bbox")
        median_face = _median_bbox(face_bboxes_across_runs) if len(face_bboxes_across_runs) >= 2 else ref_e.get("face_bbox")
        merged_e = {**ref_e, "bbox": median_bbox, "face_bbox": median_face}
        merged_elements.append(merged_e)

    merged = {**ref, "elements": merged_elements, "_n_runs": len(runs)}
    return merged


def ocr_text_bbox(img_path: Path, min_confidence: int = 30) -> dict[str, float] | None:
    """Use Tesseract to locate text regions in an image. Returns the union
    bbox of all detected words (as normalized fractions of image dims), or
    None if no confident text is found.

    Deterministic and fast (typically <200ms/image). Used to override
    Qwen's text-bbox predictions, which have high spatial-localization
    error for small text elements like speech bubbles and hand-lettered
    labels. Qwen stays authoritative for character and object bboxes.
    """
    if pytesseract is None:
        return None
    try:
        img = Image.open(img_path).convert("RGB")
        src_w, src_h = img.size
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception:
        return None

    n = len(data.get("text", []))
    xs0: list[int] = []
    ys0: list[int] = []
    xs1: list[int] = []
    ys1: list[int] = []
    for i in range(n):
        text = (data["text"][i] or "").strip()
        conf_raw = data["conf"][i]
        try:
            conf = int(conf_raw) if conf_raw not in ("-1", -1) else -1
        except (ValueError, TypeError):
            conf = -1
        # Filter: require confident recognition AND at least 2 chars
        # (Tesseract fires spurious single-char detections on busy backgrounds).
        if text and conf >= min_confidence and len(text) >= 2:
            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])
            xs0.append(x)
            ys0.append(y)
            xs1.append(x + w)
            ys1.append(y + h)

    if not xs0:
        return None
    return {
        "x0": round(min(xs0) / src_w, 4),
        "y0": round(min(ys0) / src_h, 4),
        "x1": round(max(xs1) / src_w, 4),
        "y1": round(max(ys1) / src_h, 4),
    }


def _bbox_width(bbox: dict[str, Any] | None) -> float:
    if not bbox:
        return 0.0
    return max(0.0, float(bbox.get("x1", 0)) - float(bbox.get("x0", 0)))


def _bbox_center_x(bbox: dict[str, Any] | None) -> float | None:
    if not bbox:
        return None
    return (float(bbox.get("x0", 0)) + float(bbox.get("x1", 0))) / 2.0


def _bbox_center_y(bbox: dict[str, Any] | None) -> float | None:
    if not bbox:
        return None
    return (float(bbox.get("y0", 0)) + float(bbox.get("y1", 0))) / 2.0


def _x_range_for_element(bbox: dict[str, Any], half: float, tolerance: float) -> tuple[float, float] | None:
    """Return the range of 9:16 crop centers that keep this bbox within
    `tolerance` of its width clipped. Returns None if the element can't
    fit any crop within tolerance (bbox width > crop width + tolerance slack)."""
    x0 = float(bbox["x0"])
    x1 = float(bbox["x1"])
    w = max(0.0, x1 - x0)
    if w <= 0:
        return (half, 1.0 - half)
    slack = w * tolerance
    # crop spans [x - half, x + half]. For element fully in: x in [x1-half, x0+half].
    # With tolerance: x in [x1 - half - slack, x0 + half + slack].
    x_lo = max(half, x1 - half - slack)
    x_hi = min(1.0 - half, x0 + half + slack)
    if x_lo > x_hi:
        return None
    return (x_lo, x_hi)


def _y_range_for_element(bbox: dict[str, Any], half_h: float, tolerance: float) -> tuple[float, float] | None:
    y0 = float(bbox["y0"])
    y1 = float(bbox["y1"])
    h = max(0.0, y1 - y0)
    slack = h * tolerance if h > 0 else 0.0
    y_lo = max(half_h, y1 - half_h - slack)
    y_hi = min(1.0 - half_h, y0 + half_h + slack)
    if y_lo > y_hi:
        return None
    return (y_lo, y_hi)


def _element_tolerance(element: dict[str, Any], is_focal: bool, strict: bool = False, focal_tol_override: float | None = None) -> float:
    """Per-element clip tolerance based on role.

    When strict=True, tolerance is tightened to -5% for text — meaning text
    must have a 5% margin from the crop edges, not just fit. Text touching
    the edge reads visually the same as text clipped, so a small padding
    gives breathing room.

    Used in the two-pass fitter: pass 1 tries strict-text (-5%), pass 2
    relaxes text to its normal tolerance.

    - Focal element: 10% (the thing the crop centers on — must be clean).
    - Text elements: 10% normal, -5% in strict pass (prefer 5% padding).
    - Secondary characters (non-focal): 15% (faces can clip more to keep
      scene context when source composition is wide).
    - Non-focal objects: 10% (key props need to be clean).
    - Contextual elements (importance 3+): 20% (nice-to-have).
    """
    kind = element.get("kind", "")
    if strict and kind == "text":
        # Negative tolerance = required padding. -0.05 means text's effective
        # bbox is 5% of text-width wider on each side, forcing a small gap
        # between text and crop edge.
        return -0.05
    if is_focal:
        return focal_tol_override if focal_tol_override is not None else 0.10
    importance = element.get("importance", 99)
    if kind == "text":
        return 0.10
    if kind == "character":
        return 0.15 if importance <= 2 else 0.20
    return 0.10 if importance <= 2 else 0.20


def _fit_center_for_elements(
    elements: list[dict[str, Any]],
    src_w: int,
    src_h: int,
    tolerance: float,  # legacy param — kept for signature compat; per-element tolerance used internally
    strict_text: bool = False,
    focal_tol_override: float | None = None,
) -> tuple[float, float] | None:
    """Find a 9:16 crop center that contains all given elements within tolerance.
    Returns (x, y) as fractions, or None if no such center exists.

    The first element in the list is treated as the focal (strict 10%);
    other elements get element-type-aware tolerance (see _element_tolerance).
    When `strict_text=True`, text elements must fit with 0% clipping (used
    in the preference pass — try to show all text first, fall back to ≤10%).
    """
    if not elements:
        return None
    # Crop dimensions relative to source, at TARGET_ASPECT (mutable, set by --aspect).
    src_aspect = src_w / src_h
    target_aspect = TARGET_ASPECT
    if src_aspect > target_aspect:
        crop_w_frac = (src_h * target_aspect) / src_w
        crop_h_frac = 1.0
    else:
        crop_w_frac = 1.0
        crop_h_frac = (src_w / target_aspect) / src_h
    crop_w_frac = min(1.0, crop_w_frac)
    crop_h_frac = min(1.0, crop_h_frac)
    half_x = crop_w_frac / 2.0
    half_y = crop_h_frac / 2.0

    x_lo_all, x_hi_all = half_x, 1.0 - half_x
    y_lo_all, y_hi_all = half_y, 1.0 - half_y
    for i, e in enumerate(elements):
        is_focal = (i == 0)
        tol = _element_tolerance(e, is_focal, strict=strict_text, focal_tol_override=focal_tol_override)
        # For characters: the 10/15% clip rule applies to FACE, not the full
        # body bbox. Use face_bbox if provided. Body can clip more than the
        # tolerance as long as the face stays within it.
        if e.get("kind") == "character" and e.get("face_bbox"):
            constraint_bb = e["face_bbox"]
        else:
            constraint_bb = e.get("bbox") or {}
        xr = _x_range_for_element(constraint_bb, half_x, tol)
        yr = _y_range_for_element(constraint_bb, half_y, tol)
        if xr is None or yr is None:
            return None
        x_lo_all = max(x_lo_all, xr[0])
        x_hi_all = min(x_hi_all, xr[1])
        y_lo_all = max(y_lo_all, yr[0])
        y_hi_all = min(y_hi_all, yr[1])
        if x_lo_all > x_hi_all or y_lo_all > y_hi_all:
            return None

    primary = elements[0]
    pbb = primary.get("bbox") or {}
    p_cx = (float(pbb.get("x0", 0)) + float(pbb.get("x1", 1))) / 2.0
    p_cy = (float(pbb.get("y0", 0)) + float(pbb.get("y1", 1))) / 2.0
    x = max(x_lo_all, min(x_hi_all, p_cx))
    y = max(y_lo_all, min(y_hi_all, p_cy))
    return (x, y)


def resolve_crop_center_generic(
    elements: list[dict[str, Any]],
    src_w: int,
    src_h: int,
    tolerance: float = 0.10,
) -> tuple[float, float, str]:
    """Generalized crop-center resolver for N importance-ranked elements.

    Algorithm:
      1. Sort elements by importance (1 = primary).
      2. Try to fit ALL elements in 9:16 with ≤tolerance clipping.
      3. If infeasible, drop the lowest-importance element and retry.
      4. Continue until at least the primary alone is kept (always feasible
         unless primary itself is wider than crop+tolerance).
      5. Returns (x, y, reason) describing which elements were fit.
    """
    if not elements:
        return (0.5, 0.5, "no-elements")

    # Sort for drop-priority: focal always first, then text > object >
    # non-focal character. Text is more important to preserve than a non-focal
    # character because text has a strict clip rule (≤10% or drop entirely)
    # and carries the current line; a secondary character can simply be out
    # of frame without hurting the scene. This overrides Qwen's importance
    # numbers when Qwen inconsistently ranks text.
    KIND_RANK = {"text": 1, "object": 2, "character": 3}

    def _sort_key(e: dict[str, Any]) -> tuple[int, int, int]:
        imp = e.get("importance") if isinstance(e.get("importance"), int) else 99
        is_focal = 0 if imp == 1 else 1  # focal always sorts first
        kind_rank = KIND_RANK.get(e.get("kind", ""), 99)
        # Within non-focal elements: drop by (kind, importance).
        return (is_focal, kind_rank, imp)

    sorted_el = sorted(
        (e for e in elements if e.get("bbox")),
        key=_sort_key,
    )
    if not sorted_el:
        return (0.5, 0.5, "no-bboxes")

    # Subset search: the focal is always kept. Explore all subsets of
    # non-focal elements, preferring larger subsets that preserve text.
    # Try progressively relaxed focal-face tolerance (10% → 12% → 15%)
    # when text-padding (5%) requires more room. Text takes priority over
    # strict focal because user's rule is "text padded beats face strict."
    from itertools import combinations

    FOCAL_FACE_STAGES = [0.10, 0.12, 0.15]  # progressive focal relaxation

    focal = sorted_el[0]
    non_focal = sorted_el[1:]

    def _subset_score(subset: tuple[dict[str, Any], ...]) -> tuple[int, int, int]:
        # Prefer: (1) larger subsets, (2) more text kept, (3) earlier-sorted kept.
        text_kept = sum(1 for e in subset if e.get("kind") == "text")
        size = len(subset)
        # Tiebreak: sum of negative kind_rank (lower kind_rank = preferred)
        kind_sum = sum(-KIND_RANK.get(e.get("kind", ""), 99) for e in subset)
        return (size, text_kept, kind_sum)

    # Iterate subset sizes from largest to smallest
    for size in range(len(non_focal), -1, -1):
        subsets = list(combinations(non_focal, size))
        subsets.sort(key=_subset_score, reverse=True)
        for subset in subsets:
            kept = [focal] + list(subset)
            # Pass 1: strict text (5% padding) with progressive focal relaxation.
            # Text padding takes priority over strict focal face — face can
            # clip up to 15% if that's what text padding requires.
            has_text = any(e.get("kind") == "text" for e in kept)
            if has_text:
                for focal_tol in FOCAL_FACE_STAGES:
                    center = _fit_center_for_elements(
                        kept, src_w, src_h, tolerance,
                        strict_text=True, focal_tol_override=focal_tol,
                    )
                    if center is not None:
                        kinds = ",".join(str(e.get("kind", "?")) for e in kept)
                        return (center[0], center[1], f"fit-{len(kept)}-of-{len(sorted_el)}-kinds={kinds}-text-pad@face{int(focal_tol*100)}")
            # Pass 2: relaxed text (allow ≤10% clip)
            center = _fit_center_for_elements(kept, src_w, src_h, tolerance, strict_text=False)
            if center is not None:
                kinds = ",".join(str(e.get("kind", "?")) for e in kept)
                return (center[0], center[1], f"fit-{len(kept)}-of-{len(sorted_el)}-kinds={kinds}")

    # Last resort: primary's own center, clamped to source edges.
    primary = sorted_el[0]
    bb = primary["bbox"]
    cx = (float(bb["x0"]) + float(bb["x1"])) / 2.0
    cy = (float(bb["y0"]) + float(bb["y1"])) / 2.0
    return (max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy)), "primary-only-oversized")


def resolve_crop_center(
    subject_bbox: dict[str, Any] | None,
    text_bbox: dict[str, Any] | None,
    src_w: int,
    src_h: int,
    text_clip_tolerance: float = 0.10,
) -> tuple[float, float, str]:
    """Compatibility shim — wraps the generalized resolver for the old
    (subject + text) signature. New code should call `resolve_crop_center_generic`
    directly with a full elements list."""
    elements: list[dict[str, Any]] = []
    if subject_bbox:
        elements.append({"bbox": subject_bbox, "importance": 1, "kind": "character"})
    if text_bbox:
        elements.append({"bbox": text_bbox, "importance": 2, "kind": "text"})
    if not elements:
        return (0.5, 0.5, "no-subject-fallback-center")
    return resolve_crop_center_generic(elements, src_w, src_h, tolerance=text_clip_tolerance)


def compute_crop_box(src_w: int, src_h: int, subject_x_frac: float, subject_y_frac: float) -> tuple[int, int, int, int]:
    """Compute a 9:16 crop centered on the subject, clamped to source edges.

    Returns (left, top, right, bottom) in pixel coords for PIL .crop().
    """
    src_aspect = src_w / src_h
    if src_aspect > TARGET_ASPECT:
        # Source wider than target — crop width, keep full height.
        crop_w = int(round(src_h * TARGET_ASPECT))
        crop_h = src_h
        subject_x_px = subject_x_frac * src_w
        left = int(round(subject_x_px - crop_w / 2))
        left = max(0, min(left, src_w - crop_w))
        top = 0
    else:
        # Source taller than target — crop height, keep full width.
        # (rare — widescreen → portrait usually falls into the first branch)
        crop_w = src_w
        crop_h = int(round(src_w / TARGET_ASPECT))
        subject_y_px = subject_y_frac * src_h
        top = int(round(subject_y_px - crop_h / 2))
        top = max(0, min(top, src_h - crop_h))
        left = 0
    return (left, top, left + crop_w, top + crop_h)


def process_chunk(
    chunk: dict[str, Any],
    session_dir: Path,
    client: VisionClient,
    force: bool,
    dry_run: bool,
) -> dict[str, Any]:
    cid = chunk.get("id", "?")
    rel_path = chunk.get("image_path")
    if not rel_path:
        return {"id": cid, "status": "skip-no-image-path"}
    src_path = session_dir / rel_path
    if not src_path.exists():
        return {"id": cid, "status": "skip-missing-source", "path": str(src_path)}

    out_dir = session_dir / "source" / "generated-assets" / "scenes" / "mobile"
    out_path = out_dir / f"{cid}-mobile.png"
    if out_path.exists() and not force:
        return {"id": cid, "status": "skip-exists", "out": str(out_path)}

    # Ask Qwen for subject center.
    try:
        b64 = encode_image(src_path)
    except Exception as e:
        return {"id": cid, "status": "error-encode", "error": str(e)[:200]}

    # Pass NARRATION (the audible line, ground truth), NOT beat_description
    # (a pre-render brief that can disagree with the actual pixels).
    # Narration is the "message" Qwen tests each element against.
    narration_parts = []
    for b in chunk.get("beats", []) or []:
        t = (b.get("narration") or "").strip()
        if t:
            narration_parts.append(t)
    narration = " ".join(narration_parts) if narration_parts else "(no narration — silent beat)"
    user_prompt = USER_PROMPT_TEMPLATE.format(narration=narration)

    # Tiered Qwen calls: 1 call for easy chunks, escalate to median-of-3 for
    # hard chunks. "Hard" triggers:
    #   - 2+ characters (spatial variance matters most here; crowded scenes
    #     are where single-run bboxes are least reliable)
    #   - OR low/medium Qwen confidence flag
    # A third trigger (fit-dropped-to-focal-only) is checked AFTER the
    # resolver runs — if the initial fit couldn't keep any constraints, we
    # re-run to see if better bboxes allow a fuller fit.
    parsed_runs: list[dict[str, Any]] = []
    first = client.call(SYSTEM_PROMPT, user_prompt, b64)
    if first is None:
        return {"id": cid, "status": "error-vision-call"}
    parsed_runs.append(first)

    def _is_hard(parsed_obj: dict[str, Any]) -> bool:
        els = parsed_obj.get("elements") or []
        char_count = sum(1 for e in els if e.get("kind") == "character")
        conf = (parsed_obj.get("confidence") or "").lower()
        return char_count >= 2 or conf in ("low", "medium")

    if _is_hard(first):
        for _ in range(2):
            r = client.call(SYSTEM_PROMPT, user_prompt, b64)
            if r is not None:
                parsed_runs.append(r)

    parsed = _merge_qwen_runs(parsed_runs) or parsed_runs[0]

    # New schema: elements[] with bbox + importance + kind.
    elements = parsed.get("elements") or []
    conf = parsed.get("confidence", "unknown")

    # Override Qwen's bboxes with OCR-derived bboxes whenever the element's
    # location is anchored to visible text. Qwen has high spatial error on
    # small elements; OCR (Tesseract) is deterministic for text regions.
    # Applies to:
    #   - kind=text elements (always — text IS the thing to locate)
    #   - kind=object/character elements whose description references text
    #     (e.g. "sticky note labeled 'redo'", "book saying X", "sign reads Y")
    #     — because OCR tells us where that text actually is, which anchors
    #     the object to the correct position.
    ocr_bbox_cached: dict[str, float] | None | str = "not-computed"

    def _desc_references_text(desc: str) -> bool:
        dl = (desc or "").lower()
        # Quoted strings or explicit text-on-object phrases
        return (
            "'" in desc
            or '"' in desc
            or " labeled " in dl
            or " saying " in dl
            or " reads " in dl
            or " titled " in dl
            or " with '" in dl
        )

    for e in list(elements):
        needs_ocr = e.get("kind") == "text" or (
            e.get("kind") in ("object", "character")
            and _desc_references_text(e.get("description", ""))
        )
        if not needs_ocr:
            continue
        if ocr_bbox_cached == "not-computed":
            ocr_bbox_cached = ocr_text_bbox(src_path)
        if ocr_bbox_cached is None:
            # OCR found no text anywhere. For text elements, drop.
            # For object/character elements, keep Qwen's bbox (best available).
            if e.get("kind") == "text":
                elements = [x for x in elements if x is not e]
            continue
        e["bbox"] = ocr_bbox_cached
        e["_ocr_override"] = True

    # Load source to get true dimensions, then compute crop center geometrically.
    try:
        img = Image.open(src_path).convert("RGB")
        src_w, src_h = img.size
    except Exception as e:
        return {"id": cid, "status": "error-open", "error": str(e)[:200]}

    try:
        x, y, reason = resolve_crop_center_generic(elements, src_w, src_h)
    except Exception as e:
        return {"id": cid, "status": "error-resolve", "error": str(e)[:200], "raw": parsed}

    # Post-resolve escalation: if the initial fit dropped to focal-only AND
    # there were 2+ elements, re-run with more Qwen calls to see if better
    # bboxes allow a fuller fit. Only escalate if we haven't already (single
    # call so far).
    if len(parsed_runs) == 1 and len(elements) >= 2 and reason.startswith("fit-1-of-"):
        for _ in range(2):
            r = client.call(SYSTEM_PROMPT, user_prompt, b64)
            if r is not None:
                parsed_runs.append(r)
        if len(parsed_runs) > 1:
            parsed = _merge_qwen_runs(parsed_runs) or parsed_runs[0]
            # Redo OCR overrides + resolve with the merged bboxes
            elements = parsed.get("elements") or []
            ocr_bbox_cached = "not-computed"
            for e in list(elements):
                needs_ocr = e.get("kind") == "text" or (
                    e.get("kind") in ("object", "character")
                    and _desc_references_text(e.get("description", ""))
                )
                if not needs_ocr:
                    continue
                if ocr_bbox_cached == "not-computed":
                    ocr_bbox_cached = ocr_text_bbox(src_path)
                if ocr_bbox_cached is None:
                    if e.get("kind") == "text":
                        elements = [x for x in elements if x is not e]
                    continue
                e["bbox"] = ocr_bbox_cached
                e["_ocr_override"] = True
            try:
                x, y, reason = resolve_crop_center_generic(elements, src_w, src_h)
            except Exception:
                pass  # keep the original result

    if dry_run:
        return {
            "id": cid,
            "status": "dry-run",
            "subject": {"x": round(x, 3), "y": round(y, 3)},
            "reason": reason,
            "elements": elements,
            "confidence": conf,
        }

    # Letterbox fallback for text-only cards: if the focal is kind=text AND the
    # text bbox is wider than a 9:16 crop can contain even with tolerance, the
    # crop will always clip words. Scale-to-fit the widescreen into the mobile
    # canvas with paper-colored bars instead. Preserves every word at smaller
    # size. Caught on dev-log-02 C4 "how I caught an AI lying" title card.
    did_letterbox = False
    try:
        focal = next((e for e in elements if e.get("importance") == 1), None)
        if focal and focal.get("kind") == "text":
            tb = focal.get("bbox") or {}
            text_w_frac = float(tb.get("x1", 0)) - float(tb.get("x0", 0))
            crop_w_frac = (src_h * TARGET_ASPECT) / src_w if src_w > 0 else 0.316
            # 10% tolerance: if text is >110% of crop width, can't fit any crop
            if text_w_frac > crop_w_frac * 1.10:
                did_letterbox = True
                scale = min(MOBILE_W / src_w, MOBILE_H / src_h)
                new_w = int(round(src_w * scale))
                new_h = int(round(src_h * scale))
                scaled = img.resize((new_w, new_h), Image.LANCZOS)
                paper = img.getpixel((5, 5))  # sample bg from top-left
                canvas = Image.new("RGB", (MOBILE_W, MOBILE_H), paper)
                canvas.paste(scaled, ((MOBILE_W - new_w) // 2, (MOBILE_H - new_h) // 2))
                out_dir.mkdir(parents=True, exist_ok=True)
                canvas.save(out_path, format="PNG")
                reason = f"letterbox-text-too-wide ({text_w_frac:.2f}>crop {crop_w_frac:.2f})"
        if not did_letterbox:
            box = compute_crop_box(src_w, src_h, x, y)
            cropped = img.crop(box)
            content = cropped.resize((MOBILE_W, CONTENT_H), Image.LANCZOS)
            out_dir.mkdir(parents=True, exist_ok=True)
            if CONTENT_H == MOBILE_H:
                content.save(out_path, format="PNG")
            else:
                # 1:1 (or any non-9:16) — letterbox content into 1080x1920 black canvas.
                canvas = Image.new("RGB", (MOBILE_W, MOBILE_H), (0, 0, 0))
                canvas.paste(content, (0, (MOBILE_H - CONTENT_H) // 2))
                canvas.save(out_path, format="PNG")
    except Exception as e:
        return {"id": cid, "status": "error-crop", "error": str(e)[:200]}

    return {
        "id": cid,
        "status": "ok",
        "subject": {"x": round(x, 3), "y": round(y, 3)},
        "reason": reason,
        "elements": elements,
        "confidence": conf,
        "crop_box": None if did_letterbox else list(box),
        "letterbox": did_letterbox,
        "out": str(out_path.relative_to(session_dir)),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--only", default=None, help="comma-separated chunk ids")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--force", action="store_true", help="regenerate even if mobile PNG exists")
    p.add_argument("--dry-run", action="store_true", help="call Qwen but don't write mobile PNGs")
    p.add_argument("--provider", default=DEFAULT_PROVIDER)
    p.add_argument("--model", default=None)
    p.add_argument("--aspect", default="9:16", choices=["9:16", "1:1"], help="target crop aspect; 1:1 is letterboxed inside the 1080x1920 mobile canvas")
    args = p.parse_args()

    global TARGET_ASPECT, CONTENT_H
    if args.aspect == "1:1":
        TARGET_ASPECT = 1.0
        CONTENT_H = MOBILE_W  # 1080x1080 content centered in 1080x1920 canvas
    else:
        TARGET_ASPECT = 9 / 16
        CONTENT_H = MOBILE_H

    session_dir = CONTENT_ROOT / "sessions" / args.session
    shot_list = load_shot_list(args.session)
    chunks = shot_list.get("chunks", [])
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        chunks = [c for c in chunks if c.get("id") in want]

    model = args.model or DEFAULT_MODEL_BY_PROVIDER[args.provider]
    client = VisionClient(args.provider, model)

    print(f"[smart-crop] session={args.session} chunks={len(chunks)} model={model} parallel={args.parallel}")

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {ex.submit(process_chunk, c, session_dir, client, args.force, args.dry_run): c.get("id") for c in chunks}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            results.append(r)
            cid = r.get("id")
            status = r.get("status")
            extra = ""
            if status == "ok":
                s = r.get("subject", {})
                extra = f" subject=({s.get('x')},{s.get('y')}) conf={r.get('confidence')}"
            elif status and status.startswith("error"):
                extra = f" error={r.get('error') or r.get('raw')}"
            print(f"[smart-crop] {cid:5} {status}{extra}")

    # Summary
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
    print(f"\n[smart-crop] summary: {by_status}")

    # Write report.
    working_dir = session_dir / "working"
    working_dir.mkdir(exist_ok=True)
    report_path = working_dir / "smart-crop-report.json"
    report_path.write_text(json.dumps({"session": args.session, "results": results}, indent=2))
    print(f"[smart-crop] report -> {report_path}")

    return 0 if all(r.get("status") in ("ok", "skip-exists", "skip-no-image-path", "dry-run") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
