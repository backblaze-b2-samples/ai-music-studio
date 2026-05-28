from datetime import UTC, datetime

import pytest

from app.runtime import generation as generation_runtime
from app.types import GenerationStatus

PROJECT_ID = "123e4567-e89b-42d3-a456-426614174000"


@pytest.mark.asyncio
async def test_generate_endpoint_returns_queued_status(client, monkeypatch):
    monkeypatch.setattr(
        generation_runtime,
        "check_generation_rate_limit",
        lambda client_id: None,
    )
    monkeypatch.setattr(
        generation_runtime,
        "enqueue_generation",
        lambda project_id, body, user_id: GenerationStatus(
            project_id=project_id,
            track_id="queued-track",
            state="queued",
            started_at=datetime(2026, 5, 28, tzinfo=UTC),
        ),
    )

    response = await client.post(
        f"/projects/{PROJECT_ID}/generate",
        json={"prompt": "ambient bells"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "queued"
    assert body["track_id"] == "queued-track"
