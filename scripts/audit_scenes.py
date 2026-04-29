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

Your job: inspect a single generated scene image and flag four failure classes
(plus one informational check at the end):

1. **ocr_missing** — the shot-list says specific text should appear on the
   frame (field `on_screen_text`). Does that exact text appear, legible, in
   the image? Flag if any declared text is missing, garbled, or substantively
   different.

2. **text_hallucination** — is the generator putting legible prose into the
   frame's FOCAL element that was not declared and reshapes what the
   narrative communicates?

   Spoolcast uses a "one rule per scene" convention in `on_screen_text`: a
   chunk whose declared text is just one line (e.g. one rules.md rule)
   typically renders as a card/document/page displaying MANY plausible
   lines — because cards with only one line look fake. These extra lines
   are scene-filling, not hallucination. The declared rule is the one the
   NARRATION quotes; the others are set dressing that gives the card weight.

   DO NOT flag as text_hallucination:

   - Additional plausible lines on a declared document, card, page, sticky
     note, terminal, or screen. When `on_screen_text` declares one line
     and the scene shows a full populated card, the extra lines are
     expected and correct.
   - Garbled / gibberish text like "MOTIVATIONAL IS GREATFUL OF THE SIORT"
     — this is stylistic wall-filler. Viewer won't read it.
   - Small background text on posters, sticky notes, wall calendars,
     bookshelves, or other decor in the periphery.
   - Monitor / terminal / screen content thematically consistent with the
     scene. A code editor showing code, a chat app showing a message, a
     dashboard showing numbers — all scene context, not hallucination.
   - Document titles / section headers (e.g. "rules.md", "CASE 2") that
     name a declared document or card; these are labels, not prose.

   DO flag as text_hallucination VERY SPARINGLY, only when the extra text
   directly contradicts or replaces the declared narrative. High bar.

   - A foreground title card or bumper whose WORDS ARE WRONG — declared
     title was "PAYOFF" but the frame shows a DIFFERENT word. (Extra
     supporting text on the same card is not a hallucination.)
   - A frame with MULTIPLE prominent unrelated prose blocks (three or
     more separate dialogue bubbles / big captions) that collectively
     push a narrative the declared text did not describe.
   - Text that's obviously generator-error: stage-direction prose
     ("character looks surprised") rendered as literal words in the frame.

   DO NOT flag:

   - A single AI dialogue line in a chat bubble when the visual_direction
     implies an AI/chat interaction (spoolcast convention: scenes show
     the AI replying even when the specific reply isn't in the shot-list;
     the CONCEPTUAL interaction is declared, the exact words are filler).
   - Any single line of prose. Single-line text, however "prominent",
     does not cross the bar alone. Need at least 2-3 undeclared prominent
     lines AND they reshape the narrative.
   - Text the model itself is describing rather than quoting (e.g., if
     your flag reads "The page contains bullets that were not declared",
     that's a meta-description, not a hallucinated text item — reject it).

   Final test: "would I regenerate this scene just to remove this text?"
   If no (the scene is fine, the extra text is set dressing), skip. If
   yes (the text meaningfully changes what the narration is saying),
   flag.

3. **anatomy** — extra limbs, malformed faces or hands, duplicate characters
   where only one was intended, phantom body parts floating in the frame,
   obviously warped or collapsed anatomy. The wojak-comic style is simple
   line art; subtle stylization is fine, structural failures are not.

4. **composition_overload** — are there so many competing focal subjects that
   the viewer's eye doesn't know where to land? Multi-panel chunks are OK if
   clearly partitioned; flag only when elements clutter without structure.

5. **mobile_unsafe** (informational — does NOT affect overall_verdict) — the
   widescreen master may optionally be exported to 9:16 mobile by center-crop
   (keeping roughly the middle 56% of the horizontal, discarding left and
   right edges).

   CRITICAL: the question is holistic, not categorical. Don't look for
   named failure modes (split-frame, side-third prop, wide text). Look
   at the scene and ask: after removing 22% from each side, how much of
   what the scene is trying to COMMUNICATE is gone?

   Mentally apply the 9:16 center-crop: erase the leftmost 22% and
   rightmost 22% of the frame. What remains is what the mobile viewer
   sees. Report the following, in order:

   (a) focal_position — where is the single most important thing in the
       frame? one of: center, left-third, right-third, top-third,
       bottom-third, split-panels (two or three distinct panels needed
       side-by-side), full-width-centered (content spanning the whole
       horizontal).

   (b) meaning_lost_to_crop — would the 9:16 center-crop remove more than
       ~10% of the scene's COMMUNICATED MEANING?

       "Communicated meaning" = everything the scene depends on to make
       its point. This includes:
       - declared on_screen_text that the viewer is meant to read
       - focal subjects (characters, objects) positioned to be the eye's
         target
       - key props the narration references or that carry the punchline
       - body prose on cards, pages, documents, checklists the viewer is
         meant to read
       - dialogue or speech bubbles
       - labels on objects, arrows pointing at things, diagrams the viewer
         is meant to parse

       It does NOT include scene dressing:
       - background posters, wall calendars, sticky notes in the periphery
       - ambient desk clutter, bookshelves, wall texture
       - blurred or garbled stylistic fill the viewer can't read anyway

       Calibration (anchor on these reference points):
       - ~0% loss: focal subject is centered, dressing is in the periphery,
         nothing the viewer needs to see lives in the side thirds → no.
       - ~5% loss: a single word trimmed by one letter in a way the viewer
         recovers from context (e.g. "DEFAULT" → "DEFAUL") → no.
       - ~15% loss: a paragraph's first or last word is clipped on every
         line and the viewer loses word flow; a key prop's label is
         clipped; a side character the scene needs is half gone → yes.
       - ~30%+ loss: a split-frame where a whole panel is discarded; a key
         prop entirely outside the center 56%; the focal subject
         positioned off-center such that the crop cuts through their face
         → yes.

       Readability-recoverability tiebreaker: if a casual viewer watching
       the video at normal speed can reconstruct the meaning despite the
       clip, no. If they can't, yes. This rule applies equally to text,
       characters, props, dialogue, and any other content — don't special-
       case text-heavy scenes.

   Verdict rule: mobile_unsafe = (meaning_lost_to_crop == yes)
                                 OR (focal_position == split-panels).
   Otherwise mobile_unsafe = false. split-panels is an automatic flag
   because side-by-side compositions are structurally unsalvageable by
   crop regardless of content.

   Suggest mobile_focal_suggestion ONLY when unsafe:
   - if focal_position is left-third or right-third → that zone name
     (the crop follows the focal off-center, e.g. "right-third" crop
     keeps the STOP sign that lives on the right)
   - (other zones available: top-third, bottom-third, upper-middle,
     lower-middle, top-left, top-right, bottom-left, bottom-right,
     top, bottom, left, right — pick the zone where the essential
     content actually lives)
   - if focal_position is split-panels → null (regen needed)
   - if focal_position is full-width-centered → null (regen needed; wide
     centered content cannot be saved by any single-zone crop)
   - if focal_position is center but meaning_lost_to_crop is still yes
     (because e.g. the focal document's body prose extends into both
     side thirds, or a labeled element needs both sides) → null
     (regen needed; crop alone cannot recover)

   Never emit mobile_focal_suggestion="center" when mobile_unsafe=true.

overall_verdict is based ONLY on categories 1-4. mobile_unsafe is a separate
signal that informs future mobile-export runs but never blocks the widescreen
render.

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
                max_tokens=3000,
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
        f"Declared on_screen_text — at minimum these lines must appear legible on the frame. "
        "Extra plausible content is acceptable when the declared text is a single line that names or "
        "implies a document, card, page, terminal, screen, or scene dressing — see system prompt rule 2 "
        "for when extra content is hallucination vs scene-filling.\n"
        f"{declared_text_block}\n\n"
        "Inspect the attached image. Reply with a single JSON object:\n"
        "{\n"
        '  "chunk_id": "<id>",\n'
        '  "ocr_missing": ["<declared text that does not appear or is garbled>", ...],\n'
        '  "text_hallucination": ["<legible text on the frame that was NOT declared>", ...],\n'
        '  "anatomy_flags": ["<specific anatomy or duplicate-character issue>", ...],\n'
        '  "composition_overload": "<null or one sentence if the frame is cluttered>",\n'
        '  "focal_position": "center" | "left-third" | "right-third" | "top-third" | "bottom-third" | "full-width-centered" | "split-panels",\n'
        '  "meaning_lost_to_crop": true | false,\n'
        '  "mobile_unsafe": true | false,\n'
        '  "mobile_focal_suggestion": "<zone name from the declared vocabulary, or null>",\n'
        '  "mobile_reasoning": "<one sentence if mobile_unsafe=true, else null>",\n'
        '  "overall_verdict": "ok" | "regenerate",\n'
        '  "reasoning": "<one to two sentences>"\n'
        "}\n"
        "If a category has no issues, return an empty array (or null for composition_overload).\n"
        "overall_verdict = 'regenerate' only when at least one of ocr_missing / text_hallucination / "
        "anatomy_flags / composition_overload has a flag. mobile_unsafe does NOT affect overall_verdict."
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
        mobile_marker = " [mobile-unsafe]" if r.get("mobile_unsafe") else ""
        print(f"  [{marker}]{mobile_marker} {cid}")
        for category in ("ocr_missing", "text_hallucination", "anatomy_flags"):
            items = r.get(category) or []
            for it in items:
                print(f"      {category}: {it}")
        co = r.get("composition_overload")
        if co:
            print(f"      composition_overload: {co}")
        if r.get("mobile_unsafe"):
            mf = r.get("mobile_focal_suggestion") or "(none — regen at mobile aspect needed)"
            mr = r.get("mobile_reasoning") or ""
            print(f"      mobile_focal_suggestion: {mf}")
            if mr:
                print(f"      mobile_reasoning: {mr}")
        if verdict == "regenerate" and r.get("reasoning"):
            print(f"      reasoning: {r['reasoning']}")


def apply_mobile_flags_to_shot_list(session: str, shot_list: dict[str, Any], results: list[dict[str, Any]]) -> int:
    """Write mobile_unsafe / mobile_focal back to the shot-list.

    Only touches `mobile_*` keys. Sparse: only writes when mobile_unsafe=true
    (or removes stale keys when a previously-unsafe chunk is now safe). Keeps
    the shot-list diff minimal and the "unsafe" state obvious at a glance.
    Returns the number of chunks where fields changed.
    """
    # Build a lookup from chunk_id -> audit result.
    audit_by_id: dict[str, dict[str, Any]] = {}
    for r in results:
        cid = r.get("chunk_id")
        if not cid or r.get("skipped") or r.get("error"):
            continue
        audit_by_id[cid] = r

    changed = 0
    for chunk in shot_list.get("chunks", []):
        cid = chunk.get("id")
        if cid not in audit_by_id:
            continue
        r = audit_by_id[cid]
        mu_new = bool(r.get("mobile_unsafe"))
        mf_new = r.get("mobile_focal_suggestion")

        mu_prev = chunk.get("mobile_unsafe", False)
        mf_prev = chunk.get("mobile_focal")

        if mu_new:
            # Sparse write: set only when non-default.
            if mu_prev is not True:
                chunk["mobile_unsafe"] = True
                changed += 1
            if mf_new and mf_new != "center" and mf_prev != mf_new:
                chunk["mobile_focal"] = mf_new
                changed += 1
            elif (not mf_new or mf_new == "center") and "mobile_focal" in chunk:
                # suggestion is null (needs regen) or center (default) —
                # clear any stale non-default value.
                del chunk["mobile_focal"]
                changed += 1
        else:
            # Chunk is safe; clear any stale unsafe/focal keys.
            if "mobile_unsafe" in chunk:
                del chunk["mobile_unsafe"]
                changed += 1
            if "mobile_focal" in chunk:
                del chunk["mobile_focal"]
                changed += 1

    path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    with path.open("w") as f:
        json.dump(shot_list, f, indent=2)
        f.write("\n")
    return changed


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
    p.add_argument(
        "--no-write-mobile-flags",
        action="store_true",
        help="skip writing mobile_unsafe / mobile_focal back to the shot-list (audit JSON only)",
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

    mobile_unsafe_count = sum(
        1 for r in results if not r.get("skipped") and not r.get("error") and r.get("mobile_unsafe")
    )

    payload = {
        "session": args.session,
        "provider": args.provider,
        "model": model,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": {
            "flags": flags,
            "skipped": skipped,
            "total": len(chunks),
            "mobile_unsafe": mobile_unsafe_count,
        },
    }
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out_path}")

    if mobile_unsafe_count:
        print(f"{mobile_unsafe_count} chunk(s) flagged mobile_unsafe (informational, does not block render)")

    if not args.no_write_mobile_flags:
        changed = apply_mobile_flags_to_shot_list(args.session, shot_list, results)
        if changed:
            print(f"wrote {changed} mobile_* field change(s) back to shot-list.json")
        else:
            print("no mobile_* field changes to shot-list.json")

    return 2 if flags > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
