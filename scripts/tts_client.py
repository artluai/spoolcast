"""
tts_client.py — thin client for Google Cloud Text-to-Speech (Chirp3-HD).

Reads GOOGLE_CLOUD_TTS_API_KEY from the repo .env.
Submits a synthesis request, saves the resulting audio.

Default voice is Chirp3-HD-Puck (chosen for spoolcast narrator tone).
See DESIGN_NOTES.md for why Google Cloud TTS over ElevenLabs.

Supports optional word-level timepoint extraction via SSML <mark> tags
and `enableTimePointing`. When `marks` are provided, each target word is
wrapped in an SSML <mark> tag and the response timepoints are saved to
`<output_path>.timepoints.json`. Used by the overlay system to time
brand-logo insertions to the exact moment the word is spoken.

Usage (python):
    from tts_client import TtsClient
    client = TtsClient()
    client.synthesize("hello world", "/tmp/out.mp3", voice="Puck")
    # with marks:
    client.synthesize(
        "I use Adobe and Descript.", "/tmp/out.mp3",
        marks=["Adobe", "Descript"],
    )

Usage (CLI):
    scripts/.venv/bin/python scripts/tts_client.py \\
        --text "hello world" --out /tmp/out.mp3 --voice Puck
    # with marks (repeat --mark for each word):
    scripts/.venv/bin/python scripts/tts_client.py \\
        --text "I use Adobe and Descript." --out /tmp/out.mp3 \\
        --mark Adobe --mark Descript
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
DEFAULT_LANGUAGE_CODE = "en-US"
DEFAULT_VOICE = "Puck"
DEFAULT_AUDIO_ENCODING = "MP3"


class TtsError(RuntimeError):
    pass


@dataclass
class TtsResult:
    output_path: Path
    voice_name: str
    byte_count: int
    timepoints: dict[str, float] = field(default_factory=dict)
    timepoints_path: Path | None = None


def _mark_name_for(word: str) -> str:
    """Normalize a target word into a safe SSML mark name."""
    return re.sub(r"[^a-z0-9]+", "_", word.lower()).strip("_") or "mark"


def _build_ssml_with_marks(text: str, marks: list[str]) -> tuple[str, dict[str, str]]:
    """Wrap `text` in <speak>...</speak> and insert <mark name="..."/> before
    each case-insensitive whole-word match of a target word.

    Returns (ssml_string, word_to_mark_name).
    Words that don't match anywhere in the text are silently skipped — the
    caller's timepoint lookup will just miss them.
    """
    escaped = html.escape(text)

    # Find all target-word positions up front so we can insert in reverse.
    word_to_markname: dict[str, str] = {}
    positions: list[tuple[int, str]] = []
    used_names: set[str] = set()
    for word in marks:
        name = _mark_name_for(word)
        # Disambiguate if two words normalize to the same name.
        base = name
        i = 2
        while name in used_names:
            name = f"{base}_{i}"
            i += 1
        used_names.add(name)

        escaped_word = html.escape(word)
        pattern = re.compile(r"\b" + re.escape(escaped_word) + r"\b", re.IGNORECASE)
        match = pattern.search(escaped)
        if match:
            positions.append((match.start(), name))
            word_to_markname[word] = name

    # Insert marks from end to start so earlier positions stay valid.
    positions.sort(key=lambda p: p[0], reverse=True)
    for pos, name in positions:
        escaped = escaped[:pos] + f'<mark name="{name}"/>' + escaped[pos:]

    return f"<speak>{escaped}</speak>", word_to_markname


class TtsClient:
    """Synchronous Google Cloud TTS client. Single-purpose."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        if api_key is None:
            repo_root = Path(__file__).resolve().parent.parent
            load_dotenv(repo_root / ".env")
            api_key = os.environ.get("GOOGLE_CLOUD_TTS_API_KEY")
        if not api_key:
            raise TtsError(
                "GOOGLE_CLOUD_TTS_API_KEY is not set. "
                "Put it in spoolcast/.env or pass it in."
            )
        self.api_key = api_key
        self.base_url = base_url

    def synthesize(
        self,
        text: str,
        output_path: Path | str,
        *,
        voice: str = DEFAULT_VOICE,
        language_code: str = DEFAULT_LANGUAGE_CODE,
        audio_encoding: str = DEFAULT_AUDIO_ENCODING,
        speaking_rate: float | None = None,
        pitch: float | None = None,
        marks: list[str] | None = None,
    ) -> TtsResult:
        """Synthesize `text` to `output_path`.

        `voice` accepts either a short name (e.g. 'Puck') or a fully-qualified
        voice name (e.g. 'en-US-Chirp3-HD-Puck').

        `marks`: optional list of words to mark for timepoint extraction. Each
        first case-insensitive whole-word match is wrapped in an SSML
        <mark name="..."/> tag and the response timepoints are saved next to
        the audio as `<output>.timepoints.json`.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_name = (
            voice
            if voice.startswith(("en-", "fr-", "es-", "de-", "ja-", "ko-", "zh-"))
            else f"{language_code}-Chirp3-HD-{voice}"
        )

        audio_config: dict[str, float | str] = {"audioEncoding": audio_encoding}
        if speaking_rate is not None:
            audio_config["speakingRate"] = speaking_rate
        if pitch is not None:
            audio_config["pitch"] = pitch

        # Build the input — plain text by default, SSML with marks if requested.
        # Caller-provided SSML (text already starts with <speak>) is detected and
        # passed through as ssml; this is the path used by batch_tts.py for
        # pronunciation-registry SSML <sub alias>/<phoneme> wrapping.
        word_to_markname: dict[str, str] = {}
        if marks:
            ssml, word_to_markname = _build_ssml_with_marks(text, marks)
            input_obj: dict[str, str] = {"ssml": ssml}
        elif text.lstrip().startswith("<speak>"):
            input_obj = {"ssml": text}
        else:
            input_obj = {"text": text}

        body: dict = {
            "input": input_obj,
            "voice": {"languageCode": language_code, "name": voice_name},
            "audioConfig": audio_config,
        }
        # enableTimePointing is a top-level request field; enables SSML <mark>
        # timepoint extraction for supported voices (Chirp3-HD included).
        if word_to_markname:
            body["enableTimePointing"] = ["SSML_MARK"]

        url = f"{self.base_url}?key={self.api_key}"
        resp = requests.post(url, json=body, timeout=60)
        if resp.status_code != 200:
            raise TtsError(
                f"google tts returned HTTP {resp.status_code}: {resp.text[:500]}"
            )
        payload = resp.json()
        audio_b64 = payload.get("audioContent")
        if not audio_b64:
            raise TtsError(f"google tts success but no audioContent: {payload}")
        audio = base64.b64decode(audio_b64)
        output_path.write_bytes(audio)

        # Extract + save timepoints when marks were requested.
        timepoints: dict[str, float] = {}
        timepoints_path: Path | None = None
        if word_to_markname:
            api_tps = payload.get("timepoints") or []
            # Reverse lookup: markName -> original word
            markname_to_word = {v: k for k, v in word_to_markname.items()}
            for tp in api_tps:
                name = tp.get("markName", "")
                secs = tp.get("timeSeconds")
                if name and secs is not None and name in markname_to_word:
                    timepoints[markname_to_word[name]] = float(secs)

            timepoints_path = output_path.with_suffix(output_path.suffix + ".timepoints.json")
            timepoints_path.write_text(
                json.dumps(
                    {
                        "audio_file": output_path.name,
                        "voice": voice_name,
                        "speaking_rate": speaking_rate,
                        "requested_marks": marks or [],
                        "timepoints": timepoints,
                    },
                    indent=2,
                )
            )

        return TtsResult(
            output_path=output_path,
            voice_name=voice_name,
            byte_count=len(audio),
            timepoints=timepoints,
            timepoints_path=timepoints_path,
        )


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize text with Google Cloud TTS (Chirp3-HD)"
    )
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", required=True, help="output audio path")
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help="Chirp3-HD voice name (default: Puck). Pass full name 'en-US-...' to override.",
    )
    parser.add_argument("--language-code", default=DEFAULT_LANGUAGE_CODE)
    parser.add_argument("--encoding", default=DEFAULT_AUDIO_ENCODING)
    parser.add_argument("--speaking-rate", type=float, default=None)
    parser.add_argument("--pitch", type=float, default=None)
    parser.add_argument(
        "--mark",
        action="append",
        default=None,
        help="Word to mark for timepoint extraction (repeatable). "
             "Saves timepoints to <out>.timepoints.json",
    )
    args = parser.parse_args()

    try:
        client = TtsClient()
        result = client.synthesize(
            args.text,
            args.out,
            voice=args.voice,
            language_code=args.language_code,
            audio_encoding=args.encoding,
            speaking_rate=args.speaking_rate,
            pitch=args.pitch,
            marks=args.mark,
        )
        print(f"[tts] {result.byte_count} bytes -> {result.output_path}")
        print(f"[tts] voice: {result.voice_name}")
        if result.timepoints:
            print(f"[tts] timepoints -> {result.timepoints_path}")
            for word, t in sorted(result.timepoints.items(), key=lambda kv: kv[1]):
                print(f"[tts]   {word!r}: {t:.3f}s")
        elif args.mark:
            print(f"[tts] WARNING: --mark given but no timepoints returned by API")
    except Exception as e:
        print(f"[tts] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
