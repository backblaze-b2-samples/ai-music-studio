<!-- last_verified: 2026-05-26 -->
# Feature: Project Asset Explorer

## Purpose
A per-project, scoped view of B2 — every object under
`projects/<id>/…`. Rendered as a "Project Files" tab inside the project
page so the user can see exactly what landed in their bucket for this
project (manifest, generated tracks, sidecars, future stems and
reference clips). Distinct from the full-bucket explorer at `/files`,
which is kept unmodified.

## Used By
- UI: `apps/web/src/components/projects/project-asset-explorer.tsx` inside the project detail page
- API: `GET /files?prefix=projects/<id>/` (re-uses the bucket explorer's endpoint, scoped to a prefix — no new API surface)

## Why both `/files` and ProjectAssetExplorer?
The full-bucket explorer (`/files`) is the **ops-style** "see everything in my
bucket" view — non-negotiable keep from the starter. The Project Asset
Explorer is the **user-level** "see everything that belongs to this
project" view. They have different audiences (operator vs end user) and
different scopes (whole bucket vs one prefix), so collapsing them would
hurt both. Keeping both is cheap because the project view reuses the
existing `/files` endpoint.

## Core Functions
- `apps/web/src/components/projects/project-asset-explorer.tsx` — flat newest-first list (a tree is overkill for ~tens of objects)
- `apps/web/src/lib/queries.ts::useProjectAssets`
- `apps/web/src/lib/api-client.ts::getProjectAssets` — thin wrapper that calls `getFiles("projects/<id>/")`

## Canonical Files
- Pattern exemplar: `apps/web/src/components/projects/project-asset-explorer.tsx`

## Inputs
- project_id (path param of the project page)

## Outputs
- `FileMetadata[]` (sorted newest-first), rendered as a list with key + size_human

## Flow
- Component reads `projectId` from the page route
- TanStack Query hook fetches `/files?prefix=projects/<id>/`
- Renders a flat list (path, size) — every object that exists under the project's prefix

## Edge Cases
- **Project with no artifacts yet** -> empty list → friendly `EmptyState`
- **Project deleted while the tab is open** -> 200 with empty list (the prefix is gone but the endpoint succeeds)
- **API unreachable** -> `ErrorState` with retry

## UX States
- Loading: skeleton card
- Empty: "No files yet — Generated tracks and uploaded reference clips will appear here"
- Loaded: divider-separated list of key / size rows
- Error: `ErrorState` with retry

## Verification
- Test files: covered by existing `/files` tests; no new backend coverage required
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Bucket Explorer (Files)](file-browser.md)
- [Projects](projects.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
