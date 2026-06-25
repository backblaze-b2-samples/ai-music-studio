<!-- last_verified: 2026-06-24 -->
# Feature: Music Generation

## Purpose
Turn a prompt + branch controls into a B2-resident track with full
provenance (prompt, provider ids, branch mode, parent track) recorded in a sidecar
`track.json`. The provider call is hidden behind the `MusicProvider`
interface so a real backend (Suno, Udio, in-house model) can be swapped
in without touching service / runtime code.

## Used By
- UI: `GenerateForm` inside `/projects/[id]`
- API:
  - `POST /projects/{id}/generate`
  - `GET /projects/{id}/generations/{track_id}`
  - `GET /projects/{id}/tracks/{track_id}`
  - `GET /projects/{id}/tracks/{track_id}/playback`
  - `GET /projects/{id}/tracks/{track_id}/download`

## Core Functions
- `apps/web/src/components/generation/generate-form.tsx` — prompt textarea, free-text style + avoid inputs, instrumental toggle, branch-mode controls, **Generate** button (drives `useGenerate`, emits the pending-generation UI state)
- `apps/web/src/lib/queries.ts::useGenerate, useProjectTrack`
- `apps/web/src/lib/api-client.ts::generateTrack, getProjectTrack, getTrackPlaybackUrl, getTrackDownloadUrl`
- `services/api/app/runtime/generation.py` — FastAPI routes
- `services/api/app/service/generation_jobs.py` — in-process queue + pollable status snapshots
- `services/api/app/service/generation.py::generate_track` — orchestrates provider call, B2 put, sidecar write, manifest bump
- `services/api/app/repo/music_provider.py` — `MusicProvider`, `MusicApiProvider`, `get_provider()`
- `services/api/app/repo/b2_projects.py::put_json` — `track.json` sidecar write
- `services/api/app/repo/b2_client.py::upload_file` — audio bytes upload
- `services/api/app/service/audio_metadata.py` — duration / sample rate / etc, stamped onto the B2 object

## Canonical Files
- Provider boundary: `services/api/app/repo/music_provider.py`
- Generation orchestration: `services/api/app/service/generation.py`

## Inputs
- `POST /projects/{id}/generate` body (`GenerationRequest`):
  - `prompt: string` (1-2000 chars, required)
  - `style?: string` (max 1000 chars; sent as one provider style string; the UI does not force a preset list)
  - `negative_tags?: string` (max 1000 chars; MusicAPI `negative_tags`; styles/elements to avoid)
  - `make_instrumental?: boolean` (MusicAPI `make_instrumental`; generate without vocals)
  - `generation_mode?: "create" | "new_take" | "extend" | "restyle"`
  - `continue_at_sec?: int` (for `extend`; defaults to parent duration when omitted)
  - `audio_weight?: float` (for `restyle`; MusicAPI cover influence from 0 to 1, default 0.6)
  - `duration_sec?: int` (legacy API field; the MusicAPI provider ignores it, so the UI does not send it)
  - `parent_track_id?: string` (when branching)

## Outputs
- `POST /projects/{id}/generate` -> `GenerationStatus(state="queued")`
- `GET /projects/{id}/generations/{track_id}` -> `GenerationStatus`
- `GET /projects/{id}/tracks/{track_id}` -> `Track`
- `/playback` -> `{ url, expires_in: 600 }` — inline presigned GET (no Content-Disposition)
- `/download` -> `{ url, expires_in: 600 }` — presigned GET with `Content-Disposition: attachment`
- Side effects: audio object created at `projects/<id>/tracks/<track-id>/audio.<ext>`, `track.json` written next to it, `project.json::track_count` incremented best-effort

## Provider abstraction
- `MusicProvider.generate(prompt, style, negative_tags, make_instrumental, generation_mode, parent_provider_clip_id, continue_at_sec, audio_weight, duration_sec, **kwargs) -> GenerationResult` returns `{ track_id, audio_bytes, audio_ext, provider, generation_ms, provider_task_id, provider_clip_id, notes }`.
- `MusicApiProvider` (default — env var `MUSIC_PROVIDER=musicapi`): calls [musicapi.ai](https://musicapi.ai), a Suno-compatible REST API with free credits on signup. POSTs to `/api/v1/sonic/create` with `task_type=create_music` for new tracks/new takes, `task_type=extend_music` plus `continue_clip_id`/`continue_at` for Extend, and `task_type=cover_music` plus `custom_mode=true`, `auto_lyrics=true`, `continue_clip_id`, optional `tags`, and `audio_weight` for Restyle. It also forwards `negative_tags` and `make_instrumental=true` when set. It accepts `task_id` from either `data` or the top-level response body, polls `/api/v1/sonic/task/{task_id}` every 5 s until `state == "succeeded"` (or fails on `"failed"` / 5-minute timeout), then downloads the MP3 from `mp3_url`/`audio_url` and persists the returned `clip_id` for future provider-native branches. Reads `MUSICAPI_API_KEY` from settings; the key is server-side only and never sent to the browser.
- Selection happens in `get_provider()`; an unknown name fails fast with `ValueError`.

## Flow
- Runtime validates project_id, optional auth, and the generation rate limit, then writes a queued `GenerationStatus`
- A background in-process worker calls `generate_track(...)`; if `generation_mode` is `extend` or `restyle`, service loads the parent track and requires `provider_clip_id`
- On submit, the UI adds a pending block to the revision tree immediately and polls `GET /projects/{id}/generations/{track_id}`. Success clears the pending row and refetches revisions; failure leaves the row visible with the provider error until dismissed.
- The worker calls `get_provider().generate(...)` and receives audio bytes + provider metadata
- `audio_metadata.extract_metadata(...)` parses duration / sample-rate / channels / codec from the bytes (same code path as the Upload pipeline)
- Repo writes audio to `projects/<id>/tracks/<track-id>/audio.<ext>` with `x-amz-meta-*` stamped from the metadata extractor + branch metadata + `parent-track-id` + `project-id` + `provider`
- Service builds the `Track` model and `put_json`s `track.json` next to the audio — its presence is what makes the track discoverable by the revision-tree builder
- Service bumps `project.track_count` (best-effort; manifest write failure logs WARN and moves on)
- TanStack Query invalidates the revision-tree, project, and project-assets queries on success so the UI re-renders without a manual refresh

## Polling behavior
Generation work runs in an in-process background executor. This avoids
blocking the request handler while MusicAPI polls upstream, while keeping
the sample database-free: status snapshots live under
`projects/<id>/generations/<track-id>.json`.

## Error states
- **Provider raises `NotImplementedError`** -> 501 with the provider's message (defense-in-depth; no shipping provider raises this today)
- **Provider raises any other exception** -> 502 with `Provider error: <e>` and a server-side `logger.exception(...)` (covers MusicAPI HTTP errors, polling timeouts, `state == "failed"`, and missing credit). MusicAPI 401/403/429 responses are normalized into operator-readable hints before they cross the service boundary.
- **Project missing** -> 404 with `"Project not found"`
- **Malformed project id** -> 400
- **Extend/Restyle without parent provider clip id** -> 400
- **B2 put fails** -> bubbled as 500
- **Sidecar write fails after audio is uploaded** -> job status becomes failed; the audio object remains in B2 and `build_tree` can surface it as an orphan with a repair action

## Verification
- Test files: `services/api/tests/test_generation_service.py`, `services/api/tests/test_generation_runtime.py`, `services/api/tests/test_generation_request_validation.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Projects](projects.md)
- [Revision History](revision-history.md)
- [Audio Metadata Extraction](audio-metadata.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
