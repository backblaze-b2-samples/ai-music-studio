<!-- last_verified: 2026-05-26 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `service/stems.py::split_stems` raises `NotImplementedError` | "Generate Stems" button is permanently disabled | Replaced with a pluggable `STEM_SPLITTER_COMMAND` boundary; when unset the API returns 501 instead of crashing, and when set it writes WAV stems + updates `track.json::stems_keys` | Medium | Mitigated |
| Generation runs synchronously inside the request | `MusicApiProvider` polls upstream for 1-3 min on every call, blocking the FastAPI request handler the whole time; browsers and reverse proxies tolerate this for a sample but will time out under load | `POST /projects/{id}/generate` now queues in-process work and returns `GenerationStatus(state="queued")`; UI polls `GET /projects/{id}/generations/{track_id}` until success/failure | High | Closed |
| No rate limiting on `POST /projects/{id}/generate` | A real provider with per-second cost will get hammered by curl loops | Added per-client token bucket settings (`GENERATION_RATE_LIMIT_CAPACITY`, `GENERATION_RATE_LIMIT_WINDOW_SEC`) | Medium | Closed |
| Single-user — no auth, no shared projects | Projects key only on UUID; anyone with the URL sees them | Added optional bearer-token auth plus `owner_id` / `shared_with` fields on `Project`; local dev remains open when `STUDIO_AUTH_TOKEN` is unset | Medium | Closed |
| `RevisionTree` rendered as indented list | Visual breaks down for deeply branched trees | Replace with d3-force / canvas graph rendering inside `components/revision-tree/` once a project hits ~20 nodes | Low | Open |
| E2E `apps/web/e2e/projects.spec.ts` is `.skip` | Generation flow isn't smoke-tested in CI | Replaced with a deterministic Playwright harness that mocks API responses and exercises create -> queue generation -> render node | Medium | Closed |
| Library / dashboard don't include project-scoped tracks | `projects/<id>/tracks/...` tracks don't show in `/library` or count toward dashboard totals | Library/dashboard now scan both `audio/` and `projects/<id>/tracks/<track-id>/audio.<ext>`; project tracks carry project/track metadata for the UI chip | Low | Closed |
| `build_tree` silently drops audio with no sidecar | A failed sidecar write leaves an orphan audio object invisible in the UI | `build_tree` now surfaces orphan audio rows and `POST /projects/{id}/tracks/{track_id}/repair` writes a minimal sidecar | Low | Closed |
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extracted to `apps/web/src/lib/utils.ts` | Low | Closed |
| `formatDate` duplicated in TypeScript | DRY violation | Extracted to `apps/web/src/lib/utils.ts` | Low | Closed |
| Reference-clip upload UI not wired into project detail | `apps/web/src/components/upload/` exists but no callsite mounts it — users can't drop a reference clip from the project page yet | Project Files tab now mounts reference upload and sends audio to `projects/<id>/reference/` | Medium | Closed |
