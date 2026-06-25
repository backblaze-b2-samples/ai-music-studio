import pytest
from pydantic import ValidationError

from app.types import GenerationRequest


def test_generation_request_rejects_overlong_style():
    with pytest.raises(ValidationError) as exc_info:
        GenerationRequest(prompt="ambient piano", style="x" * 1001)

    assert any(
        error["loc"] == ("style",) and error["type"] == "string_too_long"
        for error in exc_info.value.errors()
    )
