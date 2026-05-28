"""FastAPI routes for track stems."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.runtime.auth import UserContext, require_user
from app.service.projects import ProjectIdError, ProjectNotFound, get_project
from app.service.revisions import TrackNotFound
from app.service.stems import (
    StemSplitError,
    StemSplitUnavailable,
    list_stems,
    split_stems,
)
from app.types import Stem

router = APIRouter()


@router.get("/projects/{project_id}/tracks/{track_id}/stems", response_model=list[Stem])
async def list_stems_endpoint(
    project_id: str,
    track_id: str,
    user: UserContext = Depends(require_user),
):
    try:
        _ = get_project(project_id, user.user_id)
        return list_stems(project_id, track_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/projects/{project_id}/tracks/{track_id}/stems", response_model=list[Stem])
async def split_stems_endpoint(
    project_id: str,
    track_id: str,
    user: UserContext = Depends(require_user),
):
    try:
        _ = get_project(project_id, user.user_id)
        return split_stems(project_id, track_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except (ProjectNotFound, TrackNotFound) as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except StemSplitUnavailable as e:
        raise HTTPException(status_code=501, detail=e.detail) from None
    except StemSplitError as e:
        raise HTTPException(status_code=502, detail=e.detail) from None
