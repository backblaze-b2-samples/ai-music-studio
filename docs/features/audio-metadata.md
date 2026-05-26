<!-- last_verified: 2026-05-26 -->
# Feature: Audio Metadata Extraction

## Purpose
Read duration, sample rate, channels, bit depth, and codec from an uploaded audio file and return them alongside the upload response. Pure-Python: stdlib `wave` for uncompressed WAV, `mutagen` for everything else. No ffmpeg dependency.

## Used By
- API: `POST /upload` (called after the B2 put)
- UI: upload results (`FileMetadataDetail`), audio asset cards (downstream — see [Track Library](track-library.md))

## Core Functions
- `services/api/app/service/audio_metadata.py` — `extract_metadata()`, `extract_audio_metadata()`, `_extract_wav_metadata()`, `_extract_mutagen_metadata()`, `to_s3_metadata()`, `S3_AUDIO_META_KEYS`
- `apps/web/src/components/files/file-metadata-panel.tsx` — displays metadata in structured card

## Canonical Files
- Audio metadata pattern: `services/api/app/service/audio_metadata.py`
- Metadata display component: `apps/web/src/components/files/file-metadata-panel.tsx`

## Inputs
- file_data: bytes
- filename: string
- content_type: string

## Outputs
- `FileMetadataDetail`: filename, size_bytes, size_human, mime_type, extension, md5, sha256, uploaded_at
- Audio-specific (populated when `content_type` matches `audio/*`): `duration_ms`, `sample_rate`, `channels`, `bit_depth`, `codec`

## Supported formats
- `.wav` — stdlib `wave` (uncompressed PCM, reported as `codec=wav`); falls back to mutagen for compressed WAV containers
- `.mp3 / .mp3` — mutagen (`MP3`)
- `.flac` — mutagen (`FLAC`)
- `.ogg / .opus` — mutagen (`OggVorbis` / `OggOpus`)
- `.m4a / .aac / .mp4` — mutagen (`MP4`)

## Flow
- Upload route receives audio and stores it in B2 under `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>`
- `extract_metadata()` called with file bytes, filename, content type **before** the B2 put
- Computes MD5 and SHA-256 hashes (treated as `usedforsecurity=False`)
- If content type starts with `audio/`, dispatch:
  - WAV extension -> `_extract_wav_metadata()` via stdlib `wave`
  - Otherwise -> `_extract_mutagen_metadata()` via mutagen's container sniffer
- `to_s3_metadata(detail)` serializes the non-`None` audio fields to a `dict[str, str]` and the Upload pipeline passes it to `upload_file(..., metadata=...)`, which forwards it to `put_object` as `Metadata=...`. The resulting B2 object carries the values as `x-amz-meta-*` user metadata, which is read back by the Library list and dashboard aggregates without re-decoding the file.
- Returns `FileMetadataDetail`; audio fields are `None` when extraction fails (and any `None` field is dropped from the S3 metadata block rather than stamped as an empty string)

## S3 user metadata stamping
On upload, the audio-specific fields are stamped onto the B2 object as `x-amz-meta-*` user metadata. Header values are ASCII-only and the keys use kebab-case (S3 folds header names to lower-case, so they read back the same way). The keys come from `S3_AUDIO_META_KEYS` in `services/api/app/service/audio_metadata.py`:

- `duration-ms` (from `FileMetadataDetail.duration_ms`)
- `sample-rate` (from `FileMetadataDetail.sample_rate`)
- `channels` (from `FileMetadataDetail.channels`)
- `bit-depth` (from `FileMetadataDetail.bit_depth`)
- `codec` (from `FileMetadataDetail.codec`)

`services/api/app/service/library.py::_metadata_from_head` reads these back from the HEAD response when the Library list and dashboard aggregates fan out. Externally-seeded files (objects under `audio/` that didn't go through this Upload pipeline) have no `x-amz-meta-*` block; they still list and play, but their audio fields stay `None` and they contribute `0` to the dashboard's total duration.

## Error modes
- **Corrupt audio** -> extractor logs a warning, returns `{}`, upload still succeeds with `None` audio fields. We never 500 on a metadata failure.
- **Unsupported codec** -> mutagen returns `None` for `audio` object; extractor returns `{}`.
- **Truncated `.wav`** -> stdlib `wave` raises; falls back to mutagen (which may also fail). Result is `{}`.
- **Compressed WAV** -> stdlib `wave` raises; mutagen handles via `WAVE` plugin.

## UX States
- Not applicable (metadata is part of the upload response and the asset card metadata strip)

## Verification
- Test files: extend `services/api/tests/` with audio-metadata coverage (1 second of silence WAV, corrupt bytes, unsupported MIME) — not shipped in the scaffold
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Reference-Clip Upload](reference-upload.md)
- [Track Library](track-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
