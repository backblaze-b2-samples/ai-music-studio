<!-- last_verified: 2026-05-26 -->
# AGENTS.md

This is the authoritative control surface for all coding agents on the
**AI Music Studio**. Read this first.

## 1. Repository Map

```
apps/web/                                    Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/projects/                          /projects — project list + new-project dialog
  src/app/projects/[id]/                     /projects/[id] — studio (generate, revision tree, compare, Project Files tab)
  src/app/library/                           /library — cross-project Track Library (audio-prefix grid)
  src/app/files/                             /files  — full-bucket explorer (kept from starter)
  src/components/projects/                   projects-view, project-detail, project-asset-explorer
  src/components/generation/                 generate-form
  src/components/revision-tree/              revision-tree, track-node, compare-dialog
  src/components/library/                    library-view, audio-asset-card, waveform
services/api/                                FastAPI backend (layered: types/config/repo/service/runtime)
  app/runtime/projects.py                    POST/GET/DELETE /projects[/{id}]
  app/runtime/generation.py                  POST /projects/{id}/generate, GET track + playback + download
  app/runtime/revisions.py                   GET /projects/{id}/revisions, GET /projects/{id}/compare
  app/runtime/library.py                     /library, /library/{key}/playback|download, DELETE /library/{key}
  app/runtime/files.py                       /files, /files/{key} (full-bucket explorer; unchanged)
  app/service/projects.py                    project lifecycle (CRUD against B2 manifests)
  app/service/generation.py                  end-to-end orchestration: provider → B2 put → sidecar
  app/service/revisions.py                   build_tree, diff_tracks
  app/service/stems.py                       list_stems live; split_stems stubbed (NotImplementedError)
  app/service/library.py                     audio key validation, list/head/delete
  app/service/audio_metadata.py              wave + mutagen extractor
  app/repo/b2_client.py                      boto3 — generic file helpers
  app/repo/b2_tracks.py                      audio-prefix helpers (alias: head_track_objects_parallel)
  app/repo/b2_projects.py                    project-scoped helpers (put/get JSON, list, delete tree, presign)
  app/repo/music_provider.py                 MusicProvider interface + MockMusicProvider + SunoMusicProvider (stub)
  app/repo/_mock_tracks/                     pre-baked WAVs for the mock provider (committed)
  app/types/project.py                       Project, Track, Stem, GenerationRequest/Status, RevisionNode, TrackDiff
  app/types/library.py                       AudioAsset
packages/shared/                             Shared TypeScript types (mirrors backend Pydantic)
docs/                                        System of record (features, workflows, security, reliability)
docs/exec-plans/                             Execution plans and tech debt tracker
infra/railway/                               Deployment config
```

## 2. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

**Project prefix layout (canonical — do not deviate):**

```
projects/<project-id>/project.json
projects/<project-id>/tracks/<track-id>/audio.<ext>
projects/<project-id>/tracks/<track-id>/track.json
projects/<project-id>/tracks/<track-id>/stems/<stem-name>.wav
projects/<project-id>/reference/<safe-filename>
```

Every project artifact lives under this prefix. `track.json` carries `parent_track_id`, which is the *only* source of revision-tree structure — the tree is reconstructed by `service/revisions.py::build_tree` reading every sidecar under the prefix. Re-rooting these prefixes is a breaking change.

**MusicProvider boundary**: `app/repo/music_provider.py` is the **only** module allowed to make a real music-generation API call. Service / runtime code goes through `get_provider()`. Mirrors "boto3 only in repo/" and is enforced by `tests/test_structure.py::test_generation_http_only_in_music_provider` (flags any `requests` or `httpx` import outside `music_provider.py`).

**Audio storage convention (legacy / cross-project library)**: the Upload pipeline writes audio assets to `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>` — the `--<uuid>` suffix keeps keys collision-proof while leading with the filename keeps keys scannable in the bucket and surfaces the filename in list responses (no per-asset HEAD). Non-audio uploads land at `uploads/<safe-filename>` and only show in Files. The Track Library lists everything under the `audio/` prefix that ends in a supported extension (wav, mp3, flac, ogg, m4a, aac, opus); files seeded into the bucket outside the Upload pipeline stay playable. Path-traversal payloads (`..`, `//`) are rejected at the API boundary by `service/library.py::AUDIO_KEY_RE`.

**B2 surface**: S3-only. No `b2-native` calls anywhere. Every `boto3.client("s3", …)` instantiation MUST pass `Config(user_agent_extra="b2ai-ai-music-studio")`. No hardcoded region strings in source (use `B2_REGION` from `.env`).

## 3. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 4. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| Generation HTTP only in MusicProvider | `tests/test_structure.py::test_generation_http_only_in_music_provider` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 5. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 6. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §8).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 7. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 8. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 9. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 10. When Unsure

- Prefer boring, stable libraries (stdlib `wave`, `mutagen` — no ffmpeg)
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
