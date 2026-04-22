#!/usr/bin/env python3
"""Structural validator for a spoolcast shot-list.

Layer 1 of the two-layer durability gate described in STORY.md § Part 2
"Two-layer enforcement". This is the deterministic schema check that runs
before build_preview_data.py. The semantic layer (viewer-cognition,
overweight, preview-structure) lives in audit_narration.py.

Usage:
    scripts/.venv/bin/python scripts/validate_shot_list.py \\
        --session spoolcast-explainer

Reads: ../spoolcast-content/sessions/<session>/shot-list/shot-list.json

Exit codes:
    0 = no errors
    1 = at least one validation error
    3 = shot-list missing / unreadable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

ALLOWED_BOUNDARY_KIND = {"continues-thread", "topic-shift", "act-boundary", "bumper"}
ALLOWED_WEIGHT = {"normal", "high"}
ALLOWED_IMAGE_SOURCE = {
    "generated",
    "proof",
    "reuse",
    "meme",
    "broll",
    "broll_image",
    "external_screenshot",
    "external_xlsx",
    "external_json",
    "external_terminal",
    "external_audio",
    "composite_pilot",
}
BROLL_SOURCES = {"broll", "broll_image"}
REVEAL_GROUP_MAX = 5

# Short-beat suppression patterns — beats whose short length is explained by
# list-enumeration or closing-conclusion structure, not by deadpan comedic
# punctuation. Mirrors audit_narration.py's bridge-flag suppression so the
# two validators agree. See STORY.md § Bridge archetypes for the source.
import re as _re
_LIST_MARKER_RE = _re.compile(
    r"^\s*("
    r"One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|"
    r"First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|"
    r"Then|Finally|Lastly|Next"
    r")\b[\.,:]",
    _re.IGNORECASE,
)
_STEP_MARKER_RE = _re.compile(r"^\s*Step\s+\d+\s*[\.:]", _re.IGNORECASE)
_NUM_MARKER_RE = _re.compile(r"^\s*\d+\s*[\.\):](?!\d)")
_CLOSING_MARKER_RE = _re.compile(
    r"^\s*("
    r"So|In short|In conclusion|To recap|To summarize|"
    r"Zooming out|Step back|Stepping back|"
    r"Which brings us|All of this means|Here'?s the frame|"
    r"Bottom line|Put differently|The upshot"
    r")\b[\.,:]?",
    _re.IGNORECASE,
)

# Read-time: seconds per on-screen-text word. Floor from STORY.md § On-screen text read-time.
READTIME_SECONDS_PER_WORD = 0.35

# TTS narration estimate: average words per second at 1.0x playback.
# Used to estimate chunk duration for the read-time floor check when no audio
# files exist yet. Close to real TTS pacing (~150 wpm).
TTS_WORDS_PER_SEC = 2.5

# Pause tiers (seconds, at user-facing playback rate).
PAUSE_TIERS = {"tight": 0.15, "short": 0.3, "medium": 0.6, "long": 1.2}

# Punchline detector: any beat whose narration is ≤3 whitespace-tokens.
PUNCHLINE_MAX_WORDS = 3

# Broll source kinds that require tv-screen framing per VISUALS.md.
TV_FRAME_REQUIRED_SOURCES = {"sibling-video", "self-reject"}
ALLOWED_BROLL_SOURCE_KINDS = {
    "sibling-video",
    "self-reject",
    "external-capture",
    "meme",
    "stock",
}
ALLOWED_BROLL_FRAMINGS = {"tv-screen", "full-frame", "inset"}


def load_shot_list(session: str) -> dict[str, Any]:
    path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: shot-list not found at {path}", file=sys.stderr)
        sys.exit(3)
    with path.open() as f:
        return json.load(f)


def load_session_config(session: str) -> dict[str, Any]:
    """Load session.json; returns empty dict if missing (legacy/partial sessions)."""
    path = CONTENT_ROOT / "sessions" / session / "session.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _collect_available_references(session_cfg: dict[str, Any]) -> set[str]:
    """Return the set of reference names visible to this session.

    Union of:
    - session.json `characters` / `objects` (session-local overrides)
    - style library's `references` map, if session has a `style` field and the
      style exists on disk

    Used to validate chunk.references.
    """
    names: set[str] = set()
    for key in ("characters", "objects"):
        for n in (session_cfg.get(key) or {}).keys():
            names.add(n)
    style_name = session_cfg.get("style")
    if style_name:
        style_json = CONTENT_ROOT / "styles" / style_name / "style.json"
        if style_json.exists():
            try:
                style_data = json.loads(style_json.read_text())
                for n in (style_data.get("references") or {}).keys():
                    names.add(n)
            except Exception:
                pass
    return names


def _word_count(text: str) -> int:
    return len((text or "").split())


# Bumper chunks don't have beats — they play a silent title card for a fixed
# window (~1.5-2s per PIPELINE.md § boundary_kind act-boundary).
BUMPER_DEFAULT_DURATION_SEC = 1.75


def _estimate_chunk_duration_sec(chunk: dict[str, Any], playback_rate: float) -> float:
    """Estimate the user-facing duration of a chunk.

    Precedence:
    1. Explicit `hold_duration_sec` field wins (used on silent-hold chunks
       whose duration doesn't come from narration + pause_after).
    2. Bumpers default to BUMPER_DEFAULT_DURATION_SEC (no beats, fixed card).
    3. Otherwise sum over beats:
       (narration_words / TTS_WORDS_PER_SEC / playback_rate) + pause_after.

    Approximation — actual duration comes from the rendered audio and may
    differ slightly. Close enough to catch egregious under-timing.
    """
    hold = chunk.get("hold_duration_sec")
    if isinstance(hold, (int, float)) and hold > 0:
        return float(hold)
    if (chunk.get("boundary_kind") or "").strip() == "bumper":
        return BUMPER_DEFAULT_DURATION_SEC
    total = 0.0
    for b in chunk.get("beats") or []:
        words = _word_count(b.get("narration") or "")
        narration_sec = (words / TTS_WORDS_PER_SEC) / max(playback_rate, 0.1)
        pause = PAUSE_TIERS.get((b.get("pause_after") or "short").lower(), 0.3)
        total += narration_sec + pause
    return total


def _estimate_paint_on_sec(chunk: dict[str, Any], playback_rate: float) -> float:
    """Estimate the paint-on (eraser-wipe) duration for a chunk.

    Mirrors build_preview_data.py's wipe_in_sec formula so the read-time
    validator uses the same number the renderer will actually produce.

    Rules (build_preview_data.py entrance logic):
      - proof / meme / broll / broll_image chunks: hard cut in, paint-on = 0
      - first chunk of video: paint-on
      - chunk after a proof: paint-on
      - standalone or callback-* continuity: paint-on
      - otherwise: hard cut in, paint-on = 0

    Duration when paint-on fires: max(0.5, min(chunk_sec * 0.2, 1.5)).
    """
    src = (chunk.get("image_source") or "generated").strip()
    if src in {"proof", "meme", "broll", "broll_image"}:
        return 0.0
    cont = (chunk.get("continuity") or "standalone").strip()
    # We don't know chunk index here; callers apply the "first-chunk" rule
    # externally when needed. Treat standalone/callback as paint-on candidates.
    if cont == "standalone" or cont.startswith("callback"):
        chunk_sec = _estimate_chunk_duration_sec(chunk, playback_rate)
        return max(0.5, min(chunk_sec * 0.2, 1.5))
    return 0.0


def _check_readtime(chunks: list[dict[str, Any]], playback_rate: float) -> list[tuple[str, str]]:
    """Read-time floor: on-screen-text word count × 0.35s <= readable window.

    The readable window is the part of the chunk AFTER the paint-on
    (eraser-wipe) finishes. During paint-on the text isn't fully legible,
    so that time doesn't count toward the read-time budget. See STORY.md §
    On-screen text read-time.

    Author opt-out: set `readtime_override: true` on a chunk to bypass this
    check when the author is deliberately picking a shorter hold by ear
    (typical reason: card is familiar from earlier in the video, or the
    viewer is meant to glance rather than read). The override is explicit
    so intent is recorded, not silently skipped.
    """
    errors: list[tuple[str, str]] = []
    first_chunk_id = chunks[0].get("id") if chunks else None
    for c in chunks:
        cid = c.get("id") or "<unnamed>"
        if c.get("readtime_override") is True:
            continue
        osts = c.get("on_screen_text") or []
        if not osts:
            continue
        if not isinstance(osts, list) or not all(isinstance(s, str) for s in osts):
            errors.append((cid, "on_screen_text must be an array of strings"))
            continue
        total_words = sum(_word_count(s) for s in osts)
        if total_words == 0:
            continue
        floor = total_words * READTIME_SECONDS_PER_WORD
        duration = _estimate_chunk_duration_sec(c, playback_rate)
        paint_on = _estimate_paint_on_sec(c, playback_rate)
        # First chunk of the video always paints on, regardless of continuity.
        if cid == first_chunk_id and paint_on == 0.0:
            chunk_sec = _estimate_chunk_duration_sec(c, playback_rate)
            paint_on = max(0.5, min(chunk_sec * 0.2, 1.5))
        readable = duration - paint_on
        if readable + 0.05 < floor:  # tiny tolerance for rounding
            errors.append(
                (
                    cid,
                    f"on-screen text needs {floor:.1f}s to read "
                    f"({total_words} words × {READTIME_SECONDS_PER_WORD}) "
                    f"but readable window is only {readable:.1f}s "
                    f"(chunk {duration:.1f}s minus paint-on {paint_on:.1f}s) — "
                    f"add pause_after, set hold_duration_sec, or reduce on-screen text",
                )
            )
    return errors


def _check_deadpan_punchline(chunks: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Flag short comedic beats buried inside multi-beat chunks.

    A beat whose narration is ≤3 words is almost always a deadpan punchline
    (Rejected. / Obviously. / That's it.) and per STORY.md § 849 belongs in
    its own chunk so the image changes exactly when the line lands.
    """
    errors: list[tuple[str, str]] = []
    for c in chunks:
        cid = c.get("id") or "<unnamed>"
        bk = (c.get("boundary_kind") or "").strip()
        if bk == "bumper":
            continue  # bumpers have no narration
        beats = c.get("beats") or []
        if len(beats) <= 1:
            continue  # single-beat chunk is already the punchline form
        for b in beats:
            narr = (b.get("narration") or "").strip()
            words = _word_count(narr)
            if not (0 < words <= PUNCHLINE_MAX_WORDS):
                continue
            # Author override: beat or chunk can opt out explicitly when the
            # short line is structurally a list-preview, callback cue, or
            # other non-deadpan form the regex patterns don't recognize.
            if b.get("not_a_punchline") is True or c.get("not_a_punchline") is True:
                continue
            # Suppress: short beats that are list-enumeration openers or
            # closing-conclusion bridges — those are structural, not deadpan.
            if (
                _LIST_MARKER_RE.match(narr)
                or _STEP_MARKER_RE.match(narr)
                or _NUM_MARKER_RE.match(narr)
                or _CLOSING_MARKER_RE.match(narr)
            ):
                continue
            bid = b.get("id") or "?"
            errors.append(
                (
                    cid,
                    f"beat {bid} narration is {words} word(s) ({b.get('narration')!r}) "
                    f"inside a multi-beat chunk — deadpan punchlines need their own "
                    f"chunk with punchline: true and image_source: meme "
                    f"(see STORY.md § Deadpan punchlines)",
                )
            )
    return errors


def _check_punchline_chunk_shape(chunks: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """When punchline: true is set, enforce the chunk shape.

    - exactly one beat
    - image_source is meme or broll_image
    """
    errors: list[tuple[str, str]] = []
    for c in chunks:
        if not c.get("punchline"):
            continue
        cid = c.get("id") or "<unnamed>"
        beats = c.get("beats") or []
        if len(beats) != 1:
            errors.append(
                (cid, f"punchline: true requires exactly 1 beat, got {len(beats)}")
            )
        isrc = (c.get("image_source") or "generated").strip()
        overlays = c.get("overlays") or []
        # Two valid punchline forms (VISUALS.md § Punchline Chunk Carve-Out):
        # - full-frame substitution: image_source in {meme, broll_image}
        # - overlay on reused prior scene: image_source = reuse, with a
        #   non-empty overlays array describing the stamp/reaction artifact
        is_full_frame = isrc in {"meme", "broll_image"}
        is_overlay_form = isrc == "reuse" and isinstance(overlays, list) and len(overlays) > 0
        if not (is_full_frame or is_overlay_form):
            errors.append(
                (
                    cid,
                    f"punchline: true requires either (a) image_source in "
                    f"{{meme, broll_image}} for full-frame form, or (b) "
                    f"image_source='reuse' with a non-empty overlays array "
                    f"for overlay-on-reused-scene form (got image_source={isrc!r}, "
                    f"overlays_count={len(overlays) if isinstance(overlays, list) else 'invalid'})",
                )
            )
    return errors


def _check_broll_framing(chunks: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Previous-video broll must be framed inside a TV/monitor graphic.

    When image_source is broll/broll_image AND broll_source_kind is
    sibling-video or self-reject, broll_framing must be tv-screen.
    """
    errors: list[tuple[str, str]] = []
    for c in chunks:
        cid = c.get("id") or "<unnamed>"
        isrc = (c.get("image_source") or "").strip()
        if isrc not in BROLL_SOURCES:
            continue
        bsk = (c.get("broll_source_kind") or "").strip()
        bf = (c.get("broll_framing") or "").strip()
        if not bsk:
            errors.append((cid, "broll missing broll_source_kind"))
        elif bsk not in ALLOWED_BROLL_SOURCE_KINDS:
            errors.append(
                (cid, f"invalid broll_source_kind: {bsk!r} "
                 f"(expected one of {sorted(ALLOWED_BROLL_SOURCE_KINDS)})")
            )
        if not bf:
            errors.append((cid, "broll missing broll_framing"))
        elif bf not in ALLOWED_BROLL_FRAMINGS:
            errors.append(
                (cid, f"invalid broll_framing: {bf!r} "
                 f"(expected one of {sorted(ALLOWED_BROLL_FRAMINGS)})")
            )
        if bsk in TV_FRAME_REQUIRED_SOURCES and bf and bf != "tv-screen":
            errors.append(
                (
                    cid,
                    f"broll_source_kind={bsk!r} requires broll_framing='tv-screen' "
                    f"(got {bf!r}) — previous-video broll must be composited "
                    f"inside a TV/monitor with dimmed background and play-icon "
                    f"overlay (see VISUALS.md § Previous-video broll framing)",
                )
            )
    return errors


def validate(shot_list: dict[str, Any], session: str | None = None) -> list[tuple[str, str]]:
    """Returns a list of (chunk_id, error_message). Empty list = pass."""
    errors: list[tuple[str, str]] = []
    chunks = shot_list.get("chunks", [])
    if not chunks:
        errors.append(("<shot-list>", "no chunks found"))
        return errors

    # Load session config once for reference-registry lookups.
    session_cfg: dict[str, Any] = {}
    available_refs: set[str] = set()
    if session:
        session_cfg = load_session_config(session)
        available_refs = _collect_available_references(session_cfg)

    # Playback rate for read-time duration estimates. Reads tts_playback_rate
    # from session.json (defaults to 1.0 if absent).
    try:
        playback_rate = float(session_cfg.get("tts_playback_rate") or 1.0)
    except (TypeError, ValueError):
        playback_rate = 1.0

    # Per-chunk field checks
    for c in chunks:
        cid = c.get("id") or "<unnamed>"
        bk = (c.get("boundary_kind") or "").strip()
        w = (c.get("weight") or "").strip()
        isrc = (c.get("image_source") or "generated").strip()

        if bk not in ALLOWED_BOUNDARY_KIND:
            if bk == "":
                errors.append((cid, "missing boundary_kind"))
            else:
                errors.append((cid, f"invalid boundary_kind: {bk!r}"))
        if w not in ALLOWED_WEIGHT:
            if w == "":
                errors.append((cid, "missing weight"))
            else:
                errors.append((cid, f"invalid weight: {w!r}"))
        if isrc not in ALLOWED_IMAGE_SOURCE:
            errors.append((cid, f"invalid image_source: {isrc!r}"))

        if bk == "act-boundary":
            if not (c.get("act_title") or "").strip():
                errors.append((cid, "act-boundary missing act_title"))
            if not (c.get("act_opener_line") or "").strip():
                errors.append((cid, "act-boundary missing act_opener_line"))
        if bk == "bumper":
            if not (c.get("act_title") or "").strip():
                errors.append((cid, "bumper missing act_title"))
            if c.get("beats"):
                errors.append((cid, "bumper has beats (should be empty)"))
        else:
            # Non-bumper chunks must have at least one beat.
            # Broll chunks may use a silent placeholder beat (empty narration)
            # because the clip plays its own audio — see build_preview_data.py.
            beats = c.get("beats") or []
            if not beats:
                errors.append((cid, "no beats"))
            # Silent-hold chunks (image_source: reuse with explicit hold_duration_sec
            # or marked silent_hold: true) legitimately have empty narration —
            # they're silent beats that let the viewer read the prior frame.
            silent_hold = (
                isrc == "reuse"
                and (c.get("silent_hold") is True or c.get("hold_duration_sec"))
            )
            for b in beats:
                if not (b.get("id") or "").strip():
                    errors.append((cid, "beat missing id"))
                if (
                    isrc not in BROLL_SOURCES
                    and not silent_hold
                    and not (b.get("narration") or "").strip()
                ):
                    bid = b.get("id") or "?"
                    errors.append((cid, f"beat {bid} missing narration"))

        if isrc in BROLL_SOURCES:
            cj = (c.get("context_justification") or "").strip().lower()
            if not cj or cj == "none":
                errors.append((cid, "broll missing context_justification"))

        # References field — each name must resolve to a registered character/object
        # in the session's registry or its style library. Only checked when a
        # session context is available.
        refs = c.get("references") or []
        if refs:
            if not isinstance(refs, list):
                errors.append((cid, f"references must be a list, got {type(refs).__name__}"))
            else:
                if session is not None:
                    for name in refs:
                        if not isinstance(name, str) or not name.strip():
                            errors.append((cid, f"references entry invalid: {name!r}"))
                            continue
                        if name not in available_refs:
                            errors.append(
                                (
                                    cid,
                                    f"references entry {name!r} not found in session registry "
                                    f"or style library (available: {sorted(available_refs) or 'none'})",
                                )
                            )

    # Adjacency / structural checks
    prev_nonbumper: dict[str, Any] | None = None
    for i, c in enumerate(chunks):
        cid = c.get("id") or "<unnamed>"
        bk = (c.get("boundary_kind") or "").strip()

        # Scene-change default: crossing a scene boundary cannot be continues-thread
        if bk != "bumper":
            if (
                prev_nonbumper is not None
                and c.get("scene") != prev_nonbumper.get("scene")
                and bk == "continues-thread"
            ):
                errors.append(
                    (
                        cid,
                        f"scene changed ({prev_nonbumper.get('scene')!r} -> "
                        f"{c.get('scene')!r}) but boundary_kind=continues-thread",
                    )
                )
            prev_nonbumper = c

        # Act-boundary must be first chunk OR preceded by a bumper
        if bk == "act-boundary":
            if i == 0:
                pass  # allowed: video can open on an Act
            else:
                prev_bk = (chunks[i - 1].get("boundary_kind") or "").strip()
                if prev_bk != "bumper":
                    errors.append((cid, "act-boundary not preceded by a bumper chunk"))

        # Bumper must be followed by an act-boundary
        if bk == "bumper":
            if i + 1 >= len(chunks):
                errors.append((cid, "bumper is the last chunk (no act-boundary follows)"))
            else:
                next_bk = (chunks[i + 1].get("boundary_kind") or "").strip()
                if next_bk != "act-boundary":
                    errors.append((cid, "bumper not immediately followed by act-boundary"))

    # Read-time floor (STORY.md § On-screen text read-time)
    errors.extend(_check_readtime(chunks, playback_rate))

    # Deadpan punchlines must own their chunk (STORY.md § 849)
    errors.extend(_check_deadpan_punchline(chunks))

    # Punchline-chunk shape (exactly one beat, image_source meme/broll_image)
    errors.extend(_check_punchline_chunk_shape(chunks))

    # Previous-video broll must be TV-framed (VISUALS.md § Previous-video broll framing)
    errors.extend(_check_broll_framing(chunks))

    # Reveal-group checks (adjacency, size, scene containment, bumper exclusion)
    group_indices: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        rg = (c.get("reveal_group") or "").strip()
        if rg:
            group_indices.setdefault(rg, []).append(i)

    for rg, idxs in group_indices.items():
        head_id = chunks[idxs[0]].get("id") or "<unnamed>"
        # Adjacency: consecutive indices
        for a, b in zip(idxs, idxs[1:]):
            if b != a + 1:
                errors.append(
                    (chunks[b].get("id") or "<unnamed>",
                     f"reveal_group {rg!r} non-adjacent "
                     f"(prev at index {a}, this at index {b})")
                )
        # Size cap
        if len(idxs) > REVEAL_GROUP_MAX:
            errors.append(
                (head_id, f"reveal_group {rg!r} size {len(idxs)} > {REVEAL_GROUP_MAX}")
            )
        # Scene containment (same Act)
        scenes = {chunks[i].get("scene") for i in idxs}
        if len(scenes) > 1:
            errors.append(
                (head_id, f"reveal_group {rg!r} spans scenes {sorted(s or '' for s in scenes)}")
            )
        # No bumper/act-boundary inside a group
        for i in idxs:
            bk = (chunks[i].get("boundary_kind") or "").strip()
            if bk in ("bumper", "act-boundary"):
                errors.append(
                    (chunks[i].get("id") or "<unnamed>",
                     f"reveal_group contains {bk!r} chunk (not allowed)")
                )

    return errors


def print_report(session: str, errors: list[tuple[str, str]]) -> None:
    print(f"=== validate_shot_list: {session} ===")
    if not errors:
        print("OK — no structural errors.")
        return
    # Group by chunk id, preserving first-seen order
    by_chunk: dict[str, list[str]] = {}
    for cid, msg in errors:
        by_chunk.setdefault(cid, []).append(msg)
    print(f"{len(errors)} errors across {len(by_chunk)} chunks:")
    print()
    for cid, msgs in by_chunk.items():
        print(f"  {cid}")
        for m in msgs:
            print(f"    - {m}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Structural validator for a spoolcast shot-list (Layer 1).",
    )
    p.add_argument("--session", required=True, help="Session ID, e.g. spoolcast-explainer")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    shot_list = load_shot_list(args.session)
    errors = validate(shot_list, session=args.session)
    print_report(args.session, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
