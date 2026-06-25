"""Pydantic models for the music-studio domain.

Projects are the user's top-level container; every artifact lives under
`projects/<project-id>/…` in B2. Tracks form a revision tree via
`parent_track_id` — a regeneration / remix is a child node of the track it
branched from. Stems are per-track and currently a placeholder (see
`service/stems.py` for the stubbed split).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.types.library import AudioAsset

GenerationMode = Literal["create", "new_take", "extend", "restyle"]


class GenerationRequest(BaseModel):
    """A user-submitted generation request.

    Either kicks off the first track in a project or branches from an
    existing track (`parent_track_id` set).
    """

    prompt: str = Field(..., min_length=1, max_length=2000)
    style: str | None = Field(default=None, max_length=1000)
    negative_tags: str | None = Field(default=None, max_length=1000)
    make_instrumental: bool = False
    generation_mode: GenerationMode = "create"
    continue_at_sec: int | None = Field(default=None, ge=0, le=3600)
    audio_weight: float | None = Field(default=None, ge=0, le=1)
    duration_sec: int = Field(default=30, ge=5, le=300)
    parent_track_id: str | None = None


GenerationStatusName = Literal["queued", "running", "succeeded", "failed"]


class GenerationStatus(BaseModel):
    """Status snapshot for a generation job.

    The MVP runs generation synchronously inside the request (mock provider
    is instant; real providers will need a background worker), so the
    "running" state is brief. Modeled as its own type so the UI can poll a
    track-detail endpoint without special-casing the response shape.
    """

    track_id: str
    project_id: str
    state: GenerationStatusName
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class Stem(BaseModel):
    """A single stem (vocals/drums/bass/other) split out from a track.

    Stub-only in v1: nothing actually populates `audio` because
    `service/stems.py::split_stems` raises `NotImplementedError`. The shape
    is real so the UI can render an empty/disabled stems panel and so a
    future real implementation slots in without changing wire types.
    """

    stem_id: str
    track_id: str
    name: Literal["vocals", "drums", "bass", "other"]
    audio: AudioAsset | None = None


class TrackVariant(BaseModel):
    """Alternative take produced by the same generation job.

    Some music providers return N candidates per call; the primary candidate
    is the `Track` itself, additional candidates land here. Unused by
    `MusicApiProvider` today (the description-mode endpoint returns one
    track); the slot is reserved so a multi-candidate provider can fan
    out without a wire change.
    """

    variant_id: str
    track_id: str
    audio: AudioAsset
    notes: str | None = None


class Track(BaseModel):
    """A generated music track stored under
    `projects/<project-id>/tracks/<track-id>/audio.<ext>` in B2.

    Carries full provenance inline so a single `track.json` sidecar is
    enough to reconstruct the revision tree from B2 without a database.
    """

    track_id: str
    project_id: str
    prompt: str
    style: str | None = None
    negative_tags: str | None = None
    make_instrumental: bool = False
    generation_mode: GenerationMode = "create"
    continue_at_sec: int | None = None
    audio_weight: float | None = None
    duration_sec: int
    provider: str
    provider_task_id: str | None = None
    provider_clip_id: str | None = None
    parent_track_id: str | None = None
    generation_ms: int | None = None
    created_at: datetime
    audio: AudioAsset
    variants: list[TrackVariant] = Field(default_factory=list)
    stems_keys: list[str] = Field(default_factory=list)
    is_orphaned: bool = False


class Project(BaseModel):
    """A music-studio project — one prompt thread plus all its branches."""

    project_id: str
    name: str
    description: str | None = None
    created_at: datetime
    archived: bool = False
    track_count: int = 0
    owner_id: str | None = None
    shared_with: list[str] = Field(default_factory=list)


class ProjectManifest(BaseModel):
    """The `project.json` document stored at
    `projects/<project-id>/project.json`.

    Holds the project shell; tracks are listed separately so the manifest
    stays small (and updates are append-only — every new track writes a
    new `track.json` sidecar rather than rewriting `project.json`).
    """

    project: Project


class RevisionNode(BaseModel):
    """A node in the revision tree returned by
    `service/revisions.py::build_tree`. Recursively-typed via a forward
    reference because Pydantic v2 handles nested `list[RevisionNode]`
    cleanly.
    """

    track: Track
    # Forward reference resolved by model_rebuild() at module load.
    children: list[RevisionNode] = Field(default_factory=list)


class TrackDiff(BaseModel):
    """Side-by-side diff between two tracks, returned by
    `GET /projects/{id}/compare?a=...&b=...`."""

    a: Track
    b: Track
    prompt_changed: bool
    style_changed: bool
    negative_tags_changed: bool
    instrumental_changed: bool
    generation_mode_changed: bool
    continue_at_changed: bool
    audio_weight_changed: bool
    duration_changed: bool
    audio_metadata_changed: bool


# Resolve the forward reference on RevisionNode for runtime use.
RevisionNode.model_rebuild()
