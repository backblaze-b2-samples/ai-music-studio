<!-- last_verified: 2026-05-26 -->
# Feature: Dashboard

## Purpose
Music-studio overview of B2 storage activity: total tracks, total
duration generated, daily generation activity, recent tracks, and
format breakdown.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /files/stats`, `GET /files`, `GET /files/stats/activity`, `GET /library`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards: Tracks, Total Duration, Generated Today, Audio Storage
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — last 10 tracks (component name retained for diff churn; renders generated tracks)
- `apps/web/src/components/dashboard/upload-chart.tsx` — bar chart of generation activity per day
- `apps/web/src/components/dashboard/format-breakdown.tsx` — per-extension chip breakdown (`wav 5 · mp3 12 · …`)
- `apps/web/src/lib/api-client.ts::getFileStats, getFiles, getUploadActivity`
- `services/api/app/runtime/files.py` — `GET /files/stats` handler
- `services/api/app/service/files.py` — `get_stats()` merges `get_upload_stats()` with `get_audio_aggregates()`
- `services/api/app/service/library.py` — `get_audio_aggregates()` totals the `audio/` prefix

## Canonical Files
- Stats service logic: `services/api/app/service/files.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /files/stats` -> `UploadStats`
- `GET /files?limit=10` -> `FileMetadata[]` for recent uploads
- `GET /files/stats/activity?days=7` -> `DailyUploadCount[]`
- `GET /library` -> `AudioAsset[]` for the Recent Tracks table

## Flow
- Page loads -> parallel calls (stats, recent tracks via `useLibrary`, activity)
- Stats cards display: Tracks, Total Duration (formatted `m:ss` / `h:mm:ss`), Generated Today, Audio Storage
- Activity chart shows server-aggregated daily counts for last 7 days
- Recent Tracks table shows last 10 tracks with Filename / Duration / Format / Date / Play (inline `<audio>` dialog)
- Empty state ("No tracks yet — create your first project") collapses every grid until the first track lands

## Notes on metrics
- `total_audio_assets` covers everything under `audio/` — project-scoped tracks at `projects/<id>/tracks/<id>/audio.<ext>` are not yet included (tracked in tech debt — the dashboard will broaden to project-scoped tracks once the Library does)
- Provider breakdown (mock vs real) is implicit in the per-track sidecars' `provider` field; surfacing it as a chart is a future enhancement (tech debt)

## Edge Cases
- API unavailable -> stats default to zeros, table shows empty state
- No tracks -> empty chart message, empty table message
- Large file count -> stats endpoint paginates through all objects using `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards and table
- Empty: hero card "No tracks yet — create your first project"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_upload_activity.py`, `services/api/tests/test_recent_files.py`, `services/api/tests/test_download_stats.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Track Library](track-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
