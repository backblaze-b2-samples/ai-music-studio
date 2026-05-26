"""FastAPI routes for the revision tree + side-by-side compare."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.service.projects import (
    ProjectIdError,
    ProjectNotFound,
    get_project,
)
from app.service.revisions import (
    TrackNotFound,
    build_tree,
    diff_tracks,
    get_track,
)
from app.types import RevisionNode, TrackDiff

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/projects/{project_id}/revisions",
    response_model=list[RevisionNode],
)
async def revisions_endpoint(project_id: str):
    try:
        _ = get_project(project_id)
        return build_tree(project_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/projects/{project_id}/compare", response_model=TrackDiff)
async def compare_endpoint(
    project_id: str,
    a: str = Query(..., description="Track A id"),
    b: str = Query(..., description="Track B id"),
):
    if a == b:
        raise HTTPException(
            status_code=400, detail="Cannot compare a track with itself"
        )
    try:
        _ = get_project(project_id)
        track_a = get_track(project_id, a)
        track_b = get_track(project_id, b)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return diff_tracks(track_a, track_b)
