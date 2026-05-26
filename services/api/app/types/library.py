from datetime import datetime

from pydantic import BaseModel


class AudioAsset(BaseModel):
    """An audio asset stored under the `audio/` prefix in B2.

    Sourced entirely from S3 list/head responses — no application database.
    The fields below intentionally cover the union of what stdlib `wave` and
    `mutagen` can extract; any single asset may have nulls for codec-specific
    fields that didn't decode (e.g., a `.wav` won't have a bitrate).
    """

    key: str
    size_bytes: int
    size_human: str
    content_type: str
    created_at: datetime
    # Audio-specific (populated by service/audio_metadata.py when present)
    duration_ms: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_depth: int | None = None
    codec: str | None = None
    # Filename shown in card header; derived from the last path segment.
    title_preview: str | None = None
