"""Revision-tree service.

A project's tracks form a tree via `parent_track_id`. The whole tree is
reconstructed each call by listing every `track.json` sidecar under the
project prefix and threading them by parent id. Bounded by the project's
track count; for the demo's expected volume this is cheap.

`diff_tracks` produces a side-by-side `TrackDiff` for the compare UI.
"""

from __future__ import annotations

import logging

from app.repo import get_json
from app.service.projects import (
    list_project_track_keys,
    validate_project_id,
)
from app.types import RevisionNode, Track, TrackDiff

logger = logging.getLogger(__name__)


class TrackNotFound(Exception):
    """Raised when a requested track sidecar is missing."""

    def __init__(self, detail: str = "Track not found"):
        self.detail = detail
        super().__init__(detail)


def _load_tracks(project_id: str) -> list[Track]:
    """Load every `track.json` under the project, skip malformed ones."""
    validate_project_id(project_id)
    keys = list_project_track_keys(project_id)
    tracks: list[Track] = []
    for key in keys:
        payload = get_json(key)
        if payload is None:
            logger.warning("Sidecar missing at %s; skipping", key)
            continue
        try:
            tracks.append(Track.model_validate(payload))
        except Exception:
            logger.warning("Sidecar malformed at %s; skipping", key)
            continue
    return tracks


def build_tree(project_id: str) -> list[RevisionNode]:
    """Build the project's revision tree.

    Returns a list of top-level roots (a project can have multiple
    independent root prompts; the UI typically renders the newest root
    first). Each root recursively contains its children sorted oldest-
    first so the timeline reads left-to-right.
    """
    tracks = _load_tracks(project_id)
    by_id: dict[str, Track] = {t.track_id: t for t in tracks}
    children_of: dict[str | None, list[Track]] = {}
    for t in tracks:
        children_of.setdefault(t.parent_track_id, []).append(t)
    for parent_id in children_of:
        children_of[parent_id].sort(key=lambda x: x.created_at)

    def make_node(track: Track) -> RevisionNode:
        kids = [make_node(c) for c in children_of.get(track.track_id, [])]
        return RevisionNode(track=track, children=kids)

    # Root = parent_track_id is None OR points at an unknown track (orphan).
    roots: list[Track] = []
    for t in tracks:
        if t.parent_track_id is None or t.parent_track_id not in by_id:
            roots.append(t)
    roots.sort(key=lambda x: x.created_at, reverse=True)
    return [make_node(r) for r in roots]


def get_track(project_id: str, track_id: str) -> Track:
    """Load a single track by id (404 if its sidecar is missing)."""
    tracks = _load_tracks(project_id)
    for t in tracks:
        if t.track_id == track_id:
            return t
    raise TrackNotFound()


def diff_tracks(a: Track, b: Track) -> TrackDiff:
    """Return a structural diff between two tracks for the compare UI."""
    prompt_changed = a.prompt != b.prompt
    style_changed = (a.style or "") != (b.style or "")
    duration_changed = a.duration_sec != b.duration_sec
    audio_meta_changed = (
        a.audio.duration_ms != b.audio.duration_ms
        or a.audio.sample_rate != b.audio.sample_rate
        or a.audio.channels != b.audio.channels
        or a.audio.bit_depth != b.audio.bit_depth
        or a.audio.codec != b.audio.codec
    )
    return TrackDiff(
        a=a,
        b=b,
        prompt_changed=prompt_changed,
        style_changed=style_changed,
        duration_changed=duration_changed,
        audio_metadata_changed=audio_meta_changed,
    )
