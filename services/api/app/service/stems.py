"""Stems service — data shape is live, split is stubbed.

The data model (`Stem`, `stems_keys` on `Track`) and the listing helper
are real so the UI has something to render. The actual stem-split
operation (`split_stems`) raises `NotImplementedError` and the UI
surfaces a disabled "Generate Stems (coming soon)" button.

Tracked in `docs/exec-plans/tech-debt-tracker.md` — when we wire up a
real splitter (Demucs / Spleeter / API), this is the only function that
needs to change. Everything downstream of `Stem` (storage, listing,
playback) already works.
"""

from __future__ import annotations

import logging

from app.repo import list_project_keys
from app.repo.b2_projects import PROJECTS_PREFIX
from app.service.projects import (
    project_prefix,
    validate_project_id,
)
from app.types import Stem

logger = logging.getLogger(__name__)


def _stems_prefix(project_id: str, track_id: str) -> str:
    return f"{project_prefix(project_id)}tracks/{track_id}/stems/"


def list_stems(project_id: str, track_id: str) -> list[Stem]:
    """List stems for a track.

    Returns an empty list when no stems exist (which is the universal
    case in v1 — see `split_stems` below). Lives as a real helper so the
    UI's stems panel can poll it with a simple TanStack Query hook and
    surface stems instantly when a future implementation lands.
    """
    validate_project_id(project_id)
    prefix = _stems_prefix(project_id, track_id)
    if not prefix.startswith(PROJECTS_PREFIX):
        # Defense in depth; `project_prefix` always returns the right shape.
        return []
    objects = list_project_keys(prefix, max_keys=100)
    stems: list[Stem] = []
    for obj in objects:
        key = obj["Key"]
        name = key.removeprefix(prefix).rsplit(".", 1)[0]
        if name not in ("vocals", "drums", "bass", "other"):
            continue
        # Note: `audio` is intentionally left None — a real implementation
        # would HEAD the key and fill in an AudioAsset. We don't fan out a
        # HEAD here in v1 because there are zero stems to begin with.
        stems.append(Stem(stem_id=key, track_id=track_id, name=name))  # type: ignore[arg-type]
    return stems


def split_stems(project_id: str, track_id: str) -> list[Stem]:
    """Split a track into vocals/drums/bass/other stems.

    **Stubbed in v1.** A real implementation would:

      1. Fetch `projects/<id>/tracks/<track-id>/audio.<ext>` from B2.
      2. Run a stem-separation model (e.g. Demucs via PyTorch or a
         hosted API like LALAL.AI / AudioShake).
      3. Upload each stem to
         `projects/<id>/tracks/<track-id>/stems/<name>.wav`.
      4. Update `track.json::stems_keys` so the revision tree knows
         the stems are available.
      5. Return the populated `Stem` list.

    Until then this raises so the failure mode is loud and obvious. The
    UI surfaces it as a disabled "Generate Stems (coming soon)" button.
    Tracked under tech debt — `docs/exec-plans/tech-debt-tracker.md`.
    """
    raise NotImplementedError(
        "Stem separation is not yet implemented. The data model and the "
        "list_stems() helper are live; wire up a real splitter (Demucs / "
        "LALAL.AI / AudioShake) inside this function and write stems to "
        "projects/<id>/tracks/<track-id>/stems/<name>.wav. See "
        "docs/exec-plans/tech-debt-tracker.md for context."
    )
