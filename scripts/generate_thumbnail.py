"""
generate_thumbnail.py — one-off image gen with a raw prompt.

Reuses kie_client + dotenv loading from generate_scene.py, but DOES NOT
mix in the session style anchor or session prompt prefix. The full prompt
is whatever you pass on the CLI — useful for thumbnails where you need
different style rules than the locked-in session look (e.g. allowing one
accent color for clickability).

Usage:
    scripts/.venv/bin/python scripts/generate_thumbnail.py \\
        --session pilot \\
        --out source/generated-assets/thumbnail-v1.png \\
        --prompt "..."
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path

# Load .env from repo root (same way generate_scene.py does)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# Now import kie_client (must come AFTER env is loaded)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kie_client import KieClient, build_input_from_session  # noqa: E402


CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "spoolcast-content"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a one-off image (no style mixing)")
    parser.add_argument("--session", required=True, help="session id — config drives resolution/aspect/model")
    parser.add_argument("--out", required=True, help="output path (relative to session dir, or absolute)")
    parser.add_argument("--prompt", required=True, help="raw prompt — no style prefix added")
    parser.add_argument("--model", default=None, help="override session.preferred_model")
    parser.add_argument("--image-ref", default=None, help="optional URL to condition on")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = CONTENT_ROOT / "sessions" / args.session / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = KieClient()
    image_refs = [args.image_ref] if args.image_ref else []
    # Session-aware: pulls resolution/aspect/output_format from session.json
    # so we don't silently ship at 2K when the project standard is 1K.
    model, input_dict = build_input_from_session(
        args.session,
        prompt=args.prompt,
        image_refs=image_refs,
        model_override=args.model,
    )
    print(f"[thumb] submitting model={model} resolution={input_dict.get('resolution')}", flush=True)
    task_id = client.submit_task(model=model, input_dict=input_dict)
    print(f"[thumb] task: {task_id}", flush=True)
    result = client.poll_task(task_id)
    print(f"[thumb] state={result.state} urls={result.result_urls}", flush=True)
    if not result.result_urls:
        print(f"[thumb] FAILED: no URLs returned (failCode={result.fail_code} failMsg={result.fail_msg})", flush=True)
        sys.exit(1)
    urllib.request.urlretrieve(result.result_urls[0], out_path)
    print(f"[thumb] -> {out_path} ({out_path.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
