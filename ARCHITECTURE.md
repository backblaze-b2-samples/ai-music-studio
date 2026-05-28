<!-- last_verified: 2026-05-26 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - **Projects** (`/projects`) — list, create, archive, delete; cards
    show track count and a link to the studio
  - **Project Studio** (`/projects/[id]`) — `GenerateForm`,
    `RevisionTree` (indented list), `TrackNode` (per-track player +
    branch / A / B / Generate Stems), `CompareDialog` (dual
    `<audio>` + diff list), plus a "Project Files" tab rendering
    `ProjectAssetExplorer` scoped to `projects/<id>/`, and reference upload
  - **Track Library** (`/library`) — cross-project `AudioAssetCard`
    grid; every generated track in one view, inline playback and delete
  - **Files** (`/files`) — full B2 bucket explorer (tree view, preview,
    download, delete) — **unchanged from the underlying starter**
  - Dashboard with music-studio metrics (total tracks, total duration,
    daily generation activity, recent tracks table)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for projects, generation, revisions/compare, the
    Track Library, and the full-bucket explorer
  - B2 S3 integration via boto3 (single client; lru-cached)
  - `MusicProvider` abstraction (mock + Suno stub)
  - Audio metadata extraction (`.wav` via stdlib `wave`, everything else
    via `mutagen` — no ffmpeg)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (`Project`, `Track`,
    `RevisionNode`, `TrackDiff`, `Stem`, `AudioAsset`, `FileMetadata`, …)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client + MusicProvider) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. **Generation-API HTTP clients (`requests`, `httpx`) only allowed in `repo/music_provider.py`** — mirrors the boto3 rule
5. All boundary data uses Pydantic models (no raw dicts across layers)
6. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                     App entrypoint, middleware, router registration
  app/
    types/                    Pydantic models (Project, Track, Stem, AudioAsset, FileMetadata, …)
    config/                   Settings loaded from environment
    repo/
      b2_client.py            Generic B2 file helpers (incl. shared `get_s3_client`)
      b2_tracks.py            Audio-prefix helpers (list / head-parallel / delete / playback presign)
      b2_projects.py          Project-scoped helpers (put_json, get_json, list, delete tree, presign)
      music_provider.py       MusicProvider interface + MusicApiProvider (calls musicapi.ai)
    service/                  Business logic — projects, generation, revisions, stems, library, upload, audio_metadata, files
    runtime/                  FastAPI route handlers — health, projects, generation, revisions, library, files, upload, metrics
  tests/                      pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No generation-API leakage**: `requests` / `httpx` may only be imported by `app/repo/music_provider.py`. Service / runtime go through `get_provider()`.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. Project ids validated against `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`. Audio asset keys validated against `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus)$` (case-insensitive) with explicit `..` / `//` rejection before any B2 call.
- **Custom user agent**: every `boto3.client("s3", …)` sets `Config(user_agent_extra="b2ai-ai-music-studio")`. No `b2-native` calls.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). The sole data store; no database.

**Canonical prefix layout:**

```
projects/<project-id>/project.json                        # ProjectManifest (JSON)
projects/<project-id>/tracks/<track-id>/audio.<ext>       # generated audio bytes
projects/<project-id>/tracks/<track-id>/track.json        # Track sidecar (carries parent_track_id)
projects/<project-id>/tracks/<track-id>/stems/<name>.wav  # stems (placeholder)
projects/<project-id>/reference/<safe-filename>           # reference clip uploads
audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>           # legacy/cross-project library prefix
uploads/<safe-filename>                                   # generic uploads (kept for parity)
```

The Library (`/library`) lists legacy `audio/` objects plus generated
project-track audio. The Project Studio reads/writes only under
`projects/<id>/`. The full-bucket Files explorer sees everything.

## External Services

- **Backblaze B2 S3 API** — audio storage, retrieval, deletion, presigned URLs.
- **Music generation provider** — abstracted via `MusicProvider`. `MusicApiProvider` calls [musicapi.ai](https://musicapi.ai) (Suno-compatible REST API, free credits on signup).

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **API -> Music Provider** — server-side only; `MUSICAPI_API_KEY` is never sent to the browser
- **Client -> B2** — presigned URLs for playback (inline) and download (attachment); 10-min expiry

## Data Flows

- **Generation**: Browser -> `POST /projects/{id}/generate` -> runtime validates project/auth/rate-limit -> service writes queued `GenerationStatus` -> in-process worker calls `get_provider().generate(...)` -> bytes returned -> repo writes audio to `projects/<id>/tracks/<track-id>/audio.<ext>` with S3 user metadata (duration / sample-rate / channels / parent-track-id / project-id / provider) -> service writes `track.json` sidecar -> service increments `project.track_count` -> UI polls `GET /projects/{id}/generations/{track_id}`.
- **Revision tree**: Browser -> `GET /projects/{id}/revisions` -> service lists every `track.json` sidecar and any audio objects missing sidecars under the project prefix -> threads them by `parent_track_id` -> returns a list of root `RevisionNode`s, each recursively populated.
- **Compare**: Browser -> `GET /projects/{id}/compare?a=...&b=...` -> service loads both tracks (404 if missing) -> returns a `TrackDiff` (booleans for prompt / style / duration / audio-metadata changes).
- **Track playback / download**: Browser -> `GET /projects/{id}/tracks/{track_id}/playback|download` -> service reads the audio key out of the sidecar (extension isn't fixed) -> repo mints a presigned GET (inline for playback, `Content-Disposition: attachment` for download) -> browser streams bytes directly from B2.
- **Library list**: Browser -> `GET /library` -> service lists `audio/` plus generated project-track audio -> HEADs every key in parallel for stamped metadata -> returns `AudioAsset[]`.
- **Bucket explorer**: Browser -> `GET /files` -> service calls repo with empty prefix -> returns full bucket tree (unchanged from starter).
- **Project asset explorer**: Browser -> `GET /files?prefix=projects/<id>/` -> reuses the bucket-explorer route under the hood, scoped to one project (no separate API surface needed).

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Music-studio domain models: `services/api/app/types/project.py`
- Music-studio orchestration: `services/api/app/service/generation.py`, `service/revisions.py`, `service/projects.py`, `service/stems.py`
- B2 project-scoped helpers: `services/api/app/repo/b2_projects.py`
- Generation provider boundary: `services/api/app/repo/music_provider.py`
- Audio metadata extractor: `services/api/app/service/audio_metadata.py`
- Generic B2 + library helpers: `services/api/app/repo/b2_client.py`, `repo/b2_tracks.py`
- Structural tests (incl. MusicProvider boundary): `services/api/tests/test_structure.py`
- Frontend API client / queries: `apps/web/src/lib/api-client.ts`, `apps/web/src/lib/queries.ts`
- Project studio UI: `apps/web/src/components/projects/project-detail.tsx`, `components/generation/generate-form.tsx`, `components/revision-tree/{revision-tree,track-node,compare-dialog}.tsx`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Projects](docs/features/projects.md)
- [Generation](docs/features/generation.md)
- [Revision History](docs/features/revision-history.md)
- [Stems (placeholder)](docs/features/stems.md)
- [Project Asset Explorer](docs/features/project-asset-explorer.md)
- [Track Library](docs/features/track-library.md)
- [Audio Metadata Extraction](docs/features/audio-metadata.md)
- [Bucket Explorer](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
