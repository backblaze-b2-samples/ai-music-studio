<!-- last_verified: 2026-05-26 -->
# Feature: Projects

## Purpose
A *project* is the top-level container for a music-studio session.
Every track, stem, and reference clip the user creates within a project
lives under one stable B2 prefix (`projects/<project-id>/…`), with the
project shell persisted as a single `project.json` manifest. B2 is the
sole data store; there is no application database.

## Used By
- UI: `/projects` page (list + create + delete dialogs), `/projects/[id]` page (studio)
- API:
  - `GET /projects`
  - `POST /projects`
  - `GET /projects/{id}`
  - `DELETE /projects/{id}`

## Core Functions
- `apps/web/src/components/projects/projects-view.tsx` — list grid, **New project** dialog, per-card delete confirm
- `apps/web/src/components/projects/project-detail.tsx` — header + Studio / Project Files tabs
- `apps/web/src/lib/queries.ts::useProjects, useProject, useCreateProject, useDeleteProject`
- `apps/web/src/lib/api-client.ts::getProjects, getProject, createProject, deleteProject`
- `services/api/app/runtime/projects.py` — FastAPI routes
- `services/api/app/service/projects.py` — id validation, manifest read/write, list, archive, hard-delete
- `services/api/app/repo/b2_projects.py` — `put_json`, `get_json`, `list_project_root_prefixes`, `delete_project_tree`
- `services/api/app/types/project.py` — `Project`, `ProjectManifest`

## Canonical Files
- Service pattern: `services/api/app/service/projects.py`
- Repo pattern: `services/api/app/repo/b2_projects.py`

## Inputs
- `POST /projects` body: `{ name: string (1-200), description?: string (0-2000) }`
- `GET /projects/{id}` path param: project_id matching `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`

## Outputs
- `GET /projects` -> `Project[]` (sorted newest-first)
- `POST /projects` -> `Project` (id minted server-side)
- `GET /projects/{id}` -> `Project`
- `DELETE /projects/{id}` -> `{ deleted: string[], errors: { Key, Code, Message }[] }` — every key under `projects/<id>/` removed
- Side effects: `project.json` written / deleted in B2; on a generation, `track_count` is incremented best-effort by the generation service

## Flow
- **Create**: client posts `{name, description}` → service mints a UUID-4 project id → writes `projects/<id>/project.json` → returns the `Project`
- **List**: service issues `list_objects_v2(Prefix="projects/", Delimiter="/")` → for each `<id>/` prefix, fetches `project.json` → returns `Project[]` sorted newest-first. Prefixes that fail the UUID-4 regex or whose manifest is missing/malformed are logged-WARN and skipped so a single orphan prefix doesn't 500 the dashboard.
- **Get**: validates id → `GetObject` `project.json` → 404 if missing
- **Delete**: validates id → `delete_project_tree(id)` lists every key under `projects/<id>/` and batches `DeleteObjects` (chunks of 1000) → returns `{ deleted, errors }`

## Edge Cases
- **Malformed project id** -> 400 from the API before B2 is touched
- **Missing manifest** -> 404 with `"Project not found"`
- **Orphan prefix during list** -> skipped + WARN log (UI still renders)
- **B2 unreachable** -> 500; raw error is not leaked to the client

## UX States
- Loading: 3 skeleton cards
- Empty: friendly `EmptyState` — "No projects yet — Create your first project to start generating music"
- Loaded: responsive card grid (`sm:grid-cols-2 xl:grid-cols-3`)
- Error: `ErrorState` with retry

## Verification
- Test files: extend `services/api/tests/` with project lifecycle coverage — not shipped in the scaffold (tech debt)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Generation](generation.md)
- [Revision History](revision-history.md)
- [Project Asset Explorer](project-asset-explorer.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
