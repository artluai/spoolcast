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
widescreen master was center-cropped to 4:5 portrait, and this is the
image a mobile viewer watching the video would see. Your job: flag any
image where content was visibly BROKEN during that crop — essential
elements that got truncated at the edges.

"Broken" means one of:

1. **Text clipped mid-word or mid-line**: a line of body text whose first
   or last word is cut off such that the meaning is lost. Example: a
   sentence rendered as "s the point of havin" instead of "what's the
   point of having rules" — viewer cannot reconstruct the meaning.
   A single compact word trimmed by one letter (e.g. "DEFAULT" → "DEFAUL")
   is NOT broken — the word is still recoverable from context.

2. **Key prop partially clipped at the edge**: a STOP sign, red X,
   labeled object, arrow, or other punchline element with a piece cut
   off at the frame edge. Background clutter getting clipped is NOT
   broken — only the scene's focal props count.

3. **Character cut off**: a character whose face is bisected by the
   frame edge, or whose body is truncated in a way that breaks the
   scene. A character positioned in-frame at the edge (not cut) is NOT
   broken.

4. **Split-frame composition where context is lost**: a before/after or
   side-by-side layout where one or more panels were discarded during
   the crop, leaving the remaining panel(s) without their pair.

5. **Any other essential scene element visibly truncated** at the frame
   edge in a way that changes what the scene communicates.

"Not broken" means:

- Scene is self-contained within the frame.
- Background posters, sticky notes, wall calendars, ambient desk clutter
  getting clipped — that's scene dressing, not a failure.
- Single compact declared text still readable even if a letter is trimmed
  (recoverability test).
- Focal subjects fully visible; crop removed only peripheral content the
  viewer wasn't meant to focus on.

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
    osts = chunk.get("on_screen_text") or []
    declared_text_block = (
        "\n".join(f"  - {json.dumps(s)}" for s in osts) if osts else "  (none declared)"
    )
    return (
        f"Chunk id: {cid}\n"
        f"Declared on_screen_text for this scene (context for judging whether text clipping is essential or not):\n"
        f"{declared_text_block}\n\n"
        "Inspect the attached image (the post-crop mobile version). Reply with:\n"
        "{\n"
        '  "chunk_id": "<id>",\n'
        '  "broken": true | false,\n'
        '  "broken_reason": "<one sentence if broken, else null>",\n'
        '  "element_clipped": "<short description of WHAT is clipped at the edge, else null>",\n'
        '  "severity": "low" | "medium" | "high" | null\n'
        "}\n"
        "severity: low = minor clip, viewer still gets meaning; medium = noticeable, some content lost but scene still lands; high = essential content gone, scene doesn't communicate. Only set severity when broken=true.\n"
        "Lean CONSERVATIVE: only flag broken when a casual viewer would clearly see the clipping and lose meaning."
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
        "results": results,
        "summary": {"broken": broken, "skipped": skipped, "total": len(chunks)},
    }
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out_path}")

    return 2 if broken > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
