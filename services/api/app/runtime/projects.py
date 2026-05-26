"""FastAPI routes for project lifecycle: list / create / get / delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.service.projects import (
    ProjectIdError,
    ProjectNotFound,
    create_project,
    delete_project,
    get_project,
    list_projects,
)
from app.types import Project

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)


@router.get("/projects", response_model=list[Project])
async def list_projects_endpoint():
    return list_projects()


@router.post("/projects", response_model=Project)
async def create_project_endpoint(body: CreateProjectRequest):
    project = create_project(name=body.name, description=body.description)
    return project


@router.get("/projects/{project_id}", response_model=Project)
async def get_project_endpoint(project_id: str):
    try:
        return get_project(project_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    try:
        deleted, errors = delete_project(project_id)
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(
            status_code=500, detail="Failed to delete project"
        ) from None
    return {"deleted": deleted, "errors": errors}
