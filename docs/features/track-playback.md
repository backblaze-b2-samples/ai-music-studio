<!-- last_verified: 2026-05-26 -->
# Feature: Track Playback & Download

## Purpose
Stream a generated track (or one of its stems) inline in the browser, or
download it as a file, without proxying audio bytes through the API. Every
playback / download URL is a short-lived (10-minute) presigned S3 GET
minted from the repo layer. Inline playback uses no `Content-Disposition`;
the download endpoint adds `Content-Disposition: attachment` with an
RFC 5987–encoded filename so non-ASCII names survive the round trip.

## Used By
- UI: project detail page (currently-selected track in the revision tree), Track Library card (cross-project listing)
- API:
  - `GET /projects/{project_id}/tracks/{track_id}/playback`
  - `GET /projects/{project_id}/tracks/{track_id}/download`
  - `GET /library/{key}/playback` (cross-project Library, see [Track Library](track-library.md))
  - `GET /library/{key}/download`

## Core Functions
- `apps/web/src/components/revision-tree/track-node.tsx` — Play / Download buttons on each tree node
- `apps/web/src/components/library/audio-asset-card.tsx` — Play / Download / Delete on the cross-project card
- `apps/web/src/lib/api-client.ts::getTrackPlaybackUrl, getTrackDownloadUrl, getLibraryPlaybackUrl, getLibraryDownloadUrl`
- `apps/web/src/lib/queries.ts` — query hooks that fetch and cache presigned URLs
- `services/api/app/runtime/generation.py::playback_endpoint, download_endpoint` — project-scoped routes
- `services/api/app/runtime/library.py` — cross-project Library routes
- `services/api/app/repo/b2_projects.py::presign_track_playback` — inline presign (no `Content-Disposition`)
- `services/api/app/repo/b2_tracks.py::presign_audio_playback` — inline presign for `audio/`-prefix assets
- `services/api/app/repo/b2_client.py::get_presigned_url` — presign that **does** set `Content-Disposition: attachment` with `filename*` (RFC 5987)

## Canonical Files
- Presign with attachment + RFC 5987: `services/api/app/repo/b2_client.py::get_presigned_url`
- Inline presign: `services/api/app/repo/b2_projects.py::presign_track_playback`

## Inputs
- `project_id: string` (UUID-4) and `track_id: string` (UUID-4) — path params
- For Library variants: `key: string` matching `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus)$`

## Outputs
- Project-scoped: `GET /projects/{pid}/tracks/{tid}/playback` -> `{ url: string, expires_in: 600 }`
- Project-scoped: `GET /projects/{pid}/tracks/{tid}/download` -> `{ url: string, expires_in: 600 }`
- Library: `GET /library/{key}/playback` -> `{ url, expires_in: 600 }`
- Library: `GET /library/{key}/download` -> `{ url, expires_in: 600 }`
- Side effects: none — presign is read-only against S3. Library downloads also bump a small in-memory counter exposed on `/library/stats` (project-scoped downloads do not — they're per-project, not aggregate).

## Flow
- Project track:
  1. Route reads `projects/<pid>/tracks/<tid>/track.json` from B2 to discover the audio extension (`.wav` for mock, `.mp3` for typical real providers)
  2. Builds the audio key `projects/<pid>/tracks/<tid>/audio.<ext>`
  3. `presign_track_playback` (inline) or `get_presigned_url(..., filename=…)` (attachment) mints the URL with a 10-minute expiry
  4. Returns `{ url, expires_in: 600 }`. The browser fetches the audio directly from B2 — the API never proxies bytes.
- Library track:
  1. Validate `key` against `AUDIO_KEY_RE`
  2. HEAD the key to 404 cleanly on a listed-but-missing artifact
  3. Mint the inline / attachment URL with the same 10-min expiry
- Stems are presigned via the same project-scoped helpers when they exist; generation depends on optional `STEM_SPLITTER_COMMAND` configuration — see [Stems](stems.md).

## Edge Cases
- **Track sidecar missing** -> 404 "Track not found"
- **Audio key listed but HEAD 404 (transient B2 consistency)** -> 404 on the playback / download route; the rest of the page still renders
- **Malformed project / track id** -> 400 before B2 is touched
- **Non-ASCII filename on download** -> `Content-Disposition: attachment; filename*=UTF-8''…` (RFC 5987). Browsers without RFC 5987 support fall back to the percent-encoded `filename=` parameter, which is also set.
- **Presigned URL expired** -> client gets S3's 403 directly; the UI catches the audio-element error and re-fetches a fresh URL
- **B2 unreachable during presign** -> 502 from the API (presign itself doesn't reach B2, but the HEAD pre-check can)

## UX States
- Idle: Play / Download buttons enabled
- Loading: button spinner while the presign request is in flight (usually <100 ms)
- Playing: inline `<audio controls>` mounted under the tree node
- Error: toast with retry; the track row stays visible

## Verification
- Test files: `services/api/tests/test_playback.py` (presign happy path, attachment Content-Disposition, RFC 5987 filename encoding, missing key → 404)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Track Library](track-library.md)
- [Revision History](revision-history.md)
- [Stems](stems.md)
- [Audio Metadata Extraction](audio-metadata.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
