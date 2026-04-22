"""
style_library.py — read/write the spoolcast style library.

A "style" is a named visual treatment (e.g. `wojak-comic`, `xkcd-inkline`) that
includes:
- a style prompt (words)
- an anchor image (picture of the locked look — may be null if style is new)
- a library of neutral character/object references shared across sessions

Each style lives at `spoolcast-content/styles/<style-name>/` with this layout:

    spoolcast-content/styles/<style-name>/
      style.json                      ← metadata (see schema below)
      anchor.png                      ← master anchor image (once generated)
      references/
        <name>.png                    ← neutral reference image
        <name>.verified.json          ← verification sidecar (per VISUALS rule)

Sessions reference a style by name via session.json's `style` field. Session
config's `characters` and `objects` maps point at library references by name;
session-specific overrides live in the session folder (not in the library).

Schema of style.json:

    {
      "name": "wojak-comic",
      "description": "...",
      "default_style_prompt": "<the words>",
      "anchor": {
        "image_path": "anchor.png",          ← relative to style dir
        "image_url": "https://kie.ai/...",   ← result URL from kie (ephemeral)
        "url_fetched_at": "2026-04-21T..."
      } | null,
      "references": {
        "builder": {
          "kind": "character",
          "description": "...",
          "image_path": "references/builder.png",
          "image_url": "...",
          "url_fetched_at": "..."
        }
      }
    }

This module is I/O only — no kie.ai calls live here. Scripts that generate
images (generate_scene, generate_reference) call kie_client directly and use
this module to persist results into the library.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"
STYLES_ROOT = CONTENT_ROOT / "styles"


class StyleLibraryError(RuntimeError):
    pass


@dataclass
class StyleRef:
    """One entry in a style's reference registry. Points at a local image and
    optionally carries the last-known kie URL + timestamp."""

    name: str
    kind: str  # "character" | "object"
    description: str
    image_path: Path  # absolute
    image_url: str = ""
    url_fetched_at: str = ""

    def as_dict(self, style_dir: Path) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "image_path": str(self.image_path.relative_to(style_dir)),
            "image_url": self.image_url,
            "url_fetched_at": self.url_fetched_at,
        }


@dataclass
class Style:
    name: str
    description: str
    default_style_prompt: str
    anchor: dict[str, Any] | None
    references: dict[str, dict[str, Any]]
    _dir: Path

    @property
    def style_dir(self) -> Path:
        return self._dir

    @property
    def anchor_image_path(self) -> Path | None:
        if not self.anchor:
            return None
        rel = self.anchor.get("image_path")
        if not rel:
            return None
        return self._dir / rel

    @property
    def anchor_image_url(self) -> str:
        if not self.anchor:
            return ""
        return self.anchor.get("image_url", "") or ""

    def has_anchor(self) -> bool:
        return bool(self.anchor and self.anchor_image_path and self.anchor_image_path.exists())

    def get_reference(self, name: str) -> dict[str, Any] | None:
        return self.references.get(name)

    def reference_image_path(self, name: str) -> Path | None:
        entry = self.references.get(name)
        if not entry:
            return None
        rel = entry.get("image_path")
        if not rel:
            return None
        return self._dir / rel

    def as_dict(self) -> dict[str, Any]:
        # Stable field order for diffability.
        return {
            "name": self.name,
            "description": self.description,
            "default_style_prompt": self.default_style_prompt,
            "anchor": self.anchor,
            "references": self.references,
        }


def style_dir(style_name: str) -> Path:
    return STYLES_ROOT / style_name


def style_json_path(style_name: str) -> Path:
    return style_dir(style_name) / "style.json"


def style_exists(style_name: str) -> bool:
    return style_json_path(style_name).exists()


def load_style(style_name: str) -> Style:
    path = style_json_path(style_name)
    if not path.exists():
        raise StyleLibraryError(f"style not found: {style_name} ({path})")
    data = json.loads(path.read_text())
    # Tolerate missing fields during load; fail on save if structure is broken.
    return Style(
        name=data.get("name", style_name),
        description=data.get("description", ""),
        default_style_prompt=data.get("default_style_prompt", ""),
        anchor=data.get("anchor"),
        references=data.get("references", {}),
        _dir=style_dir(style_name),
    )


def save_style(style: Style) -> None:
    # Preserve unknown fields (e.g. `created_at`, `notes`) that the on-disk
    # style.json may carry for human context. Merge in the managed fields on
    # top of whatever's there.
    path = style_json_path(style.name)
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except Exception:
            existing = {}
    merged = {**existing, **style.as_dict()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2) + "\n")


def list_styles() -> list[str]:
    if not STYLES_ROOT.exists():
        return []
    return sorted(
        p.name for p in STYLES_ROOT.iterdir()
        if p.is_dir() and (p / "style.json").exists()
    )


# ---- session.json style wiring ---------------------------------------------

def session_style_name(session_cfg: dict[str, Any]) -> str | None:
    """Pull the style name from session.json. Returns None if not set (legacy
    sessions without a style field continue to work on their own prompt)."""
    name = session_cfg.get("style")
    if not name or not isinstance(name, str):
        return None
    return name


def session_style(session_cfg: dict[str, Any]) -> Style | None:
    name = session_style_name(session_cfg)
    if not name:
        return None
    if not style_exists(name):
        raise StyleLibraryError(
            f"session.json points at style {name!r} but {style_json_path(name)} does not exist"
        )
    return load_style(name)


def resolve_reference(
    session_cfg: dict[str, Any],
    session_dir_path: Path,
    ref_name: str,
) -> tuple[Path | None, str]:
    """Resolve a reference name to (local image path, kie URL).

    Resolution order:
    1. Session-local override at session_dir/source/generated-assets/references/<name>.png
       + session.json's `characters`/`objects` maps
    2. Style library reference

    Returns (None, "") if neither has the reference.
    """
    # 1. session-local override
    session_chars = session_cfg.get("characters", {}) or {}
    session_objs = session_cfg.get("objects", {}) or {}
    local_entry = session_chars.get(ref_name) or session_objs.get(ref_name)
    if local_entry:
        rel = local_entry.get("image_path", "")
        if rel:
            local_path = session_dir_path / rel
            if local_path.exists():
                return local_path, local_entry.get("image_url", "") or ""

    # 2. style library
    style = session_style(session_cfg)
    if style:
        lib_path = style.reference_image_path(ref_name)
        entry = style.get_reference(ref_name)
        if lib_path and lib_path.exists() and entry:
            return lib_path, entry.get("image_url", "") or ""

    return None, ""
