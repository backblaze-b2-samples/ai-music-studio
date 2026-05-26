"""Project lifecycle service.

Project state lives entirely in B2: each project has a single
`projects/<id>/project.json` manifest, plus a tree of track artifacts
under the same prefix. No database — listing projects is a
`ListObjectsV2` with `Delimiter="/"`, loading a project is a single
`GetObject`.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from app.repo import (
    PROJECTS_PREFIX,
    delete_project_tree,
    get_json,
    list_project_keys,
    list_project_root_prefixes,
    put_json,
)
from app.types import Project, ProjectManifest

logger = logging.getLogger(__name__)

# UUID 4 in canonical lowercase. Project IDs are server-minted (clients
# never supply them), so we match strictly.
_PROJECT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class ProjectIdError(Exception):
    """Raised when a project id is malformed."""

    def __init__(self, detail: str = "Invalid project id"):
        self.detail = detail
        super().__init__(detail)


class ProjectNotFound(Exception):
    """Raised when no manifest exists at the requested project key."""

    def __init__(self, detail: str = "Project not found"):
        self.detail = detail
        super().__init__(detail)


def validate_project_id(project_id: str) -> None:
    if not project_id or not _PROJECT_ID_RE.match(project_id):
        raise ProjectIdError()


def manifest_key(project_id: str) -> str:
    return f"{PROJECTS_PREFIX}{project_id}/project.json"


def project_prefix(project_id: str) -> str:
    return f"{PROJECTS_PREFIX}{project_id}/"


def create_project(name: str, description: str | None = None) -> Project:
    """Create a new project and persist the manifest.

    The project id is a fresh UUID-4 minted server-side so clients never
    forge one. Manifest write failures bubble up as RuntimeError; the
    runtime layer translates that to a 500.
    """
    project = Project(
        project_id=str(uuid.uuid4()),
        name=name.strip() or "Untitled project",
        description=(description or "").strip() or None,
        created_at=datetime.now(UTC),
        archived=False,
        track_count=0,
    )
    manifest = ProjectManifest(project=project)
    put_json(manifest_key(project.project_id), manifest.model_dump(mode="json"))
    logger.info("Project created: id=%s name=%r", project.project_id, project.name)
    return project


def get_project(project_id: str) -> Project:
    validate_project_id(project_id)
    payload = get_json(manifest_key(project_id))
    if payload is None:
        raise ProjectNotFound()
    return ProjectManifest.model_validate(payload).project


def list_projects() -> list[Project]:
    """List every project by reading each manifest in parallel-ish order.

    `list_project_root_prefixes` returns `projects/<id>/` strings; for
    each we fetch `project.json`. The B2 round-trip count is the project
    count (no fan-out helper is added yet — `list_project_root_prefixes`
    bounds the result at 1000, which is plenty for a demo). A project
    with a missing manifest is skipped with a WARN log rather than 500'd
    — it's a leaked prefix and the UI shouldn't choke on it.
    """
    prefixes = list_project_root_prefixes()
    projects: list[Project] = []
    for prefix in prefixes:
        # prefix is "projects/<id>/" — extract <id>.
        project_id = prefix.removeprefix(PROJECTS_PREFIX).rstrip("/")
        if not _PROJECT_ID_RE.match(project_id):
            # Stray prefix that doesn't look like a UUID — log and skip.
            logger.warning("Skipping non-uuid project prefix: %s", prefix)
            continue
        payload = get_json(manifest_key(project_id))
        if payload is None:
            logger.warning("Project prefix %s has no manifest; skipping", prefix)
            continue
        try:
            projects.append(ProjectManifest.model_validate(payload).project)
        except Exception:
            logger.warning("Project %s has malformed manifest; skipping", project_id)
            continue
    # Newest-first for the UI's project list.
    projects.sort(key=lambda p: p.created_at, reverse=True)
    return projects


def archive_project(project_id: str) -> None:
    """Mark the project as archived but keep the artifacts.

    Mirrors a soft-delete UX where the user can recover. Hard-delete is
    `delete_project`. Both validate the id first.
    """
    validate_project_id(project_id)
    project = get_project(project_id)
    project.archived = True
    manifest = ProjectManifest(project=project)
    put_json(manifest_key(project_id), manifest.model_dump(mode="json"))
    logger.info("Project archived: id=%s", project_id)


def delete_project(project_id: str) -> tuple[list[str], list[dict]]:
    """Hard-delete a project and every artifact under its prefix.

    Returns `(deleted_keys, errors)` so partial failures surface in the
    UI. The manifest is part of the tree and gets nuked first by virtue
    of the list+batch-delete pattern.
    """
    validate_project_id(project_id)
    deleted, errors = delete_project_tree(project_id)
    logger.info(
        "Project deleted: id=%s deleted=%d errors=%d",
        project_id,
        len(deleted),
        len(errors),
    )
    return deleted, errors


def list_project_track_keys(project_id: str) -> list[str]:
    """Return the keys of every `track.json` under the project."""
    validate_project_id(project_id)
    prefix = f"{project_prefix(project_id)}tracks/"
    objects = list_project_keys(prefix, max_keys=10_000)
    return [o["Key"] for o in objects if o["Key"].endswith("/track.json")]
