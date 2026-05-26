<!-- last_verified: 2026-05-26 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `SunoMusicProvider` raises `NotImplementedError` | Sample only runs with the in-the-box mock provider | Implement the real Suno (or Udio/etc.) API call inside `services/api/app/repo/music_provider.py::SunoMusicProvider.generate`: read `SUNO_API_KEY`, POST to the generate endpoint, poll for completion, fetch the final mp3 | High | Open |
| `service/stems.py::split_stems` raises `NotImplementedError` | "Generate Stems" button is permanently disabled | Wire up a stem-separation backend (Demucs via PyTorch, LALAL.AI, or AudioShake); write each stem to `projects/<id>/tracks/<track-id>/stems/<name>.wav` and append to `track.json::stems_keys` | Medium | Open |
| Generation runs synchronously inside the request | Real providers that take 30-90s will time out the FastAPI request | Move `generate_track` to a background worker; have the runtime endpoint return `GenerationStatus(state="queued")` immediately; UI polls `GET /projects/{id}/tracks/{track_id}` until success | High | Open (deferred until real provider lands) |
| No rate limiting on `POST /projects/{id}/generate` | A real provider with per-second cost will get hammered by curl loops | Add a per-IP token bucket in `runtime/generation.py` (or sit behind an external rate limiter); document the limit in `docs/SECURITY.md` | Medium | Open |
| Single-user — no auth, no shared projects | Projects key only on UUID; anyone with the URL sees them | Add owner / ACL fields to `Project` (the manifest schema is forward-compatible) and gate `runtime/projects.py` behind auth | Medium | Open |
| `RevisionTree` rendered as indented list | Visual breaks down for deeply branched trees | Replace with d3-force / canvas graph rendering inside `components/revision-tree/` once a project hits ~20 nodes | Low | Open |
| E2E `apps/web/e2e/projects.spec.ts` is `.skip` | Generation flow isn't smoke-tested in CI | Stand up a deterministic mock-driven harness (set `MUSIC_PROVIDER=mock`, B2 stub bucket) and remove the `.skip` | Medium | Open |
| Library / dashboard don't include project-scoped tracks | `projects/<id>/tracks/...` tracks don't show in `/library` or count toward dashboard totals | Broaden `list_audio_objects` to either scan multiple prefixes or move project tracks under `audio/` too; surface a project chip on each card | Low | Open |
| `build_tree` silently drops audio with no sidecar | A failed sidecar write leaves an orphan audio object invisible in the UI | Surface orphans as a recoverable row in `RevisionTree` with a "repair" affordance that re-creates a minimal sidecar | Low | Open |
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| `formatDate` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| Reference-clip upload UI not wired into project detail | `apps/web/src/components/upload/` exists but no callsite mounts it — users can't drop a reference clip from the project page yet | Wire `<UploadForm scope="reference"/>` into `apps/web/src/components/projects/project-detail.tsx` when the reference-upload feature is prioritized; documented in `docs/features/reference-upload.md` | Medium | Open |
