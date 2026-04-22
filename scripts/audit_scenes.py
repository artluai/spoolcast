#!/usr/bin/env python3
"""Vision audit of generated scene images for a spoolcast session.

Parallel to audit_narration.py but operates on rendered PNGs rather than
narration text. Catches the failure modes that a text-only audit cannot see:

- **OCR check** — does the literal `on_screen_text` declared in the shot-list
  actually appear on the rendered frame? Catches cases where the image model
  drew stage-direction text, hallucinated an unrelated quote, or omitted the
  intended card entirely.
- **Text-hallucination** — is there legible text on the frame that was NOT
  declared in `on_screen_text`? Catches the "generator bled stage-direction
  words into the image" failure.
- **Anatomy** — extra limbs, malformed faces/hands, duplicate characters,
  phantom body parts. Catches the motion-verb-in-still-prompt failure and
  the wojak-under-hood cranium bug.
- **Composition overload** — is the frame too busy, with multiple competing
  focal subjects fighting for attention?

Default provider is openrouter (Qwen-VL). Gates render the same way
audit_narration.py does: a non-empty audit = block, must be resolved or
explicitly bypassed.

Usage:
  scripts/.venv/bin/python scripts/audit_scenes.py \\
      --session spoolcast-dev-log \\
      [--provider openrouter] [--model qwen/qwen-2.5-vl-72b-instruct] \\
      [--parallel 4] \\
      [--only C1,C2,C3]

Reads:  ../spoolcast-content/sessions/<session>/shot-list/shot-list.json
        ../spoolcast-content/sessions/<session>/source/generated-assets/scenes/*.png
Writes: ../spoolcast-content/sessions/<session>/working/scene-audit.json

Exit codes:
  0 = no flags
  2 = at least one flag raised
  3 = session / shot-list / image missing
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


DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL_BY_PROVIDER = {
    "openrouter": "qwen/qwen-2.5-vl-72b-instruct",
}
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"


SYSTEM_PROMPT = """You are a vision reviewer for a spoolcast illustrated video.

Your job: inspect a single generated scene image and flag four failure classes:

1. **ocr_missing** — the shot-list says specific text should appear on the
   frame (field `on_screen_text`). Does that exact text appear, legible, in
   the image? Flag if any declared text is missing, garbled, or substantively
   different.

2. **text_hallucination** — is there legible text on the frame that was NOT
   declared in `on_screen_text`? This happens when the generator renders
   stage-direction prose as literal text, or invents its own quote. Flag the
   specific words that shouldn't be there.

3. **anatomy** — extra limbs, malformed faces or hands, duplicate characters
   where only one was intended, phantom body parts floating in the frame,
   obviously warped or collapsed anatomy. The wojak-comic style is simple
   line art; subtle stylization is fine, structural failures are not.

4. **composition_overload** — are there so many competing focal subjects that
   the viewer's eye doesn't know where to land? Multi-panel chunks are OK if
   clearly partitioned; flag only when elements clutter without structure.

Always reply with a single JSON object, no prose outside the JSON."""


def load_shot_list(session: str) -> dict[str, Any]:
    path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: shot-list not found at {path}", file=sys.stderr)
        sys.exit(3)
    with path.open() as f:
        return json.load(f)


def scene_image_path(session: str, chunk_id: str) -> Path:
    return (
        CONTENT_ROOT
        / "sessions"
        / session
        / "source"
        / "generated-assets"
        / "scenes"
        / f"{chunk_id}.png"
    )


def parse_json_reply(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def encode_image(path: Path) -> str:
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


class VisionClient:
    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        if provider == "openrouter":
            if OpenAI is None:
                print(
                    "ERROR: openai SDK not installed (needed for OpenRouter). "
                    "Run: scripts/.venv/bin/pip install openai",
                    file=sys.stderr,
                )
                sys.exit(3)
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                print("ERROR: OPENROUTER_API_KEY not set.", file=sys.stderr)
                sys.exit(3)
            self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
        else:
            print(f"ERROR: unknown provider {provider!r}", file=sys.stderr)
            sys.exit(3)

    def call(self, system_prompt: str, user_prompt: str, image_b64: str) -> dict[str, Any] | None:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=700,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                },
                            },
                        ],
                    },
                ],
            )
            text = (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"  WARN: vision API call failed: {e}", file=sys.stderr)
            return None
        if not text:
            return None
        parsed = parse_json_reply(text)
        if parsed is None:
            print(f"  WARN: failed to parse JSON: {text[:200]!r}", file=sys.stderr)
        return parsed


def build_user_prompt(chunk: dict[str, Any]) -> str:
    cid = chunk.get("id") or "?"
    osts = chunk.get("on_screen_text") or []
    declared_text_block = (
        "\n".join(f"  - {json.dumps(s)}" for s in osts) if osts else "  (none declared)"
    )
    vd = (chunk.get("visual_direction") or chunk.get("beat_description") or "").strip()
    return (
        f"Chunk id: {cid}\n"
        f"Visual direction (for context only — not a target): {vd or '(none)'}\n\n"
        f"Declared on_screen_text (these and only these words should appear as legible text on the frame):\n"
        f"{declared_text_block}\n\n"
        "Inspect the attached image. Reply with a single JSON object:\n"
        "{\n"
        '  "chunk_id": "<id>",\n'
        '  "ocr_missing": ["<declared text that does not appear or is garbled>", ...],\n'
        '  "text_hallucination": ["<legible text on the frame that was NOT declared>", ...],\n'
        '  "anatomy_flags": ["<specific anatomy or duplicate-character issue>", ...],\n'
        '  "composition_overload": "<null or one sentence if the frame is cluttered>",\n'
        '  "overall_verdict": "ok" | "regenerate",\n'
        '  "reasoning": "<one to two sentences>"\n'
        "}\n"
        "If a category has no issues, return an empty array (or null for composition_overload).\n"
        "Set overall_verdict to 'regenerate' only when at least one category has a flag."
    )


def audit_chunk(
    client: VisionClient,
    session: str,
    chunk: dict[str, Any],
) -> dict[str, Any]:
    cid = chunk.get("id") or "?"
    isrc = (chunk.get("image_source") or "generated").strip()
    if isrc not in {"generated"}:
        # Only audit AI-generated scenes. External/meme/broll are verified via
        # the asset-verification sidecar rule (VISUALS.md § Asset-content
        # verification), not by vision audit.
        return {"chunk_id": cid, "skipped": f"image_source={isrc}"}

    img_path = scene_image_path(session, cid)
    if not img_path.exists():
        return {"chunk_id": cid, "error": f"image not found at {img_path}"}

    try:
        b64 = encode_image(img_path)
    except OSError as e:
        return {"chunk_id": cid, "error": f"cannot read image: {e}"}

    user_prompt = build_user_prompt(chunk)
    parsed = client.call(SYSTEM_PROMPT, user_prompt, b64)
    if parsed is None:
        return {"chunk_id": cid, "error": "vision call failed or returned non-JSON"}
    parsed["chunk_id"] = cid  # ensure set
    return parsed


def summarize(results: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (flag_count, skipped_count)."""
    flags = 0
    skipped = 0
    for r in results:
        if r.get("skipped"):
            skipped += 1
            continue
        if r.get("overall_verdict") == "regenerate":
            flags += 1
    return flags, skipped


def print_report(results: list[dict[str, Any]]) -> None:
    for r in results:
        cid = r.get("chunk_id", "?")
        if r.get("skipped"):
            print(f"  {cid}: skipped ({r['skipped']})")
            continue
        if r.get("error"):
            print(f"  {cid}: ERROR {r['error']}")
            continue
        verdict = r.get("overall_verdict", "?")
        marker = "FLAG" if verdict == "regenerate" else "ok  "
        print(f"  [{marker}] {cid}")
        for category in ("ocr_missing", "text_hallucination", "anatomy_flags"):
            items = r.get(category) or []
            for it in items:
                print(f"      {category}: {it}")
        co = r.get("composition_overload")
        if co:
            print(f"      composition_overload: {co}")
        if verdict == "regenerate" and r.get("reasoning"):
            print(f"      reasoning: {r['reasoning']}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Vision audit of generated scenes.")
    p.add_argument("--session", required=True)
    p.add_argument("--provider", default=DEFAULT_PROVIDER)
    p.add_argument("--model", default=None)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument(
        "--only",
        default=None,
        help="comma-separated chunk ids to audit (default: all generated chunks)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="output path (default: working/scene-audit.json in the session dir)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    model = args.model or DEFAULT_MODEL_BY_PROVIDER.get(args.provider)
    if not model:
        print(
            f"ERROR: no default model for provider {args.provider!r} — pass --model",
            file=sys.stderr,
        )
        return 3

    shot_list = load_shot_list(args.session)
    chunks = shot_list.get("chunks") or []
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        chunks = [c for c in chunks if c.get("id") in wanted]

    out_path = (
        Path(args.out)
        if args.out
        else CONTENT_ROOT / "sessions" / args.session / "working" / "scene-audit.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = VisionClient(args.provider, model)
    results: list[dict[str, Any]] = [None] * len(chunks)  # type: ignore[list-item]

    def _do(i: int) -> tuple[int, dict[str, Any]]:
        return i, audit_chunk(client, args.session, chunks[i])

    print(f"Auditing {len(chunks)} chunks (parallel={args.parallel}) via {args.provider}:{model}")
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

    flags, skipped = summarize(results)
    print()
    print(f"=== scene audit: {args.session} ===")
    print_report(results)
    print()
    print(f"{flags} flag(s), {skipped} skipped, {len(chunks)} total")

    payload = {
        "session": args.session,
        "provider": args.provider,
        "model": model,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": {"flags": flags, "skipped": skipped, "total": len(chunks)},
    }
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out_path}")

    return 2 if flags > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
