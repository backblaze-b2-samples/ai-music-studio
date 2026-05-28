"""Unit tests for upload filename handling."""

import re

from app.service import library as library_service
from app.service import upload as upload_service
from app.types import FileMetadataDetail, FileUploadResponse


def _stub_upload(
    monkeypatch,
    captured: list[str] | None = None,
    captured_kwargs: list[dict] | None = None,
    metadata_detail: FileMetadataDetail | None = None,
):
    def _upload(file_data, key, content_type, metadata=None):
        if captured is not None:
            captured.append(key)
        if captured_kwargs is not None:
            captured_kwargs.append(
                {
                    "key": key,
                    "content_type": content_type,
                    "metadata": metadata,
                }
            )
        return FileUploadResponse(
            key=key,
            filename=key.rsplit("/", 1)[-1],
            size_bytes=len(file_data),
            size_human="5 B",
            content_type=content_type,
            uploaded_at="2026-02-14T00:00:00Z",
            url=None,
            metadata=None,
        )

    monkeypatch.setattr(upload_service, "upload_file", _upload)
    monkeypatch.setattr(
        upload_service,
        "extract_metadata",
        lambda file_data, filename, content_type: metadata_detail,
    )


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    _stub_upload(monkeypatch)

    result = upload_service.process_upload(
        file_data=b"hello",
        filename="report.txt",
        content_type="text/plain",
        content_length=5,
    )

    assert result.key == "uploads/report.txt"


def test_audio_upload_embeds_sanitized_filename_in_key(monkeypatch):
    """Audio keys are `audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>` so the
    user's filename survives into list responses and downloads."""
    _stub_upload(monkeypatch)

    result = upload_service.process_upload(
        file_data=b"RIFF\x00\x00\x00\x00WAVEfmt ",
        filename="My Cool Kick.wav",
        content_type="audio/wav",
        content_length=16,
    )

    # Sanitization replaces unsafe chars (space → _) before key construction.
    assert re.match(
        r"^audio/\d{4}/\d{2}/My_Cool_Kick--[0-9a-f-]{36}\.wav$",
        result.key,
    ), result.key
    # And the Library helper recovers the filename portion for display/download.
    assert library_service._filename_from_key(result.key) == "My_Cool_Kick.wav"


def test_filename_from_key_handles_externally_seeded_files():
    """Files dropped into the bucket outside the Upload pipeline have no
    `--` separator; the helper returns the full last segment."""
    assert (
        library_service._filename_from_key("audio/seed/sample.wav") == "sample.wav"
    )


def test_filename_from_key_preserves_double_dash_in_user_filename():
    """A sanitized filename may itself contain `--`; only the rightmost
    `--<uuid>` segment (before the extension) should be stripped."""
    key = "audio/2026/05/foo--bar--550e8400-e29b-41d4-a716-446655440000.wav"
    assert library_service._filename_from_key(key) == "foo--bar.wav"


def test_audio_upload_stamps_s3_metadata_on_upload_file(monkeypatch):
    """Audio uploads pass `to_s3_metadata(detail)` through to `upload_file`
    as kebab-case `x-amz-meta-*` keys, so the dashboard can HEAD the object
    and read back duration / sample rate / etc. Non-`None` extractor fields
    are serialized; `None` fields are dropped."""
    from datetime import UTC, datetime

    detail = FileMetadataDetail(
        filename="My_Cool_Kick.wav",
        size_bytes=16,
        size_human="16 B",
        mime_type="audio/wav",
        extension="wav",
        md5="deadbeef",
        sha256="cafebabe",
        uploaded_at=datetime(2026, 2, 14, tzinfo=UTC),
        duration_ms=1234,
        sample_rate=44100,
        channels=2,
        bit_depth=16,
        codec="wav",
    )
    captured_kwargs: list[dict] = []
    _stub_upload(
        monkeypatch,
        captured_kwargs=captured_kwargs,
        metadata_detail=detail,
    )

    upload_service.process_upload(
        file_data=b"RIFF\x00\x00\x00\x00WAVEfmt ",
        filename="My Cool Kick.wav",
        content_type="audio/wav",
        content_length=16,
    )

    assert len(captured_kwargs) == 1
    metadata = captured_kwargs[0]["metadata"]
    assert metadata == {
        "duration-ms": "1234",
        "sample-rate": "44100",
        "channels": "2",
        "bit-depth": "16",
        "codec": "wav",
    }
    # Sanity-check: every key is ASCII (S3 user-metadata requirement) and uses
    # the kebab-case spelling that `service/library.py::_metadata_from_head`
    # reads back.
    for k, v in metadata.items():
        assert k.isascii() and v.isascii()


def test_non_audio_upload_skips_s3_metadata(monkeypatch):
    """Non-audio uploads must not stamp audio fields — they land under
    `uploads/` and `upload_file` is called with `metadata=None`."""
    captured_kwargs: list[dict] = []
    _stub_upload(monkeypatch, captured_kwargs=captured_kwargs)

    upload_service.process_upload(
        file_data=b"hello",
        filename="report.txt",
        content_type="text/plain",
        content_length=5,
    )

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["metadata"] is None


def test_reference_upload_uses_project_reference_prefix(monkeypatch):
    captured: list[str] = []
    _stub_upload(monkeypatch, captured=captured)

    result = upload_service.process_upload(
        file_data=b"RIFF\x00\x00\x00\x00WAVEfmt ",
        filename="../Guide Clip.wav",
        content_type="audio/wav",
        content_length=16,
        key_prefix="projects/123e4567-e89b-42d3-a456-426614174000/reference/",
        audio_only=True,
    )

    assert result.key == (
        "projects/123e4567-e89b-42d3-a456-426614174000/reference/Guide_Clip.wav"
    )
    assert captured == [result.key]
