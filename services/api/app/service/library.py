"""Audio Library service layer.

Lists, heads, deletes, and presigns audio assets stored under the `audio/`
prefix in B2. The service layer owns key validation and orchestration; raw
S3 calls live in `repo/b2_client.py`.

The canonical shape produced by the Upload pipeline is
`audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>`, but the Library plays any
object under `audio/` ending in a supported extension — files seeded into
the bucket via the B2 console, an earlier sample, or direct S3 sync stay
playable. The `--<uuid>` suffix is stripped for display via
`_filename_from_key`; externally-seeded keys with no `--` are shown as-is.
"""

from __future__ import annotations

import logging
import mimetypes
import re

from app.repo import (
    AUDIO_PREFIX,
    delete_audio_object,
    delete_audio_objects_batch,
    get_presigned_url,
    head_audio_object,
    head_track_objects_parallel,
    list_audio_objects,
    presign_audio_playback,
)
from app.types import AudioAsset
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# Audio assets live under the `audio/` prefix and end in a supported
# extension. The shape is intentionally permissive: the Upload pipeline
# produces `audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>`, but the bucket
# may also hold audio seeded by the B2 console, an earlier sample, or
# direct S3 sync — all should be playable. Path-traversal payloads and
# unknown extensions are still rejected before any B2 call.
AUDIO_KEY_RE = re.compile(
    r"^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus)$",
    re.IGNORECASE,
)


class AudioKeyError(Exception):
    """Raised when an audio asset key is malformed."""

    def __init__(self, detail: str = "Invalid audio key"):
        self.detail = detail
        super().__init__(detail)


class AudioAssetNotFound(Exception):
    """Raised when no asset exists at the requested key."""

    def __init__(self, detail: str = "Audio asset not found"):
        self.detail = detail
        super().__init__(detail)


def validate_audio_key(key: str) -> None:
    """Reject keys that don't match the audio prefix shape."""
    if not key or ".." in key or "//" in key or not AUDIO_KEY_RE.match(key):
        raise AudioKeyError()


def _guess_codec(key: str) -> str | None:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return ext or None


def _content_type_for(key: str) -> str:
    mime, _ = mimetypes.guess_type(key)
    return mime or "application/octet-stream"


def _filename_from_key(key: str) -> str:
    """Return the human-readable filename embedded in a key.

    Upload-pipeline keys have shape `audio/<YYYY>/<MM>/<name>--<uuid>.<ext>`;
    strip the `--<uuid>` suffix that sits between the stem and the extension.
    Externally-seeded files have no `--` separator, so the last path segment
    is returned as-is. A sanitized name may itself contain `--`, so we strip
    only the rightmost occurrence.
    """
    segment = key.rsplit("/", 1)[-1]
    if "--" not in segment:
        return segment
    if "." in segment:
        body, _, ext = segment.rpartition(".")
        stem, sep, _ = body.rpartition("--")
        if not sep:
            return segment
        return f"{stem}.{ext}" if stem else segment
    stem, sep, _ = segment.rpartition("--")
    return stem if sep and stem else segment


def _int_or_none(v: object) -> int | None:
    """Parse a metadata string back to int; ignore garbage rather than 500."""
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _metadata_from_head(head: dict | None) -> dict:
    """Pull audio fields out of an S3 HEAD response.

    boto3 normalizes `x-amz-meta-*` headers into `head["Metadata"]` with
    lower-case keys — mirrors the kebab-case names emitted by
    `audio_metadata.to_s3_metadata`.
    """
    if not head:
        return {}
    meta = head.get("Metadata") or {}
    return {
        "duration_ms": _int_or_none(meta.get("duration-ms")),
        "sample_rate": _int_or_none(meta.get("sample-rate")),
        "channels": _int_or_none(meta.get("channels")),
        "bit_depth": _int_or_none(meta.get("bit-depth")),
        "codec": meta.get("codec") or None,
    }


def _asset_from_object(obj: dict, head: dict | None = None) -> AudioAsset:
    key = obj["Key"]
    size = obj["Size"]
    extra = _metadata_from_head(head)
    # Fall back to extension-derived codec when the object pre-dates the
    # metadata stamping (externally-seeded files).
    if not extra.get("codec"):
        extra["codec"] = _guess_codec(key)
    return AudioAsset(
        key=key,
        size_bytes=size,
        size_human=humanize_bytes(size),
        content_type=_content_type_for(key),
        created_at=obj["LastModified"],
        title_preview=_filename_from_key(key),
        **extra,
    )


def list_audio_assets(limit: int = 100, with_metadata: bool = True) -> list[AudioAsset]:
    """List audio assets, newest-first.

    When `with_metadata=True` (default) we HEAD each returned object in
    parallel to pull duration / sample rate / channels / bit depth / codec
    out of the S3 user metadata stamped at upload time. The cost is one
    extra round-trip per asset, capped at `limit` — for the dashboard's
    10-row table and the Library grid this stays well under the
    list-objects latency. Pass `with_metadata=False` from any caller that
    only needs the key/size/created_at trio.
    """
    if limit < 1 or limit > 500:
        raise ValueError("Limit must be between 1 and 500")
    raw = list_audio_objects(max_keys=1000)
    raw.sort(key=lambda o: o["LastModified"], reverse=True)
    raw = raw[:limit]
    heads: dict[str, dict] = (
        head_track_objects_parallel([obj["Key"] for obj in raw])
        if with_metadata
        else {}
    )
    return [_asset_from_object(obj, heads.get(obj["Key"])) for obj in raw]


def get_playback_url(key: str) -> str:
    """Return an inline presigned GET (no Content-Disposition)."""
    validate_audio_key(key)
    if head_audio_object(key) is None:
        raise AudioAssetNotFound()
    return presign_audio_playback(key)


def get_download_url(key: str) -> str:
    """Return a presigned GET with `Content-Disposition: attachment`."""
    validate_audio_key(key)
    head = head_audio_object(key)
    if head is None:
        raise AudioAssetNotFound()
    return get_presigned_url(key, filename=_filename_from_key(key))


def delete_audio_asset(key: str) -> None:
    """Validate the key and delete the asset from B2."""
    validate_audio_key(key)
    delete_audio_object(key)


def bulk_delete_audio_assets(keys: list[str]) -> tuple[list[str], list[dict]]:
    """Validate each audio key and batch-delete via S3 DeleteObjects.

    Mirrors `service.files.bulk_remove_files` but uses the Library's stricter
    `AUDIO_KEY_RE` so path-traversal and non-audio prefixes are rejected
    before any B2 call. Returns `(deleted_keys, errors)` so partial failures
    surface to the UI.
    """
    if not keys:
        raise AudioKeyError("No keys provided")
    if len(keys) > 1000:
        raise AudioKeyError("Cannot delete more than 1000 keys per request")
    seen: set[str] = set()
    cleaned: list[str] = []
    for k in keys:
        validate_audio_key(k)
        if k not in seen:
            seen.add(k)
            cleaned.append(k)
    return delete_audio_objects_batch(cleaned)


def get_audio_aggregates() -> dict:
    """Return audio-aware aggregates for the dashboard endpoint.

    HEADs every audio object in parallel to sum durations from
    `x-amz-meta-duration-ms` (stamped at upload). Externally-seeded files
    that pre-date the stamp simply contribute 0 to the total — they still
    count toward asset/format totals so the dashboard isn't lying about
    bucket contents. The HEAD fanout caps at 10k objects to keep an
    accidentally-huge bucket from melting the dashboard endpoint.
    """
    raw = list_audio_objects(max_keys=10_000)
    total = len(raw)
    total_size = sum(obj["Size"] for obj in raw)

    keys = [obj["Key"] for obj in raw]
    heads = head_track_objects_parallel(keys) if keys else {}

    total_duration_ms = 0
    formats: dict[str, int] = {}
    for obj in raw:
        ext = _guess_codec(obj["Key"]) or "other"
        formats[ext] = formats.get(ext, 0) + 1
        head = heads.get(obj["Key"])
        if head is None:
            continue
        dur = _int_or_none((head.get("Metadata") or {}).get("duration-ms"))
        if dur:
            total_duration_ms += dur

    return {
        "total_audio_assets": total,
        "total_duration_ms": total_duration_ms,
        "total_size_bytes": total_size,
        "total_size_human": humanize_bytes(total_size),
        "audio_prefix": AUDIO_PREFIX,
        "formats": formats,
    }
