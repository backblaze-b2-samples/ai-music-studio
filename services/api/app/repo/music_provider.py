"""Music-generation provider abstraction.

This is the only module allowed to call generation APIs. `MusicApiProvider`
wraps MusicAPI's Sonic endpoints and hides task creation, polling, and
audio download behind the synchronous `MusicProvider.generate()` boundary.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.repo.musicapi_helpers import (
    build_musicapi_payload,
    raise_musicapi_for_status,
)

logger = logging.getLogger(__name__)

MUSICAPI_BASE_URL = "https://api.musicapi.ai"
MUSICAPI_CREATE_PATH = "/api/v1/sonic/create"
MUSICAPI_TASK_PATH = "/api/v1/sonic/task/{task_id}"

# Default Sonic model — Suno-compatible. Bump as MusicAPI ships newer
# revisions; older mv strings keep working so this is safe to change.
MUSICAPI_DEFAULT_MV = "sonic-v4-5"

# Polling tuned for MusicAPI's typical job latency (1-3 min). Caps the
# total wait at ~5 min so a stuck job surfaces as a clean 502 instead
# of hanging the FastAPI request indefinitely.
POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 300


@dataclass
class GenerationResult:
    """What a provider returns to the service layer.

    Service code then writes `audio_bytes` to B2 under
    `projects/<id>/tracks/<track-id>/audio.<ext>` and stamps `track.json`.
    """

    track_id: str
    audio_bytes: bytes
    audio_ext: str  # e.g. "wav", "mp3"
    provider: str
    generation_ms: int
    notes: str | None = None
    provider_task_id: str | None = None
    provider_clip_id: str | None = None


class MusicProvider(ABC):
    """Interface every music provider implements.

    `generate()` is synchronous from the service's point of view. Real
    providers that need polling (typical music gen takes 60-180 s) poll
    internally — the boundary between "fast and synchronous" and "slow
    and pollable" is hidden behind this method so the service layer
    stays simple.
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        style: str | None = None,
        negative_tags: str | None = None,
        make_instrumental: bool = False,
        generation_mode: str = "create",
        parent_provider_clip_id: str | None = None,
        continue_at_sec: int | None = None,
        audio_weight: float | None = None,
        duration_sec: int = 30,
        **_kwargs: object,
    ) -> GenerationResult:
        """Generate a track and return its bytes + metadata."""


class MusicApiProvider(MusicProvider):
    """musicapi.ai Sonic provider."""

    name = "musicapi"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        # Late import keeps this module decoupled from settings at import
        # time so tests can instantiate a provider with an explicit key
        # without touching the environment.
        from app.config import settings

        key = api_key if api_key is not None else settings.musicapi_api_key
        if not key:
            raise RuntimeError(
                "MUSICAPI_API_KEY required when MUSIC_PROVIDER=musicapi. "
                "Sign up at https://musicapi.ai to get a free key and set "
                "it in .env."
            )
        self.api_key = key
        self.base_url = (base_url or MUSICAPI_BASE_URL).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        prompt: str,
        style: str | None,
        negative_tags: str | None,
        make_instrumental: bool,
        generation_mode: str = "create",
        parent_provider_clip_id: str | None = None,
        continue_at_sec: int | None = None,
        audio_weight: float | None = None,
    ) -> dict:
        """Build the create-task body.

        Uses MusicAPI's "AI description" mode (`custom_mode=false`) so a
        single free-text prompt is enough — the model handles lyric
        structure, title, and style internally. If the caller supplied a
        `style`, we prepend it to the prompt so it influences the
        generation (the description-mode endpoint doesn't take a
        separate `tags` field).
        """
        return build_musicapi_payload(
            prompt=prompt,
            style=style,
            negative_tags=negative_tags,
            make_instrumental=make_instrumental,
            generation_mode=generation_mode,
            parent_provider_clip_id=parent_provider_clip_id,
            continue_at_sec=continue_at_sec,
            audio_weight=audio_weight,
            default_mv=MUSICAPI_DEFAULT_MV,
        )

    def _unwrap_data(self, body: dict) -> dict:
        """Normalize MusicAPI response shapes.

        MusicAPI responses can put task fields in `data` (as an object or
        candidate list) or directly on the response body. Return the most
        useful object so callers don't have to branch on every endpoint.
        """
        data = body.get("data")
        if isinstance(data, list):
            first = data[0] if data else {}
            return first if isinstance(first, dict) else {}
        if isinstance(data, dict):
            return data
        return body

    def _create_task(self, client: httpx.Client, payload: dict) -> str:
        resp = client.post(
            self.base_url + MUSICAPI_CREATE_PATH,
            json=payload,
            headers=self._headers(),
            timeout=30.0,
        )
        raise_musicapi_for_status(resp, "task creation")
        body = resp.json()
        code = body.get("code")
        if code not in (None, 0, 200):
            raise RuntimeError(
                f"MusicAPI create failed: code={body.get('code')} "
                f"message={body.get('message')}"
            )
        task_id = self._unwrap_data(body).get("task_id")
        if not task_id:
            raise RuntimeError(f"MusicAPI create response missing task_id: {body}")
        return task_id

    def _poll_task(self, client: httpx.Client, task_id: str) -> dict:
        """Poll until `state == "succeeded"`, returning the final task
        body. Raises on `"failed"` or after `POLL_TIMEOUT_SEC`."""
        url = self.base_url + MUSICAPI_TASK_PATH.format(task_id=task_id)
        deadline = time.monotonic() + POLL_TIMEOUT_SEC
        last_state = "pending"
        while time.monotonic() < deadline:
            resp = client.get(url, headers=self._headers(), timeout=30.0)
            raise_musicapi_for_status(resp, "task polling")
            body = resp.json()
            data = self._unwrap_data(body)
            state = (data.get("state") or "").lower()
            if state != last_state:
                logger.info(
                    "MusicAPI task %s state=%s", task_id, state or "unknown"
                )
                last_state = state
            if state == "succeeded":
                return data
            if state == "failed":
                raise RuntimeError(
                    f"MusicAPI task {task_id} failed: "
                    f"{data.get('error') or data.get('message') or 'no detail'}"
                )
            time.sleep(POLL_INTERVAL_SEC)
        raise TimeoutError(
            f"MusicAPI task {task_id} did not complete within "
            f"{POLL_TIMEOUT_SEC}s (last state: {last_state})"
        )

    def _download_audio(self, client: httpx.Client, audio_url: str) -> bytes:
        resp = client.get(audio_url, timeout=60.0)
        raise_musicapi_for_status(resp, "audio download")
        return resp.content

    def generate(
        self,
        prompt: str,
        style: str | None = None,
        negative_tags: str | None = None,
        make_instrumental: bool = False,
        generation_mode: str = "create",
        parent_provider_clip_id: str | None = None,
        continue_at_sec: int | None = None,
        audio_weight: float | None = None,
        duration_sec: int = 30,
        **_kwargs: object,
    ) -> GenerationResult:
        started = time.monotonic()
        payload = self._build_payload(
            prompt,
            style,
            negative_tags,
            make_instrumental,
            generation_mode,
            parent_provider_clip_id,
            continue_at_sec,
            audio_weight,
        )
        with httpx.Client() as client:
            task_id = self._create_task(client, payload)
            logger.info("MusicAPI task created: %s", task_id)
            data = self._poll_task(client, task_id)
            audio_url = data.get("mp3_url") or data.get("audio_url")
            if not audio_url:
                raise RuntimeError(
                    f"MusicAPI task {task_id} succeeded without an audio url: {data}"
                )
            audio_bytes = self._download_audio(client, audio_url)

        return GenerationResult(
            track_id=str(uuid.uuid4()),
            audio_bytes=audio_bytes,
            audio_ext="mp3",
            provider=self.name,
            generation_ms=round((time.monotonic() - started) * 1000),
            notes=f"musicapi task={task_id}",
            provider_task_id=task_id,
            provider_clip_id=data.get("clip_id"),
        )


def get_provider(name: str | None = None) -> MusicProvider:
    """Return the configured provider implementation.

    `name` overrides the env-var selection; falls back to
    `settings.music_provider` (default `musicapi`). Unknown names raise
    so a typo'd env var fails fast rather than silently degrading.
    """
    from app.config import settings

    selected = (name or settings.music_provider or "musicapi").lower()
    if selected == "musicapi":
        return MusicApiProvider()
    raise ValueError(
        f"Unknown MUSIC_PROVIDER '{selected}' — supported: 'musicapi'"
    )
