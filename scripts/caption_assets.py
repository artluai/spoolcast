"""caption_assets.py — shared helpers for building burn-in ASS subtitle files.

Used by both burn_captions.py (widescreen caption burn) and export_mobile.py
(mobile crop + caption burn) so the caption style stays identical across
surfaces. Any future path that burns captions (mobile-first authoring,
different aspect variants) should import from here rather than duplicate.

See SHIPPING.md § Part 3 Caption Styling for the shared style reference.
"""

from __future__ import annotations

from pathlib import Path


def srt_ts_to_ass(ts: str) -> str:
    """SRT HH:MM:SS,mmm -> ASS H:MM:SS.cc (centiseconds)."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    cs = int(ms) // 10
    return f"{int(h)}:{m}:{s}.{cs:02d}"


def srt_to_ass(
    srt_path: Path,
    ass_path: Path,
    play_res_x: int,
    play_res_y: int,
    font_size: int,
    margin_v: int,
    watermark: bool = True,
    watermark_alpha_hex: str = "59",  # ~65% opacity (alpha 0x59 = 35% transparent)
    outline_px: int = 6,
    cue_offset_sec: float = 0.0,   # shift all cues by -offset (for part 2/N)
    cue_window_sec: tuple[float, float] | None = None,  # (start, end) — filter cues
    part_label: str | None = None,  # e.g. "1 of 2" — renders in top bar
) -> int:
    """Convert an SRT file to an ASS v4+ file with explicit PlayRes.

    The explicit `PlayResX` / `PlayResY` header is the thing that makes
    MarginV work in frame-pixel units. Passing an SRT through ffmpeg's
    `subtitles` filter (libass's SRT reader) uses a small default PlayRes
    (~288 tall), which makes MarginV values project wildly wrong on
    1080 / 1920-tall frames. ASS files with `PlayRes*` set skip that trap.

    Returns cue count.
    """
    # ASS color: &HAABBGGRR (hex). White opaque = &H00FFFFFF. Black = &H00000000.
    # Captions use Montserrat Black — heavy sans-serif, bold, highest legibility
    # at mobile screen sizes. Caveat (the handwritten house font) was too soft
    # for mobile caption duty; still used elsewhere for in-scene text and
    # bumpers.
    style_line = (
        "Style: Default,Montserrat Black,"
        f"{font_size},"
        "&H00FFFFFF,"          # PrimaryColour (white)
        "&H000000FF,"          # SecondaryColour (unused)
        "&H00000000,"          # OutlineColour (black)
        "&H00000000,"          # BackColour (unused, no shadow)
        "-1,"                  # Bold (-1 = true)
        "0,0,0,"               # Italic, Underline, StrikeOut
        "100,100,"             # ScaleX, ScaleY
        "0,0,"                 # Spacing, Angle
        "1,"                   # BorderStyle (1 = outline + drop shadow)
        f"{outline_px},"       # Outline (px)
        "0,"                   # Shadow (px; 0 = no shadow)
        "8,"                   # Alignment (8 = top-center) — caption top-edge anchored
        "30,30,"               # MarginL, MarginR (px) — captions stretch close to edges
        f"{margin_v},"         # MarginV (px from TOP of canvas for top-anchored)
        "1"                    # Encoding
    )

    # Part badge: top-center of the TOP letterbox bar. Renders on black.
    part_badge_style_line = (
        "Style: PartBadge,Montserrat Black,"
        "60,"
        "&H00FFFFFF,"
        "&H00000000,"
        "&H00000000,"
        "&H00000000,"
        "-1,"
        "0,0,0,"
        "100,100,"
        "0,0,"
        "1,"
        "4,"    # outline
        "0,"
        "8,"    # Alignment 8 = top-center
        "40,40,"
        "150,"  # MarginV from top — centers badge in the 285-tall top bar
        "1"
    )

    # Bottom-anchored caption style — for cues estimated to wrap to 4+ lines.
    # Grows UP from a fixed bottom so the caption text block ends just above
    # the watermark row, accepting some overlap into the video content area.
    # The alternative (top-anchored 4+ line caption) runs off the bottom of
    # the frame. See SHIPPING.md § Mobile layout conventions.
    bottom_caption_style_line = (
        "Style: BottomCaption,Montserrat Black,"
        f"{font_size},"
        "&H00FFFFFF,"
        "&H000000FF,"
        "&H00000000,"
        "&H00000000,"
        "-1,"
        "0,0,0,"
        "100,100,"
        "0,0,"
        "1,"
        f"{outline_px},"
        "0,"
        "2,"    # Alignment 2 = bottom-center (grows up)
        "30,30,"
        "90,"   # MarginV from bottom → baseline y≈1830, top of watermark y≈1840
        "1"
    )

    # Watermark styles: rendered on the bottom letterbox bar (black strip
    # below the 4:5 content area on a 9:16 canvas), not over the video.
    # Two separate styles so we can use different fonts for each brand —
    # JetBrains Mono for "artlu.ai" (terminal feel), Comic Neue Bold for
    # "made by spoolcast" (chalkboard feel). Both ~65% opacity; size set
    # close to the caption size so they read as a credit row.
    watermark_size = max(40, font_size - 40)
    watermark_left_style_line = (
        "Style: WatermarkLeft,JetBrains Mono,"
        f"{watermark_size},"
        f"&H{watermark_alpha_hex}FFFFFF,"
        "&H00000000,"
        f"&H{watermark_alpha_hex}000000,"
        "&H00000000,"
        "0,"    # JetBrains Mono regular (Bold off)
        "0,0,0,"
        "100,100,"
        "0,0,"
        "1,"
        "3,"    # 3px outline
        "0,"
        "1,"    # Alignment 1 = bottom-LEFT
        "40,40,"
        "30,"   # MarginV 30 from bottom (sits in bottom bar)
        "1"
    )
    watermark_right_style_line = (
        "Style: WatermarkRight,Comic Neue,"
        f"{watermark_size},"
        f"&H{watermark_alpha_hex}FFFFFF,"
        "&H00000000,"
        f"&H{watermark_alpha_hex}000000,"
        "&H00000000,"
        "-1,"   # Comic Neue bold
        "0,0,0,"
        "100,100,"
        "0,0,"
        "1,"
        "3,"
        "0,"
        "3,"    # Alignment 3 = bottom-RIGHT
        "40,40,"
        "30,"
        "1"
    )

    header = (
        "[Script Info]\n"
        "Title: spoolcast-burn\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_res_x}\n"
        f"PlayResY: {play_res_y}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{style_line}\n"
        f"{bottom_caption_style_line}\n"
        f"{watermark_left_style_line}\n"
        f"{watermark_right_style_line}\n"
        f"{part_badge_style_line}\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    def _srt_ts_to_sec(ts: str) -> float:
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    def _sec_to_ass(sec: float) -> str:
        if sec < 0:
            sec = 0.0
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    cues: list[str] = []
    text = srt_path.read_text().replace("\r\n", "\n")
    for block in text.strip().split("\n\n"):
        lines = [line for line in block.split("\n") if line.strip()]
        if len(lines) < 3:
            continue
        start_srt, end_srt = [t.strip() for t in lines[1].split("-->")]
        start_sec = _srt_ts_to_sec(start_srt)
        end_sec = _srt_ts_to_sec(end_srt)
        if cue_window_sec is not None:
            window_start, window_end = cue_window_sec
            if end_sec <= window_start or start_sec >= window_end:
                continue
            start_sec = max(start_sec, window_start)
            end_sec = min(end_sec, window_end)
        start_sec -= cue_offset_sec
        end_sec -= cue_offset_sec
        start = _sec_to_ass(start_sec)
        end = _sec_to_ass(end_sec)
        content = "\\N".join(lines[2:])
        # Pick style based on estimated line count. 1020-px caption area at
        # Fontsize 70 fits ~18 chars/line. 4+ lines → bottom-anchored to
        # avoid running off the frame bottom; else top-anchored.
        char_count = sum(len(l) for l in lines[2:])
        est_lines = max(1, (char_count + 17) // 18)
        style_name = "BottomCaption" if est_lines >= 4 else "Default"
        cues.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{content}")

    if watermark:
        cues.append(
            "Dialogue: 0,0:00:00.00,9:59:59.99,WatermarkLeft,,0,0,0,,"
            "artlu.ai"
        )
        cues.append(
            "Dialogue: 0,0:00:00.00,9:59:59.99,WatermarkRight,,0,0,0,,"
            "made by spoolcast"
        )

    if part_label:
        cues.append(
            f"Dialogue: 0,0:00:00.00,9:59:59.99,PartBadge,,0,0,0,,{part_label}"
        )

    ass_path.write_text(header + "\n".join(cues) + "\n")
    return len(cues)
