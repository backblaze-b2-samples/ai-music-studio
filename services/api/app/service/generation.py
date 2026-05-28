"""Generation service — orchestrates provider call, B2 writes, sidecar.

Flow (synchronous):

  1. Validate request and project id.
  2. Call `get_provider().generate(...)` → returns audio bytes + provider
     metadata + a fresh track UUID.
  3. Upload the audio to
     `projects/<project-id>/tracks/<track-id>/audio.<ext>` via the repo
     layer, stamping S3 user metadata for duration/sample-rate/channels
     from `audio_metadata.extract_metadata`.
  4. Build a `Track` model and write its `track.json` sidecar.
  5. Return the `Track` (the runtime layer wraps it in a 200 response).

The whole thing is synchronous — the MusicApi provider polls upstream
internally and can take 1-3 min, which blocks the FastAPI request that
whole time. Moving generation to a background worker is tracked in
`docs/exec-plans/tech-debt-tracker.md`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.config import settings
from app.repo import upload_file
from app.repo.b2_projects import put_json
from app.repo.music_provider import GenerationResult, MusicProvider, get_provider
from app.service.audio_metadata import extract_metadata, to_s3_metadata
from app.service.projects import (
    ProjectNotFound,
    get_project,
    manifest_key,
    project_prefix,
    validate_project_id,
)
from app.service.revisions import TrackNotFound, get_track
from app.types import (
    AudioAsset,
    GenerationRequest,
    ProjectManifest,
    Track,
)
from app.types.formatting import humanize_bytes

# Pydantic field defaults must be literal-or-callable, so `GenerationRequest.
# duration_sec` keeps its `Field(default=30, …)` shape (the literal `30`
# stays as the floor). The env-driven override
# (`MUSIC_PROVIDER_DEFAULT_DURATION_SEC`) is applied here at the orchestrator
# level: if the inbound request's duration equals the Pydantic default,
# we swap in the settings value before calling the provider.
_GENERATION_REQUEST_FIELD_DEFAULT_DURATION_SEC = 30
_RESTYLE_DEFAULT_AUDIO_WEIGHT = 0.6

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when generation orchestration fails before/around the provider call."""

    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _track_audio_key(project_id: str, track_id: str, ext: str) -> str:
    return f"{project_prefix(project_id)}tracks/{track_id}/audio.{ext}"


def _track_sidecar_key(project_id: str, track_id: str) -> str:
    return f"{project_prefix(project_id)}tracks/{track_id}/track.json"


def _content_type_for(ext: str) -> str:
    ext = ext.lower()
    if ext == "wav":
        return "audio/wav"
    if ext == "mp3":
        return "audio/mpeg"
    if ext == "flac":
        return "audio/flac"
    if ext == "ogg":
        return "audio/ogg"
    if ext == "m4a":
        return "audio/m4a"
    return "application/octet-stream"


def _default_continue_at_sec(parent: Track | None) -> int:
    if parent and parent.audio.duration_ms:
        return max(0, round(parent.audio.duration_ms / 1000))
    return 0


def _resolve_generation_context(
    project_id: str,
    request: GenerationRequest,
) -> tuple[str, Track | None, str | None, int | None, float | None]:
    mode = request.generation_mode
    if request.parent_track_id and mode == "create":
        mode = "new_take"
    if mode != "create" and not request.parent_track_id:
        raise GenerationError(f"{mode} requires a parent track", status_code=400)

    parent: Track | None = None
    if request.parent_track_id:
        try:
            parent = get_track(project_id, request.parent_track_id)
        except TrackNotFound as e:
            raise GenerationError(e.detail, status_code=404) from e

    parent_clip_id: str | None = None
    if mode in {"extend", "restyle"}:
        parent_clip_id = parent.provider_clip_id if parent else None
        if not parent_clip_id:
            raise GenerationError(
                "Parent track has no provider clip id; generate a fresh MusicAPI "
                "track before using Extend or Restyle.",
                status_code=400,
            )

    continue_at = None
    if mode == "extend":
        continue_at = (
            request.continue_at_sec
            if request.continue_at_sec is not None
            else _default_continue_at_sec(parent)
        )

    audio_weight = None
    if mode == "restyle":
        audio_weight = (
            request.audio_weight
            if request.audio_weight is not None
            else _RESTYLE_DEFAULT_AUDIO_WEIGHT
        )
    return mode, parent, parent_clip_id, continue_at, audio_weight


def _increment_track_count(project_id: str) -> None:
    """Bump `track_count` on the manifest. Best-effort — a write failure
    here doesn't invalidate the just-written track; we log and move on."""
    try:
        project = get_project(project_id)
    except ProjectNotFound:
        logger.warning("Track count bump skipped: project %s missing", project_id)
        return
    project.track_count += 1
    manifest = ProjectManifest(project=project)
    try:
        put_json(manifest_key(project_id), manifest.model_dump(mode="json"))
    except RuntimeError:
        logger.warning(
            "Track count bump failed for project %s (non-fatal)", project_id
        )


def generate_track(
    project_id: str,
    request: GenerationRequest,
    provider: MusicProvider | None = None,
    track_id: str | None = None,
) -> Track:
    """Run a generation request end-to-end and return the persisted Track.

    `provider` is an injection seam for tests; production callers leave
    it unset and `get_provider()` reads `MUSIC_PROVIDER`.
    """
    validate_project_id(project_id)
    # Existence check — raises ProjectNotFound (translated to 404 by the
    # runtime layer) so generation can't write into a nonexistent prefix.
    _ = get_project(project_id)

    selected = provider or get_provider()

    # Honor MUSIC_PROVIDER_DEFAULT_DURATION_SEC when the client didn't
    # specify a duration. Pydantic populated the field with its literal
    # default (30); if the value still equals that literal, prefer the
    # settings value so operators can change the studio's default without
    # editing source.
    duration_sec = request.duration_sec
    if duration_sec == _GENERATION_REQUEST_FIELD_DEFAULT_DURATION_SEC:
        duration_sec = settings.music_provider_default_duration_sec
    mode, _parent, parent_clip_id, continue_at_sec, audio_weight = (
        _resolve_generation_context(project_id, request)
    )

    started = datetime.now(UTC)
    try:
        result: GenerationResult = selected.generate(
            prompt=request.prompt,
            style=request.style,
            negative_tags=request.negative_tags,
            make_instrumental=request.make_instrumental,
            generation_mode=mode,
            parent_provider_clip_id=parent_clip_id,
            continue_at_sec=continue_at_sec,
            audio_weight=audio_weight,
            duration_sec=duration_sec,
        )
    except NotImplementedError as e:
        raise GenerationError(str(e), status_code=501) from e
    except Exception as e:
        logger.exception("Provider %s failed", selected.name)
        raise GenerationError(f"Provider error: {e}", status_code=502) from e

    resolved_track_id = track_id or result.track_id
    audio_key = _track_audio_key(project_id, resolved_track_id, result.audio_ext)
    content_type = _content_type_for(result.audio_ext)

    # Extract metadata BEFORE the put so we can stamp duration/etc onto
    # the B2 object — same pattern as the Upload pipeline. A failure here
    # is non-fatal; the track will simply lack the optional fields.
    detail = extract_metadata(result.audio_bytes, f"audio.{result.audio_ext}", content_type)
    s3_meta = to_s3_metadata(detail)
    # Stamp the parent track id so the revision tree is still
    # reconstructible if `track.json` is ever lost (defense in depth).
    if request.parent_track_id:
        s3_meta["parent-track-id"] = request.parent_track_id
    if request.negative_tags:
        s3_meta["negative-tags"] = request.negative_tags
    if request.make_instrumental:
        s3_meta["make-instrumental"] = "true"
    s3_meta["generation-mode"] = mode
    if continue_at_sec is not None:
        s3_meta["continue-at-sec"] = str(continue_at_sec)
    if audio_weight is not None:
        s3_meta["audio-weight"] = str(audio_weight)
    if result.provider_task_id:
        s3_meta["provider-task-id"] = result.provider_task_id
    if result.provider_clip_id:
        s3_meta["provider-clip-id"] = result.provider_clip_id
    s3_meta["project-id"] = project_id
    s3_meta["provider"] = selected.name

    upload_file(
        result.audio_bytes,
        audio_key,
        content_type,
        metadata=s3_meta or None,
    )

    audio_asset = AudioAsset(
        key=audio_key,
        size_bytes=len(result.audio_bytes),
        size_human=humanize_bytes(len(result.audio_bytes)),
        content_type=content_type,
        created_at=started,
        duration_ms=detail.duration_ms,
        sample_rate=detail.sample_rate,
        channels=detail.channels,
        bit_depth=detail.bit_depth,
        codec=detail.codec,
        title_preview=f"track-{resolved_track_id[:8]}.{result.audio_ext}",
        project_id=project_id,
        track_id=resolved_track_id,
        source="project",
    )

    track = Track(
        track_id=resolved_track_id,
        project_id=project_id,
        prompt=request.prompt,
        style=request.style,
        negative_tags=request.negative_tags,
        make_instrumental=request.make_instrumental,
        generation_mode=mode,
        continue_at_sec=continue_at_sec,
        audio_weight=audio_weight,
        duration_sec=duration_sec,
        provider=selected.name,
        provider_task_id=result.provider_task_id,
        provider_clip_id=result.provider_clip_id,
        parent_track_id=request.parent_track_id,
        generation_ms=result.generation_ms,
        created_at=started,
        audio=audio_asset,
    )

    # Write the per-track sidecar last — its presence is what makes the
    # track "discoverable" by the revision-tree builder.
    put_json(_track_sidecar_key(project_id, resolved_track_id), track.model_dump(mode="json"))

    _increment_track_count(project_id)

    logger.info(
        "Track generated: project=%s track=%s provider=%s parent=%s gen_ms=%s",
        project_id,
        resolved_track_id,
        selected.name,
        request.parent_track_id,
        result.generation_ms,
    )
    return track
