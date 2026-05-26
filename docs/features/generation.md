<!-- last_verified: 2026-05-26 -->
# Feature: Music Generation

## Purpose
Turn a prompt + style + duration into a B2-resident track with full
provenance (prompt, provider, parent track) recorded in a sidecar
`track.json`. The provider call is hidden behind the `MusicProvider`
interface so a real backend (Suno, Udio, in-house model) can be swapped
in without touching service / runtime code.

## Used By
- UI: `GenerateForm` inside `/projects/[id]`
- API:
  - `POST /projects/{id}/generate`
  - `GET /projects/{id}/tracks/{track_id}`
  - `GET /projects/{id}/tracks/{track_id}/playback`
  - `GET /projects/{id}/tracks/{track_id}/download`

## Core Functions
- `apps/web/src/components/generation/generate-form.tsx` — prompt textarea, style dropdown, duration input, **Generate** button (drives `useGenerate`)
- `apps/web/src/lib/queries.ts::useGenerate, useProjectTrack`
- `apps/web/src/lib/api-client.ts::generateTrack, getProjectTrack, getTrackPlaybackUrl, getTrackDownloadUrl`
- `services/api/app/runtime/generation.py` — FastAPI routes
- `services/api/app/service/generation.py::generate_track` — orchestrates provider call, B2 put, sidecar write, manifest bump
- `services/api/app/repo/music_provider.py` — `MusicProvider`, `MockMusicProvider`, `SunoMusicProvider`, `get_provider()`
- `services/api/app/repo/b2_projects.py::put_json` — `track.json` sidecar write
- `services/api/app/repo/b2_client.py::upload_file` — audio bytes upload
- `services/api/app/service/audio_metadata.py` — duration / sample rate / etc, stamped onto the B2 object

## Canonical Files
- Provider boundary: `services/api/app/repo/music_provider.py`
- Generation orchestration: `services/api/app/service/generation.py`

## Inputs
- `POST /projects/{id}/generate` body (`GenerationRequest`):
  - `prompt: string` (1-2000 chars, required)
  - `style?: string`
  - `duration_sec?: int` (5-300, default 30)
  - `parent_track_id?: string` (when branching)

## Outputs
- `POST /projects/{id}/generate` -> `Track` (id minted server-side, audio key derived from id + provider's extension)
- `GET /projects/{id}/tracks/{track_id}` -> `Track`
- `/playback` -> `{ url, expires_in: 600 }` — inline presigned GET (no Content-Disposition)
- `/download` -> `{ url, expires_in: 600 }` — presigned GET with `Content-Disposition: attachment`
- Side effects: audio object created at `projects/<id>/tracks/<track-id>/audio.<ext>`, `track.json` written next to it, `project.json::track_count` incremented best-effort

## Provider abstraction
- `MusicProvider.generate(prompt, style, duration_sec, **kwargs) -> GenerationResult` returns `{ track_id, audio_bytes, audio_ext, provider, generation_ms, notes }`.
- `MockMusicProvider` (default — env var `MUSIC_PROVIDER=mock`): pre-baked WAVs in `services/api/app/repo/_mock_tracks/` (`ambient.wav`, `upbeat.wav`, `mellow.wav`). `manifest.json` maps prompt keywords to files; no keyword match → deterministic pick keyed on prompt hash. Sleeps a few hundred ms so the UI's loading state is observable. Runs end-to-end with **zero external credentials**.
- `SunoMusicProvider` (env var `MUSIC_PROVIDER=suno`): currently raises `NotImplementedError` with a docstring pointing at the wiring spot. Real implementation reads `SUNO_API_KEY`, POSTs to Suno's generate endpoint, polls the job-status endpoint until `completed`, downloads the final mp3. Tracked in `docs/exec-plans/tech-debt-tracker.md`.
- Selection happens in `get_provider()`; an unknown name fails fast with `ValueError`.

## Flow
- Service validates project_id and existence of `project.json`
- `get_provider().generate(...)` returns audio bytes + provider metadata
- `audio_metadata.extract_metadata(...)` parses duration / sample-rate / channels / codec from the bytes (same code path as the Upload pipeline)
- Repo writes audio to `projects/<id>/tracks/<track-id>/audio.<ext>` with `x-amz-meta-*` stamped from the metadata extractor + `parent-track-id` + `project-id` + `provider`
- Service builds the `Track` model and `put_json`s `track.json` next to the audio — its presence is what makes the track discoverable by the revision-tree builder
- Service bumps `project.track_count` (best-effort; manifest write failure logs WARN and moves on)
- TanStack Query invalidates the revision-tree, project, and project-assets queries on success so the UI re-renders without a manual refresh

## Polling behavior
The MVP runs generation synchronously inside the request because the
mock provider returns instantly. For a real provider that takes 30-90s,
the recommended evolution is: change `generate_track` to enqueue a
background task and return a `GenerationStatus(track_id, state="queued")`
immediately; the UI polls `GET /projects/{id}/tracks/{track_id}` until
it succeeds. The `GenerationStatus` model and `polling` UX scaffolding
are deliberately present even though the synchronous path doesn't need
them yet — they're the wiring point. Tracked in tech debt.

## Error states
- **Provider raises `NotImplementedError`** -> 501 with the provider's message (used by Suno stub)
- **Provider raises any other exception** -> 502 with `Provider error: <e>` and a server-side `logger.exception(...)`
- **Project missing** -> 404 with `"Project not found"`
- **Malformed project id** -> 400
- **B2 put fails** -> bubbled as 500
- **Sidecar write fails after audio is uploaded** -> service returns 500 but the audio object remains in B2; a re-list under the project prefix would surface it as an orphan (tracked in tech debt; build_tree currently ignores audio objects with no sidecar)

## Verification
- Test files: extend `services/api/tests/` with mock-provider end-to-end coverage — not shipped in the scaffold (tech debt)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Projects](projects.md)
- [Revision History](revision-history.md)
- [Audio Metadata Extraction](audio-metadata.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
