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
import fcntl
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from kie_client import KieClient, KieError, build_input_for_model, resolve_model
from style_library import (
    resolve_reference,
    session_style,
)


# ---- paths -------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


MOBILE_PREAMBLE = (
    "This scene is being regenerated for a 9:16 portrait mobile video. "
    "Compose everything for a tall vertical canvas — the widescreen original "
    "won't survive a mobile center-crop, so rebuild the scene to fit the "
    "portrait frame naturally. If the visual direction below describes a "
    "horizontal layout (side-by-side panels, left/right positioning, "
    "split-frame), restructure it as a vertical arrangement (stacked panels, "
    "top/bottom positioning, upper-half / lower-half). Keep all declared "
    "on_screen_text legible inside the portrait canvas. Existing style "
    "anchor applies unchanged."
)


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


@contextmanager
def _locked_manifest_rw(session_id: str) -> Iterator[dict[str, Any]]:
    """Exclusive-lock the manifest file, yield the current state for mutation,
    and atomically save on exit.

    Serializes concurrent manifest read-modify-write cycles. Fixes the race
    where two parallel `generate_scene.py` processes each load the same
    snapshot, each append their own item, each save — and the last writer
    silently drops the first writer's item. Known to have orphaned 4 chunks
    (C6, C28, C39, C41) on spoolcast-dev-log when two batch_scenes runs
    overlapped.

    fcntl.flock is POSIX-only; on non-POSIX platforms this degrades to
    no-op and the race returns. Not a concern on macOS/Linux hosts.
    """
    path = manifest_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Open in a+ so we can create-if-missing, then hold the same descriptor
    # through the lock / read / write / unlock cycle.
    with open(path, "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            content = f.read()
            if content.strip():
                manifest = json.loads(content)
            else:
                manifest = {
                    "run_name": f"scenes-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    "session_id": session_id,
                    "created_at": _dt.datetime.now(_dt.UTC).isoformat(),
                    "style_anchor": None,
                    "items": [],
                }
            yield manifest
            f.seek(0)
            f.truncate()
            json.dump(manifest, f, indent=2)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# ---- prompt composition ------------------------------------------------

def compose_prompt(
    cfg: dict[str, Any],
    narration: str,
    beat: str | None = None,
    *,
    visual_direction: str | None = None,
    on_screen_text: list[str] | None = None,
    motion_notes: str | None = None,
) -> tuple[str, list[str]]:
    """Build the image prompt + image_input list for this chunk.

    Style source precedence (per VISUALS.md § Style library):
    1. If session.json has a `style` field, pull default_style_prompt from the
       style library entry.
    2. Else session.json's own `style_reference` (URL or prompt) or
       `default_style_prompt`.

    Structured slots (preferred):
    - `visual_direction` — how the image should look/feel. Sent as scene guidance.
    - `on_screen_text` — literal text to render on the frame. Sent with explicit
      "render exactly these words" framing so the model doesn't mix it with style
      direction or hallucinate inspirational quotes.
    - `motion_notes` — deliberately IGNORED. Still-image models can't render
      motion; describing motion produces overlapping duplicate elements
      (phantom limbs, double characters). Motion belongs to the reveal layer.

    Backward compatibility: if no structured slots are provided, falls back to
    the legacy `beat` string (which mixes all three concerns into one blob).
    """
    style = session_style(cfg)

    style_text: str | None = None
    image_input: list[str] = []

    if style:
        # Session uses the style library. Style prompt is authoritative.
        style_text = style.default_style_prompt or None
    else:
        style_ref = cfg.get("style_reference")
        default_style = cfg.get("default_style_prompt")
        if isinstance(style_ref, str) and style_ref.startswith(("http://", "https://")):
            image_input.append(style_ref)
        elif isinstance(style_ref, str) and style_ref.strip():
            style_text = style_ref
        elif default_style:
            style_text = default_style
        else:
            raise ValueError(
                "session config has neither style (library), style_reference, "
                "nor default_style_prompt — refusing to generate without a "
                "locked style (see VISUALS.md § Style Anchor Rule)"
            )

    parts: list[str] = []
    if style_text:
        parts.append(style_text.rstrip("."))

    # Prefer structured slots. Fall back to legacy `beat` blob otherwise.
    # Require actual content in at least one structured slot — an empty list or
    # blank string is treated as "not using structured" so the legacy beat still
    # provides a scene description. Previously `on_screen_text=[]` (empty list)
    # routed into the structured path and produced a prompt with no Scene:
    # section, which caused the model to invent a scene freely.
    visual_direction_has_content = (
        isinstance(visual_direction, str) and visual_direction.strip() != ""
    )
    on_screen_text_has_content = (
        isinstance(on_screen_text, list)
        and any(isinstance(t, str) and t.strip() for t in on_screen_text)
    )
    using_structured = visual_direction_has_content or on_screen_text_has_content
    if using_structured:
        # Scene description: prefer structured visual_direction, but fall back to
        # legacy beat_description when on_screen_text forced the structured path
        # without an explicit visual_direction. Otherwise a chunk with
        # beat_description + on_screen_text renders as pure typography (the
        # beat_description gets silently dropped). Caught on dev-log-02 regen.
        scene_text = (visual_direction or "").strip() or (beat or "").strip()
        if scene_text:
            parts.append(f"Scene: {scene_text.rstrip('.')}")
        if on_screen_text:
            # Filter empty strings, keep author's literal text verbatim.
            texts = [t.strip() for t in on_screen_text if t and t.strip()]
            if texts:
                # Explicit instruction so the model renders these exact words
                # rather than interpreting them as style direction.
                joined = " | ".join(f'"{t}"' for t in texts)
                parts.append(
                    f"Render exactly this text on the frame, "
                    f"hand-lettered in the session style: {joined}"
                )
        # motion_notes intentionally NOT appended — see docstring.
    else:
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
    references: list[str] | None = None,
    visual_direction: str | None = None,
    on_screen_text: list[str] | None = None,
    motion_notes: str | None = None,
    mobile_variant: bool = False,
    mobile_aspect: str = "9:16",
) -> Path:
    cfg = load_session_config(session_id)
    scenes = scenes_dir(session_id)
    scenes.mkdir(parents=True, exist_ok=True)
    # Mobile variants land in scenes/mobile/<chunk>-mobile.png so they stay
    # isolated from the widescreen scenes/<chunk>.png. Both coexist; each is
    # consumed by its own export path. Mirrors the renders/mobile/ convention.
    if mobile_variant:
        mobile_scenes = scenes / "mobile"
        mobile_scenes.mkdir(parents=True, exist_ok=True)
        default_dest = mobile_scenes / f"{chunk_id}-mobile.png"
    else:
        default_dest = scenes / f"{chunk_id}.png"
    dest = dest_override if dest_override is not None else default_dest
    model = model_override or cfg["preferred_model"]

    if dest.exists() and not force:
        print(f"[gen] {chunk_id}{'-mobile' if mobile_variant else ''} already exists at {dest}. Use --force to regenerate.")
        return dest

    # For mobile variants at 9:16 or 4:5, prepend the mobile preamble to the
    # visual_direction so the model restructures horizontal layouts into
    # vertical ones. 1:1 (square) skips the preamble — a square is close
    # enough to the widescreen's central content that restructuring isn't
    # needed, and keeping the prompt identical to the widescreen source
    # preserves character / style consistency with the original scene.
    # on_screen_text and narration are unchanged in all cases.
    effective_visual_direction = visual_direction
    if mobile_variant and mobile_aspect != "1:1":
        base = (visual_direction or "").strip()
        effective_visual_direction = f"{MOBILE_PREAMBLE}\n\n{base}" if base else MOBILE_PREAMBLE

    prompt, image_input = compose_prompt(
        cfg,
        narration,
        beat,
        visual_direction=effective_visual_direction,
        on_screen_text=on_screen_text,
        motion_notes=motion_notes,
    )

    # Resolve the ONE image_ref for this generation. Precedence:
    # 1. Explicit --image-ref override (continues-from-prev / callback).
    # 2. First entry in `references` list (character/object reference — doubles as style anchor).
    # 3. The session's style-library anchor URL (or legacy manifest style_anchor).
    #
    # See VISUALS.md § Style Anchor Rule + § Reference Registry for the rule.
    manifest = load_or_init_manifest(session_id)

    style = session_style(cfg)

    if image_ref_override:
        # Explicit continuity reference — overrides any other ref.
        image_input = [image_ref_override]
    elif references:
        # Character/object reference for this chunk. Use the FIRST resolved
        # reference only (VISUALS rule: one image_input per generation — passing
        # multiple confuses compositional tendencies). The reference doubles
        # as the style anchor for this scene.
        session_path = session_dir(session_id)
        chosen_url = ""
        chosen_name = ""
        for name in references:
            local, url = resolve_reference(cfg, session_path, name)
            if url:
                chosen_url = url
                chosen_name = name
                break
            if local and local.exists():
                print(
                    f"[gen] warning: reference {name!r} has local file {local} "
                    f"but no live kie URL — skipping (regenerate the reference to refresh)"
                )
        if chosen_url:
            image_input = [chosen_url]
            print(f"[gen] using reference {chosen_name!r} as image_ref for chunk {chunk_id}")
        elif style:
            # Style-library session: references were declared but none resolved
            # to a live URL. Fall back to prompt-only (per VISUALS rule — don't
            # bleed the style anchor in). Log loudly.
            print(
                f"[gen] references {references} had no live URLs — generating prompt-only (per VISUALS.md rule)"
            )
    elif style:
        # Style-library session, chunk has NO references — generate prompt-only.
        # Do NOT pass the style anchor as image_input (VISUALS.md § "visual anchor
        # when something specific recurs, text anchor otherwise"). Style lock is
        # carried by the default_style_prompt text, not by the image.
        print(f"[gen] no references on chunk {chunk_id} — generating prompt-only")
    else:
        # Legacy fallback (sessions without a style library): use the manifest
        # style_anchor URL as image_input. Kept for pre-style-library sessions.
        anchor = manifest.get("style_anchor")
        if anchor and anchor.get("kind") == "image_url":
            anchor_src = anchor.get("value")
            if anchor_src:
                image_input = [anchor_src]
                print(f"[gen] legacy manifest style anchor applied (no style library)")

    client = KieClient()
    # Resolve model-family variants (e.g. GPT Image 2 text-vs-image-to-image)
    # BEFORE logging or building the request so the model field sent to kie
    # matches the input shape. See kie_client.resolve_model.
    model = resolve_model(model, image_input)

    print(f"[gen] session={session_id} chunk={chunk_id}")
    print(f"[gen] model={model} resolution={cfg.get('resolution', '2K')}")
    print(f"[gen] prompt: {prompt}")
    if image_input:
        print(f"[gen] image_input: {image_input}")

    # Pass session's resolution verbatim as `quality`. build_input_for_model
    # accepts both seedream-style ("basic"/"high") and explicit ("1K"/"2K"/"4K")
    # and maps to each target model's vocabulary.
    aspect_ratio = mobile_aspect if mobile_variant else cfg.get("aspect_ratio", "16:9")
    input_dict = build_input_for_model(
        model,
        prompt=prompt,
        image_refs=image_input,
        aspect_ratio=aspect_ratio,
        quality=cfg.get("resolution", "1K"),
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

    item_id = f"{chunk_id}-mobile" if mobile_variant else chunk_id
    item_role = "scene-mobile" if mobile_variant else "scene"
    item = {
        "id": item_id,
        "chunk_id": chunk_id,
        "role": item_role,
        "model": model,
        "prompt": prompt,
        "task_id": result.task_id,
        "result_url": result.result_urls[0] if result.result_urls else "",
        "local_path": str(dest.relative_to(CONTENT_ROOT)),
        "mime_type": "image/png",
        "status": "success",
        "aspect_ratio": aspect_ratio,
        "resolution": cfg.get("resolution", "1K"),
        "output_format": cfg.get("output_format", "png"),
        "image_input": list(image_input),
    }

    # Manifest update under exclusive lock — re-reads the current manifest
    # state, replaces the (chunk_id, role) entry, updates style_anchor if
    # first scene, then atomically saves. Serializes with any concurrent
    # generate_scene.py process writing to the same manifest. The load +
    # mutate + save must stay inside the lock block; pulling any of them
    # out re-opens the race.
    with _locked_manifest_rw(session_id) as manifest:
        manifest["items"] = [
            i for i in manifest["items"]
            if not (i.get("chunk_id") == chunk_id and i.get("role") == item_role)
        ] + [item]

        # First-scene style anchor recording. Only tracked from widescreen
        # generations — mobile variants inherit the widescreen anchor and do
        # not reset it.
        if not mobile_variant and manifest.get("style_anchor") is None:
            style_ref = cfg.get("style_reference")
            if isinstance(style_ref, str) and style_ref.startswith(("http://", "https://")):
                manifest["style_anchor"] = {"kind": "image_url", "value": style_ref}
            elif result.result_urls:
                # kie-hosted result_url is temporary but valid for some hours —
                # fine for sequential batches, not for sessions spanning days.
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
        help="URL of an image to pass as image_input (overrides everything else). Used for continues-from-prev / callback continuity.",
    )
    parser.add_argument(
        "--references",
        default=None,
        help="comma-separated list of character/object reference names for this chunk. The FIRST one with a live URL is used as the scene's image_input (doubling as the style anchor).",
    )
    parser.add_argument(
        "--visual-direction",
        default=None,
        help="structured slot: how the image should look/feel (composition, mood, pose). Replaces the legacy `--beat` blob. See PIPELINE.md § visual_direction.",
    )
    parser.add_argument(
        "--on-screen-text",
        default=None,
        help="structured slot: JSON array of literal text strings to render on the frame (e.g. '[\"rules.md\", \"(a) update the rule\"]'). Empty/missing = no text.",
    )
    parser.add_argument(
        "--motion-notes",
        default=None,
        help="structured slot: motion description for the reveal layer. ACCEPTED BUT IGNORED by the image model (still images can't render motion).",
    )
    parser.add_argument(
        "--mobile-variant",
        action="store_true",
        help="regenerate this chunk at portrait aspect (Process A.1). Prepends a mobile-composition preamble to visual_direction, writes to scenes/<chunk>-mobile.png, adds a 'scene-mobile' manifest entry without clobbering the widescreen one.",
    )
    parser.add_argument(
        "--mobile-aspect",
        default="9:16",
        help="aspect ratio for mobile variant (default 9:16; alternatives: 4:5 for IG Feed, 1:1 square). Only used when --mobile-variant is set.",
    )
    args = parser.parse_args()

    references_list: list[str] | None = None
    if args.references:
        references_list = [r.strip() for r in args.references.split(",") if r.strip()]

    on_screen_text_list: list[str] | None = None
    if args.on_screen_text:
        try:
            parsed = json.loads(args.on_screen_text)
            if not isinstance(parsed, list) or not all(isinstance(s, str) for s in parsed):
                raise ValueError("on-screen-text must be a JSON array of strings")
            on_screen_text_list = parsed
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[gen] invalid --on-screen-text: {e}", file=sys.stderr)
            sys.exit(2)

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
            references=references_list,
            visual_direction=args.visual_direction,
            on_screen_text=on_screen_text_list,
            motion_notes=args.motion_notes,
            mobile_variant=args.mobile_variant,
            mobile_aspect=args.mobile_aspect,
        )
    except Exception as e:
        print(f"[gen] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
