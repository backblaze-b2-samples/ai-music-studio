import re
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import upload_file
from app.service.audio_metadata import (
    AUDIO_MIME_TYPES,
    extract_metadata,
    to_s3_metadata,
)
from app.types import FileUploadResponse
from app.types.formatting import humanize_bytes

# Audio MIME types are the primary surface for this sample. Non-audio
# uploads are kept to preserve the underlying starter kit's "drop anything"
# UX — they land under the generic `uploads/` prefix and only surface in
# the bucket explorer (Files), not the audio Library.
GENERIC_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/zip",
    "video/mp4",
}

ALLOWED_TYPES = AUDIO_MIME_TYPES | GENERIC_TYPES

# Extension allowlist per declared MIME, used to catch
# extension/MIME-type spoofing before we touch B2.
MIME_EXTENSION_MAP: dict[str, set[str]] = {
    # Audio (primary surface)
    "audio/wav": {"wav"},
    "audio/x-wav": {"wav"},
    "audio/wave": {"wav"},
    "audio/mpeg": {"mp3", "mpeg"},
    "audio/mp3": {"mp3"},
    "audio/flac": {"flac"},
    "audio/x-flac": {"flac"},
    "audio/ogg": {"ogg", "oga"},
    "audio/opus": {"opus"},
    "audio/mp4": {"m4a", "mp4"},
    "audio/m4a": {"m4a"},
    "audio/x-m4a": {"m4a"},
    "audio/aac": {"aac"},
    # Generic (kept for parity with the starter kit)
    "image/jpeg": {"jpg", "jpeg", "jfif"},
    "image/png": {"png"},
    "image/gif": {"gif"},
    "image/webp": {"webp"},
    "image/svg+xml": {"svg"},
    "application/pdf": {"pdf"},
    "text/plain": {"txt", "text", "log", "md"},
    "text/csv": {"csv"},
    "application/json": {"json"},
    "application/zip": {"zip"},
    "video/mp4": {"mp4"},
}

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename: strip path components, remove unsafe chars, limit length."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = _SAFE_FILENAME_RE.sub("_", name)
    name = re.sub(r"[_.]{2,}", "_", name)
    name = name.lstrip(".").strip()
    if len(name) > 200:
        base, _, ext = name.rpartition(".")
        name = base[: 200 - len(ext) - 1] + "." + ext if ext else name[:200]
    return name or "unnamed"


def validate_extension_matches_type(filename: str, content_type: str) -> bool:
    """Verify the file extension is consistent with the declared MIME type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_exts = MIME_EXTENSION_MAP.get(content_type)
    if allowed_exts is None:
        return False
    if not ext:
        return True
    return ext in allowed_exts


class UploadError(Exception):
    """Raised when upload validation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _audio_key_for(safe_name: str) -> str:
    """Build an `audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>` key.

    The `--<uuid>` suffix keeps the key collision-proof regardless of the
    original filename; leading with the sanitized filename keeps keys
    scannable in the bucket and surfaces the filename in list responses
    without a per-asset HEAD. Downloads use the embedded name for a
    recognizable Content-Disposition.
    """
    now = datetime.now(UTC)
    if "." in safe_name:
        stem, _, ext = safe_name.rpartition(".")
        ext = ext.lower()
    else:
        stem, ext = safe_name, "bin"
    return f"audio/{now.year:04d}/{now.month:02d}/{stem}--{uuid.uuid4()}.{ext}"


def process_upload(
    file_data: bytes,
    filename: str,
    content_type: str,
    content_length: int | None = None,
    key_prefix: str | None = None,
    audio_only: bool = False,
) -> FileUploadResponse:
    """Validate and process a file upload. Raises UploadError on failure."""
    if not filename:
        raise UploadError("No filename provided")

    if content_length and content_length > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    if content_type not in ALLOWED_TYPES:
        raise UploadError(
            f"File type '{content_type}' not allowed", status_code=415
        )

    safe_name = sanitize_filename(filename)

    if not validate_extension_matches_type(safe_name, content_type):
        raise UploadError(
            "File extension does not match declared content type",
            status_code=415,
        )

    if len(file_data) == 0:
        raise UploadError("Empty file")

    if len(file_data) > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    # B2 buckets are always versioned — uploading the same key creates a new
    # version automatically. No duplicate rejection needed.
    is_audio = content_type in AUDIO_MIME_TYPES or content_type.startswith("audio/")
    if audio_only and not is_audio:
        raise UploadError("Reference clips must be audio files", status_code=415)
    if key_prefix is not None:
        key = f"{key_prefix}{safe_name}"
    else:
        key = _audio_key_for(safe_name) if is_audio else f"uploads/{safe_name}"

    # Extract metadata BEFORE uploading so we can stamp audio fields onto the
    # B2 object (`x-amz-meta-*`). The dashboard aggregates HEAD each object to
    # sum durations and bucket formats; without this stamp we'd be back to the
    # "Total Duration: 0:00" placeholder.
    detail = extract_metadata(file_data, safe_name, content_type)
    s3_meta = to_s3_metadata(detail) if is_audio else {}

    result = upload_file(file_data, key, content_type, metadata=s3_meta or None)

    return FileUploadResponse(
        key=result.key,
        filename=result.filename,
        size_bytes=result.size_bytes,
        size_human=result.size_human,
        content_type=content_type,
        uploaded_at=result.uploaded_at,
        url=result.url,
        metadata=detail,
    )
