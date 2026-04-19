"""
generate_scene.py — generate ONE illustration for a spoolcast chunk.

Reads session config from spoolcast-content/sessions/<session-id>/session.json
for model, resolution, style anchor. Composes a per-chunk prompt from:
- the session style anchor (prompt or reference image)
- the chunk's narration
- optional beat description

Calls kie_client, saves the PNG to the canonical scenes folder, and writes or
updates the scenes manifest.

See ASSET_RULES.md (Primary Visual Pipeline) for the full contract.

Usage:
    scripts/.venv/bin/python scripts/generate_scene.py \\
        --session <session-id> \\
        --chunk <chunk-id> \\
        --narration "the narration text for this chunk" \\
        --beat "optional beat description"
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

from kie_client import KieClient, KieError, build_input_for_model


# ---- paths -------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


def session_dir(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id


def scenes_dir(session_id: str) -> Path:
    return session_dir(session_id) / "source" / "generated-assets" / "scenes"


def manifest_path(session_id: str) -> Path:
    return session_dir(session_id) / "manifests" / "scenes.manifest.json"


def session_config_path(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"


# ---- config ------------------------------------------------------------

def load_session_config(session_id: str) -> dict[str, Any]:
    path = session_config_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"session config not found: {path}")
    with open(path) as f:
        cfg = json.load(f)
    for required in ("session_id", "ai_budget", "preferred_model"):
        if required not in cfg:
            raise ValueError(f"session.json missing required field: {required}")
    if cfg["session_id"] != session_id:
        raise ValueError(
            f"session.json session_id mismatch: {cfg['session_id']!r} vs {session_id!r}"
        )
    return cfg


# ---- manifest ----------------------------------------------------------

def load_or_init_manifest(session_id: str) -> dict[str, Any]:
    path = manifest_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {
        "run_name": f"scenes-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "session_id": session_id,
        "created_at": _dt.datetime.now(_dt.UTC).isoformat(),
        "style_anchor": None,
        "items": [],
    }


def save_manifest(session_id: str, manifest: dict[str, Any]) -> None:
    path = manifest_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


# ---- prompt composition ------------------------------------------------

def compose_prompt(
    cfg: dict[str, Any], narration: str, beat: str | None = None
) -> tuple[str, list[str]]:
    """Build the image prompt + image_input list for this chunk.

    Tight assembly: style + scene description only. The narration text is kept
    in the signature for future use (timing, audio sync) but is NOT included
    in the image prompt — the beat should describe exactly what the image
    must show. If no beat is provided, narration is used as the fallback
    scene description.
    """
    style_ref = cfg.get("style_reference")
    default_style = cfg.get("default_style_prompt")

    style_text: str | None = None
    image_input: list[str] = []

    if isinstance(style_ref, str) and style_ref.startswith(("http://", "https://")):
        image_input.append(style_ref)
    elif isinstance(style_ref, str) and style_ref.strip():
        style_text = style_ref
    elif default_style:
        style_text = default_style
    else:
        raise ValueError(
            "session config has neither style_reference nor default_style_prompt — "
            "refusing to generate without a locked style (see ASSET_RULES.md)"
        )

    parts: list[str] = []
    if style_text:
        parts.append(style_text.rstrip("."))
    scene = beat if beat else narration
    if scene:
        parts.append(f"Scene: {scene.rstrip('.')}")

    prompt = ". ".join(parts) + "."
    return prompt, image_input


# ---- generate ----------------------------------------------------------

def generate(
    session_id: str,
    chunk_id: str,
    narration: str,
    beat: str | None = None,
    *,
    force: bool = False,
    model_override: str | None = None,
    dest_override: Path | None = None,
    image_ref_override: str | None = None,
) -> Path:
    cfg = load_session_config(session_id)
    scenes = scenes_dir(session_id)
    scenes.mkdir(parents=True, exist_ok=True)
    dest = dest_override if dest_override is not None else (scenes / f"{chunk_id}.png")
    model = model_override or cfg["preferred_model"]

    if dest.exists() and not force:
        print(f"[gen] {chunk_id} already exists at {dest}. Use --force to regenerate.")
        return dest

    prompt, image_input = compose_prompt(cfg, narration, beat)

    if image_ref_override:
        # Explicit continuity reference — overrides any manifest style anchor.
        # Used for continues-from-prev / callback-to-<chunk-id> cases.
        image_input = [image_ref_override]
        manifest = load_or_init_manifest(session_id)
    else:
        # Pass the existing style anchor image back in on subsequent generations
        # (style consistency rule — see ASSET_RULES.md § Style Anchor Rule).
        manifest = load_or_init_manifest(session_id)
        anchor = manifest.get("style_anchor")
        if anchor and anchor.get("kind") in ("image_url", "local_image"):
            anchor_src = anchor.get("value")
            if anchor_src and anchor_src not in image_input:
                # kie.ai needs a URL, so only pass through if it's a URL.
                if anchor.get("kind") == "image_url":
                    image_input.append(anchor_src)

    client = KieClient()
    print(f"[gen] session={session_id} chunk={chunk_id}")
    print(f"[gen] model={model} resolution={cfg.get('resolution', '2K')}")
    print(f"[gen] prompt: {prompt}")
    if image_input:
        print(f"[gen] image_input: {image_input}")

    # Pass session's resolution verbatim as `quality`. build_input_for_model
    # accepts both seedream-style ("basic"/"high") and explicit ("1K"/"2K"/"4K")
    # and maps to each target model's vocabulary.
    input_dict = build_input_for_model(
        model,
        prompt=prompt,
        image_refs=image_input,
        aspect_ratio=cfg.get("aspect_ratio", "16:9"),
        quality=cfg.get("resolution", "2K"),
        output_format=cfg.get("output_format", "png"),
    )

    try:
        result = client.submit_and_download(
            model=model,
            input_dict=input_dict,
            dest_path=dest,
        )
    except KieError as e:
        print(f"[gen] FAILED: {e}")
        raise

    item = {
        "id": chunk_id,
        "chunk_id": chunk_id,
        "role": "scene",
        "model": model,
        "prompt": prompt,
        "task_id": result.task_id,
        "result_url": result.result_urls[0] if result.result_urls else "",
        "local_path": str(dest.relative_to(CONTENT_ROOT)),
        "mime_type": "image/png",
        "status": "success",
        "aspect_ratio": cfg.get("aspect_ratio", "16:9"),
        "resolution": cfg.get("resolution", "2K"),
        "output_format": cfg.get("output_format", "png"),
        "image_input": list(image_input),
    }

    # Replace any existing entry for this chunk (regeneration is explicit).
    manifest["items"] = [
        i for i in manifest["items"] if i.get("chunk_id") != chunk_id
    ] + [item]

    # First-scene style anchor recording.
    if manifest.get("style_anchor") is None:
        style_ref = cfg.get("style_reference")
        if isinstance(style_ref, str) and style_ref.startswith(("http://", "https://")):
            manifest["style_anchor"] = {"kind": "image_url", "value": style_ref}
        elif result.result_urls:
            # Use the kie-hosted result_url as the anchor so subsequent
            # generations can reference it directly via image_input. NOTE:
            # kie.ai result URLs are temporary — they remain valid for some
            # hours. For batches generated in sequence this works fine; for
            # sessions generated across days, a more permanent host would
            # be needed for the anchor.
            manifest["style_anchor"] = {
                "kind": "image_url",
                "value": result.result_urls[0],
                "local_path": str(dest.relative_to(CONTENT_ROOT)),
                "source_prompt": style_ref or cfg.get("default_style_prompt", ""),
            }
        else:
            manifest["style_anchor"] = {
                "kind": "local_image",
                "value": str(dest.relative_to(CONTENT_ROOT)),
                "source_prompt": style_ref or cfg.get("default_style_prompt", ""),
            }

    save_manifest(session_id, manifest)
    print(f"[gen] wrote {dest}")
    print(f"[gen] manifest updated: {manifest_path(session_id)}")
    # Machine-parseable last line — lets batch drivers capture the result URL
    # without racing on the manifest file.
    result_url = result.result_urls[0] if result.result_urls else ""
    print(f"RESULT_URL={result_url}")
    return dest


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate one scene illustration")
    parser.add_argument("--session", required=True, help="session id (folder name)")
    parser.add_argument("--chunk", required=True, help="chunk id (e.g. C1)")
    parser.add_argument("--narration", required=True, help="narration text for the chunk")
    parser.add_argument("--beat", default=None, help="optional beat description")
    parser.add_argument(
        "--force", action="store_true", help="regenerate even if the file exists"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="override the session's preferred_model for this one generation",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="override the destination path (default: scenes/<chunk>.png)",
    )
    parser.add_argument(
        "--image-ref",
        default=None,
        help="URL of an image to pass as image_input (overrides the style anchor from manifest). Used for continues-from-prev / callback continuity.",
    )
    args = parser.parse_args()

    try:
        generate(
            session_id=args.session,
            chunk_id=args.chunk,
            narration=args.narration,
            beat=args.beat,
            force=args.force,
            model_override=args.model,
            dest_override=Path(args.out) if args.out else None,
            image_ref_override=args.image_ref,
        )
    except Exception as e:
        print(f"[gen] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
