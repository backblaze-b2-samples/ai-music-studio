<!-- last_verified: 2026-05-28 -->
# Tech Debt Burn-Down

## Goal
Stabilize the fixes started from the tech-debt request without changing the
canonical project prefix layout.

## Scope
- Include project-scoped generated tracks in `/library`, dashboard totals, and
  activity metrics.
- Surface audio objects that are missing `track.json` sidecars and provide a
  repair endpoint that writes a minimal sidecar.
- Move generation request handling to an in-process background queue with
  pollable status and add basic per-client rate limiting.
- Add project owner / sharing fields and optional bearer-token gating for
  project routes.
- Wire project reference upload into the project detail page.
- Replace the stem `NotImplementedError` with a pluggable splitter boundary and
  a clear unavailable response when no splitter is configured.
- Mark already-completed DRY work for `humanizeBytes` and `formatDate`.

## Stopped Here
Per user correction on 2026-05-28, no more feature expansion. Remaining open
work stays in `docs/exec-plans/tech-debt-tracker.md`; notably the full
revision-tree graph rendering upgrade is still open.

## Verification
- `pnpm lint`
- `pnpm lint:api`
- `pnpm test:api`
- `pnpm check:structure`
