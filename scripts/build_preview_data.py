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
from pathlib import Path
from typing import Any

from mutagen.mp3 import MP3  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"

PAUSE_SECONDS = {
    "": 0.3,
    "none": 0.0,
    "short": 0.3,
    "medium": 0.5,  # was 0.8 — felt excessive on mid-length chunks
    "long": 0.8,    # was 1.5 — felt dead; 0.8 is a real breath without stalling
}

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

    for chunk in shot_list.get("chunks", []):
        chunk_id = chunk["id"]
        image_rel = chunk.get("image_path", "")
        image_path = _image_abs_path(session_id, image_rel)
        beats = chunk.get("beats") or []

        if not image_path.exists():
            skipped.append((chunk_id, f"image missing at {image_rel}"))
            continue

        missing_audio = [b["id"] for b in beats if not _audio_path(session_id, b["id"]).exists()]
        if missing_audio:
            skipped.append((chunk_id, f"audio missing for beats {missing_audio}"))
            continue

        chunk_start_frame = running_frame
        beats_out: list[dict[str, Any]] = []

        for beat in beats:
            raw_dur = _audio_duration_sec(_audio_path(session_id, beat["id"])) or 1.0
            # Speeding up playback shrinks the effective duration.
            dur = raw_dur / playback_rate
            beat_start_rel = running_frame - chunk_start_frame
            dur_frames = round(dur * fps_value)
            pause_s = PAUSE_SECONDS.get(beat.get("pause_after", "") or "", 0.3)
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
        # Check for preprocessed stroke-reveal frames
        frames_dir_abs = session_dir(session_id) / "frames" / chunk_id
        pre_gen_count = 0
        frames_dir_rel = ""
        if frames_dir_abs.exists():
            pre_gen_count = len(list(frames_dir_abs.glob("frame_*.png")))
            if pre_gen_count > 0:
                frames_dir_rel = f"frames/{chunk_id}"

        chunks_out.append({
            "id": chunk_id,
            "scene": chunk.get("scene", ""),
            "sceneTitle": chunk.get("scene_title", ""),
            "summary": chunk.get("summary", ""),
            "continuity": chunk.get("continuity", "standalone"),
            "reveal_direction": chunk.get("reveal_direction", "") or "",
            "imageSource": chunk.get("image_source", "generated"),
            "imageSrc": image_rel,
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
    # - proof chunks always hard-cut in AND out (the style clash IS the transition)
    # - first chunk of video: wipe-in
    # - chunk immediately after a proof: wipe-in (returning to illustrated world)
    # - continues-from-prev / callback-to-*: cut in (scene already established)
    # - standalone chunks: wipe-in (new visual world)
    # - arc end (last of video OR next chunk is NOT continues-from-prev): wipe-out
    # - arc middle (next chunk IS continues-from-prev): cut out
    # - proof always: cut out
    for i, chunk in enumerate(chunks_out):
        cont = chunk.get("continuity", "standalone")
        src = chunk.get("imageSource", "generated")
        prev = chunks_out[i - 1] if i > 0 else None
        next_ = chunks_out[i + 1] if i + 1 < len(chunks_out) else None

        # entrance
        if src == "proof":
            entrance = "cut"
        elif i == 0:
            entrance = "eraser-wipe"
        elif prev and prev.get("imageSource") == "proof":
            entrance = "eraser-wipe"
        elif cont == "standalone" or cont.startswith("callback"):
            entrance = "eraser-wipe"
        else:
            entrance = "cut"

        # exit — wipe out ONLY at chapter/scene boundaries (not arc boundaries).
        # "scene" in shot-list terms = the chapter from the voiceover script
        # (scene 01 Cold Open, scene 02 What TRIBE Is, etc.)
        if src == "proof":
            exit_ = "cut"
        elif next_ is None:
            # last chunk of the whole video — wipe out as closing flourish
            exit_ = "eraser-wipe"
        elif next_.get("imageSource") == "proof":
            # next is a proof insert — hard cut into it (style clash is the point)
            exit_ = "cut"
        elif chunk.get("scene") != next_.get("scene"):
            # crossing a scene/chapter boundary — wipe out
            exit_ = "eraser-wipe"
        else:
            # same scene — keep cutting through
            exit_ = "cut"

        # wipe durations scale with chunk duration (bounded)
        chunk_sec = chunk["durationFrames"] / fps_value
        if entrance == "eraser-wipe":
            wipe_in_sec = max(1.0, min(chunk_sec * 0.4, 3.0))
            wipe_in_frames = round(wipe_in_sec * fps_value)
        else:
            wipe_in_frames = 0
        if exit_ == "eraser-wipe":
            wipe_out_sec = max(0.8, min(chunk_sec * 0.25, 2.0))
            wipe_out_frames = round(wipe_out_sec * fps_value)
        else:
            wipe_out_frames = 0

        chunk["entrance"] = entrance
        chunk["exit"] = exit_
        chunk["wipeInFrames"] = wipe_in_frames
        chunk["wipeOutFrames"] = wipe_out_frames
        chunk["wipeSeed"] = _hash(chunk["id"]) % 6  # 6 variation buckets
        # reveal_direction comes from shot-list; empty means auto (seed-based)
        chunk["wipeDirection"] = chunk.get("reveal_direction", "") or ""
        # legacy field kept for compatibility with any old Composition code
        chunk["transition"] = entrance

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
    args = parser.parse_args()

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
