#!/usr/bin/env python3
"""audit_mobile_crops.py — vision audit of post-crop mobile scene PNGs.

Inverts the direction of `audit_scenes.py`'s mobile-safety check. Instead
of showing Qwen the widescreen and asking *"would a crop lose content?"*
(a geometric imagination task the model is unreliable at), this script
shows Qwen the already-cropped mobile PNG and asks *"is anything in this
image visibly broken or clipped at the edges?"* — a direct perceptual
task the model is much better at.

Reads:  scenes/mobile/<chunk>-mobile.png (cropped or regen'd mobile assets)
Writes: working/mobile-crop-audit.json
Flags:  chunks where content was visibly clipped or damaged during the
        widescreen→mobile crop, so they can be regenerated at native
        mobile aspect.

Usage:
  scripts/.venv/bin/python scripts/audit_mobile_crops.py \\
      --session spoolcast-dev-log \\
      [--only C1,C2,C3] [--parallel 4]
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

# Share the existing helpers/constants.
from audit_scenes import (
    DEFAULT_PROVIDER,
    DEFAULT_MODEL_BY_PROVIDER,
    OPENROUTER_BASE_URL,
    VisionClient,
    encode_image,
    parse_json_reply,
    load_shot_list,
)

CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"


SYSTEM_PROMPT = """You are a vision reviewer for mobile-exported spoolcast scenes.

Each image you see is the POST-CROP mobile version of a scene. The
widescreen master was cropped to 9:16 portrait, and this is what a
mobile viewer watching the video would see while the chunk's narration
plays in their ears.

**Primary question: while the viewer hears this chunk's narration, does
the cropped image still communicate the message that the script / beat
is trying to convey?**

If the answer is no, the chunk is broken — regardless of whether any
individual element looks "clipped" in isolation. The rule is about
meaning loss, not edge clipping. Edge clipping is one way meaning is
lost; severed compositions, halved comparisons, and broken relational
layouts are the same failure mode.

Common ways comprehension fails (not an exhaustive list):

1. **Text clipped mid-word or mid-line** so the meaning is lost. A
   single compact word trimmed by one letter (e.g. "DEFAULT" → "DEFAUL")
   is NOT broken — recoverable from context.

2. **Key prop partially clipped at the edge** (STOP sign, red X,
   labeled object, arrow tip). Background scene dressing clipping is
   NOT broken; only focal props count.

3. **Character cut off** in a way that breaks the scene — face bisected
   by frame edge, body truncated such that the action no longer reads.
   A character positioned at the edge but not cut is NOT broken.

4. **Split-frame composition where the comparison is lost** — side-by-
   side or before/after layouts where one panel got discarded. NOT
   automatically broken if the surviving panel alone still conveys the
   beat. Flag only when the surviving fragment no longer communicates
   without its missing pair.

5. **Severed sequential / relational composition** — narration describes
   "X leading to Y" or "X compared with Y" but the crop cut the
   connection between elements, leaving them visually disconnected
   (an arrow pointing at empty space, a relationship halved, a
   contrast lost).

6. **Any other essential scene element visibly truncated** in a way
   that changes what the scene communicates relative to the narration.

"Not broken" means:

- The image, paired with the narration, still lands the beat.
- Background posters, sticky notes, wall calendars, ambient clutter
  getting clipped — scene dressing, not failure.
- Single compact declared text still readable even with a trimmed letter.
- Focal subjects and their relationships are intact within frame.

**Lean toward catching real failures, not avoiding flags.** A false
positive costs one regen call (~$0.04). A false negative ships a chunk
where the viewer doesn't understand the moment — much more expensive.
When uncertain whether the cropped frame lands the narrated beat, flag.

Reply with a single JSON object, no prose outside the JSON."""


def mobile_scene_image_path(session: str, chunk_id: str) -> Path:
    return (
        CONTENT_ROOT
        / "sessions"
        / session
        / "source"
        / "generated-assets"
        / "scenes"
        / "mobile"
        / f"{chunk_id}-mobile.png"
    )


def build_user_prompt(chunk: dict[str, Any]) -> str:
    cid = chunk.get("id") or "?"
    beats = chunk.get("beats") or []
    narration = " ".join(
        (b.get("narration") or "").strip() for b in beats if (b.get("narration") or "").strip()
    ).strip() or "(no narration)"
    beat_description = (chunk.get("beat_description") or "").strip() or "(none)"
    osts = chunk.get("on_screen_text") or []
    declared_text_block = (
        "\n".join(f"  - {json.dumps(s)}" for s in osts) if osts else "  (none declared)"
    )
    return (
        f"Chunk id: {cid}\n\n"
        f"Narration the viewer hears during this chunk:\n  {json.dumps(narration)}\n\n"
        f"Intended beat / visual scaffolding (what the scene was authored to convey):\n  {beat_description}\n\n"
        f"Declared on_screen_text for this scene:\n{declared_text_block}\n\n"
        "Inspect the attached image (the post-crop mobile version).\n\n"
        "Question: while the viewer hears the narration above, does this cropped image\n"
        "still communicate the message the beat is trying to convey?\n\n"
        "If no — flag broken. Failure can be visual clipping, a halved split-panel,\n"
        "a severed relational composition, or any other reason the cropped frame\n"
        "no longer lands the narrated beat.\n\n"
        "Reply with:\n"
        "{\n"
        '  "chunk_id": "<id>",\n'
        '  "broken": true | false,\n'
        '  "broken_reason": "<one sentence tying the failure to the narration / beat, else null>",\n'
        '  "element_clipped": "<short description of what specifically broke the scene, else null>",\n'
        '  "severity": "low" | "medium" | "high" | null\n'
        "}\n"
        "severity: low = minor, viewer still gets the gist; medium = noticeable meaning loss but scene partially lands; high = beat fails, viewer cannot understand what this moment is about. Only set severity when broken=true."
    )


def audit_chunk(
    client: VisionClient,
    session: str,
    chunk: dict[str, Any],
) -> dict[str, Any]:
    cid = chunk.get("id") or "?"
    img_path = mobile_scene_image_path(session, cid)
    if not img_path.exists():
        return {"chunk_id": cid, "skipped": f"no mobile scene at {img_path}"}
    try:
        b64 = encode_image(img_path)
    except OSError as e:
        return {"chunk_id": cid, "error": f"cannot read image: {e}"}

    user_prompt = build_user_prompt(chunk)
    parsed = client.call(SYSTEM_PROMPT, user_prompt, b64)
    if parsed is None:
        return {"chunk_id": cid, "error": "vision call failed or returned non-JSON"}
    parsed["chunk_id"] = cid
    return parsed


def summarize(results: list[dict[str, Any]]) -> tuple[int, int]:
    broken = sum(1 for r in results if not r.get("skipped") and not r.get("error") and r.get("broken"))
    skipped = sum(1 for r in results if r.get("skipped"))
    return broken, skipped


def print_report(results: list[dict[str, Any]]) -> None:
    for r in results:
        cid = r.get("chunk_id", "?")
        if r.get("skipped"):
            print(f"  {cid}: skipped ({r['skipped']})")
            continue
        if r.get("error"):
            print(f"  {cid}: ERROR {r['error']}")
            continue
        if r.get("broken"):
            sev = r.get("severity") or "?"
            elem = r.get("element_clipped") or "?"
            rsn = r.get("broken_reason") or ""
            print(f"  [BROKEN/{sev}] {cid}: {elem}")
            if rsn:
                print(f"      reason: {rsn}")
        else:
            print(f"  [ok      ] {cid}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Vision audit of post-crop mobile scene PNGs.")
    p.add_argument("--session", required=True)
    p.add_argument("--provider", default=DEFAULT_PROVIDER)
    p.add_argument("--model", default=None)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument(
        "--only",
        default=None,
        help="comma-separated chunk ids to audit (default: all with scenes/mobile/*.png)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="output path (default: working/mobile-crop-audit.json)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    model = args.model or DEFAULT_MODEL_BY_PROVIDER.get(args.provider)
    if not model:
        print(f"ERROR: no default model for provider {args.provider!r}", file=sys.stderr)
        return 3

    shot_list = load_shot_list(args.session)
    chunks = shot_list.get("chunks") or []
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        chunks = [c for c in chunks if c.get("id") in wanted]

    # Only audit chunks that actually have a mobile scene on disk.
    chunks = [c for c in chunks if mobile_scene_image_path(args.session, c.get("id") or "").exists()]

    out_path = (
        Path(args.out)
        if args.out
        else CONTENT_ROOT / "sessions" / args.session / "working" / "mobile-crop-audit.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = VisionClient(args.provider, model)
    results: list[dict[str, Any]] = [None] * len(chunks)  # type: ignore[list-item]

    def _do(i: int) -> tuple[int, dict[str, Any]]:
        return i, audit_chunk(client, args.session, chunks[i])

    print(f"Auditing {len(chunks)} mobile crops (parallel={args.parallel}) via {args.provider}:{model}")
    if args.parallel <= 1:
        for i in range(len(chunks)):
            _, r = _do(i)
            results[i] = r
            print(f"  {i + 1}/{len(chunks)} {chunks[i].get('id')}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futures = {ex.submit(_do, i): i for i in range(len(chunks))}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                i, r = fut.result()
                results[i] = r
                done += 1
                if done % 5 == 0 or done == len(chunks):
                    print(f"  {done}/{len(chunks)}")

    broken, skipped = summarize(results)
    print()
    print(f"=== mobile-crop audit: {args.session} ===")
    print_report(results)
    print()
    print(f"{broken} broken, {skipped} skipped, {len(chunks)} total")

    payload = {
        "session": args.session,
        "provider": args.provider,
        "model": model,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "chunks": results,
        # Backward-compatible alias for older readers. New code should use
        # `chunks`, matching the rest of the spoolcast shot-list vocabulary.
        "results": results,
        "summary": {"broken": broken, "skipped": skipped, "total": len(chunks)},
    }
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out_path}")

    return 2 if broken > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
