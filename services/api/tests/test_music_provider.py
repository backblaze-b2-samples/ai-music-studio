import httpx
import pytest

from app.repo.music_provider import MusicApiProvider


class CreateTaskClient:
    def __init__(self, body: dict[str, object], status_code: int = 200):
        self.body = body
        self.status_code = status_code

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(self.status_code, json=self.body, request=request)


@pytest.mark.parametrize(
    ("body", "expected_task_id"),
    [
        ({"message": "success", "task_id": "top-level-task"}, "top-level-task"),
        ({"code": 200, "task_id": "ok-code-task"}, "ok-code-task"),
        ({"code": 0, "data": {"task_id": "nested-task"}}, "nested-task"),
        ({"code": 0, "data": [{"task_id": "list-task"}]}, "list-task"),
    ],
)
def test_musicapi_create_task_accepts_known_task_id_shapes(
    body: dict[str, object],
    expected_task_id: str,
):
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    task_id = provider._create_task(
        CreateTaskClient(body),
        {"gpt_description_prompt": "make it bright"},
    )

    assert task_id == expected_task_id


def test_musicapi_create_task_maps_403_to_credit_hint():
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    with pytest.raises(RuntimeError, match="insufficient credits"):
        provider._create_task(
            CreateTaskClient({"message": "no credits"}, status_code=403),
            {"gpt_description_prompt": "make it bright"},
        )


def test_musicapi_payload_adds_instrumental_flag():
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    payload = provider._build_payload(
        prompt="peaceful piano with soft strings",
        style=None,
        negative_tags=None,
        make_instrumental=True,
    )

    assert payload["make_instrumental"] is True
    assert payload["custom_mode"] is False
    assert payload["gpt_description_prompt"] == "peaceful piano with soft strings"


def test_musicapi_payload_adds_negative_tags_and_style_prefix():
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    payload = provider._build_payload(
        prompt="a nocturnal synth track",
        style="dreamy synth-pop",
        negative_tags="country, acoustic",
        make_instrumental=False,
    )

    assert payload["negative_tags"] == "country, acoustic"
    assert payload["gpt_description_prompt"] == (
        "dreamy synth-pop. a nocturnal synth track"
    )
    assert "make_instrumental" not in payload


def test_musicapi_payload_builds_extend_request():
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    payload = provider._build_payload(
        prompt="add a bigger final chorus",
        style="anthemic pop",
        negative_tags=None,
        make_instrumental=False,
        generation_mode="extend",
        parent_provider_clip_id="clip-parent",
        continue_at_sec=91,
        audio_weight=None,
    )

    assert payload["task_type"] == "extend_music"
    assert payload["continue_clip_id"] == "clip-parent"
    assert payload["continue_at"] == 91


def test_musicapi_payload_builds_restyle_request():
    provider = MusicApiProvider(api_key="test-key", base_url="https://musicapi.test")

    payload = provider._build_payload(
        prompt="turn this into a smoky jazz version",
        style="jazz trio",
        negative_tags="edm",
        make_instrumental=False,
        generation_mode="restyle",
        parent_provider_clip_id="clip-parent",
        continue_at_sec=None,
        audio_weight=0.7,
    )

    assert payload["task_type"] == "cover_music"
    assert payload["custom_mode"] is True
    assert payload["auto_lyrics"] is True
    assert payload["continue_clip_id"] == "clip-parent"
    assert payload["audio_weight"] == 0.7
    assert payload["negative_tags"] == "edm"
    assert payload["prompt"] == "turn this into a smoky jazz version"
    assert payload["tags"] == "jazz trio"
    assert "gpt_description_prompt" not in payload
