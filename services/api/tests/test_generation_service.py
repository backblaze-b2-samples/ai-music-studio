from datetime import UTC, datetime

import pytest

from app.repo.music_provider import GenerationResult
from app.service import generation
from app.types import AudioAsset, FileMetadataDetail, GenerationRequest, Project, Track

PROJECT_ID = "123e4567-e89b-42d3-a456-426614174000"


def _project() -> Project:
    return Project(
        project_id=PROJECT_ID,
        name="Project 1",
        description=None,
        created_at=datetime.now(UTC),
    )


def _asset(key: str, duration_ms: int | None = 124_000) -> AudioAsset:
    return AudioAsset(
        key=key,
        size_bytes=100,
        size_human="100 B",
        content_type="audio/mpeg",
        created_at=datetime.now(UTC),
        duration_ms=duration_ms,
        sample_rate=44_100,
        channels=2,
        bit_depth=None,
        codec="mp3",
        title_preview=None,
    )


def _track(track_id: str, provider_clip_id: str | None) -> Track:
    return Track(
        track_id=track_id,
        project_id=PROJECT_ID,
        prompt="original",
        style="synth-pop",
        duration_sec=30,
        provider="musicapi",
        provider_clip_id=provider_clip_id,
        created_at=datetime.now(UTC),
        audio=_asset(f"projects/{PROJECT_ID}/tracks/{track_id}/audio.mp3"),
    )


def _metadata_detail() -> FileMetadataDetail:
    return FileMetadataDetail(
        filename="audio.mp3",
        size_bytes=10,
        size_human="10 B",
        mime_type="audio/mpeg",
        extension="mp3",
        md5="md5",
        sha256="sha256",
        uploaded_at=datetime.now(UTC),
        duration_ms=10_000,
        sample_rate=44_100,
        channels=2,
        bit_depth=None,
        codec="mp3",
    )


class CapturingProvider:
    name = "musicapi"

    def __init__(self):
        self.kwargs = {}

    def generate(self, **kwargs):
        self.kwargs = kwargs
        return GenerationResult(
            track_id="child",
            audio_bytes=b"audio",
            audio_ext="mp3",
            provider=self.name,
            generation_ms=12,
            provider_task_id="task-child",
            provider_clip_id="clip-child",
        )


@pytest.fixture
def generation_fakes(monkeypatch):
    monkeypatch.setattr(generation, "get_project", lambda project_id: _project())
    monkeypatch.setattr(generation, "upload_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(generation, "put_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        generation,
        "extract_metadata",
        lambda *args, **kwargs: _metadata_detail(),
    )


def test_generate_track_passes_extend_context(generation_fakes, monkeypatch):
    parent = _track("parent", provider_clip_id="clip-parent")
    monkeypatch.setattr(generation, "get_track", lambda project_id, track_id: parent)
    provider = CapturingProvider()

    track = generation.generate_track(
        PROJECT_ID,
        GenerationRequest(
            prompt="add a bigger final chorus",
            parent_track_id="parent",
            generation_mode="extend",
        ),
        provider=provider,
    )

    assert provider.kwargs["generation_mode"] == "extend"
    assert provider.kwargs["parent_provider_clip_id"] == "clip-parent"
    assert provider.kwargs["continue_at_sec"] == 124
    assert track.generation_mode == "extend"
    assert track.provider_task_id == "task-child"
    assert track.provider_clip_id == "clip-child"


def test_restyle_requires_parent_provider_clip_id(generation_fakes, monkeypatch):
    parent = _track("parent", provider_clip_id=None)
    monkeypatch.setattr(generation, "get_track", lambda project_id, track_id: parent)

    with pytest.raises(generation.GenerationError) as exc:
        generation.generate_track(
                PROJECT_ID,
            GenerationRequest(
                prompt="make it smoky jazz",
                parent_track_id="parent",
                generation_mode="restyle",
            ),
            provider=CapturingProvider(),
        )

    assert exc.value.status_code == 400
