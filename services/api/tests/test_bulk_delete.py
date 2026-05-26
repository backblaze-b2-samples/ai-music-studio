"""Tests for bulk-delete endpoints on /files and /library.

Both endpoints share a contract: validate every key before any S3 call,
forward a single DeleteObjects request, and return `{deleted, errors}` so
the UI can render partial success.
"""

import pytest

from app.service import files as files_service
from app.service import library as library_service


@pytest.mark.asyncio
async def test_bulk_delete_files_success(client, monkeypatch):
    captured: dict = {}

    def _fake_batch(keys):
        captured["keys"] = list(keys)
        return list(keys), []

    monkeypatch.setattr(files_service, "delete_files_batch", _fake_batch)

    response = await client.post(
        "/files/bulk-delete",
        json={"keys": ["uploads/a.txt", "uploads/b.txt"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == ["uploads/a.txt", "uploads/b.txt"]
    assert body["errors"] == []
    assert captured["keys"] == ["uploads/a.txt", "uploads/b.txt"]


@pytest.mark.asyncio
async def test_bulk_delete_files_dedupes(client, monkeypatch):
    captured: dict = {}

    def _fake_batch(keys):
        captured["keys"] = list(keys)
        return list(keys), []

    monkeypatch.setattr(files_service, "delete_files_batch", _fake_batch)

    response = await client.post(
        "/files/bulk-delete",
        json={"keys": ["uploads/a.txt", "uploads/a.txt", "uploads/b.txt"]},
    )

    assert response.status_code == 200
    assert captured["keys"] == ["uploads/a.txt", "uploads/b.txt"]


@pytest.mark.asyncio
async def test_bulk_delete_files_rejects_path_traversal(client, monkeypatch):
    """A single malformed key should fail the batch before any S3 call."""
    called = False

    def _fake_batch(keys):
        nonlocal called
        called = True
        return list(keys), []

    monkeypatch.setattr(files_service, "delete_files_batch", _fake_batch)

    response = await client.post(
        "/files/bulk-delete",
        json={"keys": ["uploads/good.txt", "../etc/passwd"]},
    )

    assert response.status_code == 400
    assert called is False


@pytest.mark.asyncio
async def test_bulk_delete_files_empty_list(client):
    response = await client.post("/files/bulk-delete", json={"keys": []})
    # FastAPI's request validation catches min_length=1 before service is hit
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_delete_files_partial_errors(client, monkeypatch):
    def _fake_batch(keys):
        return [keys[0]], [
            {"Key": keys[1], "Code": "AccessDenied", "Message": "nope"}
        ]

    monkeypatch.setattr(files_service, "delete_files_batch", _fake_batch)

    response = await client.post(
        "/files/bulk-delete",
        json={"keys": ["uploads/a.txt", "uploads/b.txt"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == ["uploads/a.txt"]
    assert body["errors"][0]["Key"] == "uploads/b.txt"
    assert body["errors"][0]["Code"] == "AccessDenied"


@pytest.mark.asyncio
async def test_bulk_delete_files_propagates_b2_error(client, monkeypatch):
    def _boom(keys):
        raise RuntimeError("B2 batch delete failed")

    monkeypatch.setattr(files_service, "delete_files_batch", _boom)

    response = await client.post(
        "/files/bulk-delete",
        json={"keys": ["uploads/a.txt"]},
    )

    assert response.status_code == 500
    assert "Failed to delete files" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_delete_library_success(client, monkeypatch):
    captured: dict = {}

    def _fake_batch(keys):
        captured["keys"] = list(keys)
        return list(keys), []

    monkeypatch.setattr(library_service, "delete_audio_objects_batch", _fake_batch)

    response = await client.post(
        "/library/bulk-delete",
        json={
            "keys": [
                "audio/2026/05/track-one--abc123.wav",
                "audio/2026/05/track-two--def456.mp3",
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == [
        "audio/2026/05/track-one--abc123.wav",
        "audio/2026/05/track-two--def456.mp3",
    ]
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_bulk_delete_library_rejects_non_audio_prefix(client, monkeypatch):
    called = False

    def _fake_batch(keys):
        nonlocal called
        called = True
        return list(keys), []

    monkeypatch.setattr(library_service, "delete_audio_objects_batch", _fake_batch)

    response = await client.post(
        "/library/bulk-delete",
        json={"keys": ["uploads/not-audio.txt"]},
    )

    assert response.status_code == 400
    assert called is False


@pytest.mark.asyncio
async def test_bulk_delete_library_rejects_path_traversal(client, monkeypatch):
    called = False

    def _fake_batch(keys):
        nonlocal called
        called = True
        return list(keys), []

    monkeypatch.setattr(library_service, "delete_audio_objects_batch", _fake_batch)

    response = await client.post(
        "/library/bulk-delete",
        json={"keys": ["audio/../../etc/passwd.wav"]},
    )

    assert response.status_code == 400
    assert called is False


@pytest.mark.asyncio
async def test_bulk_delete_library_partial_errors(client, monkeypatch):
    def _fake_batch(keys):
        return [keys[0]], [
            {"Key": keys[1], "Code": "InternalError", "Message": "transient"}
        ]

    monkeypatch.setattr(library_service, "delete_audio_objects_batch", _fake_batch)

    response = await client.post(
        "/library/bulk-delete",
        json={
            "keys": [
                "audio/2026/05/a--1.wav",
                "audio/2026/05/b--2.mp3",
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == ["audio/2026/05/a--1.wav"]
    assert body["errors"][0]["Key"] == "audio/2026/05/b--2.mp3"
