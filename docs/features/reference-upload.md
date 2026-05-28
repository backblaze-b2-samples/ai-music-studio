<!-- last_verified: 2026-05-26 -->
# Feature: Reference-Clip Upload

## Purpose
Lets a user upload an inspiration / reference audio clip into an existing
project so a future generation can condition on it (provider-dependent —
mock provider ignores it, real Suno can take a reference). The reference
file lives at `projects/<project-id>/reference/<safe-filename>` in B2 so
it sits alongside the project's tracks and stems and is captured by the
Project Asset Explorer view.

## Used By
- UI: project detail page — Project Files tab reference-clip drop zone
- API: `POST /projects/{project_id}/reference`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — drag-and-drop + file picker, progress bar, error toasts
- `apps/web/src/components/upload/dropzone.tsx` — drag-target primitive
- `apps/web/src/components/upload/upload-progress.tsx` — chunked progress UI
- `apps/web/src/lib/api-client.ts::uploadProjectReference` — multipart POST
- `apps/web/src/lib/queries.ts::useUpload, useProjectAssets` — TanStack hooks
- `services/api/app/runtime/upload.py` — `POST /upload` route handler
- `services/api/app/service/upload.py` — filename sanitization, content-type sniff, key composition, metadata stamping
- `services/api/app/service/audio_metadata.py` — `extract_metadata`, `to_s3_metadata`
- `services/api/app/repo/b2_client.py::upload_file` — single `PutObject` call with `Metadata=…`

## Canonical Files
- Upload service pattern: `services/api/app/service/upload.py`
- B2 put with metadata: `services/api/app/repo/b2_client.py::upload_file`

## Inputs
- `POST /upload` multipart form:
  - `file: UploadFile` — the audio bytes
- Max size: `MAX_FILE_SIZE` from `services/api/app/config/settings.py` (default 100 MB)

## Outputs
- `POST /upload` -> `{ key: string, metadata: FileMetadataDetail }`
  - `key` is `projects/<id>/reference/<safe-filename>` (no `--<uuid>` suffix — references are addressed by name within their project, not globally)
  - `metadata` carries `duration_ms`, `sample_rate`, `channels`, `bit_depth`, `codec` when extraction succeeds, plus `md5` / `sha256` / `mime_type`
- Side effects: B2 object created with `x-amz-meta-*` user metadata stamped onto it; `useProjectAssets` query is invalidated so the Project Asset Explorer refreshes

## Flow
- User opens the project page and drops a file into the reference-clip dropzone
- The web layer sanitizes the filename (`service/upload.py::_safe_filename` lowercases, strips path separators, replaces non-`[A-Za-z0-9._-]` characters with `-`) and builds the destination key
- `extract_metadata` reads the file in memory (stdlib `wave` for `.wav`, `mutagen` for everything else) and produces `FileMetadataDetail`
- `to_s3_metadata(detail)` emits the audio sub-fields as a `dict[str, str]` (kebab-case keys, ASCII values)
- `b2_client.upload_file(bytes, key, content_type, metadata=…)` issues one `PutObject` with `Metadata=…`. B2 stamps those as `x-amz-meta-*` headers on the object, readable later via HEAD without redecoding the bytes
- API returns `{ key, metadata }`; the UI shows the upload in the Project Asset Explorer

## Edge Cases
- **Non-audio upload** -> 415; project references are audio-only
- **Path-traversal in filename** -> sanitizer strips `..`, `/`, `\`, `%00`, `\x00`
- **File too large** -> 413 from the API with `X-Max-Size` header
- **Unsupported content type** -> 415 (non-audio MIME types accepted into `uploads/`, not `projects/<id>/reference/`)
- **Metadata extraction failure** -> upload still succeeds with audio-specific fields `None`; never blocks the put
- **B2 unreachable** -> 502 from the upload route

## UX States
- Idle: drop zone with "Drop a reference clip here, or click to browse"
- Dragging: highlighted border
- Uploading: progress bar with bytes/total
- Success: toast + the new asset appears in the Project Asset Explorer
- Error: toast with the API error message

## Verification
- Test files: `services/api/tests/test_upload_conflict.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Audio Metadata Extraction](audio-metadata.md)
- [Project Asset Explorer](project-asset-explorer.md)
- [Projects](projects.md)
- [Generation](generation.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
