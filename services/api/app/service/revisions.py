"""Revision-tree service.

A project's tracks form a tree via `parent_track_id`. The whole tree is
reconstructed each call by listing every `track.json` sidecar under the
project prefix and threading them by parent id. Bounded by the project's
track count; for the demo's expected volume this is cheap.

`diff_tracks` produces a side-by-side `TrackDiff` for the compare UI.
"""

from __future__ import annotations

import logging

from app.repo import get_json, head_track_objects_parallel, list_project_keys, put_json
from app.service.library import PROJECT_TRACK_AUDIO_RE, audio_asset_from_object
from app.service.projects import (
    list_project_track_keys,
    project_prefix,
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


def _mode_from_meta(value: str | None) -> str:
    return value if value in {"create", "new_take", "extend", "restyle"} else "create"


def _orphan_track_from_object(project_id: str, obj: dict, head: dict | None) -> Track:
    match = PROJECT_TRACK_AUDIO_RE.match(obj["Key"])
    if not match:
        raise TrackNotFound("Audio object is not a project track")
    meta = (head or {}).get("Metadata") or {}
    audio = audio_asset_from_object(obj, head)
    duration_sec = round(audio.duration_ms / 1000) if audio.duration_ms else 0
    return Track(
        track_id=match.group("track_id"),
        project_id=project_id,
        prompt="Recovered orphan audio",
        style=None,
        negative_tags=meta.get("negative-tags") or None,
        make_instrumental=meta.get("make-instrumental") == "true",
        generation_mode=_mode_from_meta(meta.get("generation-mode")),  # type: ignore[arg-type]
        continue_at_sec=int(meta["continue-at-sec"]) if meta.get("continue-at-sec") else None,
        audio_weight=float(meta["audio-weight"]) if meta.get("audio-weight") else None,
        duration_sec=duration_sec,
        provider=meta.get("provider") or "unknown",
        provider_task_id=meta.get("provider-task-id") or None,
        provider_clip_id=meta.get("provider-clip-id") or None,
        parent_track_id=meta.get("parent-track-id") or None,
        generation_ms=None,
        created_at=obj["LastModified"],
        audio=audio,
        is_orphaned=True,
    )


def _load_orphan_tracks(project_id: str, known_ids: set[str]) -> list[Track]:
    prefix = f"{project_prefix(project_id)}tracks/"
    objects = [
        obj
        for obj in list_project_keys(prefix, max_keys=10_000)
        if PROJECT_TRACK_AUDIO_RE.match(obj["Key"])
        and PROJECT_TRACK_AUDIO_RE.match(obj["Key"]).group("track_id") not in known_ids
    ]
    heads = head_track_objects_parallel([obj["Key"] for obj in objects])
    return [_orphan_track_from_object(project_id, obj, heads.get(obj["Key"])) for obj in objects]


def build_tree(project_id: str) -> list[RevisionNode]:
    """Build the project's revision tree.

    Returns a list of top-level roots (a project can have multiple
    independent root prompts; the UI typically renders the newest root
    first). Each root recursively contains its children sorted oldest-
    first so the timeline reads left-to-right.
    """
    tracks = _load_tracks(project_id)
    tracks.extend(_load_orphan_tracks(project_id, {t.track_id for t in tracks}))
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
    for t in _load_orphan_tracks(project_id, {x.track_id for x in tracks}):
        if t.track_id == track_id:
            return t
    raise TrackNotFound()


def repair_track_sidecar(project_id: str, track_id: str) -> Track:
    """Write a minimal sidecar for an orphaned audio object."""
    tracks = _load_tracks(project_id)
    for track in tracks:
        if track.track_id == track_id:
            return track
    for orphan in _load_orphan_tracks(project_id, {t.track_id for t in tracks}):
        if orphan.track_id == track_id:
            repaired = orphan.model_copy(update={"is_orphaned": False})
            key = f"{project_prefix(project_id)}tracks/{track_id}/track.json"
            put_json(key, repaired.model_dump(mode="json"))
            return repaired
    raise TrackNotFound()


def diff_tracks(a: Track, b: Track) -> TrackDiff:
    """Return a structural diff between two tracks for the compare UI."""
    prompt_changed = a.prompt != b.prompt
    style_changed = (a.style or "") != (b.style or "")
    negative_tags_changed = (a.negative_tags or "") != (b.negative_tags or "")
    instrumental_changed = a.make_instrumental != b.make_instrumental
    generation_mode_changed = a.generation_mode != b.generation_mode
    continue_at_changed = a.continue_at_sec != b.continue_at_sec
    audio_weight_changed = a.audio_weight != b.audio_weight
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
        negative_tags_changed=negative_tags_changed,
        instrumental_changed=instrumental_changed,
        generation_mode_changed=generation_mode_changed,
        continue_at_changed=continue_at_changed,
        audio_weight_changed=audio_weight_changed,
        duration_changed=duration_changed,
        audio_metadata_changed=audio_meta_changed,
    )
