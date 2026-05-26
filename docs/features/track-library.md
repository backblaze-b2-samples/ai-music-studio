<!-- last_verified: 2026-05-26 -->
# Feature: Track Library

## Purpose
List, play back, download, and delete every audio asset stored under
the `audio/` prefix in B2 — sourced entirely from S3 list/head/delete so
there is no application database. The Track Library is the
**cross-project** view: it doesn't filter by project. For a per-project
view, see [Project Asset Explorer](project-asset-explorer.md).

## Used By
- UI: `/library` page
- API:
  - `GET /library`
  - `GET /library/{key}/playback`
  - `GET /library/{key}/download`
  - `DELETE /library/{key}`
  - `POST /library/bulk-delete`

## Core Functions
- `apps/web/src/components/library/library-view.tsx` — responsive grid (`sm:grid-cols-2 xl:grid-cols-3`), Refresh button, skeletons, EmptyState, ErrorState, multi-select header, bulk-delete confirm dialog
- `apps/web/src/components/library/audio-asset-card.tsx` — individual card: selection checkbox, title preview, metadata strip, inline `<Waveform />`, Play / Download / Delete (AlertDialog confirm), inline `<audio controls>` on Play
- `apps/web/src/components/library/waveform.tsx` — lightweight SVG waveform stub
- `apps/web/src/lib/queries.ts::useLibrary, useDeleteAudioAsset, useBulkDeleteAudioAssets`
- `apps/web/src/lib/api-client.ts::getLibrary, getPlaybackUrl, getLibraryDownloadUrl, deleteAudioAsset, bulkDeleteAudioAssets`
- `services/api/app/runtime/library.py` — FastAPI routes
- `services/api/app/service/library.py` — key validation, listing, delete, bulk delete, aggregates
- `services/api/app/repo/b2_tracks.py::list_audio_objects, head_audio_object, head_track_objects_parallel, delete_audio_object, delete_audio_objects_batch, presign_audio_playback`

## Canonical Files
- Pattern exemplar: `apps/web/src/components/library/audio-asset-card.tsx`
- Service orchestration: `services/api/app/service/library.py`

## Inputs
- `limit: int` (query param on `GET /library`, default 100, max 500)
- `key: string` (path param on `/library/{key}/...`) — must match `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus)$` (case-insensitive) and contain no `..` or `//`
- `POST /library/bulk-delete` body: `{ keys: string[] }` (1-1000 keys, each matching the same regex)

## Outputs
- `GET /library` -> `AudioAsset[]` sorted newest-first
- `GET /library/{key}/playback` -> `{ url, expires_in }` — inline presigned GET
- `GET /library/{key}/download` -> `{ url, expires_in }` — presigned GET with `Content-Disposition: attachment`
- `DELETE /library/{key}` -> `{ deleted: true, key }`
- `POST /library/bulk-delete` -> `{ deleted: string[], errors: { Key, Code, Message }[] }`
- Side effects: TanStack Query invalidates library + stats on delete

## Library vs. Project Asset Explorer vs. Files
- **Track Library** (`/library`) — every object under the `audio/` prefix, across all projects. Audio-only UX (playback, waveform, formatted duration).
- **Project Asset Explorer** (inside a project page) — every object under `projects/<id>/…`, scoped to one project. Includes manifests, sidecars, and stems.
- **Files** (`/files`) — full B2 bucket explorer, every object regardless of prefix. Ops-style.

In v1 the project-scoped tracks (`projects/<id>/tracks/<id>/audio.<ext>`)
don't show up in `/library` because the Library only scans `audio/`.
Tracking this in tech debt — a future iteration may broaden the Library
listing to include project-scoped tracks (with a project chip on each
card).

## Flow
- `GET /library` -> `list_objects_v2(Prefix="audio/")` -> sort newest-first -> fan out HEADs via `head_track_objects_parallel` (10 workers) to pull `duration_ms`, `sample_rate`, `channels`, `bit_depth`, `codec` from `x-amz-meta-*` -> return
- Playback / download -> validate key -> HEAD for existence -> mint presigned URL -> return
- Delete -> validate -> `delete_object` -> 200
- Bulk delete -> validate every key, deduplicate, one `DeleteObjects` call (chunks of 1000) -> `{ deleted, errors }`

## Edge Cases
- **Listed-but-not-head-able key** -> playback / download return 404 (transient B2 consistency artifact); the rest of the library still renders
- **Malformed key** -> 400 from the API before B2 is touched
- **Missing key** -> 404
- **B2 unreachable** -> 500
- **Empty prefix** -> 200 with `[]`; the UI shows an EmptyState

## UX States
- Loading: 6 skeleton cards
- Empty: "Nothing here yet — Generate a track from a project to see it appear in the cross-project library"
- Loaded: responsive grid of `AudioAssetCard`s
- Error: `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_bulk_delete.py` (library half — happy path, non-audio prefix rejection, path-traversal rejection, partial errors)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Project Asset Explorer](project-asset-explorer.md)
- [Audio Metadata Extraction](audio-metadata.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
