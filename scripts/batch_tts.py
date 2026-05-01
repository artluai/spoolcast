#!/usr/bin/env python3
"""Batch-generate TTS audio for every beat in a session's shot-list.

One mp3 per beat at source/audio/<beat_id>.mp3. Honors session.json's
tts_voice and tts_playback_rate. Skips beats that already have an mp3
unless --force is set. Uses a ThreadPoolExecutor for throughput.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
TTS_SCRIPT = REPO_ROOT / "scripts" / "tts_client.py"
PYTHON = REPO_ROOT / "scripts" / ".venv" / "bin" / "python"


def apply_pronunciations(text: str, pronunciations: dict[str, str]) -> str:
    """Apply session pronunciation registry to narration text.

    Default mode: PLAIN-TEXT substitution. The mapped word in the narration
    is replaced with its alias spelling directly in the text sent to the TTS
    engine. This bypasses Chirp3-HD's unreliable <sub>/<phoneme> SSML support
    (caught on dev-log-04: IPA <phoneme> rendered as "art-dash-lu-dot-ai"
    instead of single-word "artlu").

    Optional SSML mode: if alias starts with `ssml:` the rest of the alias
    is treated as a raw SSML fragment to inject in place of the word. Only
    use this with voices known to honor the relevant SSML tags.

    Per STORY.md § Brand pronunciation registry.
    """
    if not pronunciations:
        return text
    out = text
    matched_ssml = False
    # Process longer keys first so compound patterns ("artlu.ai") match before
    # their substrings ("artlu") — otherwise the substring match would fire and
    # leave the compound pattern unaddressed.
    for word, alias in sorted(pronunciations.items(), key=lambda kv: len(kv[0]), reverse=True):
        if not word or not alias:
            continue
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        if not pattern.search(out):
            continue
        if alias.startswith("ssml:"):
            # SSML opt-in: wrap raw SSML fragment around the word.
            frag = alias[len("ssml:"):]
            out = pattern.sub(frag, out)
            matched_ssml = True
        else:
            # Default: plain-text substitution. Most reliable across voices.
            out = pattern.sub(alias, out)
    if matched_ssml:
        return f"<speak>{html.escape(out, quote=False)}</speak>"
    return out


def run_one(beat_id: str, text: str, out_path: Path, voice: str, rate: float, force: bool) -> tuple[str, bool, str]:
    if out_path.exists() and not force:
        return beat_id, True, "skip-exists"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PYTHON), str(TTS_SCRIPT),
        "--text", text,
        "--out", str(out_path),
        "--voice", voice,
        "--speaking-rate", str(rate),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return beat_id, False, result.stderr.strip()[:200]
        return beat_id, True, "ok"
    except subprocess.TimeoutExpired:
        return beat_id, False, "timeout"
    except Exception as e:
        return beat_id, False, str(e)[:200]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--only", default=None,
                   help="comma-separated beat ids (e.g. 01A,02B) to generate")
    args = p.parse_args()

    cfg_path = CONTENT_ROOT / "sessions" / args.session / "session.json"
    cfg = json.loads(cfg_path.read_text())
    voice = cfg.get("tts_voice", "Puck")
    rate = float(cfg.get("tts_playback_rate", 1.0))
    pronunciations = cfg.get("pronunciations") or {}

    shot_list_path = CONTENT_ROOT / "sessions" / args.session / "shot-list" / "shot-list.json"
    d = json.loads(shot_list_path.read_text())

    only = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}

    audio_dir = CONTENT_ROOT / "sessions" / args.session / "source" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for c in d["chunks"]:
        for b in c.get("beats") or []:
            bid = b.get("id")
            text = (b.get("narration") or "").strip()
            if not bid or not text:
                continue
            if only and bid not in only:
                continue
            text = apply_pronunciations(text, pronunciations)
            out = audio_dir / f"{bid}.mp3"
            jobs.append((bid, text, out))

    print(f"[tts-batch] session={args.session} jobs={len(jobs)} voice={voice} rate={rate} workers={args.workers}")
    successes = 0
    skipped = 0
    failures: list[tuple[str, str]] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(run_one, bid, text, out, voice, rate, args.force): bid
            for bid, text, out in jobs
        }
        for fut in cf.as_completed(futures):
            bid, ok, msg = fut.result()
            if ok and msg == "skip-exists":
                skipped += 1
                marker = "·"
            elif ok:
                successes += 1
                marker = "✓"
            else:
                failures.append((bid, msg))
                marker = "✗"
            print(f"[tts-batch] {marker} {bid} ({msg})")

    print(f"\n[tts-batch] done. {successes} new, {skipped} skipped, {len(failures)} failed.")
    if failures:
        print("[tts-batch] failures:")
        for bid, err in failures:
            print(f"  {bid}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
