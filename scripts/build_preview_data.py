"""
build_preview_data.py — generate the Remotion preview-data from shot-list.json.

Reads:
    ../spoolcast-content/sessions/<session>/shot-list/shot-list.json

Reads audio durations via mutagen from:
    ../spoolcast-content/sessions/<session>/source/audio/<beat_id>.mp3

Writes:
    <repo>/src/data/preview-data.json

Only includes chunks that are fully renderable (image file exists + all
beat audio files exist). Chunks missing any prerequisite are skipped so
a partial render can be done while other generations are still running.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mutagen.mp3 import MP3  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

PAUSE_SECONDS = {
    "": 0.3,
    "none": 0.0,
    "tight": 0.15,  # rapid-fire cadence (default inside reveal groups)
    "short": 0.3,
    "medium": 0.5,  # was 0.8 — felt excessive on mid-length chunks
    "long": 0.8,    # was 1.5 — felt dead; 0.8 is a real breath without stalling
}

# Default pause between chunks INSIDE a reveal group, in seconds. Overrides the
# beat's normal pause_after unless the author set an explicit value. See
# STORY.md § Part 2 "Reveal groups".
REVEAL_GROUP_DEFAULT_PAUSE_SEC = 0.15


def _resolve_pause_seconds(pause_after: str) -> float | None:
    """Resolve a `pause_after` value to seconds. Returns None if unrecognized
    (caller decides the fallback)."""
    key = (pause_after or "").strip()
    if key in PAUSE_SECONDS:
        return PAUSE_SECONDS[key]
    # Accept explicit seconds like "1.2s" or "0.5"
    try:
        return float(key.rstrip("s"))
    except (ValueError, AttributeError):
        return None


def _compute_reveal_group_positions(chunks: list[dict[str, Any]]) -> dict[str, str]:
    """Returns {chunk_id: "first"|"middle"|"last"|"solo"} for every chunk.

    A reveal group is a run of adjacent chunks sharing the same `reveal_group`
    value. Chunks with no `reveal_group` are "solo" (normal behavior).
    Non-adjacent chunks with the same value are flagged via stderr — the
    validator should catch this earlier.
    """
    positions: dict[str, str] = {}
    i = 0
    seen_groups: set[str] = set()
    while i < len(chunks):
        group = chunks[i].get("reveal_group", "") or ""
        if not group:
            positions[chunks[i]["id"]] = "solo"
            i += 1
            continue
        # Walk forward while group matches and chunks are adjacent.
        j = i
        while j < len(chunks) and chunks[j].get("reveal_group", "") == group:
            j += 1
        run_ids = [c["id"] for c in chunks[i:j]]
        if group in seen_groups:
            print(
                f"[preview-data] WARN: reveal_group {group!r} appears in "
                f"non-adjacent chunks. Treating {run_ids[0]} as its own group.",
                file=sys.stderr,
            )
        seen_groups.add(group)
        if len(run_ids) == 1:
            # Solo-in-group: treat as normal (no suppression).
            positions[run_ids[0]] = "solo"
        else:
            positions[run_ids[0]] = "first"
            for mid in run_ids[1:-1]:
                positions[mid] = "middle"
            positions[run_ids[-1]] = "last"
        i = j
    return positions

ZOOM_VALUES = {
    "": 1.0,
    "wide": 1.0,
    "medium": 1.4,
    "tight": 2.2,
    "close": 3.3,
}


def session_dir(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id


def _audio_path(session_id: str, beat_id: str) -> Path:
    return session_dir(session_id) / "source" / "audio" / f"{beat_id}.mp3"


def _image_abs_path(session_id: str, rel_path: str) -> Path:
    return session_dir(session_id) / rel_path


def _audio_duration_sec(path: Path) -> float | None:
    if not path.exists():
        return None
    try:
        return float(MP3(str(path)).info.length)
    except Exception:
        return None


def build(session_id: str, fps: int | None = None) -> dict[str, Any]:
    sl_path = session_dir(session_id) / "shot-list" / "shot-list.json"
    with open(sl_path) as f:
        shot_list = json.load(f)

    # session config drives playback-rate
    cfg_path = session_dir(session_id) / "session.json"
    session_cfg: dict[str, Any] = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            session_cfg = json.load(f)
    playback_rate = float(session_cfg.get("tts_playback_rate", 1.0))

    canvas = shot_list.get("canvas", {})
    fps_value = fps or canvas.get("fps") or 30
    # Resolve canvas dimensions from aspect_ratio. session.json may
    # override; defaults assume 1080-line full HD.
    aspect = canvas.get("aspect_ratio", "16:9")
    aspect_dims = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),  # mobile / shorts / Reels
        "1:1":  (1080, 1080),  # square / IG feed
        "4:5":  (1080, 1350),  # IG portrait
        "21:9": (2520, 1080),  # ultra-wide
    }
    width, height = aspect_dims.get(aspect, (1920, 1080))
    width = int(session_cfg.get("width", width))
    height = int(session_cfg.get("height", height))

    chunks_out: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    running_frame = 0

    # Reveal-group membership (computed once up front so we know each chunk's
    # position within its group: "first" / "middle" / "last" / "solo").
    reveal_positions = _compute_reveal_group_positions(shot_list.get("chunks", []))

    for chunk in shot_list.get("chunks", []):
        chunk_id = chunk["id"]
        image_rel = chunk.get("image_path", "")
        image_path = _image_abs_path(session_id, image_rel)
        beats = chunk.get("beats") or []
        image_source = chunk.get("image_source", "generated")
        is_broll = image_source == "broll"
        boundary_kind = chunk.get("boundary_kind", "")
        is_bumper = boundary_kind == "bumper"

        # Bumper chunks are standalone title cards — no image, no beats, no audio.
        # Composition.tsx's BumperRenderer draws them from act_title.
        if is_bumper:
            bumper_secs = float(chunk.get("duration_s", 1.8))
            bumper_frames = round(bumper_secs * fps_value)
            chunks_out.append({
                "id": chunk_id,
                "scene": chunk.get("scene", ""),
                "sceneTitle": chunk.get("scene_title", ""),
                "summary": chunk.get("summary", ""),
                "continuity": "standalone",
                "imageSource": "bumper",
                "imageSrc": "",
                "brollFraming": None,
                "startFromSec": 0,
                "overlays": [],
                "startFrame": running_frame,
                "durationFrames": bumper_frames,
                "wipeInFrames": 0,
                "wipeOutFrames": 0,
                "framesDir": "",
                "preGenFrameCount": 0,
                "beats": [],
                "boundary_kind": "bumper",
                "act_title": chunk.get("act_title", ""),
                "weight": chunk.get("weight", "normal"),
            })
            running_frame += bumper_frames
            continue

        if not image_path.exists():
            skipped.append((chunk_id, f"image missing at {image_rel}"))
            continue

        # B-roll chunks with placeholder "silent" beats (empty narration, no mp3
        # expected) bypass the audio-existence check — the mp4 plays its own audio.
        if is_broll:
            pass  # no beat audio required; video plays with original audio
        else:
            missing_audio = [b["id"] for b in beats if not _audio_path(session_id, b["id"]).exists()]
            if missing_audio:
                skipped.append((chunk_id, f"audio missing for beats {missing_audio}"))
                continue

        chunk_start_frame = running_frame
        beats_out: list[dict[str, Any]] = []

        # For broll chunks with placeholder beats, use a fixed-length display
        # derived from beat_description hint or fall back to 6s.
        if is_broll and all(not _audio_path(session_id, b.get("id","")).exists() for b in beats):
            # No audio — derive duration from beat_description hint or chunk notes
            import re as _re
            desc = (chunk.get("beat_description") or "") + " " + (chunk.get("notes") or "")
            m = _re.search(r"(\d+)\s*(?:-\s*(\d+))?\s*sec", desc, _re.IGNORECASE)
            if m:
                secs = (int(m.group(1)) + int(m.group(2) or m.group(1))) / 2
            else:
                secs = 6.0
            dur_frames = round(secs * fps_value)
            # Synthesize a single silent-placeholder beat so timeline lines up
            beats_out.append({
                "id": beats[0].get("id", chunk_id + "-broll") if beats else chunk_id + "-broll",
                "narration": "",
                "audioSrc": "",
                "audioDurationSec": round(secs, 3),
                "startFrameInChunk": 0,
                "endFrameInChunk": dur_frames,
                "pauseFrames": 0,
                "camera": {"reason": "", "target": "", "zoom": "", "zoomValue": 1.0, "transitionSec": 0},
            })
            running_frame += dur_frames
        else:
            reveal_pos = reveal_positions.get(chunk_id, "solo")
            for beat_idx, beat in enumerate(beats):
                raw_dur = _audio_duration_sec(_audio_path(session_id, beat["id"])) or 1.0
                # Speeding up playback shrinks the effective duration.
                dur = raw_dur / playback_rate
                beat_start_rel = running_frame - chunk_start_frame
                dur_frames = round(dur * fps_value)

                is_last_beat_of_chunk = beat_idx == len(beats) - 1
                pause_raw = (beat.get("pause_after", "") or "").strip()
                resolved = _resolve_pause_seconds(pause_raw)
                # Default when unset: 0.3s. But if this is the last beat of a
                # chunk that's first/middle in a reveal group AND the author
                # is using the default ("" or "short"), force tight (0.15s)
                # to preserve BOOM cadence — see STORY.md § Part 2.
                uses_default = pause_raw in ("", "short")
                if (
                    is_last_beat_of_chunk
                    and reveal_pos in ("first", "middle")
                    and uses_default
                ):
                    pause_s = REVEAL_GROUP_DEFAULT_PAUSE_SEC
                else:
                    pause_s = resolved if resolved is not None else 0.3

                pause_frames = round(pause_s * fps_value)

                zoom_label = beat.get("camera_zoom", "") or ""
                beats_out.append({
                    "id": beat["id"],
                    "narration": beat.get("narration", ""),
                    "audioSrc": f"source/audio/{beat['id']}.mp3",
                    "audioDurationSec": round(dur, 3),
                    "startFrameInChunk": beat_start_rel,
                    "endFrameInChunk": beat_start_rel + dur_frames,
                    "pauseFrames": pause_frames,
                    "camera": {
                        "reason": beat.get("camera_reason", "") or "",
                        "target": beat.get("camera_target", "") or "",
                        "zoom": zoom_label,
                        "zoomValue": ZOOM_VALUES.get(zoom_label, 1.0),
                        "transitionSec": float(beat.get("transition_s") or 0),
                    },
                })
                running_frame += dur_frames + pause_frames

        chunk_end_frame = running_frame

        # Honor explicit hold_duration_sec — extend the chunk by the gap
        # between the narrated-beats duration and the requested hold time.
        # Renderer holds the final frame (no paint, no animation) for the
        # extra frames. See PIPELINE.md § hold_duration_sec.
        hold_sec = chunk.get("hold_duration_sec")
        if isinstance(hold_sec, (int, float)) and hold_sec > 0:
            required_frames = round(float(hold_sec) * fps_value)
            current_frames = chunk_end_frame - chunk_start_frame
            if required_frames > current_frames:
                extra = required_frames - current_frames
                running_frame += extra
                chunk_end_frame = running_frame
                # Stretch the last beat's endFrameInChunk so the held frame
                # range is explicit (audio already finished playing).
                if beats_out:
                    last = beats_out[-1]
                    last["endFrameInChunk"] = (
                        last.get("endFrameInChunk", 0) + extra
                    )

        # Check for preprocessed stroke-reveal frames
        frames_dir_abs = session_dir(session_id) / "frames" / chunk_id
        pre_gen_count = 0
        frames_dir_rel = ""
        if frames_dir_abs.exists():
            pre_gen_count = len(list(frames_dir_abs.glob("frame_*.png")))
            if pre_gen_count > 0:
                frames_dir_rel = f"frames/{chunk_id}"

        # Rewrite imageSrc to strip `../` prefixes so staticFile() accepts it.
        # Public symlinks should already cover the other session dirs (see public/).
        def _normalize_src(s: str) -> str:
            # ../pilot/...  →  pilot/...   (requires public/pilot symlink)
            # ../<other>/   →  <other>/    (requires matching symlink)
            if s.startswith("../"):
                return s[len("../"):]
            return s

        # weight:high enforces ≥1.0s silence + linger after the chunk.
        # Bump the last beat's pause to at least 1.0s worth of frames.
        # CRITICAL: extra frames must be folded into THIS chunk's duration,
        # not left as a gap after chunk_end_frame — otherwise the renderer
        # shows composition-white during those frames (visible as a flash
        # between chunks). See VISUALS.md § Inter-chunk transition vocabulary.
        weight = chunk.get("weight", "normal")
        if weight == "high" and beats_out:
            min_tail_frames = round(1.0 * fps_value)
            last = beats_out[-1]
            if last["pauseFrames"] < min_tail_frames:
                added = min_tail_frames - last["pauseFrames"]
                last["pauseFrames"] = min_tail_frames
                running_frame += added
                chunk_end_frame = running_frame  # close the gap

        chunks_out.append({
            "id": chunk_id,
            "scene": chunk.get("scene", ""),
            "sceneTitle": chunk.get("scene_title", ""),
            "summary": chunk.get("summary", ""),
            "continuity": chunk.get("continuity", "standalone"),
            "reveal_direction": chunk.get("reveal_direction", "") or "",
            "imageSource": image_source,
            "imageSrc": _normalize_src(image_rel),
            "brollFraming": chunk.get("broll_framing", None),
            "boundary_kind": chunk.get("boundary_kind", ""),
            "act_title": chunk.get("act_title", ""),
            "weight": weight,
            "reveal_group": chunk.get("reveal_group", "") or "",
            # For broll chunks: start_from_sec controls which portion of the
            # source mp4 plays. Useful when multiple chunks share one mp4 and
            # we want them to show different moments.
            "startFromSec": float(chunk.get("start_from_sec", 0) or 0),
            # Snap overlay end to chunk end when within ~6 frames (200ms) of, or
            # past, durationFrames. Author-set timing_end_s drifts vs the actual
            # rendered chunk duration by 2–5 frames; without the snap that gap
            # reads as a flash where the meme vanishes a beat before the chunk
            # cuts. Explicit early exits (large gaps) are preserved.
            "overlays": [
                {
                    "src": _normalize_src(o.get("source", "")),
                    "startFrameInChunk": round(float(o.get("timing_start_s", 0)) * fps_value),
                    "endFrameInChunk": (
                        (chunk_end_frame - chunk_start_frame)
                        if (chunk_end_frame - chunk_start_frame) - round(float(o.get("timing_end_s", 0)) * fps_value) <= 6
                        else round(float(o.get("timing_end_s", 0)) * fps_value)
                    ),
                    "x": float(o.get("x", 0.5)),
                    "y": float(o.get("y", 0.18)),
                    "anchor": o.get("anchor", "center"),
                    "width": float(o.get("width", 0.08)),
                    "rotationDeg": float(o.get("rotation_deg", 0)),
                    "entryTransition": o.get("entry_transition", "cut"),
                    "exitTransition": o.get("exit_transition", "cut"),
                }
                for o in (chunk.get("overlays") or [])
            ],
            "framesDir": frames_dir_rel,
            "preGenFrameCount": pre_gen_count,
            "startFrame": chunk_start_frame,
            "endFrame": chunk_end_frame,
            "durationFrames": chunk_end_frame - chunk_start_frame,
            "beats": beats_out,
        })

    reveal_style = session_cfg.get("reveal_style", "eraser-wipe")

    def _hash(s: str) -> int:
        h = 0
        for ch in s:
            h = ((h << 5) - h) + ord(ch)
            h &= 0xFFFFFFFF
        return h

    # Annotate each chunk with entrance/exit transitions.
    # Rules:
    # - proof / meme / broll_image / broll chunks always hard-cut in AND out
    #   (external/reference assets should appear and disappear with no animation
    #   — the style-clash IS the transition; any wipe dilutes it)
    # - first chunk of video: wipe-in
    # - chunk immediately after a hard-cut external asset: wipe-in (returning
    #   to the illustrated world)
    # - continues-from-prev / callback-to-*: cut in (scene already established)
    # - standalone chunks: wipe-in (new visual world)
    # - arc end (last of video OR next chunk is NOT continues-from-prev): wipe-out
    # - arc middle (next chunk IS continues-from-prev): cut out
    # Hard-cut sources: external assets (memes, broll, proof) + reuse chunks.
    # These always hard-cut in AND out — no fade, no paint-on.
    HARD_CUT_SOURCES = {"proof", "meme", "broll_image", "broll", "reuse"}

    # Transition vocabulary (VISUALS.md § Inter-chunk transition vocabulary):
    # - cut: instant, no animation
    # - crossfade: prior-frame underlay + fade-in on the incoming chunk
    #
    # paint-on is DEFERRED pending preprocessor support for RGBA paint frames
    # (the existing stroke-reveal outputs RGB with white background, so it
    # flashes white at every entrance — VISUALS.md § Paint-on deferred).
    #
    # A crossfade entrance requires the prior chunk to have a valid still
    # image to use as underlay. Prior chunks without one (broll videos,
    # bumpers, first chunk of the video) fall back to a cut entrance.
    def _has_underlay(prev_chunk: dict) -> bool:
        if prev_chunk is None:
            return False
        prev_path = (prev_chunk.get("imageSrc", "") or "").lower()
        if not prev_path:
            return False
        if any(prev_path.endswith(ext) for ext in (".mp4", ".mov", ".webm")):
            return False
        # Bumpers have no imageSrc; they're rendered as a title card, not
        # from a file — crossfade underlay would have nothing to display.
        if prev_chunk.get("boundary_kind") == "bumper":
            return False
        return True

    for i, chunk in enumerate(chunks_out):
        src = chunk.get("imageSource", "generated")
        prev = chunks_out[i - 1] if i > 0 else None
        prev_src = (prev or {}).get("imageSource", "")

        # Entrance classifier — STORY.md § Visual transition primitives lists
        # CUT / comicPan / pageFlip / panelSplit. Crossfade is NOT in the spec.
        # Default is `cut` (hard-cut) for everything; soft transitions are
        # opt-in via a future shot-list field. Aligns code with STORY.md §
        # "CUT is the deadpan default" and avoids the visible-wobble flash
        # when consecutive scenes are visually similar (caught on dev-log-04
        # C11→C12 — both ai-figure at desk; the 0.35s crossfade made the
        # similar-but-not-identical scenes appear to flash).
        entrance = "cut"
        chunk["entrance"] = entrance

    # Crossfade is entrance-side only — the incoming chunk fades in over the
    # prior's held last frame. Every chunk's exit is a simple "cut" (hold
    # final frame until the next chunk takes over). No fade-to-white, no
    # two-sided wipe.
    for chunk in chunks_out:
        chunk["exit"] = "cut"

    # Durations per chunk based on entrance. Under the cut/crossfade
    # vocabulary, only crossfade has an animated duration.
    fps_value_f = float(fps_value)
    for i, chunk in enumerate(chunks_out):
        entrance = chunk.get("entrance", "cut")

        # paint-on is deferred — no chunks should have this, but keep the
        # field at 0 for backward compat with any consumers.
        wipe_in_frames = 0
        wipe_out_frames = 0

        if entrance == "crossfade":
            crossfade_in_frames = round(0.35 * fps_value_f)
        else:
            crossfade_in_frames = 0
        crossfade_out_frames = 0  # exit-side fades don't exist under new vocab

        # Reveal-group suppression: group-interior chunks hard-cut in (the
        # group's cadence IS the rhythm; soft transitions inside dilute it).
        reveal_pos = reveal_positions.get(chunk["id"], "solo")
        if reveal_pos in ("middle", "last"):
            crossfade_in_frames = 0
            chunk["entrance"] = "cut"

        # Record final-state image path from the previous chunk so the renderer
        # can composite a crossfade underlay. Blank when the prev asset is a
        # video (Img can't decode a video) — renderer falls back to no
        # underlay in that case (effectively a cut into the new chunk).
        prev_img = ""
        if i > 0:
            prev_chunk = chunks_out[i - 1]
            prev_path = (prev_chunk.get("imageSrc", "") or "").lower()
            is_video = any(
                prev_path.endswith(ext) for ext in (".mp4", ".mov", ".webm")
            )
            if not is_video:
                prev_img = prev_chunk.get("imageSrc", "") or ""
        chunk["priorFinalImageSrc"] = prev_img

        chunk["wipeInFrames"] = wipe_in_frames
        chunk["wipeOutFrames"] = wipe_out_frames
        chunk["crossfadeInFrames"] = crossfade_in_frames
        chunk["crossfadeOutFrames"] = crossfade_out_frames
        chunk["wipeSeed"] = _hash(chunk["id"]) % 6  # 6 variation buckets
        # reveal_direction comes from shot-list; empty means auto (seed-based)
        chunk["wipeDirection"] = chunk.get("reveal_direction", "") or ""
        chunk["reveal_group"] = chunk.get("reveal_group", "")
        chunk["reveal_group_position"] = reveal_pos
        # legacy field kept for compatibility with any old Composition code
        chunk["transition"] = chunk["entrance"]

    return {
        "sessionId": session_id,
        "canvas": canvas,
        "width": width,
        "height": height,
        "fps": fps_value,
        "playbackRate": playback_rate,
        "revealStyle": reveal_style,
        "totalFrames": running_frame,
        "chunkCount": len(chunks_out),
        "skipped": [{"chunk": c, "reason": r} for c, r in skipped],
        "chunks": chunks_out,
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Build preview-data.json for Remotion")
    parser.add_argument("--session", required=True)
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "src" / "data" / "preview-data.json"),
    )
    parser.add_argument(
        "--chunks",
        default=None,
        help="Comma-separated chunk IDs to include (default: all renderable).",
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help=(
            "BYPASS the narration-audit gate. Logs a prominent warning and "
            "writes a bypass marker to sessions/<id>/working/audit-bypass.json "
            "so downstream stages (and future sessions) can see the render was "
            "not audited. Not allowed for final builds — use --preview to mark "
            "this as an intentional preview-only build."
        ),
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Mark this build as a preview-only render (pre-audit iteration). "
            "Required alongside --skip-audit for the bypass to be honored. "
            "Final builds require a fresh audit report."
        ),
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="DANGEROUS: skip structural validation. Use only for debugging.",
    )
    args = parser.parse_args()

    # --- Layer 1: structural validator ---
    if not args.skip_validate:
        import validate_shot_list  # sibling module in scripts/

        shot_list = validate_shot_list.load_shot_list(args.session)
        errors = validate_shot_list.validate(shot_list)
        if errors:
            validate_shot_list.print_report(args.session, errors)
            print(
                "\n[preview-data] refused to build: shot-list has structural errors.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --- Layer 2: narration audit gate ---
    audit_bypass_path = (
        CONTENT_ROOT
        / "sessions"
        / args.session
        / "working"
        / "audit-bypass.json"
    )
    if args.skip_audit:
        if not args.preview:
            print(
                "[preview-data] refused to build: --skip-audit without --preview.\n"
                "  --skip-audit is for preview-only iteration, not final builds.\n"
                "  Final builds require a fresh audit. Options:\n"
                "    (a) run `scripts/audit_narration.py --session "
                f"{args.session}` and address the flags, then rebuild, OR\n"
                "    (b) if this is a deliberate preview build, re-run with both "
                "`--skip-audit --preview` so the bypass is recorded.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Preview bypass is allowed — log loudly and write a marker.
        import datetime as _dt
        print(
            "\n" + "=" * 72 + "\n"
            "[preview-data] WARNING: building with --skip-audit (preview mode).\n"
            "  This build is NOT audited for bridge / overweight / preview / "
            "layman / alignment issues.\n"
            "  A bypass marker is being written to the session so downstream "
            "stages can see it.\n"
            "  Do NOT ship this build as final.\n" + "=" * 72 + "\n",
            file=sys.stderr,
        )
        audit_bypass_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_bypass_path.open("w") as f:
            json.dump({
                "session_id": args.session,
                "bypassed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "reason": "preview build via --skip-audit --preview",
                "is_preview_only": True,
            }, f, indent=2)
    else:
        # Normal path: require a fresh, clean audit.
        # Clear any stale bypass marker on an audited build.
        if audit_bypass_path.exists():
            audit_bypass_path.unlink()
        audit_path = (
            CONTENT_ROOT
            / "sessions"
            / args.session
            / "working"
            / "narration-audit.json"
        )
        sl_path = (
            CONTENT_ROOT
            / "sessions"
            / args.session
            / "shot-list"
            / "shot-list.json"
        )
        if not audit_path.exists():
            print(
                f"[preview-data] refused to build: no audit report at {audit_path}.\n"
                f"  Run: scripts/audit_narration.py --session {args.session}\n"
                f"  Or for a preview-only iteration build, pass both "
                f"`--skip-audit --preview`.",
                file=sys.stderr,
            )
            sys.exit(1)
        if audit_path.stat().st_mtime < sl_path.stat().st_mtime:
            print(
                f"[preview-data] refused to build: audit report is older than the "
                f"shot-list. Re-run audit_narration.py, or for preview-only "
                f"iteration pass `--skip-audit --preview`.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            with audit_path.open() as f:
                audit = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[preview-data] refused to build: unreadable audit report: {e}",
                  file=sys.stderr)
            sys.exit(1)
        unresolved = (
            len(audit.get("bridge_flags") or [])
            + len(audit.get("overweight_flags") or [])
            + len(audit.get("preview_flags") or [])
            + len(audit.get("layman_flags") or [])
            + len(audit.get("alignment_flags") or [])
        )
        if unresolved:
            print(
                f"[preview-data] refused to build: audit report has {unresolved} "
                f"unresolved flag(s) across bridge/overweight/preview/layman/"
                f"alignment. Resolve or rebuild as preview-only with "
                f"`--skip-audit --preview`.",
                file=sys.stderr,
            )
            sys.exit(1)

    data = build(args.session)
    # Apply --chunks filter after build (preserves timeline recomputation).
    if args.chunks:
        keep = {c.strip() for c in args.chunks.split(",")}
        filtered = [c for c in data["chunks"] if c["id"] in keep]
        # Recompute global startFrame/endFrame for the filtered timeline
        running = 0
        for c in filtered:
            dur = c["durationFrames"]
            c["startFrame"] = running
            c["endFrame"] = running + dur
            running += dur
        data["chunks"] = filtered
        data["chunkCount"] = len(filtered)
        data["totalFrames"] = running
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2))

    total_s = data["totalFrames"] / data["fps"]
    print(f"[preview-data] wrote {out}")
    print(f"[preview-data] {data['chunkCount']} chunks, {data['totalFrames']} frames at {data['fps']}fps = {total_s:.1f}s")
    if data["skipped"]:
        print(f"[preview-data] skipped {len(data['skipped'])} chunks:")
        for s in data["skipped"][:5]:
            print(f"  {s['chunk']}: {s['reason']}")
        if len(data["skipped"]) > 5:
            print(f"  ... and {len(data['skipped']) - 5} more")


if __name__ == "__main__":
    _cli()
