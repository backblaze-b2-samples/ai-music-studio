"""Stems service with a pluggable external splitter command."""

from __future__ import annotations

import logging
import shlex
import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.repo import (
    download_file,
    head_track_objects_parallel,
    list_project_keys,
    put_json,
    upload_file,
)
from app.repo.b2_projects import PROJECTS_PREFIX
from app.service.library import audio_asset_from_object
from app.service.projects import (
    project_prefix,
    validate_project_id,
)
from app.service.revisions import get_track
from app.types import Stem, Track

logger = logging.getLogger(__name__)
STEM_NAMES = ("vocals", "drums", "bass", "other")


class StemSplitUnavailable(Exception):
    def __init__(self, detail: str = "Stem splitter is not configured"):
        self.detail = detail
        super().__init__(detail)


class StemSplitError(Exception):
    def __init__(self, detail: str = "Stem split failed"):
        self.detail = detail
        super().__init__(detail)


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
    heads = head_track_objects_parallel([obj["Key"] for obj in objects])
    stems: list[Stem] = []
    for obj in objects:
        key = obj["Key"]
        name = key.removeprefix(prefix).rsplit(".", 1)[0]
        if name not in STEM_NAMES:
            continue
        audio = audio_asset_from_object(obj, heads.get(key))
        stems.append(Stem(stem_id=key, track_id=track_id, name=name, audio=audio))  # type: ignore[arg-type]
    return stems


def _sidecar_key(project_id: str, track_id: str) -> str:
    return f"{project_prefix(project_id)}tracks/{track_id}/track.json"


def _run_splitter(input_path: Path, output_dir: Path) -> None:
    if not settings.stem_splitter_command:
        raise StemSplitUnavailable(
            "Set STEM_SPLITTER_COMMAND to enable stem separation"
        )
    command = settings.stem_splitter_command.format(
        input=shlex.quote(str(input_path)),
        output=shlex.quote(str(output_dir)),
    )
    try:
        subprocess.run(
            shlex.split(command),
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("Stem splitter failed: %s", e.stderr or e.stdout)
        raise StemSplitError("Stem splitter command failed") from e
    except subprocess.TimeoutExpired as e:
        raise StemSplitError("Stem splitter timed out") from e


def _write_stem_keys(project_id: str, track_id: str, track: Track, keys: list[str]) -> None:
    repaired = track.model_copy(update={"stems_keys": keys, "is_orphaned": False})
    put_json(_sidecar_key(project_id, track_id), repaired.model_dump(mode="json"))


def split_stems(project_id: str, track_id: str) -> list[Stem]:
    """Run the configured splitter and upload any produced WAV stems."""
    validate_project_id(project_id)
    track = get_track(project_id, track_id)
    ext = track.audio.key.rsplit(".", 1)[-1].lower()
    with tempfile.TemporaryDirectory(prefix="ai-music-stems-") as tmp:
        root = Path(tmp)
        input_path = root / f"input.{ext}"
        output_dir = root / "out"
        output_dir.mkdir()
        input_path.write_bytes(download_file(track.audio.key))
        _run_splitter(input_path, output_dir)
        written: list[str] = []
        for name in STEM_NAMES:
            stem_path = output_dir / f"{name}.wav"
            if not stem_path.exists():
                continue
            key = f"{_stems_prefix(project_id, track_id)}{name}.wav"
            upload_file(stem_path.read_bytes(), key, "audio/wav")
            written.append(key)
    if not written:
        raise StemSplitError("Stem splitter produced no recognized stems")
    _write_stem_keys(project_id, track_id, track, written)
    return list_stems(project_id, track_id)
