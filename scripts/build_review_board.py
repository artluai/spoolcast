"""
build_review_board.py — generate an HTML review board from a shot-list JSON.

Reads:
    ../spoolcast-content/sessions/<session>/shot-list/shot-list.json

Writes:
    ../spoolcast-content/sessions/<session>/review/shot-review.html

Each chunk is rendered as a card showing: chunk id, scene, beats +
narration, beat description (the per-chunk part of the prompt), image,
duration, and notes. Image paths are resolved relative to the session
root so the HTML works when opened locally.

Usage:
    scripts/.venv/bin/python scripts/build_review_board.py --session pilot
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT.parent / "spoolcast-content"


def session_dir(session_id: str) -> Path:
    return CONTENT_ROOT / "sessions" / session_id


def shot_list_path(session_id: str) -> Path:
    return session_dir(session_id) / "shot-list" / "shot-list.json"


def review_html_path(session_id: str) -> Path:
    return session_dir(session_id) / "review" / "shot-review.html"


def _render_beat_row(beat: dict[str, Any]) -> str:
    pid = html.escape(beat.get("id", ""))
    text = html.escape(beat.get("narration", ""))
    pause = html.escape(beat.get("pause_after", "") or "")
    pause_badge = (
        f'<span class="pause pause-{pause}">pause: {pause}</span>' if pause else ""
    )
    return (
        f'<li class="beat">'
        f'<span class="beat-id">{pid}</span>'
        f'<span class="beat-text">{text}</span>'
        f"{pause_badge}"
        f"</li>"
    )


def _render_chunk_card(chunk: dict[str, Any], session_root_href: str) -> str:
    cid = html.escape(chunk.get("id", ""))
    scene = html.escape(chunk.get("scene", ""))
    scene_title = html.escape(chunk.get("scene_title", ""))
    duration = chunk.get("duration_seconds", 0)
    beat_desc = html.escape(chunk.get("beat_description", ""))
    image_rel = chunk.get("image_path", "")
    image_href = f"{session_root_href}/{image_rel}" if image_rel else ""
    notes = html.escape(chunk.get("notes", "") or "")
    beats_html = "".join(_render_beat_row(b) for b in chunk.get("beats", []))
    beat_count = len(chunk.get("beats", []))

    image_block = (
        f'<a href="{html.escape(image_href)}" target="_blank">'
        f'<img class="scene-img" src="{html.escape(image_href)}" alt="{cid}">'
        f"</a>"
        if image_href
        else '<div class="scene-img scene-img-missing">image missing</div>'
    )

    notes_block = f'<div class="notes"><span class="label">notes:</span> {notes}</div>' if notes else ""

    return f"""
<article class="chunk">
  <header class="chunk-header">
    <div class="chunk-id">{cid}</div>
    <div class="chunk-meta">
      <span class="scene-tag">scene {scene} · {scene_title}</span>
      <span class="duration-tag">{duration}s · {beat_count} beats</span>
    </div>
  </header>
  <div class="chunk-body">
    <div class="chunk-image">{image_block}</div>
    <div class="chunk-info">
      <div class="section-label">beats + narration</div>
      <ol class="beats">{beats_html}</ol>
      <div class="section-label">scene description (per-chunk prompt)</div>
      <div class="beat-desc">{beat_desc}</div>
      {notes_block}
    </div>
  </div>
</article>
"""


CSS = """
:root {
  --bg: #0f1115;
  --panel: #171a21;
  --panel-2: #1f232c;
  --border: #2b303a;
  --text: #e8ebf0;
  --text-dim: #9aa3b2;
  --accent: #6ea8ff;
  --ok: #4ade80;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text); font-family: -apple-system, "SF Pro Text", ui-sans-serif, system-ui, sans-serif; }
body { padding: 48px 32px 96px; max-width: 1400px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 8px; }
.sub { color: var(--text-dim); margin: 0 0 40px; font-size: 14px; }
.chunk { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; margin-bottom: 28px; overflow: hidden; }
.chunk-header { display: flex; justify-content: space-between; align-items: baseline; padding: 16px 24px; background: var(--panel-2); border-bottom: 1px solid var(--border); }
.chunk-id { font-size: 22px; font-weight: 600; color: var(--accent); letter-spacing: 0.02em; }
.chunk-meta { display: flex; gap: 12px; font-size: 13px; color: var(--text-dim); }
.scene-tag, .duration-tag { background: var(--bg); border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; }
.chunk-body { display: grid; grid-template-columns: minmax(420px, 1fr) 1fr; gap: 24px; padding: 20px 24px; }
.chunk-image { align-self: start; }
.scene-img { width: 100%; border-radius: 8px; border: 1px solid var(--border); background: #fff; display: block; }
.scene-img-missing { width: 100%; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-style: italic; }
.chunk-info > .section-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-dim); margin-top: 4px; margin-bottom: 8px; }
.chunk-info > .section-label:first-child { margin-top: 0; }
.beats { list-style: none; padding: 0; margin: 0 0 18px; }
.beat { display: grid; grid-template-columns: 54px 1fr auto; gap: 10px; padding: 7px 0; border-bottom: 1px dashed var(--border); font-size: 14px; align-items: baseline; }
.beat:last-child { border-bottom: none; }
.beat-id { color: var(--text-dim); font-variant-numeric: tabular-nums; font-size: 12px; }
.beat-text { color: var(--text); }
.pause { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; }
.pause-long { color: var(--accent); border-color: var(--accent); }
.beat-desc { font-size: 13px; line-height: 1.5; color: var(--text); background: var(--panel-2); border: 1px solid var(--border); padding: 12px 14px; border-radius: 8px; }
.notes { margin-top: 14px; font-size: 13px; color: var(--text-dim); }
.notes .label { color: var(--accent); margin-right: 6px; text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px; }
.scene-break { height: 1px; background: linear-gradient(to right, transparent, var(--border), transparent); margin: 40px 0 28px; }
.scene-hed { font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-dim); margin: 36px 0 14px; }
"""


def build_html(shot_list: dict[str, Any]) -> str:
    chunks = shot_list.get("chunks", [])
    session_id = shot_list.get("session_id", "")

    # Group by scene for scene-break dividers.
    cards_html: list[str] = []
    prev_scene: str | None = None
    for chunk in chunks:
        scene = chunk.get("scene", "")
        if scene != prev_scene:
            if prev_scene is not None:
                cards_html.append('<div class="scene-break"></div>')
            cards_html.append(
                f'<div class="scene-hed">scene {html.escape(scene)} — {html.escape(chunk.get("scene_title", ""))}</div>'
            )
            prev_scene = scene
        cards_html.append(_render_chunk_card(chunk, session_root_href=".."))

    total_chunks = len(chunks)
    total_duration = sum(c.get("duration_seconds", 0) for c in chunks)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>spoolcast shot review — {html.escape(session_id)}</title>
  <style>{CSS}</style>
</head>
<body>
  <h1>spoolcast shot review — {html.escape(session_id)}</h1>
  <p class="sub">{total_chunks} chunks · ~{total_duration}s total · generated by build_review_board.py</p>
  {''.join(cards_html)}
</body>
</html>
"""


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Build the HTML shot review board")
    parser.add_argument("--session", required=True, help="session id (folder name)")
    args = parser.parse_args()

    sl_path = shot_list_path(args.session)
    if not sl_path.exists():
        print(f"[review] shot list not found: {sl_path}", file=sys.stderr)
        sys.exit(1)

    with open(sl_path) as f:
        shot_list = json.load(f)

    html_out = build_html(shot_list)
    out_path = review_html_path(args.session)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out)
    print(f"[review] wrote {out_path}")


if __name__ == "__main__":
    _cli()
