"""Small helpers for MusicAPI request/response shaping."""

from __future__ import annotations

from typing import Any


def _task_type(generation_mode: str) -> str:
    if generation_mode == "extend":
        return "extend_music"
    if generation_mode == "restyle":
        return "cover_music"
    return "create_music"


def build_musicapi_payload(
    *,
    prompt: str,
    style: str | None,
    negative_tags: str | None,
    make_instrumental: bool,
    generation_mode: str,
    parent_provider_clip_id: str | None,
    continue_at_sec: int | None,
    audio_weight: float | None,
    default_mv: str,
) -> dict[str, Any]:
    if generation_mode == "restyle":
        if not parent_provider_clip_id:
            raise RuntimeError("restyle requires a provider clip id")
        payload: dict[str, Any] = {
            "custom_mode": True,
            "auto_lyrics": True,
            "mv": default_mv,
            "prompt": prompt,
            "task_type": _task_type(generation_mode),
            "continue_clip_id": parent_provider_clip_id,
        }
        if style:
            payload["tags"] = style
        if audio_weight is not None:
            payload["audio_weight"] = audio_weight
    else:
        description = f"{style}. {prompt}" if style else prompt
        payload = {
            "custom_mode": False,
            "mv": default_mv,
            "gpt_description_prompt": description,
            "task_type": _task_type(generation_mode),
        }
        if generation_mode == "extend":
            if not parent_provider_clip_id:
                raise RuntimeError("extend requires a provider clip id")
            payload["continue_clip_id"] = parent_provider_clip_id
            payload["continue_at"] = continue_at_sec or 0

    if negative_tags:
        payload["negative_tags"] = negative_tags
    if make_instrumental:
        payload["make_instrumental"] = True
    return payload


def _response_detail(resp: Any) -> str | None:
    try:
        body = resp.json()
    except ValueError:
        text = resp.text.strip()
        return text[:500] if text else None
    if isinstance(body, dict):
        detail = body.get("message") or body.get("detail") or body.get("error")
        return str(detail) if detail else None
    return None


def raise_musicapi_for_status(resp: Any, action: str) -> None:
    if 200 <= resp.status_code < 400:
        return

    detail = _response_detail(resp)
    if resp.status_code == 403:
        message = (
            f"MusicAPI rejected {action} with 403 Forbidden. "
            "MusicAPI docs list 403 as insufficient credits; check credits "
            "or account access."
        )
    elif resp.status_code == 401:
        message = (
            f"MusicAPI rejected {action} with 401 Unauthorized. "
            "Check MUSICAPI_API_KEY."
        )
    elif resp.status_code == 429:
        message = (
            f"MusicAPI rate-limited {action} with 429 Too Many Requests. "
            "Wait a moment and retry."
        )
    else:
        message = (
            f"MusicAPI {action} failed with HTTP {resp.status_code} "
            f"{resp.reason_phrase}."
        )
    if detail:
        message = f"{message} Upstream detail: {detail}"
    raise RuntimeError(message)
