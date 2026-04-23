"""
generate_reference.py — generate a single named reference image.

Produces a clean reference PNG of a character or object in the locked style.
Writes to either:
- the style library: `spoolcast-content/styles/<style>/references/<name>.png`
- or a session override: `sessions/<session>/source/generated-assets/references/<name>.png`

And registers the result in the corresponding JSON (style.json or session.json).

Flow:
1. Load target style (from the --style arg, or via --session's style field).
2. Compose the prompt: style's default_style_prompt + "Scene: neutral reference
   of <description>, single subject on plain white background, no other
   elements" (unless --raw-description is passed, in which case the description
   is used verbatim).
3. image_refs: if the target style has an anchor image with a live URL, pass
   it as image_input so the reference matches the style. For the very first
   anchor generation (or when --no-anchor-ref is set), skip.
4. Call kie via build_input_from_session or direct build, save local PNG.
5. Update style.json or session.json's reference registry with image_path + URL.

Usage:
    # Register a library-scoped character reference (uses default style):
    scripts/.venv/bin/python scripts/generate_reference.py \\
        --style wojak-comic --name builder --kind character \\
        --description "weary hooded stick figure at a laptop, round face, gray tones"

    # Register a session-specific variant (lives in the session folder):
    scripts/.venv/bin/python scripts/generate_reference.py \\
        --session spoolcast-dev-log --name builder-sitting --kind character \\
        --description "the builder, sitting at a desk in front of a monitor, tired"

    # Generate the very first anchor for a style (no existing anchor to reference):
    scripts/.venv/bin/python scripts/generate_reference.py \\
        --style wojak-comic --anchor --no-anchor-ref
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

from kie_client import DEFAULT_MODEL, KieClient, KieError, build_input_for_model, resolve_model
from style_library import (
    CONTENT_ROOT,
    Style,
    StyleLibraryError,
    load_style,
    save_style,
    style_exists,
)


def _session_cfg_path(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id / "session.json"


def _session_dir(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id


def _load_session_cfg(session_id: str) -> dict[str, Any]:
    path = _session_cfg_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"session config not found: {path}")
    return json.loads(path.read_text())


def _save_session_cfg(session_id: str, cfg: dict[str, Any]) -> None:
    path = _session_cfg_path(session_id)
    path.write_text(json.dumps(cfg, indent=2) + "\n")


def _compose_prompt(style: Style, description: str, *, raw: bool, is_anchor: bool) -> str:
    style_part = (style.default_style_prompt or "").rstrip(".")
    desc = description.rstrip(".")
    if raw:
        scene = desc
    elif is_anchor:
        # Anchor composition: the anchor itself IS the style definition.
        # Keep scene description open — let the style words do the heavy lift.
        scene = f"Scene: {desc}"
    else:
        scene = (
            f"Scene: neutral reference of {desc}, single subject on plain white background, "
            "no other elements, clean composition suitable for use as a style reference."
        )
    parts = [p for p in (style_part, scene) if p]
    return ". ".join(parts) + "."


def _image_refs_for_reference(style: Style, no_anchor_ref: bool) -> list[str]:
    if no_anchor_ref:
        return []
    url = style.anchor_image_url
    return [url] if url else []


def generate_reference(
    *,
    style_name: str,
    name: str,
    kind: str,
    description: str,
    session_id: str | None = None,
    is_anchor: bool = False,
    raw_description: bool = False,
    no_anchor_ref: bool = False,
    model_override: str | None = None,
    force: bool = False,
    image_ref_override: str | None = None,
) -> Path:
    # Load the target style.
    if not style_exists(style_name):
        raise StyleLibraryError(f"style not found: {style_name}")
    style = load_style(style_name)

    # Resolve destination directory and the registry that owns this reference.
    if session_id:
        dest_dir = _session_dir(session_id) / "source" / "generated-assets" / "references"
    elif is_anchor:
        dest_dir = style.style_dir
    else:
        dest_dir = style.style_dir / "references"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # File name: anchor.png for the anchor, <name>.png otherwise.
    filename = "anchor.png" if is_anchor else f"{name}.png"
    dest = dest_dir / filename

    if dest.exists() and not force:
        print(f"[ref] {dest} already exists. Use --force to regenerate.")
        return dest

    prompt = _compose_prompt(style, description, raw=raw_description, is_anchor=is_anchor)
    if image_ref_override:
        image_refs = [image_ref_override]
    else:
        image_refs = _image_refs_for_reference(style, no_anchor_ref or is_anchor)

    # Pull kie config from the style's hint or sensible defaults. (Sessions
    # have their own config; the style library uses a fixed default here.)
    model = resolve_model(model_override or DEFAULT_MODEL, image_refs)
    quality = "1K"
    aspect_ratio = "1:1" if not is_anchor else "16:9"
    output_format = "png"

    input_dict = build_input_for_model(
        model,
        prompt=prompt,
        image_refs=image_refs,
        aspect_ratio=aspect_ratio,
        quality=quality,
        output_format=output_format,
    )

    client = KieClient()
    print(f"[ref] style={style_name} name={name} kind={kind} is_anchor={is_anchor}")
    print(f"[ref] model={model} quality={quality} aspect={aspect_ratio}")
    print(f"[ref] prompt: {prompt}")
    if image_refs:
        print(f"[ref] image_refs: {image_refs}")

    try:
        result = client.submit_and_download(
            model=model,
            input_dict=input_dict,
            dest_path=dest,
        )
    except KieError as e:
        print(f"[ref] FAILED: {e}")
        raise

    url = result.result_urls[0] if result.result_urls else ""
    now = _dt.datetime.now(_dt.UTC).isoformat()

    # Register into the right place.
    if is_anchor:
        # Update the style's anchor.
        style.anchor = {
            "image_path": "anchor.png",
            "image_url": url,
            "url_fetched_at": now,
            "task_id": result.task_id,
        }
        save_style(style)
        print(f"[ref] anchor registered in {style.style_dir / 'style.json'}")
    elif session_id:
        # Session-local override. Maintain registry in session.json.
        cfg = _load_session_cfg(session_id)
        registry_key = "characters" if kind == "character" else "objects"
        cfg.setdefault(registry_key, {})
        cfg[registry_key][name] = {
            "description": description,
            "image_path": str(dest.relative_to(_session_dir(session_id))),
            "image_url": url,
            "url_fetched_at": now,
            "task_id": result.task_id,
        }
        _save_session_cfg(session_id, cfg)
        print(f"[ref] session override registered in {_session_cfg_path(session_id)}")
    else:
        # Library reference. Maintain registry inside the style's json.
        style.references[name] = {
            "kind": kind,
            "description": description,
            "image_path": f"references/{name}.png",
            "image_url": url,
            "url_fetched_at": now,
            "task_id": result.task_id,
        }
        save_style(style)
        print(f"[ref] library reference registered in {style.style_dir / 'style.json'}")

    print(f"[ref] wrote {dest}")
    print(f"RESULT_URL={url}")
    return dest


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate one style-locked reference image")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--style", help="target style (library-scoped reference)")
    src.add_argument("--session", help="target session (session-scoped override)")
    parser.add_argument(
        "--name",
        help="reference name (e.g. 'builder', 'rules-md'). Required unless --anchor.",
    )
    parser.add_argument(
        "--kind",
        choices=("character", "object"),
        help="character or object. Required for non-anchor references.",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="free-text description of the reference. Style prompt is added automatically.",
    )
    parser.add_argument(
        "--anchor",
        action="store_true",
        help="generate the style's master anchor image (use with --style; writes to style/anchor.png).",
    )
    parser.add_argument(
        "--raw-description",
        action="store_true",
        help="use --description verbatim as the scene description (skip the neutral-reference template).",
    )
    parser.add_argument(
        "--no-anchor-ref",
        action="store_true",
        help="do NOT pass the style's existing anchor as image_input. Used for first anchor generation.",
    )
    parser.add_argument("--model", default=None, help="override kie model")
    parser.add_argument("--force", action="store_true", help="regenerate if the file exists")
    parser.add_argument(
        "--image-ref",
        default=None,
        help="override the image_input URL. By default, a library reference uses the style's anchor as image_ref unless --no-anchor-ref is set. Pass --image-ref <URL> to explicitly anchor against a different image (e.g. to match a sibling library's reference face style).",
    )
    args = parser.parse_args()

    # Resolve style_name: session's style or the --style arg.
    if args.session:
        cfg = _load_session_cfg(args.session)
        style_name = cfg.get("style")
        if not style_name:
            print(
                f"[ref] session {args.session} has no 'style' field in session.json",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        style_name = args.style

    if args.anchor:
        if args.session:
            print("[ref] --anchor is library-only; drop --session or add to the style directly", file=sys.stderr)
            sys.exit(1)
        if args.name:
            print("[ref] --name ignored when --anchor is set (anchor always writes to anchor.png)")
        name = "anchor"
        kind = "anchor"
    else:
        if not args.name or not args.kind:
            print("[ref] --name and --kind are required unless --anchor is set", file=sys.stderr)
            sys.exit(1)
        name = args.name
        kind = args.kind

    try:
        generate_reference(
            style_name=style_name,
            name=name,
            kind=kind,
            description=args.description,
            session_id=args.session,
            is_anchor=args.anchor,
            raw_description=args.raw_description,
            no_anchor_ref=args.no_anchor_ref,
            model_override=args.model,
            force=args.force,
            image_ref_override=args.image_ref,
        )
    except Exception as e:
        print(f"[ref] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
