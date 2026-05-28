"""In-process generation queue with B2-backed status snapshots."""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from app.repo import get_json, put_json
from app.service.generation import GenerationError, generate_track
from app.service.projects import get_project, project_prefix, validate_project_id
from app.service.revisions import TrackNotFound, get_track
from app.types import GenerationRequest, GenerationStatus

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="generation")


class GenerationJobNotFound(Exception):
    def __init__(self, detail: str = "Generation job not found"):
        self.detail = detail
        super().__init__(detail)


def _status_key(project_id: str, track_id: str) -> str:
    return f"{project_prefix(project_id)}generations/{track_id}.json"


def _write_status(status: GenerationStatus) -> None:
    put_json(_status_key(status.project_id, status.track_id), status.model_dump(mode="json"))


def enqueue_generation(
    project_id: str,
    request: GenerationRequest,
    user_id: str | None = None,
) -> GenerationStatus:
    """Queue generation work and return a pollable status immediately."""
    validate_project_id(project_id)
    _ = get_project(project_id, user_id)
    track_id = str(uuid.uuid4())
    status = GenerationStatus(
        track_id=track_id,
        project_id=project_id,
        state="queued",
        started_at=datetime.now(UTC),
    )
    _write_status(status)
    _executor.submit(_run_generation, project_id, track_id, request)
    return status


def _run_generation(project_id: str, track_id: str, request: GenerationRequest) -> None:
    running = GenerationStatus(
        track_id=track_id,
        project_id=project_id,
        state="running",
        started_at=datetime.now(UTC),
    )
    try:
        _write_status(running)
        generate_track(project_id, request, track_id=track_id)
    except GenerationError as e:
        logger.warning("Generation failed: project=%s track=%s %s", project_id, track_id, e.detail)
        _write_status(
            running.model_copy(
                update={
                    "state": "failed",
                    "finished_at": datetime.now(UTC),
                    "error": e.detail,
                }
            )
        )
    except Exception as e:
        logger.exception("Generation worker crashed: project=%s track=%s", project_id, track_id)
        _write_status(
            running.model_copy(
                update={
                    "state": "failed",
                    "finished_at": datetime.now(UTC),
                    "error": str(e),
                }
            )
        )
    else:
        _write_status(
            running.model_copy(
                update={"state": "succeeded", "finished_at": datetime.now(UTC)}
            )
        )


def get_generation_status(project_id: str, track_id: str) -> GenerationStatus:
    validate_project_id(project_id)
    payload = get_json(_status_key(project_id, track_id))
    if payload is not None:
        return GenerationStatus.model_validate(payload)
    try:
        track = get_track(project_id, track_id)
    except TrackNotFound as e:
        raise GenerationJobNotFound() from e
    return GenerationStatus(
        track_id=track.track_id,
        project_id=project_id,
        state="succeeded",
        started_at=track.created_at,
        finished_at=track.created_at,
    )
