from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    """Per-file metadata returned alongside an upload response.

    For audio uploads the audio-specific fields are populated by
    `service/audio_metadata.py`. For non-audio uploads (kept supported for
    parity with the underlying starter kit) only the common fields are
    populated and the audio fields remain null.
    """

    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
    # Audio-specific (populated when the upload is audio/*)
    duration_ms: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_depth: int | None = None
    codec: str | None = None
