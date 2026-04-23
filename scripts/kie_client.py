"""
kie_client.py — thin client for kie.ai image generation.

Reads KIE_API_KEY from the repo .env file.
Submits a task, polls until success/fail, downloads the result image.

This is the single integration point for kie.ai. Everything that needs a
generated image calls submit_and_download() — no other code should touch
the kie.ai API directly.

See ASSET_RULES.md (Kie Provider Spec) for the canonical API shape.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
import os


# ---- config ------------------------------------------------------------

BASE_URL = "https://api.kie.ai"
SUBMIT_PATH = "/api/v1/jobs/createTask"
POLL_PATH = "/api/v1/jobs/recordInfo"

TERMINAL_STATES = {"success", "fail"}
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 300  # 5 minutes per task

# HTTP request timeout per single API call. Without this, hung connections
# never surface — wrappers sit forever instead of erroring. 60s is generous
# for an async-submit POST; image downloads override with a longer value.
REQUEST_TIMEOUT_SECONDS = 60

# Single source of truth for the global default model. Imported by
# init_session.py, generate_reference.py, and any CLI that falls back when
# no session / --model override is present. Sessions created before a
# default change keep their own captured `preferred_model`.
DEFAULT_MODEL = "gpt-image-2-text-to-image"


def resolve_model(model: str, image_refs: Sequence[str] = ()) -> str:
    """Resolve a family slug to the specific variant needed given image_refs.

    GPT Image 2 is a family with two endpoints; refs presence dictates which
    one kie.ai accepts. Any caller that builds a request payload must pass
    this function's output as both the top-level `model` field AND the basis
    for `build_input_for_model`. Calling with only one side swapped produces
    silently-broken requests (right shape, wrong endpoint, refs ignored).
    """
    if model == "gpt-image-2-text-to-image" and image_refs:
        return "gpt-image-2-image-to-image"
    if model == "gpt-image-2-image-to-image" and not image_refs:
        return "gpt-image-2-text-to-image"
    return model


# ---- types -------------------------------------------------------------

@dataclass
class KieResult:
    task_id: str
    state: str  # "success" or "fail"
    result_urls: list[str]
    model: str
    local_path: Path | None
    fail_code: str = ""
    fail_msg: str = ""


class KieError(RuntimeError):
    pass


# ---- session-aware helper ---------------------------------------------

def build_input_from_session(
    session_id: str,
    *,
    prompt: str,
    image_refs: Sequence[str] = (),
    model_override: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build (model, input_dict) for a kie call, using session.json defaults.

    PREFERRED entrypoint for any one-off image generation. Reads:
    - resolution (mapped to nano-banana resolution / seedream quality)
    - aspect_ratio
    - output_format
    - preferred_model (unless overridden)

    from `<content-root>/sessions/<session_id>/session.json`.

    This exists to prevent a class of bug where ad-hoc scripts call
    `build_input_for_model` directly and silently get wrong defaults
    (e.g. 2K when the project standard is 1K).
    """
    # CONTENT_ROOT mirrors the convention used in generate_scene.py
    repo_root = Path(__file__).resolve().parent.parent
    content_root = repo_root.parent / "spoolcast-content"
    cfg_path = content_root / "sessions" / session_id / "session.json"
    if not cfg_path.exists():
        raise KieError(f"session config not found: {cfg_path}")
    cfg = json.loads(cfg_path.read_text())

    model = model_override or cfg.get("preferred_model") or DEFAULT_MODEL
    model = resolve_model(model, image_refs)
    quality = cfg.get("resolution") or "1K"  # "1K"/"2K"/"4K"
    aspect_ratio = cfg.get("aspect_ratio") or "16:9"
    output_format = cfg.get("output_format") or "png"

    input_dict = build_input_for_model(
        model,
        prompt=prompt,
        quality=quality,
        image_refs=image_refs,
        aspect_ratio=aspect_ratio,
        output_format=output_format,
    )
    return model, input_dict


# ---- per-model input shape ---------------------------------------------

def build_input_for_model(
    model: str,
    *,
    prompt: str,
    quality: str,  # REQUIRED — no default. Force callers to think about it.
    image_refs: Sequence[str] = (),
    aspect_ratio: str = "16:9",
    output_format: str = "png",
) -> dict[str, Any]:
    """Return the `input` dict shape for the given kie.ai model.

    Different kie models require different field names:
    - gpt-image-2-text-to-image: prompt, aspect_ratio, nsfw_checker (no image refs)
    - gpt-image-2-image-to-image: prompt, input_urls, aspect_ratio, nsfw_checker
    - seedream/5-lite-text-to-image: prompt, aspect_ratio, quality (no image refs)
    - seedream/5-lite-image-to-image: prompt, image_urls, aspect_ratio, quality
    - nano-banana-2 / nano-banana-pro / wan: prompt, image_input, aspect_ratio,
      resolution, output_format

    The `quality` arg uses seedream's `basic`/`high` vocabulary OR explicit
    nano-banana `1K`/`2K`/`4K`. For the nano-banana family it maps to
    `resolution`; for seedream it passes through as `quality`. GPT Image 2
    doesn't accept a quality/resolution knob — the arg is accepted and ignored.

    `quality` is REQUIRED with no default because silent defaults caused a
    bug where one-off scripts shipped at 2K instead of the project's 1K
    convention. Always pass session config's `resolution` value (read it
    via `build_input_from_session()` for safety).
    """
    # GPT Image 2 family: auto-swap between text-to-image and image-to-image
    # based on whether references are being passed. This lives here (not only
    # in build_input_from_session) so every caller — direct and session-wrapped —
    # gets the swap for free.
    if model in ("gpt-image-2-text-to-image", "gpt-image-2-image-to-image"):
        if image_refs:
            return {
                "prompt": prompt,
                "input_urls": list(image_refs),
                "aspect_ratio": aspect_ratio,
                "nsfw_checker": False,
            }
        return {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "nsfw_checker": False,
        }
    if model == "seedream/5-lite-text-to-image":
        return {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "quality": quality,
        }
    if model == "seedream/5-lite-image-to-image":
        return {
            "prompt": prompt,
            "image_urls": list(image_refs),
            "aspect_ratio": aspect_ratio,
            "quality": quality,
        }
    # Default: nano-banana family (nano-banana-2, nano-banana-pro), wan, etc.
    # Accept either seedream-style ("basic"/"high") or explicit ("1K"/"2K"/"4K").
    if quality in ("1K", "2K", "4K"):
        nano_res = quality
    else:
        nano_res = {"basic": "2K", "high": "4K"}.get(quality, "1K")
    return {
        "prompt": prompt,
        "image_input": list(image_refs),
        "aspect_ratio": aspect_ratio,
        "resolution": nano_res,
        "output_format": output_format,
    }


# ---- client ------------------------------------------------------------

class KieClient:
    """Small synchronous client wrapping kie.ai's async job API."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        if api_key is None:
            # load .env from the repo root (one level up from scripts/)
            repo_root = Path(__file__).resolve().parent.parent
            load_dotenv(repo_root / ".env")
            api_key = os.environ.get("KIE_API_KEY")
        if not api_key:
            raise KieError(
                "KIE_API_KEY is not set. Put it in spoolcast/.env or pass it in."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    # ---- submit ----

    def submit_task(
        self,
        *,
        model: str,
        input_dict: dict[str, Any],
        callback_url: str | None = None,
    ) -> str:
        """Submit a task with a raw `input` dict. Returns task_id.

        Callers should build `input_dict` via `build_input_for_model` (or
        manually if using a model not yet in the builder).
        """
        body: dict[str, Any] = {
            "model": model,
            "input": input_dict,
        }
        if callback_url:
            body["callBackUrl"] = callback_url

        url = f"{self.base_url}{SUBMIT_PATH}"
        resp = self._session.post(
            url, data=json.dumps(body), timeout=REQUEST_TIMEOUT_SECONDS
        )
        _raise_for_kie(resp, context=f"submit {model}")

        payload = resp.json()
        data = payload.get("data") or {}
        task_id = data.get("taskId")
        if not task_id:
            raise KieError(f"submit succeeded but no taskId in response: {payload}")
        return task_id

    # ---- poll ----

    def poll_task(
        self,
        task_id: str,
        *,
        interval_seconds: float = POLL_INTERVAL_SECONDS,
        timeout_seconds: float = POLL_TIMEOUT_SECONDS,
    ) -> KieResult:
        """Poll a task until it reaches a terminal state. Returns a KieResult."""
        deadline = time.monotonic() + timeout_seconds
        poll_url = f"{self.base_url}{POLL_PATH}?{urlencode({'taskId': task_id})}"

        while True:
            resp = self._session.get(poll_url, timeout=REQUEST_TIMEOUT_SECONDS)
            _raise_for_kie(resp, context=f"poll {task_id}")
            payload = resp.json()
            data = payload.get("data") or {}
            state = data.get("state", "unknown")

            if state in TERMINAL_STATES:
                result_urls: list[str] = []
                result_json = data.get("resultJson")
                if result_json:
                    try:
                        parsed = json.loads(result_json)
                        result_urls = list(parsed.get("resultUrls") or [])
                    except json.JSONDecodeError:
                        # keep going; result_urls stays empty, caller can inspect
                        pass
                return KieResult(
                    task_id=task_id,
                    state=state,
                    result_urls=result_urls,
                    model=data.get("model", ""),
                    local_path=None,
                    fail_code=data.get("failCode") or "",
                    fail_msg=data.get("failMsg") or "",
                )

            if time.monotonic() > deadline:
                raise KieError(
                    f"task {task_id} did not reach terminal state within "
                    f"{timeout_seconds}s (last state: {state})"
                )
            time.sleep(interval_seconds)

    # ---- download ----

    def download_result(
        self,
        result_url: str,
        dest_path: Path,
        *,
        chunk_size: int = 64 * 1024,
    ) -> Path:
        """Download a result URL to dest_path. Creates parent dirs if needed."""
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Use a fresh requests.get — the result URL is on a different host
        # (e.g. tempfile.aiquickdraw.com) and doesn't want our auth header.
        with requests.get(result_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        return dest_path

    # ---- combined ----

    def submit_and_download(
        self,
        *,
        model: str,
        input_dict: dict[str, Any],
        dest_path: Path,
        callback_url: str | None = None,
        poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
        poll_timeout_seconds: float = POLL_TIMEOUT_SECONDS,
    ) -> KieResult:
        """Submit, poll, and download in one call. Returns the KieResult
        with local_path set on success.

        `input_dict` should be built via `build_input_for_model(model, ...)`.
        """
        task_id = self.submit_task(
            model=model,
            input_dict=input_dict,
            callback_url=callback_url,
        )
        result = self.poll_task(
            task_id,
            interval_seconds=poll_interval_seconds,
            timeout_seconds=poll_timeout_seconds,
        )
        if result.state != "success":
            raise KieError(
                f"kie task {task_id} failed "
                f"(code={result.fail_code}, msg={result.fail_msg})"
            )
        if not result.result_urls:
            raise KieError(f"kie task {task_id} succeeded but returned no urls")

        local = self.download_result(result.result_urls[0], Path(dest_path))
        result.local_path = local
        return result


# ---- helpers -----------------------------------------------------------

def _raise_for_kie(resp: requests.Response, *, context: str) -> None:
    """Raise KieError if the HTTP or API-level response indicates failure."""
    if resp.status_code >= 400:
        raise KieError(
            f"{context} returned HTTP {resp.status_code}: {resp.text[:500]}"
        )
    try:
        payload = resp.json()
    except ValueError:
        raise KieError(f"{context} returned non-JSON: {resp.text[:500]}")
    code = payload.get("code")
    if code is not None and code != 200:
        raise KieError(
            f"{context} returned api code {code}: {payload.get('msg') or payload}"
        )


# ---- CLI smoke test ----------------------------------------------------

def _smoke_test() -> None:
    """Tiny CLI: submit a test prompt and print the result url.

    Usage:
        scripts/.venv/bin/python scripts/kie_client.py

    NOTE: this spends real kie.ai credits. Only run when you mean to.
    """
    import argparse

    parser = argparse.ArgumentParser(description="kie.ai smoke test")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--prompt",
        default="a simple hand-drawn marker illustration of a single tree on paper",
    )
    parser.add_argument("--out", default="kie-smoke.png")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--resolution", default="1K", help="1K|2K|4K (or basic|high)")
    args = parser.parse_args()

    client = KieClient()
    print(f"[kie] submitting: model={args.model} prompt={args.prompt!r}")
    input_dict = build_input_for_model(
        args.model,
        prompt=args.prompt,
        aspect_ratio=args.aspect_ratio,
        quality=args.resolution,  # passed through directly; build_input_for_model handles it
    )
    result = client.submit_and_download(
        model=args.model,
        input_dict=input_dict,
        dest_path=Path(args.out),
    )
    print(f"[kie] success: task_id={result.task_id}")
    print(f"[kie] result_url={result.result_urls[0]}")
    print(f"[kie] local_path={result.local_path}")


if __name__ == "__main__":
    _smoke_test()
