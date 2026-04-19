"""
shot_list_io.py — read/write the spoolcast shot list as xlsx.

The shot list has ONE sheet. Every column is visible without tab-switching.
Chunk-level columns use merged cells across the chunk's beats so grouping
is visually obvious. Rows are tinted per chunk (cycling pastel palette).

Layout (top-down):
  row 1: title
  row 2: session metadata (session id, canvas aspect, fps)
  row 3: separator (blank)
  row 4: table headers
  row 5+: beats (rows grouped by chunk via merged cells + fill color)

Usage (as a library):
    import shot_list_io
    data = shot_list_io.load_json(json_path)      # from our canonical JSON
    shot_list_io.write_xlsx(xlsx_path, data)      # produce the editable xlsx
    data = shot_list_io.read_xlsx(xlsx_path)      # read user edits back

Usage (CLI, generate xlsx from JSON):
    scripts/.venv/bin/python scripts/shot_list_io.py \\
        --from-json <session-dir>/shot-list/shot-list.json \\
        --to-xlsx <session-dir>/shot-list/shot-list.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

try:
    from mutagen.mp3 import MP3  # type: ignore
    _HAS_MUTAGEN = True
except Exception:
    _HAS_MUTAGEN = False


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


# ---- column spec -------------------------------------------------------

# scope: "chunk" columns use merged cells across the chunk's beats,
#        "beat" columns are per-row.
COLUMNS: list[tuple[str, str, str, int]] = [
    # (key, header, scope, width_chars)
    # Left half: scannable basics + camera action + timing.
    ("chunk_id",         "Chunk",            "chunk", 7),
    ("scene",            "Scene",            "chunk", 18),
    ("summary",          "Summary",          "chunk", 32),
    ("continuity",       "Continuity",       "chunk", 20),
    ("reveal_direction", "Reveal Direction", "chunk", 14),
    ("beat_id",          "Beat",             "beat",  7),
    ("narration",        "Narration",        "beat",  48),
    ("pause_after",      "Pause After",      "beat",  10),
    ("camera_reason",    "Camera Reason",    "beat",  36),
    ("camera_target",    "Camera Target",    "beat",  14),
    ("camera_zoom",      "Camera Zoom",      "beat",  12),
    ("transition_s",     "Transition (s)",   "beat",  12),
    ("start_s",          "Start (s)",        "beat",  10),
    ("end_s",            "End (s)",          "beat",  10),
    # Right half: reference data (long text, scrolled to when needed).
    ("beat_description", "Beat Description", "chunk", 50),
    ("full_prompt",      "Full Prompt",      "chunk", 60),
    ("image_source",     "Image Source",     "chunk", 14),
    ("image_path",       "Image Path",       "chunk", 36),
]

CHUNK_SCOPE_KEYS = {k for k, _, scope, _ in COLUMNS if scope == "chunk"}


# ---- palette -----------------------------------------------------------

CHUNK_ROW_COLORS = [
    "E3F2FD",  # pale blue
    "E8F5E9",  # pale green
    "FFF9E6",  # pale yellow
    "FCE4EC",  # pale pink
    "F3E5F5",  # pale purple
    "FFF3E0",  # pale orange
    "E0F2F1",  # pale teal
    "F5F5F5",  # pale gray
]


# ---- pause mapping -----------------------------------------------------

PAUSE_SECONDS = {
    "": 0.3,       # default rhythm — a brief natural beat
    "none": 0.0,
    "short": 0.3,
    "medium": 0.8,
    "long": 1.5,
}


# ---- data loading ------------------------------------------------------

def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _session_config(session_id: str) -> dict[str, Any]:
    cfg_path = CONTENT_ROOT / "sessions" / session_id / "session.json"
    if not cfg_path.exists():
        return {}
    with open(cfg_path) as f:
        return json.load(f)


def _audio_path(session_id: str, beat_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id / "source" / "audio" / f"{beat_id}.mp3"


def _audio_duration(session_id: str, beat_id: str) -> float | None:
    """Returns audio duration in seconds, or None if unavailable."""
    p = _audio_path(session_id, beat_id)
    if not p.exists() or not _HAS_MUTAGEN:
        return None
    try:
        return float(MP3(str(p)).info.length)
    except Exception:
        return None


def _compute_timeline(session_id: str, chunks: list[dict[str, Any]]) -> None:
    """Fill start_s/end_s on each beat based on audio duration + pause."""
    running = 0.0
    for chunk in chunks:
        for beat in chunk.get("beats", []):
            dur = _audio_duration(session_id, beat.get("id", ""))
            if dur is None:
                # fallback: estimate from narration length at ~14 cps
                text = beat.get("narration", "") or ""
                dur = max(1.0, len(text) / 14.0)
            pause = PAUSE_SECONDS.get(beat.get("pause_after", "") or "", 0.3)
            beat["_audio_duration"] = round(dur, 2)
            beat["start_s"] = round(running, 2)
            running += dur
            beat["end_s"] = round(running, 2)
            running += pause


# ---- prompt assembly ---------------------------------------------------

def _full_prompt(style_prompt: str, beat_description: str) -> str:
    style = (style_prompt or "").rstrip(".")
    beat = (beat_description or "").rstrip(".")
    parts = []
    if style:
        parts.append(style)
    if beat:
        parts.append(f"Scene: {beat}")
    return ". ".join(parts) + "." if parts else ""


# ---- xlsx writer -------------------------------------------------------

def write_xlsx(xlsx_path: Path, data: dict[str, Any]) -> None:
    session_id = data.get("session_id", "")
    canvas = data.get("canvas", {})
    chunks = data.get("chunks", [])

    cfg = _session_config(session_id)
    style_prompt = cfg.get("default_style_prompt") or cfg.get("style_reference") or ""

    # Compute timeline (fills start_s, end_s).
    _compute_timeline(session_id, chunks)

    wb = Workbook()
    ws = wb.active
    ws.title = "shot-list"

    # --- header area ---
    ws.cell(row=1, column=1, value=f"spoolcast shot list — {session_id}")
    ws.cell(row=1, column=1).font = Font(bold=True, size=16)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLUMNS))

    meta_parts = [
        f"Session: {session_id}",
        f"Canvas: {canvas.get('aspect_ratio', '16:9')}",
        f"FPS: {canvas.get('fps', 30)}",
        f"Chunks: {len(chunks)}",
    ]
    ws.cell(row=2, column=1, value=" · ".join(meta_parts))
    ws.cell(row=2, column=1).font = Font(italic=True, color="666666")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(COLUMNS))

    # row 3 left blank as spacer.

    # --- column headers (row 4) ---
    header_row = 4
    header_fill = PatternFill("solid", fgColor="D6D9DF")
    thin = Side(border_style="thin", color="CCCCCC")
    header_border = Border(top=thin, bottom=thin, left=thin, right=thin)
    for col_idx, (_key, label, _scope, _w) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=label)
        cell.font = Font(bold=True, size=11)
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = header_border

    # --- data rows ---
    data_start_row = header_row + 1
    current_row = data_start_row

    for chunk_idx, chunk in enumerate(chunks):
        beats = chunk.get("beats") or [{}]
        chunk_start = current_row
        chunk_end = current_row + len(beats) - 1
        color = CHUNK_ROW_COLORS[chunk_idx % len(CHUNK_ROW_COLORS)]
        fill = PatternFill("solid", fgColor=color)

        # Chunk-level values (written once; merged across beats).
        image_source = chunk.get("image_source", "generated")
        # For non-generated chunks, Full Prompt doesn't apply (no kie call).
        full_prompt_value = (
            _full_prompt(style_prompt, chunk.get("beat_description", ""))
            if image_source == "generated"
            else "—"
        )
        chunk_values = {
            "chunk_id": chunk.get("id", ""),
            "scene": f"{chunk.get('scene', '')} — {chunk.get('scene_title', '')}".strip(" —"),
            "summary": chunk.get("summary", ""),
            "continuity": chunk.get("continuity", "standalone"),
            "reveal_direction": chunk.get("reveal_direction", ""),
            "image_source": image_source,
            "image_path": chunk.get("image_path", ""),
            "beat_description": chunk.get("beat_description", ""),
            "full_prompt": full_prompt_value,
        }

        for beat_idx, beat in enumerate(beats):
            row = current_row + beat_idx
            for col_idx, (key, _label, scope, _w) in enumerate(COLUMNS, start=1):
                if scope == "chunk":
                    value = chunk_values.get(key, "") if beat_idx == 0 else None
                    v_align = "center"
                else:
                    # Beat-level: the "beat_id" column maps to beat["id"]
                    # (the JSON uses "id" per-beat).
                    if key == "beat_id":
                        value = beat.get("id", "")
                    else:
                        value = beat.get(key, "")
                    # Normalize blank numeric fields to None so they don't
                    # show as "" stringly.
                    if key in ("transition_s", "start_s", "end_s") and value == "":
                        value = None
                    v_align = "top"
                cell = ws.cell(row=row, column=col_idx, value=value)
                cell.fill = fill
                cell.alignment = Alignment(vertical=v_align, wrap_text=True)
                cell.font = Font(size=11)

        # Merge chunk-level columns across this chunk's beats.
        if chunk_end > chunk_start:
            for col_idx, (_key, _label, scope, _w) in enumerate(COLUMNS, start=1):
                if scope == "chunk":
                    ws.merge_cells(
                        start_row=chunk_start,
                        start_column=col_idx,
                        end_row=chunk_end,
                        end_column=col_idx,
                    )

        current_row = chunk_end + 1

    # --- column widths ---
    for col_idx, (_key, _label, _scope, width) in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # --- row heights ---
    # Set header/meta rows explicitly; leave data rows unset so the
    # spreadsheet app auto-grows them to fit wrapped narration.
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[header_row].height = 24

    # --- freeze panes so header stays visible ---
    ws.freeze_panes = f"A{data_start_row}"

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx_path)


# ---- xlsx reader -------------------------------------------------------

def read_xlsx(xlsx_path: Path) -> dict[str, Any]:
    """Read the xlsx back into the normalized data dict.

    Merged chunk-level cells: the top-left of the merge holds the value;
    other cells in the merge are None. We forward-fill those by chunk.
    """
    wb = load_workbook(xlsx_path)
    ws = wb.active

    # Find the header row by looking for the "Chunk" label.
    header_row = None
    for r in range(1, 10):
        if ws.cell(row=r, column=1).value == "Chunk":
            header_row = r
            break
    if header_row is None:
        raise ValueError(f"could not locate header row in {xlsx_path}")

    key_by_col = {}
    for col_idx, (key, label, _scope, _w) in enumerate(COLUMNS, start=1):
        key_by_col[col_idx] = key

    chunks: dict[str, dict[str, Any]] = {}
    chunk_order: list[str] = []

    # Build a value lookup that resolves merged cells to the top-left value.
    def _get(row: int, col: int) -> Any:
        cell = ws.cell(row=row, column=col)
        # if the cell is part of a merged range, return the top-left value
        for merged in ws.merged_cells.ranges:
            if cell.coordinate in merged:
                return ws.cell(row=merged.min_row, column=merged.min_col).value
        return cell.value

    r = header_row + 1
    while True:
        chunk_id = _get(r, 1)
        if not chunk_id:
            break
        beat_id = _get(r, 4)  # "Beat" column

        if chunk_id not in chunks:
            # New chunk: capture chunk-level fields by looking up by key name.
            scene_raw = _get_by_key(r, "scene", key_by_col, _get) or ""
            if " — " in scene_raw:
                scene, scene_title = scene_raw.split(" — ", 1)
            else:
                scene, scene_title = scene_raw, ""
            chunks[chunk_id] = {
                "id": chunk_id,
                "scene": scene,
                "scene_title": scene_title,
                "summary": _get_by_key(r, "summary", key_by_col, _get) or "",
                "continuity": _get_by_key(r, "continuity", key_by_col, _get) or "standalone",
                "reveal_direction": _get_by_key(r, "reveal_direction", key_by_col, _get) or "",
                "image_source": _get_by_key(r, "image_source", key_by_col, _get) or "generated",
                "image_path": _get_by_key(r, "image_path", key_by_col, _get) or "",
                "beat_description": _get_by_key(r, "beat_description", key_by_col, _get) or "",
                "beats": [],
            }
            chunk_order.append(chunk_id)

        beat: dict[str, Any] = {"id": beat_id or ""}
        for col_idx in range(1, len(COLUMNS) + 1):
            key = key_by_col[col_idx]
            if key in CHUNK_SCOPE_KEYS or key == "beat_id":
                continue
            value = ws.cell(row=r, column=col_idx).value
            if value is None:
                continue
            beat[key] = value
        chunks[chunk_id]["beats"].append(beat)
        r += 1

    return {
        "session_id": _read_session_id_from_meta(ws),
        "canvas": _read_canvas_from_meta(ws),
        "chunks": [chunks[cid] for cid in chunk_order],
    }


def _get_by_key(row: int, key: str, key_by_col: dict[int, str], getter: Any) -> Any:
    for col_idx, k in key_by_col.items():
        if k == key:
            return getter(row, col_idx)
    return None


def _read_session_id_from_meta(ws: Any) -> str:
    meta = ws.cell(row=2, column=1).value or ""
    for part in str(meta).split("·"):
        part = part.strip()
        if part.lower().startswith("session:"):
            return part.split(":", 1)[1].strip()
    return ""


def _read_canvas_from_meta(ws: Any) -> dict[str, Any]:
    meta = ws.cell(row=2, column=1).value or ""
    canvas: dict[str, Any] = {}
    for part in str(meta).split("·"):
        part = part.strip()
        if part.lower().startswith("canvas:"):
            canvas["aspect_ratio"] = part.split(":", 1)[1].strip()
        elif part.lower().startswith("fps:"):
            try:
                canvas["fps"] = int(part.split(":", 1)[1].strip())
            except Exception:
                pass
    return canvas


# ---- CLI ---------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Convert between shot-list JSON and xlsx"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("to-xlsx", help="Generate xlsx from JSON")
    p1.add_argument("--from-json", required=True)
    p1.add_argument("--to-xlsx", required=True)

    p2 = sub.add_parser("from-xlsx", help="Read xlsx and dump normalized JSON to stdout")
    p2.add_argument("--xlsx", required=True)

    args = parser.parse_args()

    if args.cmd == "to-xlsx":
        data = load_json(Path(args.from_json))
        write_xlsx(Path(args.to_xlsx), data)
        print(f"[shot-list] wrote {args.to_xlsx}")
    elif args.cmd == "from-xlsx":
        data = read_xlsx(Path(args.xlsx))
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    _cli()
