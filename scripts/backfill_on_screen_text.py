#!/usr/bin/env python3
"""One-time extractor: populate `on_screen_text` from legacy `beat_description`.

Older sessions authored image prompts as one free-form `beat_description` blob
that mixed style direction and literal on-screen text into one string. The new
schema splits those: `visual_direction` for style, `on_screen_text` for text
(an array of strings the generator renders literally). See PIPELINE.md.

This script walks a session's shot-list, reads each chunk's existing
`beat_description`, extracts any literal on-screen text via regex heuristics
and an optional Qwen cleanup pass, and writes the result back to
`on_screen_text`. Chunks that already have `on_screen_text` populated are
skipped.

Heuristics, in order (fastest to slowest):
1. Quoted strings of 2+ words inside `beat_description` (single or double
   quotes, curly quotes). These are almost always card/caption content.
2. Patterns like "text reads X", "caption: 'X'", "hand-lettered: X",
   "label 'X'", "card showing X" → extract the X.
3. Fallback (optional, --llm): send the full beat_description to Qwen with
   the prompt "extract any text that will appear visible on the rendered
   frame; return a JSON array. Return [] if none." Catches the cases where
   text is described without quotes.

Usage:
    scripts/.venv/bin/python scripts/backfill_on_screen_text.py \\
        --session spoolcast-dev-log [--dry-run] [--llm]

Dry-run mode prints the proposed changes without writing. Default writes the
updated shot-list in place (pretty-printed, 2-space indent).
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]


CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_MODEL = "qwen/qwen-2.5-72b-instruct"

# Quoted-string extraction: straight quotes, curly quotes, backticks. Multi-word
# content (≥2 whitespace-separated tokens) to avoid matching every quoted single
# word (e.g. "the 'no' rule"). Case-insensitive flag is irrelevant for quotes.
_QUOTED_RE = re.compile(
    r"""
    (?:["'`\u201C\u2018])       # opening quote (curly or straight)
    ([^"'`\u201D\u2019\u201C\u2018]{2,})  # content, at least 2 chars
    (?:["'`\u201D\u2019])       # closing quote
    """,
    re.VERBOSE,
)

# Cue phrases that introduce on-screen text. Capture the quoted or trailing
# content after the cue.
_CUE_RE = re.compile(
    r"""
    (?:text\s+reads|caption(?:\s+reads|:)?|hand[- ]lettered(?::|\s+reading)?|
       label(?:ed)?(?:\s+reads)?|card\s+(?:reading|showing|reads)|title\s+reads|
       rendered\s+as|shown\s+as|rule\s+reads|bullet\s+reads|stamp\s+reads)
    [\s:]*
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_via_regex(beat_description: str) -> list[str]:
    """Return a deduplicated list of plausible on-screen text strings.

    Conservative: multi-word quoted strings + cue-introduced trailing quotes.
    Does NOT try to decide whether a string is on-screen text vs. a quoted
    narration fragment — reviewer/LLM pass handles that nuance.
    """
    if not beat_description:
        return []
    candidates: list[str] = []

    # Primary: all multi-word quoted strings.
    for m in _QUOTED_RE.finditer(beat_description):
        text = m.group(1).strip()
        if len(text.split()) >= 2:
            candidates.append(text)

    # Cue-phrase hits that might precede a quoted capture we already grabbed
    # are fine — dedup below. Cues pointing at a quoted value already handled.
    # Dedup preserving first-seen order.
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def llm_cleanup(client: "OpenAI", beat_description: str, existing: list[str]) -> list[str]:
    """Ask Qwen to review the beat_description and produce the final array.

    The prompt gives it the existing regex-extracted candidates and the full
    beat_description, and asks for the final authoritative list.
    """
    if not beat_description:
        return existing
    system_prompt = (
        "You are a migration tool extracting on-screen text from a scene prompt.\n"
        "Given a free-form description of an illustrated scene, identify every "
        "piece of text that will appear visible (legible) on the rendered frame "
        "— titles, labels, captions, rule cards, documents, bullet points, "
        "stamps, handwritten notes, signs. Exclude: narration quoted only as "
        "spoken dialogue, character names that don't appear as on-frame text, "
        "style descriptors. Return a JSON array of strings (the exact words "
        "that should be rendered). Return [] if none. No prose outside the JSON."
    )
    user = (
        f"Scene description:\n{beat_description}\n\n"
        f"Regex pre-extraction produced these candidates (may be incomplete "
        f"or contain false positives): {json.dumps(existing)}\n\n"
        f"Produce the final JSON array of on-screen text strings."
    )
    try:
        resp = client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"  WARN: llm cleanup failed, keeping regex result: {e}", file=sys.stderr)
        return existing
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
        if text.rstrip().endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
            return [s.strip() for s in parsed if s.strip()]
    except json.JSONDecodeError:
        pass
    print(f"  WARN: llm returned non-JSON, keeping regex result: {text[:120]!r}", file=sys.stderr)
    return existing


def make_llm_client() -> "OpenAI":
    if OpenAI is None:
        print(
            "ERROR: openai SDK not installed. Run: scripts/.venv/bin/pip install openai",
            file=sys.stderr,
        )
        sys.exit(3)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(3)
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill on_screen_text from beat_description.")
    p.add_argument("--session", required=True)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print proposed changes, don't write the shot-list",
    )
    p.add_argument(
        "--llm",
        action="store_true",
        help="use Qwen (via OpenRouter) to review and clean up regex extractions",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing on_screen_text even when already populated",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    path = CONTENT_ROOT / "sessions" / args.session / "shot-list" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: shot-list not found at {path}", file=sys.stderr)
        return 3
    with path.open() as f:
        shot_list = json.load(f)

    llm_client = make_llm_client() if args.llm else None

    updated = 0
    skipped = 0
    print(f"=== backfill on_screen_text: {args.session} ===")
    for c in shot_list.get("chunks", []):
        cid = c.get("id") or "<unnamed>"
        isrc = (c.get("image_source") or "generated").strip()
        if isrc not in {"generated"}:
            skipped += 1
            continue
        existing = c.get("on_screen_text")
        if existing and not args.overwrite:
            skipped += 1
            continue
        bd = c.get("beat_description") or ""
        candidates = extract_via_regex(bd)
        final = candidates
        if llm_client is not None:
            final = llm_cleanup(llm_client, bd, candidates)
        if not final:
            # No text detected. Set empty array explicitly so validator knows
            # this chunk was reviewed (vs. absent/unreviewed).
            final = []
        if final == existing:
            skipped += 1
            continue
        print(f"  {cid}: {json.dumps(final)}")
        c["on_screen_text"] = final
        updated += 1

    print()
    print(f"updated={updated} skipped={skipped}")

    if args.dry_run:
        print("(dry-run: shot-list not written)")
        return 0

    if updated == 0:
        print("no changes to write")
        return 0

    with path.open("w") as f:
        json.dump(shot_list, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
