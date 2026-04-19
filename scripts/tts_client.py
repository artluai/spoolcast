"""
tts_client.py — thin client for Google Cloud Text-to-Speech (Chirp3-HD).

Reads GOOGLE_CLOUD_TTS_API_KEY from the repo .env.
Submits a synthesis request, saves the resulting audio.

Default voice is Chirp3-HD-Puck (chosen for spoolcast narrator tone).
See DESIGN_NOTES.md for why Google Cloud TTS over ElevenLabs.

Usage (python):
    from tts_client import TtsClient
    client = TtsClient()
    client.synthesize("hello world", "/tmp/out.mp3", voice="Puck")

Usage (CLI):
    scripts/.venv/bin/python scripts/tts_client.py \\
        --text "hello world" --out /tmp/out.mp3 --voice Puck
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
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
    ) -> TtsResult:
        """Synthesize `text` to `output_path`.

        `voice` accepts either a short name (e.g. 'Puck') or a fully-qualified
        voice name (e.g. 'en-US-Chirp3-HD-Puck').
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

        body = {
            "input": {"text": text},
            "voice": {"languageCode": language_code, "name": voice_name},
            "audioConfig": audio_config,
        }

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
        return TtsResult(
            output_path=output_path, voice_name=voice_name, byte_count=len(audio)
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
        )
        print(f"[tts] {result.byte_count} bytes -> {result.output_path}")
        print(f"[tts] voice: {result.voice_name}")
    except Exception as e:
        print(f"[tts] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
