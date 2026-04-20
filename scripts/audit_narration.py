#!/usr/bin/env python3
"""Pairwise narration audit of a spoolcast shot-list.

For every adjacent beat pair, checks whether beat N+1 is a natural continuation
of beat N from the viewer's perspective (bridge test). For every beat, checks
whether it's overweight/packed with decorative density (overload test). Uses
Claude Haiku via the Anthropic SDK.

Usage:
  scripts/.venv/bin/python scripts/audit_narration.py \\
      --session spoolcast-explainer \\
      [--out audit-report.json] \\
      [--model claude-haiku-4-5-20251001] \\
      [--parallel N]

Reads: ../spoolcast-content/sessions/<session>/shot-list/shot-list.json
Writes: ../spoolcast-content/sessions/<session>/working/narration-audit.json

Exit codes:
  0 = no flags
  1 = at least one bridge flag raised
  2 = at least one overweight flag raised (overrides 1 if both, takes precedence)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Load .env from repo root (matches kie_client / tts_client pattern).
try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass  # dotenv optional — env vars can also come from the shell directly.

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore[assignment,misc]

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]


DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL_BY_PROVIDER = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openrouter": "qwen/qwen-2.5-72b-instruct",
}
# OpenRouter is OpenAI-SDK-compatible; just point base_url at their endpoint.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CONTENT_ROOT = Path("../spoolcast-content")

# Deterministic post-filter patterns. A beat starting with one of these is
# explicitly signaling "next item in a list" or "conclusion coming" — the
# transition itself IS the bridge. Used to suppress LLM false-positive bridge
# flags where the model doesn't respect the strict enumerated-list or
# closing-conclusion archetypes.
import re as _re

# Matches at start of narration (case-insensitive): "One.", "Two.", ... "Ten.",
# "First.", "Second.", ..., "Step 1.", "1.", ordinal-followed-by-period.
_ENUMERATION_RE = _re.compile(
    r"^\s*("
    r"One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|"
    r"First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|"
    r"Then|Finally|Lastly|Next"
    r")\b[\.,:]",
    _re.IGNORECASE,
)
_STEP_RE = _re.compile(r"^\s*Step\s+\d+\s*[\.:]", _re.IGNORECASE)
# Integer followed by `.` or `)` or `:` but NOT followed by another digit
# (so "1." enumerates but "1.2x" doesn't match).
_NUM_DOT_RE = _re.compile(r"^\s*\d+\s*[\.\):](?!\d)")

# Beats that begin the outro / wrap-up. If N+1 starts with one of these, the
# closing-conclusion archetype applies and no bridge is needed.
_CLOSING_RE = _re.compile(
    r"^\s*("
    r"So|In short|In conclusion|To recap|To summarize|"
    r"Zooming out|Step back|Stepping back|"
    r"Which brings us|All of this means|Here'?s the frame|"
    r"Bottom line|Put differently|The upshot"
    r")\b[\.,:]?",
    _re.IGNORECASE,
)


def _starts_with_list_marker(text: str) -> bool:
    text = text.strip()
    return bool(
        _ENUMERATION_RE.match(text)
        or _STEP_RE.match(text)
        or _NUM_DOT_RE.match(text)
    )


def _starts_with_closing_marker(text: str) -> bool:
    return bool(_CLOSING_RE.match(text.strip()))


def filter_false_positives(
    bridge_flags: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply deterministic post-filter. Returns (kept_flags, suppressed_flags).

    Suppresses bridge flags where:
    - both beats share a non-empty `reveal_group` — visual continuity and
      tight cadence IS the bridge (see STORY.md § Part 2 "Reveal groups").
    - beat N+1's narration starts with an enumeration marker (One. / Two. /
      First. / Step 1. / 1. / etc) — the marker itself bridges the list item.
    - beat N+1's narration starts with a closing-conclusion marker (So... / In
      short... / Zooming out... / etc) — the closing framing is the bridge.

    Each suppressed flag is annotated with a `suppressed_reason` field.
    """
    kept: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for f in bridge_flags:
        group_n = (f.get("beat_n_reveal_group") or "").strip()
        group_n1 = (f.get("beat_n1_reveal_group") or "").strip()
        if group_n and group_n == group_n1:
            f2 = dict(f)
            f2["suppressed_reason"] = (
                f"beats share reveal_group {group_n!r} — visual + cadence IS the bridge"
            )
            suppressed.append(f2)
            continue
        n1_text = f.get("beat_n1_narration", "")
        if _starts_with_list_marker(n1_text):
            f2 = dict(f)
            f2["suppressed_reason"] = "beat N+1 starts with enumeration marker"
            suppressed.append(f2)
            continue
        if _starts_with_closing_marker(n1_text):
            f2 = dict(f)
            f2["suppressed_reason"] = "beat N+1 starts with closing-conclusion marker"
            suppressed.append(f2)
            continue
        kept.append(f)
    return kept, suppressed

BRIDGE_SYSTEM_PROMPT = """You are a narrative pacing reviewer for an explainer video.

Your job: for each adjacent beat pair (N, N+1), decide whether beat N+1 is a
natural continuation of beat N from the viewer's perspective, or whether the
transition needs a bridge line.

Apply the viewer-cognition test:
1. What is the viewer likely thinking after hearing beat N?
2. Does beat N+1 answer that implicit thought, or does it introduce something
   orthogonal that requires a bridge?

Bridge archetypes (connection_type values):
- setup-consequence: fact → what it means ("X happened. Which means Y.")
- state-question: experience → implied question → answer ("You build things. It came out great. Now what?")
- claim-evidence: assertion → proof ("X is true. Watch this.")
- problem-attempt: pain point → naive fix → failure ("The naive fix is a CSS wipe. It's robotic.")
- problem-solution: pain point → real fix
- comparison: two things → which wins
- enumerated-list: STRICT — items only qualify as a list (and skip the
  bridge requirement between items) if the list is explicitly marked with
  ordinal cues ("One. Two. Three." / "First. Then. Finally." / "Step 1.") OR
  an upfront enumerate-framing ("There are three. The first is..."). Merely
  adjacent parallel statements without an explicit list signal DO still
  require bridges — the viewer has no frame for treating them as a list.
- tricolon: STRICT — parallel structure carries the transition ONLY when
  ALL of: exactly three (or at most four) short items, same opening word or
  phrase (anaphora) on each, grammatically identical structure. If any piece
  is missing, treat as adjacent statements needing a bridge.
- closing-conclusion: signals wrap-up / outro / core-message restatement.
  Phrases like "So...", "So where does this leave us?", "In short.",
  "To recap.", "Which brings us back to...", "Zooming out.", "All of this
  means...". A wrap-up chunk arriving without a closing signal is an
  orthogonal-jump, even if the content is right.
- callback: explicit reference to earlier establishment
- orthogonal-jump: no archetype fits; bridge is missing

Default is "bridge-needed" unless you can justify the pair fits one of the
non-orthogonal-jump archetypes above. In particular: do NOT mark adjacent
parallel statements as "tricolon" or "enumerated-list" unless the STRICT
tests pass.

Always reply with a single JSON object. No prose outside the JSON."""

OVERLOAD_SYSTEM_PROMPT = """You are a narrative pacing reviewer for an explainer video.

Your job: for each beat, decide whether it is overweight — packed with
decorative density, stacked jargon, or multiple concepts that would land better
spread out.

Apply the overload test:
1. Is this beat load-bearing for the core message, or decorative?
2. Is the density appropriate for its position in the video? (Cold opens should
   be dense-quick; middle sections should be relaxed; proof/punchline moments
   should be slow.)
3. Could half the words be cut without losing the argument? Is jargon stacked?
   Are multiple concepts packed in when they'd land better spread out?

Always reply with a single JSON object. No prose outside the JSON."""


def load_shot_list(session: str) -> dict[str, Any]:
    path = CONTENT_ROOT / "sessions" / session / "shot-list" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: shot-list not found at {path}", file=sys.stderr)
        sys.exit(3)
    with path.open() as f:
        return json.load(f)


def load_core_message(session: str) -> str:
    path = CONTENT_ROOT / "sessions" / session / "session.json"
    if not path.exists():
        return ""
    try:
        with path.open() as f:
            data = json.load(f)
        return str(data.get("core_message", "") or "")
    except (json.JSONDecodeError, OSError):
        return ""


def flatten_beats(shot_list: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten chunks into a sequential list of beats, skipping empty narrations.
    Tags each beat with its chunk's `reveal_group` so the post-filter can
    suppress intra-group bridge flags."""
    beats: list[dict[str, Any]] = []
    chunks = shot_list.get("chunks", [])
    for chunk in chunks:
        chunk_id = chunk.get("id") or chunk.get("chunk_id") or ""
        scene_title = (
            chunk.get("scene_title")
            or chunk.get("scene")
            or chunk.get("title")
            or ""
        )
        reveal_group = (chunk.get("reveal_group") or "").strip()
        chunk_beats = chunk.get("beats", [])
        for i, beat in enumerate(chunk_beats):
            narration = (beat.get("narration") or "").strip()
            if not narration:
                continue
            beats.append(
                {
                    "reveal_group": reveal_group,
                    "chunk_id": chunk_id,
                    "scene_title": scene_title,
                    "beat_id": beat.get("id") or beat.get("beat_id") or "",
                    "narration": narration,
                    "pause_after": beat.get("pause_after"),
                    "is_last_beat_of_chunk": (i == len(chunk_beats) - 1),
                    "boundary_kind": beat.get("boundary_kind"),
                    "weight": beat.get("weight"),
                }
            )
    return beats


def parse_json_reply(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from a model reply. Returns None on failure."""
    text = text.strip()
    # Strip common code-fence wrappers.
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence.
        lines = lines[1:]
        # Drop closing fence if present.
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    # Last-ditch: find the first {...} blob.
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


class ModelClient:
    """Thin provider-dispatch client. Wraps either Anthropic or OpenAI-SDK (used
    against OpenRouter for Qwen). Same `call()` signature for both."""

    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        if provider == "anthropic":
            if Anthropic is None:
                print(
                    "ERROR: anthropic SDK not installed. "
                    "Run: scripts/.venv/bin/pip install anthropic",
                    file=sys.stderr,
                )
                sys.exit(3)
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
                sys.exit(3)
            self._client = Anthropic()
        elif provider == "openrouter":
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

    def call(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        try:
            if self.provider == "anthropic":
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text_parts = [
                    b.text
                    for b in response.content
                    if getattr(b, "type", None) == "text"
                ]
                text = "".join(text_parts) if text_parts else ""
            else:  # openrouter
                response = self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=400,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                text = (response.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"  WARN: API call failed: {e}", file=sys.stderr)
            return None

        if not text:
            print("  WARN: empty response", file=sys.stderr)
            return None
        parsed = parse_json_reply(text)
        if parsed is None:
            print(
                f"  WARN: failed to parse JSON from response: {text[:200]!r}",
                file=sys.stderr,
            )
        return parsed


# Backwards-compat shim: old name still callable.
def call_claude(
    client: "ModelClient | Anthropic",
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any] | None:
    if isinstance(client, ModelClient):
        return client.call(system_prompt, user_prompt)
    # Legacy path (raw Anthropic client): wrap and call
    wrapped = ModelClient.__new__(ModelClient)
    wrapped.provider = "anthropic"
    wrapped.model = model
    wrapped._client = client
    return wrapped.call(system_prompt, user_prompt)


def build_bridge_prompt(
    core_message: str,
    beat_n: dict[str, Any],
    beat_n1: dict[str, Any],
) -> str:
    same_chunk = beat_n["chunk_id"] == beat_n1["chunk_id"]
    if same_chunk:
        context_line = "They are inside the same chunk, same image."
    else:
        context_line = (
            "They are in different chunks, beat N+1 begins a new chunk."
        )
    return (
        f'Core message of the video: "{core_message}"\n\n'
        f'Beat N:     "{beat_n["narration"]}"\n'
        f'Beat N+1:   "{beat_n1["narration"]}"\n\n'
        f"Context: beat N and beat N+1 are adjacent in the narration. "
        f"{context_line}\n\n"
        "Apply the viewer-cognition test:\n"
        "1. What is the viewer likely thinking after hearing beat N?\n"
        "2. Does beat N+1 answer that implicit thought, or does it introduce "
        "something orthogonal that requires a bridge?\n\n"
        "Reply in JSON:\n"
        "{\n"
        '  "verdict": "ok" | "bridge_needed",\n'
        '  "viewer_thought_after_n": "<one sentence>",\n'
        '  "connection_type": "<one of: setup-consequence, state-question, '
        "claim-evidence, problem-attempt, problem-solution, comparison, "
        'tricolon, callback, orthogonal-jump>",\n'
        '  "proposed_bridge": "<if bridge_needed: one sentence in the same '
        'voice as the existing narration. else: null>",\n'
        '  "reasoning": "<one sentence>"\n'
        "}"
    )


def build_overload_prompt(
    core_message: str,
    beat: dict[str, Any],
    beat_index: int,
    total_beats: int,
) -> str:
    word_count = len(beat["narration"].split())
    percentage = int(round((beat_index + 1) / max(total_beats, 1) * 100))
    return (
        f'Core message: "{core_message}"\n'
        f'Scene: "{beat.get("scene_title") or ""}"\n'
        f"Position in video: {beat_index + 1} of {total_beats} beats "
        f"(~{percentage}% in)\n\n"
        f'Beat narration: "{beat["narration"]}"\n'
        f"Word count: {word_count}\n\n"
        "Apply the overload test:\n"
        "1. Is this beat load-bearing for the core message, or decorative?\n"
        "2. Is the density appropriate for its position in the video? "
        "(Cold opens should be dense-quick; middle sections should be relaxed; "
        "proof/punchline moments should be slow.)\n"
        "3. Could half the words be cut without losing the argument? Is jargon "
        "stacked? Are multiple concepts packed in when they'd land better "
        "spread out?\n\n"
        "Reply in JSON:\n"
        "{\n"
        '  "verdict": "ok" | "overweight",\n'
        '  "proposed_fix": "<if overweight: one of \'cut\', \'simplify\', '
        "'split' + the proposed replacement text>\",\n"
        '  "reasoning": "<one sentence>"\n'
        "}"
    )


def run_bridge_audit(
    client: "ModelClient",
    model: str,
    beats: list[dict[str, Any]],
    core_message: str,
    parallel: int,
) -> list[dict[str, Any]]:
    pairs = list(range(len(beats) - 1))
    results: list[dict[str, Any] | None] = [None] * len(pairs)

    def audit_pair(i: int) -> tuple[int, dict[str, Any] | None]:
        beat_n = beats[i]
        beat_n1 = beats[i + 1]
        prompt = build_bridge_prompt(core_message, beat_n, beat_n1)
        parsed = call_claude(client, model, BRIDGE_SYSTEM_PROMPT, prompt)
        return i, parsed

    print(f"Auditing {len(pairs)} adjacent pairs (parallel={parallel})...")
    if parallel <= 1:
        for i in pairs:
            _, parsed = audit_pair(i)
            results[i] = parsed
            if (i + 1) % 10 == 0 or i == len(pairs) - 1:
                print(f"  bridge: {i + 1}/{len(pairs)}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as ex:
            futures = {ex.submit(audit_pair, i): i for i in pairs}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                i, parsed = fut.result()
                results[i] = parsed
                done += 1
                if done % 10 == 0 or done == len(pairs):
                    print(f"  bridge: {done}/{len(pairs)}")

    flags: list[dict[str, Any]] = []
    for i, parsed in enumerate(results):
        if parsed is None:
            continue
        verdict = parsed.get("verdict")
        if verdict != "bridge_needed":
            continue
        beat_n = beats[i]
        beat_n1 = beats[i + 1]
        flags.append(
            {
                "beat_n_id": beat_n["beat_id"],
                "beat_n_chunk": beat_n["chunk_id"],
                "beat_n_narration": beat_n["narration"],
                "beat_n_reveal_group": beat_n.get("reveal_group", ""),
                "beat_n1_id": beat_n1["beat_id"],
                "beat_n1_chunk": beat_n1["chunk_id"],
                "beat_n1_narration": beat_n1["narration"],
                "beat_n1_reveal_group": beat_n1.get("reveal_group", ""),
                "verdict": verdict,
                "viewer_thought_after_n": parsed.get("viewer_thought_after_n"),
                "connection_type": parsed.get("connection_type"),
                "proposed_bridge": parsed.get("proposed_bridge"),
                "reasoning": parsed.get("reasoning"),
            }
        )
    return flags


def run_overweight_audit(
    client: "ModelClient",
    model: str,
    beats: list[dict[str, Any]],
    core_message: str,
    parallel: int,
) -> list[dict[str, Any]]:
    total = len(beats)
    results: list[dict[str, Any] | None] = [None] * total

    def audit_beat(i: int) -> tuple[int, dict[str, Any] | None]:
        prompt = build_overload_prompt(core_message, beats[i], i, total)
        parsed = call_claude(client, model, OVERLOAD_SYSTEM_PROMPT, prompt)
        return i, parsed

    print(f"Auditing {total} beats for overweight (parallel={parallel})...")
    if parallel <= 1:
        for i in range(total):
            _, parsed = audit_beat(i)
            results[i] = parsed
            if (i + 1) % 10 == 0 or i == total - 1:
                print(f"  overweight: {i + 1}/{total}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as ex:
            futures = {ex.submit(audit_beat, i): i for i in range(total)}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                i, parsed = fut.result()
                results[i] = parsed
                done += 1
                if done % 10 == 0 or done == total:
                    print(f"  overweight: {done}/{total}")

    flags: list[dict[str, Any]] = []
    for i, parsed in enumerate(results):
        if parsed is None:
            continue
        verdict = parsed.get("verdict")
        if verdict != "overweight":
            continue
        beat = beats[i]
        flags.append(
            {
                "beat_id": beat["beat_id"],
                "chunk_id": beat["chunk_id"],
                "narration": beat["narration"],
                "verdict": verdict,
                "proposed_fix": parsed.get("proposed_fix"),
                "reasoning": parsed.get("reasoning"),
            }
        )
    return flags


def print_stdout_report(
    session_id: str,
    total_beats: int,
    total_pairs: int,
    bridge_flags: list[dict[str, Any]],
    overweight_flags: list[dict[str, Any]],
) -> None:
    print()
    print(f"=== Narration audit: {session_id} ===")
    print(f"Total beats: {total_beats}")
    print(f"Total pairs audited: {total_pairs}")
    print(f"Bridge flags: {len(bridge_flags)}")
    print(f"Overweight flags: {len(overweight_flags)}")
    print()

    for f in bridge_flags:
        conn = f.get("connection_type") or "?"
        n_chunk = f.get("beat_n_chunk") or "?"
        n_id = f.get("beat_n_id") or "?"
        n1_chunk = f.get("beat_n1_chunk") or "?"
        n1_id = f.get("beat_n1_id") or "?"
        print(
            f"BRIDGE — {n_chunk}/{n_id} -> {n1_chunk}/{n1_id}: {conn}"
        )
        print(f'  N:   "{f.get("beat_n_narration")}"')
        print(f'  N+1: "{f.get("beat_n1_narration")}"')
        if f.get("proposed_bridge"):
            print(f'  Proposed bridge: "{f["proposed_bridge"]}"')
        print()

    for f in overweight_flags:
        chunk_id = f.get("chunk_id") or "?"
        beat_id = f.get("beat_id") or "?"
        print(f"OVERWEIGHT — {chunk_id}/{beat_id}")
        print(f'  "{f.get("narration")}"')
        if f.get("proposed_fix"):
            print(f"  Proposed fix: {f['proposed_fix']}")
        print()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Pairwise narration audit of a spoolcast shot-list. "
            "Checks adjacency (bridge) and density (overload) using Claude Haiku."
        ),
    )
    p.add_argument(
        "--session",
        required=True,
        help="Session ID, e.g. spoolcast-explainer",
    )
    p.add_argument(
        "--out",
        default=None,
        help=(
            "Output JSON path. Default: "
            "../spoolcast-content/sessions/<session>/working/narration-audit.json"
        ),
    )
    p.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        choices=["anthropic", "openrouter"],
        help=(
            f"LLM provider (default: {DEFAULT_PROVIDER}). "
            "anthropic uses ANTHROPIC_API_KEY; openrouter uses OPENROUTER_API_KEY."
        ),
    )
    p.add_argument(
        "--model",
        default=None,
        help=(
            "Model ID. Defaults depend on provider: "
            f"anthropic={DEFAULT_MODEL_BY_PROVIDER['anthropic']}, "
            f"openrouter={DEFAULT_MODEL_BY_PROVIDER['openrouter']}."
        ),
    )
    p.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Max concurrent requests (default: 1 = sequential)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    provider = args.provider
    model = args.model or DEFAULT_MODEL_BY_PROVIDER[provider]

    shot_list = load_shot_list(args.session)
    core_message = load_core_message(args.session)
    beats = flatten_beats(shot_list)

    if len(beats) == 0:
        print("ERROR: no non-empty narration beats found in shot-list.", file=sys.stderr)
        return 3

    # ModelClient init handles provider-specific key checks + SDK presence.
    client = ModelClient(provider=provider, model=model)
    print(f"Audit provider={provider} model={model}")

    bridge_flags: list[dict[str, Any]] = []
    overweight_flags: list[dict[str, Any]] = []

    if len(beats) >= 2:
        bridge_flags = run_bridge_audit(
            client, model, beats, core_message, args.parallel
        )
    else:
        print("Only 1 beat — skipping bridge audit.")

    # Deterministic post-filter: suppress bridge flags where beat N+1 starts
    # with an enumeration marker or closing-conclusion marker. These signal
    # the bridge is already there structurally — LLMs (especially Qwen) often
    # flag them anyway.
    raw_bridge_count = len(bridge_flags)
    bridge_flags, suppressed_flags = filter_false_positives(bridge_flags)
    if suppressed_flags:
        print(
            f"Post-filter: suppressed {len(suppressed_flags)} bridge flags "
            f"(enumeration/closing markers). Kept {len(bridge_flags)}."
        )

    overweight_flags = run_overweight_audit(
        client, model, beats, core_message, args.parallel
    )

    report = {
        "session_id": args.session,
        "total_beats": len(beats),
        "total_pairs": max(0, len(beats) - 1),
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "bridge_flags_raw_count": raw_bridge_count,
        "bridge_flags_suppressed_count": len(suppressed_flags),
        "bridge_flags": bridge_flags,
        "overweight_flags": overweight_flags,
        "suppressed_bridge_flags": suppressed_flags,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = (
            CONTENT_ROOT
            / "sessions"
            / args.session
            / "working"
            / "narration-audit.json"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote report: {out_path}")

    print_stdout_report(
        args.session,
        len(beats),
        max(0, len(beats) - 1),
        bridge_flags,
        overweight_flags,
    )

    if overweight_flags:
        return 2
    if bridge_flags:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
