import pytest
from pydantic import ValidationError

from app.types import GenerationRequest


def test_generation_request_rejects_overlong_style():
    with pytest.raises(ValidationError) as exc_info:
        GenerationRequest(prompt="ambient piano", style="x" * 1001)

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("style",)
