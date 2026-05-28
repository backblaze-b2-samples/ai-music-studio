from datetime import UTC, datetime

from app.service import revisions
from app.service.revisions import build_tree, diff_tracks
from app.types import AudioAsset, Track


def _asset(key: str) -> AudioAsset:
    return AudioAsset(
        key=key,
        size_bytes=100,
        size_human="100 B",
        content_type="audio/mpeg",
        created_at=datetime.now(UTC),
        duration_ms=10_000,
        sample_rate=44_100,
        channels=2,
        bit_depth=None,
        codec="mp3",
        title_preview=None,
    )


def _track(track_id: str, **kwargs) -> Track:
    base = {
        "track_id": track_id,
        "project_id": "project-1",
        "prompt": "a nocturnal synth track",
        "style": "dreamy synth-pop",
        "duration_sec": 30,
        "provider": "musicapi",
        "created_at": datetime.now(UTC),
        "audio": _asset(f"projects/project-1/tracks/{track_id}/audio.mp3"),
    }
    base.update(kwargs)
    return Track(**base)


def test_diff_tracks_includes_generation_controls():
    a = _track("a", make_instrumental=False, negative_tags=None)
    b = _track("b", make_instrumental=True, negative_tags="country, acoustic")

    diff = diff_tracks(a, b)

    assert diff.instrumental_changed is True
    assert diff.negative_tags_changed is True


def test_build_tree_surfaces_orphan_audio(monkeypatch):
    project_id = "123e4567-e89b-42d3-a456-426614174000"
    key = f"projects/{project_id}/tracks/orphan/audio.mp3"
    uploaded_at = datetime(2026, 5, 22, tzinfo=UTC)

    monkeypatch.setattr(revisions, "list_project_track_keys", lambda project_id: [])
    monkeypatch.setattr(
        revisions,
        "list_project_keys",
        lambda prefix, max_keys: [{"Key": key, "Size": 123, "LastModified": uploaded_at}],
    )
    monkeypatch.setattr(
        revisions,
        "head_track_objects_parallel",
        lambda keys: {key: {"Metadata": {"provider": "musicapi", "duration-ms": "30000"}}},
    )

    tree = build_tree(project_id)

    assert len(tree) == 1
    assert tree[0].track.track_id == "orphan"
    assert tree[0].track.is_orphaned is True
    assert tree[0].track.audio.key == key
