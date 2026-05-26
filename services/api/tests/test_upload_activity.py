"""Tests for the upload activity endpoint.

The activity chart is scoped to audio uploads (the kit is audio-first), so
these tests stub the audio listing/HEAD helpers rather than the generic
`list_files`.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.service import files as files_service


def _make_audio_obj(key: str, uploaded_at: datetime) -> dict:
    return {"Key": key, "Size": 1234, "LastModified": uploaded_at}


@pytest.mark.asyncio
async def test_upload_activity_returns_daily_counts(client, monkeypatch):
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    fake_objs = [
        _make_audio_obj("audio/2026/05/a.wav", today),
        _make_audio_obj("audio/2026/05/b.wav", today),
        _make_audio_obj("audio/2026/05/c.wav", yesterday),
    ]
    monkeypatch.setattr(
        files_service, "list_audio_objects", lambda max_keys: fake_objs
    )
    monkeypatch.setattr(
        files_service,
        "head_track_objects_parallel",
        lambda keys: {k: {"Metadata": {"duration-ms": "30000"}} for k in keys},
    )

    response = await client.get("/files/stats/activity?days=7")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 7

    # Last two entries should match today and yesterday
    date_map = {entry["date"]: entry for entry in data}
    assert date_map[today.date().isoformat()]["uploads"] == 2
    assert date_map[today.date().isoformat()]["duration_ms"] == 60000
    assert date_map[yesterday.date().isoformat()]["uploads"] == 1
    assert date_map[yesterday.date().isoformat()]["duration_ms"] == 30000


@pytest.mark.asyncio
async def test_upload_activity_rejects_invalid_days(client):
    response = await client.get("/files/stats/activity?days=0")
    assert response.status_code == 400

    response = await client.get("/files/stats/activity?days=91")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_activity_fills_missing_days(client, monkeypatch):
    monkeypatch.setattr(files_service, "list_audio_objects", lambda max_keys: [])
    monkeypatch.setattr(
        files_service, "head_track_objects_parallel", lambda keys: {}
    )

    response = await client.get("/files/stats/activity?days=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3
    assert all(entry["uploads"] == 0 for entry in data)
    assert all(entry["duration_ms"] == 0 for entry in data)
