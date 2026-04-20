"""
publish_youtube.py — upload an mp4 + thumbnail to YouTube via Data API v3.

CLI tool that:
1. Authenticates via OAuth 2.0 (first run opens browser; later runs use a
   saved refresh token).
2. Uploads a video resumably via videos.insert.
3. Attaches a custom thumbnail via thumbnails.set.
4. Prints the final https://youtube.com/watch?v=<id> URL.

Credentials:
- Reads YOUTUBE_CLIENT_SECRETS_PATH from the repo .env (same load_dotenv
  pattern used by kie_client.py / tts_client.py).
- Saves the refreshable token at ~/.config/spoolcast/youtube-token.json
  by default (override with --token-path).

Scopes:
- youtube.upload — upload videos
- youtube         — thumbnails.set (which requires the broader scope)

See the usage example block at the bottom of this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# ---- scopes / constants ------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

DEFAULT_TOKEN_PATH = Path.home() / ".config" / "spoolcast" / "youtube-token.json"
DEFAULT_CATEGORY = 28  # 28 = Science & Technology
DEFAULT_PRIVACY = "unlisted"
VALID_PRIVACIES = {"private", "unlisted", "public"}

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB resumable chunks

SETUP_INSTRUCTIONS = """\
Setup required:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project (or pick one)
3. Enable YouTube Data API v3
4. Create OAuth 2.0 Client ID -> Desktop app
5. Download the client_secret.json
6. Add YOUTUBE_CLIENT_SECRETS_PATH=/path/to/client_secret.json to repo .env
7. Re-run this script
"""

SDK_INSTALL_HINT = """\
ERROR: Google SDK not installed. Run:
  scripts/.venv/bin/pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
"""


# ---- SDK import (lazy-ish: we want a clean error if missing) -----------

try:
    from google.auth.transport.requests import Request  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
    from googleapiclient.errors import HttpError  # type: ignore
    from googleapiclient.http import MediaFileUpload  # type: ignore
except ImportError:
    print(SDK_INSTALL_HINT, file=sys.stderr)
    sys.exit(3)


# ---- env / config ------------------------------------------------------

def _load_env() -> None:
    """Load repo-root .env — same pattern as kie_client.py."""
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")


def _resolve_client_secrets(cli_value: str | None) -> Path:
    """Resolve the client_secret.json path from CLI arg or env var."""
    candidate = cli_value or os.environ.get("YOUTUBE_CLIENT_SECRETS_PATH")
    if not candidate:
        print(SETUP_INSTRUCTIONS, file=sys.stderr)
        sys.exit(2)
    path = Path(candidate).expanduser()
    if not path.exists():
        print(
            f"ERROR: client secrets file not found at {path}\n\n"
            + SETUP_INSTRUCTIONS,
            file=sys.stderr,
        )
        sys.exit(2)
    return path


# ---- auth --------------------------------------------------------------

def get_credentials(
    client_secrets_path: Path,
    token_path: Path,
) -> Credentials:
    """Return valid OAuth credentials, refreshing or prompting as needed.

    Flow:
    - If a token file exists, load it.
    - If valid, return it.
    - If expired but refreshable, refresh silently.
    - Otherwise, run the local-server consent flow (opens browser).
    - Save the (possibly refreshed) token back to token_path.
    """
    creds: Credentials | None = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )
        except (ValueError, json.JSONDecodeError) as e:
            print(
                f"[publish_youtube] existing token unreadable ({e}); "
                "re-authenticating.",
                file=sys.stderr,
            )
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
            return creds
        except Exception as e:  # pragma: no cover - network-dependent
            print(
                f"[publish_youtube] refresh failed ({e}); "
                "re-running consent flow.",
                file=sys.stderr,
            )
            creds = None

    # First-time or fallback: interactive consent.
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path), SCOPES
    )
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path)
    return creds


def _save_token(creds: Credentials, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    # token file contains a refresh token — tighten perms.
    try:
        os.chmod(token_path, 0o600)
    except OSError:
        pass


# ---- upload ------------------------------------------------------------

def upload_video(
    youtube,
    *,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category: int,
    privacy: str,
) -> str:
    """Upload the video resumably. Returns the new video ID."""
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(category),
        },
        "status": {
            "privacyStatus": privacy,
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=CHUNK_SIZE,
        resumable=True,
        mimetype="video/mp4",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    last_pct = -1
    while response is None:
        status, response = request.next_chunk()
        if status is not None:
            pct = int(status.progress() * 100)
            if pct != last_pct:
                print(f"Uploaded {pct}%")
                last_pct = pct

    print("Uploaded 100%")
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"videos.insert returned no id: {response!r}")
    return video_id


def set_thumbnail(youtube, *, video_id: str, thumbnail_path: Path) -> None:
    """Attach a custom thumbnail to an already-uploaded video."""
    media = MediaFileUpload(str(thumbnail_path))
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


# ---- CLI ---------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Upload an mp4 + thumbnail to YouTube via Data API v3."
    )
    p.add_argument("--video", required=True, type=Path, help="path to .mp4")
    p.add_argument("--title", required=True, help="YouTube video title")

    desc_group = p.add_mutually_exclusive_group(required=True)
    desc_group.add_argument(
        "--description-file", type=Path, help="path to description text file"
    )
    desc_group.add_argument("--description", help="description text inline")

    p.add_argument("--thumbnail", type=Path, help="optional thumbnail image")
    p.add_argument("--tags", default="", help="comma-separated tag list")
    p.add_argument(
        "--category",
        type=int,
        default=DEFAULT_CATEGORY,
        help="numeric categoryId (default 28 = Science & Technology)",
    )
    p.add_argument(
        "--privacy",
        default=DEFAULT_PRIVACY,
        choices=sorted(VALID_PRIVACIES),
        help="privacyStatus (default unlisted)",
    )
    p.add_argument(
        "--client-secrets",
        type=str,
        default=None,
        help="override YOUTUBE_CLIENT_SECRETS_PATH env var",
    )
    p.add_argument(
        "--token-path",
        type=Path,
        default=DEFAULT_TOKEN_PATH,
        help=f"where to cache the OAuth token (default {DEFAULT_TOKEN_PATH})",
    )
    return p.parse_args(argv)


def _read_description(args: argparse.Namespace) -> str:
    if args.description is not None:
        return args.description
    path: Path = args.description_file
    if not path.exists():
        print(f"ERROR: description file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def _parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # Validate inputs up front.
    if not args.video.exists():
        print(f"ERROR: video not found: {args.video}", file=sys.stderr)
        return 1
    if args.thumbnail is not None and not args.thumbnail.exists():
        print(f"ERROR: thumbnail not found: {args.thumbnail}", file=sys.stderr)
        return 1

    _load_env()
    client_secrets_path = _resolve_client_secrets(args.client_secrets)

    description = _read_description(args)
    tags = _parse_tags(args.tags)

    print(f"[publish_youtube] authenticating (token: {args.token_path})")
    creds = get_credentials(client_secrets_path, args.token_path)
    youtube = build("youtube", "v3", credentials=creds)

    try:
        print(f"[publish_youtube] uploading {args.video} ({args.privacy})")
        video_id = upload_video(
            youtube,
            video_path=args.video,
            title=args.title,
            description=description,
            tags=tags,
            category=args.category,
            privacy=args.privacy,
        )
        print(f"[publish_youtube] video id: {video_id}")

        if args.thumbnail is not None:
            print(f"[publish_youtube] setting thumbnail {args.thumbnail}")
            set_thumbnail(
                youtube, video_id=video_id, thumbnail_path=args.thumbnail
            )
            print("[publish_youtube] thumbnail set")

        url = f"https://youtube.com/watch?v={video_id}"
        print(url)
        return 0
    except HttpError as e:
        print(f"ERROR: YouTube API call failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ---- usage example -----------------------------------------------------
#
# End-to-end invocation once credentials are configured:
#
#   # one-time setup: add to spoolcast/.env
#   #   YOUTUBE_CLIENT_SECRETS_PATH=/absolute/path/to/client_secret.json
#
#   scripts/.venv/bin/python scripts/publish_youtube.py \
#       --video /Users/ralphxu/Documents/Projects/spoolcast-content/renders/spoolcast-explainer-v6.mp4 \
#       --title "I don't make videos. My AI pipeline does." \
#       --description-file /Users/ralphxu/Documents/Projects/spoolcast-content/renders/description.txt \
#       --thumbnail /Users/ralphxu/Documents/Projects/spoolcast-content/renders/thumbnail.png \
#       --tags spoolcast,ai-video,automation,builder \
#       --category 28 \
#       --privacy unlisted
#
# First run: a browser window opens for Google consent. Approve the two
# scopes (youtube.upload, youtube). The refresh token is written to
# ~/.config/spoolcast/youtube-token.json — future runs are silent.
#
# Successful output ends with a line like:
#   https://youtube.com/watch?v=dQw4w9WgXcQ
