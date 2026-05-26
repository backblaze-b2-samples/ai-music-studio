"""Music-generation provider abstraction.

Defines a single `MusicProvider` protocol with two concrete implementations:

- `MockMusicProvider` — returns a pre-baked WAV from
  `repo/_mock_tracks/`. Selected when `MUSIC_PROVIDER=mock` (default), so
  the sample is runnable end-to-end with zero external credentials.
- `SunoMusicProvider` — stub. `generate()` raises `NotImplementedError`;
  the docstring points at where the real Suno API call goes.

Architectural invariant (AGENTS.md §2): **this module is the only place
in the codebase allowed to make a real generation API call.** Service
code goes through `get_provider()`, never reaches into providers
directly, and never imports `requests` / `httpx` to call a generation
API from elsewhere. Mirrors the "boto3 only in repo/" rule.

The mock provider's pre-baked WAVs are generated at scaffold time by
the build script (stdlib `wave`) so the implementation is deterministic
and reproducible — no external audio is ever sourced.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MOCK_TRACKS_DIR = Path(__file__).resolve().parent / "_mock_tracks"


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


class MusicProvider(ABC):
    """Interface every music provider implements.

    `generate()` is synchronous from the service's point of view. Real
    providers that need polling (Suno typically takes 30-90 s) can poll
    internally — the boundary between "fast and synchronous" and "slow
    and pollable" should be hidden behind this method so the service
    layer stays simple.
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        style: str | None = None,
        duration_sec: int = 30,
        **_kwargs: object,
    ) -> GenerationResult:
        """Generate a track and return its bytes + metadata."""


class MockMusicProvider(MusicProvider):
    """In-the-box mock provider.

    Loads one of the pre-baked WAVs in `_mock_tracks/` based on prompt
    keywords (from `manifest.json`). Falls back to a stable random pick
    if no keyword matches. Pretends to take 500 ms-3 s to "generate" so
    the UI's loading state has something to render.
    """

    name = "mock"

    def __init__(self, tracks_dir: Path | None = None):
        self.tracks_dir = tracks_dir or MOCK_TRACKS_DIR
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        manifest_path = self.tracks_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning("Mock provider: manifest.json missing at %s", manifest_path)
            return {}
        try:
            return json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            logger.warning("Mock provider: manifest.json is malformed")
            return {}

    def _pick_file(self, prompt: str) -> Path:
        """Pick a mock track based on prompt keywords.

        The manifest maps a list of keywords to a filename. First keyword
        hit wins. If no keyword matches, deterministically rotate through
        the available files keyed on the prompt hash so repeat prompts
        return the same track (developer-friendly while playing with the
        UI).
        """
        text = prompt.lower()
        entries = self._manifest.get("entries", [])
        for entry in entries:
            keywords = [k.lower() for k in entry.get("keywords", [])]
            filename = entry.get("file")
            if not filename:
                continue
            if any(k in text for k in keywords):
                return self.tracks_dir / filename
        # No keyword hit — pick deterministically based on prompt hash.
        files = sorted(
            f.name for f in self.tracks_dir.iterdir() if f.suffix.lower() == ".wav"
        )
        if not files:
            raise RuntimeError(
                f"MockMusicProvider has no .wav files in {self.tracks_dir}"
            )
        idx = hash(prompt) % len(files)
        return self.tracks_dir / files[idx]

    def generate(
        self,
        prompt: str,
        style: str | None = None,
        duration_sec: int = 30,
        **_kwargs: object,
    ) -> GenerationResult:
        # Small jitter so the UI's "generating..." state is observable;
        # short enough that demo flows still feel snappy. Random within
        # [0.4, 1.2)s — caps the worst-case API latency well under the
        # FastAPI default request timeout.
        delay = 0.4 + random.random() * 0.8
        time.sleep(delay)

        path = self._pick_file(prompt)
        try:
            audio_bytes = path.read_bytes()
        except OSError as e:
            raise RuntimeError(f"Mock track {path} unreadable: {e}") from e

        return GenerationResult(
            track_id=str(uuid.uuid4()),
            audio_bytes=audio_bytes,
            audio_ext=path.suffix.lstrip(".") or "wav",
            provider=self.name,
            generation_ms=round(delay * 1000),
            notes=f"mock: {path.name}",
        )


class SunoMusicProvider(MusicProvider):
    """Suno provider — stub.

    Real implementation slots in here:

      1. Read `SUNO_API_KEY` from settings (already declared in `.env.example`).
      2. POST to Suno's generate endpoint with prompt/style/duration.
      3. Poll the job-status endpoint until `completed` (typical 30-90 s).
      4. Download the final mp3, return its bytes + a fresh UUID.

    Listed under tech debt (`docs/exec-plans/tech-debt-tracker.md`). Until
    that lands, instantiating this provider and calling `generate()`
    raises so the failure mode is loud and obvious.
    """

    name = "suno"

    def generate(
        self,
        prompt: str,
        style: str | None = None,
        duration_sec: int = 30,
        **_kwargs: object,
    ) -> GenerationResult:
        raise NotImplementedError(
            "SunoMusicProvider is not yet wired up. Set MUSIC_PROVIDER=mock "
            "or implement the real Suno API call here. See "
            "docs/exec-plans/tech-debt-tracker.md for context."
        )


def get_provider(name: str | None = None) -> MusicProvider:
    """Return the configured provider implementation.

    `name` overrides the env-var selection; falls back to `MUSIC_PROVIDER`
    (default `mock`). Unknown names raise so a typo'd env var fails fast
    rather than silently degrading.
    """
    selected = (name or os.environ.get("MUSIC_PROVIDER", "mock")).lower()
    if selected == "mock":
        return MockMusicProvider()
    if selected == "suno":
        return SunoMusicProvider()
    raise ValueError(
        f"Unknown MUSIC_PROVIDER '{selected}' — supported: 'mock', 'suno'"
    )
