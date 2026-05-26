"""Audio metadata extraction.

Inputs are the raw bytes of an uploaded audio file plus the filename and
declared content type. Outputs are duration_ms, sample_rate, channels,
bit_depth, and codec. We deliberately avoid ffmpeg — `.wav` is handled by
the stdlib `wave` module, everything else by `mutagen` (small, pure-Python).

If extraction fails for any reason (corrupt file, unsupported codec, format
we don't decode) we return Nones rather than raising. The upload still
succeeds — partial metadata is better than a 500 because the encoder
embedded an obscure tag.
"""

from __future__ import annotations

import hashlib
import io
import logging
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


# MIME content_types we recognize as audio. Mirrors the upload allowlist.
AUDIO_MIME_TYPES = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/x-flac",
        "audio/ogg",
        "audio/opus",
        "audio/mp4",
        "audio/aac",
        "audio/m4a",
        "audio/x-m4a",
    }
)


def _extract_wav_metadata(file_data: bytes) -> dict:
    """Extract metadata from a RIFF WAV file using the stdlib `wave` module.

    Returns at most: duration_ms, sample_rate, channels, bit_depth, codec.
    `wave` only handles uncompressed PCM; compressed WAV containers fall
    through to mutagen via the caller's chain.
    """
    try:
        import wave

        with wave.open(io.BytesIO(file_data), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_ms = round(frames * 1000 / rate) if rate else None
            return {
                "duration_ms": duration_ms,
                "sample_rate": rate,
                "channels": wf.getnchannels(),
                "bit_depth": wf.getsampwidth() * 8,
                "codec": "wav",
            }
    except Exception:
        logger.warning("WAV metadata extraction failed", exc_info=True)
        return {}


def _extract_mutagen_metadata(file_data: bytes, filename: str) -> dict:
    """Extract metadata using mutagen (mp3, flac, ogg, opus, m4a, aac).

    mutagen sniffs the container from the bytes; we pass the filename only
    as a hint for ambiguous cases.
    """
    try:
        from mutagen import File as MutagenFile

        bio = io.BytesIO(file_data)
        # `easy=False` keeps the underlying format object so we can read
        # info.length / info.sample_rate / info.bits_per_sample / info.channels.
        audio = MutagenFile(bio, easy=False)
        if audio is None or not getattr(audio, "info", None):
            return {}

        info = audio.info
        duration_ms = (
            round(getattr(info, "length", 0) * 1000)
            if getattr(info, "length", None) is not None
            else None
        )
        codec = type(audio).__name__.lower() if audio is not None else None
        return {
            "duration_ms": duration_ms,
            "sample_rate": getattr(info, "sample_rate", None),
            "channels": getattr(info, "channels", None),
            "bit_depth": getattr(info, "bits_per_sample", None),
            "codec": codec,
        }
    except Exception:
        logger.warning(
            "Mutagen metadata extraction failed for %s", filename, exc_info=True
        )
        return {}


def extract_audio_metadata(file_data: bytes, filename: str) -> dict:
    """Public entrypoint — pick a decoder based on extension/MIME.

    Returns a dict that may be empty if nothing decoded. All keys are a
    subset of the audio fields on `FileMetadataDetail`.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Prefer stdlib for plain WAV (no extra deps, deterministic).
    if ext == "wav":
        wav = _extract_wav_metadata(file_data)
        if wav:
            return wav

    # Everything else (and WAV fallback for compressed containers) — mutagen.
    return _extract_mutagen_metadata(file_data, filename)


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    """Compute common metadata + audio-specific metadata (when applicable)."""
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}
    if content_type in AUDIO_MIME_TYPES or content_type.startswith("audio/"):
        extra = extract_audio_metadata(file_data, filename)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
        **extra,
    )


# Keys we stamp onto the B2 object as user metadata. S3 only accepts ASCII
# and folds header names to lower-case kebab-case, so we keep these names
# stable and read them back the same way in `service/library.py`.
S3_AUDIO_META_KEYS = ("duration-ms", "sample-rate", "channels", "bit-depth", "codec")


def to_s3_metadata(detail: FileMetadataDetail | None) -> dict[str, str]:
    """Serialize audio fields onto the S3 `x-amz-meta-*` surface.

    Only emits keys whose source field is set — a wav without bitrate stays
    out of the metadata block rather than being stamped with an empty string,
    so HEAD reads don't have to distinguish "absent" from "blank".
    """
    if detail is None:
        return {}
    pairs: list[tuple[str, object | None]] = [
        ("duration-ms", detail.duration_ms),
        ("sample-rate", detail.sample_rate),
        ("channels", detail.channels),
        ("bit-depth", detail.bit_depth),
        ("codec", detail.codec),
    ]
    return {k: str(v) for k, v in pairs if v is not None}
