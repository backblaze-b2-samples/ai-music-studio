"""FastAPI routes for music generation + per-track playback/download."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.repo import (
    get_presigned_url,
    presign_track_playback,
)
from app.repo.b2_projects import get_json
from app.runtime.auth import UserContext, require_user
from app.service.generation_jobs import (
    GenerationJobNotFound,
    enqueue_generation,
    get_generation_status,
)
from app.service.projects import (
    ProjectIdError,
    ProjectNotFound,
    get_project,
    project_prefix,
    validate_project_id,
)
from app.service.rate_limit import RateLimitExceeded, check_generation_rate_limit
from app.service.revisions import TrackNotFound, get_track
from app.types import GenerationRequest, GenerationStatus, Track

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects/{project_id}/generate", response_model=GenerationStatus)
async def generate_endpoint(
    project_id: str,
    body: GenerationRequest,
    request: Request,
    user: UserContext = Depends(require_user),
):
    try:
        client_id = request.client.host if request.client else "unknown"
        check_generation_rate_limit(client_id)
        return enqueue_generation(project_id, body, user.user_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail="Too many generation requests",
            headers={"Retry-After": str(e.retry_after)},
        ) from None


@router.get(
    "/projects/{project_id}/generations/{track_id}",
    response_model=GenerationStatus,
)
async def generation_status_endpoint(
    project_id: str,
    track_id: str,
    _user: UserContext = Depends(require_user),
):
    try:
        _ = get_project(project_id, _user.user_id)
        return get_generation_status(project_id, track_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except GenerationJobNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/projects/{project_id}/tracks/{track_id}", response_model=Track)
async def get_track_endpoint(
    project_id: str,
    track_id: str,
    user: UserContext = Depends(require_user),
):
    try:
        # Existence check on the project first so we 404 the right thing.
        _ = get_project(project_id, user.user_id)
        return get_track(project_id, track_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


def _track_audio_key_from_sidecar(project_id: str, track_id: str) -> str:
    """Read the audio key out of the sidecar.

    The audio extension isn't fixed (mock returns .wav, real provider may
    return .mp3), so we can't reconstruct the key from id alone — we
    look it up in `track.json`.
    """
    validate_project_id(project_id)
    sidecar_key = f"{project_prefix(project_id)}tracks/{track_id}/track.json"
    payload = get_json(sidecar_key)
    if payload is None:
        return get_track(project_id, track_id).audio.key
    audio = payload.get("audio") or {}
    key = audio.get("key")
    if not key:
        raise TrackNotFound("Track sidecar has no audio key")
    return key


@router.get("/projects/{project_id}/tracks/{track_id}/playback")
async def playback_endpoint(
    project_id: str,
    track_id: str,
    user: UserContext = Depends(require_user),
):
    try:
        _ = get_project(project_id, user.user_id)
        audio_key = _track_audio_key_from_sidecar(project_id, track_id)
        url = presign_track_playback(audio_key)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}


@router.get("/projects/{project_id}/tracks/{track_id}/download")
async def download_endpoint(
    project_id: str,
    track_id: str,
    user: UserContext = Depends(require_user),
):
    try:
        _ = get_project(project_id, user.user_id)
        audio_key = _track_audio_key_from_sidecar(project_id, track_id)
        # Use the generic presign helper to get `Content-Disposition: attachment`.
        filename = audio_key.rsplit("/", 1)[-1]
        url = get_presigned_url(audio_key, filename=filename)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}
