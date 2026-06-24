import pytest
from pydantic import ValidationError

from app.types import GenerationRequest


def test_generation_request_rejects_overlong_style():
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="ambient piano", style="x" * 1001)
