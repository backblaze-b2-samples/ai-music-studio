"""Tests for `service.library.get_audio_aggregates`.

Aggregates feed the dashboard's Audio Storage tile, Total Duration card, and
Format breakdown. The function HEADs every audio object in parallel to pull
durations stamped at upload time. We stub both `list_audio_objects` and
`head_track_objects_parallel` to exercise the summation, formats bucketing,
and the externally-seeded (no-metadata) fallback path.
"""

from datetime import UTC, datetime

from app.service import library as library_service


def _audio_obj(key: str, size: int = 1234) -> dict:
    return {
        "Key": key,
        "Size": size,
        "LastModified": datetime(2026, 5, 22, tzinfo=UTC),
    }


def test_aggregates_sum_duration_from_head_metadata(monkeypatch):
    """Real `total_duration_ms` is summed from `x-amz-meta-duration-ms`."""
    objs = [
        _audio_obj("audio/2026/05/a--abc.wav", size=1000),
        _audio_obj("audio/2026/05/b--def.mp3", size=2000),
        _audio_obj("audio/2026/05/c--ghi.flac", size=3000),
    ]
    heads = {
        "audio/2026/05/a--abc.wav": {"Metadata": {"duration-ms": "1000"}},
        "audio/2026/05/b--def.mp3": {"Metadata": {"duration-ms": "2500"}},
        "audio/2026/05/c--ghi.flac": {"Metadata": {"duration-ms": "500"}},
    }
    monkeypatch.setattr(
        library_service, "list_library_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        library_service, "head_track_objects_parallel", lambda keys: heads
    )

    result = library_service.get_audio_aggregates()

    assert result["total_audio_assets"] == 3
    assert result["total_duration_ms"] == 4000
    assert result["total_size_bytes"] == 6000


def test_aggregates_format_counts_include_other_bucket(monkeypatch):
    """`formats` is keyed by extension; unknown extensions land in `other`."""
    objs = [
        _audio_obj("audio/2026/05/one--abc.wav"),
        _audio_obj("audio/2026/05/two--def.wav"),
        _audio_obj("audio/2026/05/three--ghi.mp3"),
        _audio_obj("audio/2026/05/four--jkl.flac"),
        # Externally-seeded file with no extension lands in the "other" bucket.
        _audio_obj("audio/legacy/noext"),
    ]
    monkeypatch.setattr(
        library_service, "list_library_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        library_service, "head_track_objects_parallel", lambda keys: {}
    )

    result = library_service.get_audio_aggregates()

    assert result["formats"] == {
        "wav": 2,
        "mp3": 1,
        "flac": 1,
        "other": 1,
    }


def test_aggregates_handle_objects_without_stamped_metadata(monkeypatch):
    """Externally-seeded objects (no `x-amz-meta-*`) contribute 0 ms but
    still count toward `total_audio_assets` and `formats`."""
    objs = [
        # Stamped: contributes 7500 ms.
        _audio_obj("audio/2026/05/stamped--abc.wav", size=500),
        # Externally seeded: no head response at all.
        _audio_obj("audio/legacy/seed.wav", size=100),
        # HEAD returned, but no Metadata block — still 0 ms.
        _audio_obj("audio/legacy/empty-meta.mp3", size=200),
    ]
    heads = {
        "audio/2026/05/stamped--abc.wav": {"Metadata": {"duration-ms": "7500"}},
        "audio/legacy/empty-meta.mp3": {"Metadata": {}},
        # `audio/legacy/seed.wav` deliberately omitted to simulate a HEAD miss.
    }
    monkeypatch.setattr(
        library_service, "list_library_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        library_service, "head_track_objects_parallel", lambda keys: heads
    )

    result = library_service.get_audio_aggregates()

    assert result["total_audio_assets"] == 3
    assert result["total_duration_ms"] == 7500
    assert result["total_size_bytes"] == 800
    assert result["formats"] == {"wav": 2, "mp3": 1}


def test_aggregates_empty_bucket_returns_zeros(monkeypatch):
    """No objects -> zero everything, empty formats dict, no HEAD fanout."""
    head_calls: list[list[str]] = []

    def _head(keys):
        head_calls.append(list(keys))
        return {}

    monkeypatch.setattr(library_service, "list_library_objects", lambda max_keys: [])
    monkeypatch.setattr(library_service, "head_track_objects_parallel", _head)

    result = library_service.get_audio_aggregates()

    assert result["total_audio_assets"] == 0
    assert result["total_duration_ms"] == 0
    assert result["total_size_bytes"] == 0
    assert result["formats"] == {}
    # Skip the HEAD fanout entirely when there's nothing to head.
    assert head_calls == []


def test_library_lists_project_scoped_tracks(monkeypatch):
    project_id = "123e4567-e89b-42d3-a456-426614174000"
    project_key = f"projects/{project_id}/tracks/track-1/audio.mp3"
    older = datetime(2026, 5, 21, tzinfo=UTC)
    newer = datetime(2026, 5, 22, tzinfo=UTC)
    monkeypatch.setattr(
        library_service,
        "list_audio_objects",
        lambda max_keys: [
            {"Key": "audio/legacy/seed.wav", "Size": 100, "LastModified": older}
        ],
    )
    monkeypatch.setattr(
        library_service,
        "list_project_keys",
        lambda prefix, max_keys: [
            {"Key": project_key, "Size": 200, "LastModified": newer},
            {
                "Key": f"projects/{project_id}/tracks/track-1/track.json",
                "Size": 50,
                "LastModified": older,
            },
        ],
    )
    monkeypatch.setattr(
        library_service,
        "head_track_objects_parallel",
        lambda keys: {project_key: {"Metadata": {"duration-ms": "90000"}}},
    )

    assets = library_service.list_audio_assets()

    assert assets[0].key == project_key
    assert assets[0].project_id == project_id
    assert assets[0].track_id == "track-1"
    assert assets[0].source == "project"
    assert assets[0].duration_ms == 90000
