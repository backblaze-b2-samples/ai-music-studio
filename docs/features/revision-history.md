<!-- last_verified: 2026-05-28 -->
# Feature: Revision History (Tree + Compare)

## Purpose
Capture every generation, new take, extend, restyle, and branch as a node in a tree against
its parent track, so two variants can be A/B'd side-by-side and the
lineage of a final mix is always inspectable. The tree is reconstructed
from `track.json` sidecars in B2 on every request — no database state
to keep in sync.

## Used By
- UI: `/projects/[id]` — `RevisionTree`, `TrackNode`, `CompareDialog`
- API:
  - `GET /projects/{id}/revisions`
  - `GET /projects/{id}/compare?a={track_a}&b={track_b}`
  - `POST /projects/{id}/tracks/{track_id}/repair`

## Core Functions
- `apps/web/src/components/revision-tree/revision-tree.tsx` — indented-tree renderer with recursive `NodeRow`
- `apps/web/src/components/revision-tree/track-node.tsx` — per-track row: prompt preview, badges (provider, branch mode), Play / Download / Branch / A / B / Generate Stems / Repair orphan
- `apps/web/src/components/revision-tree/pending-track-node.tsx` — temporary row shown immediately after submitting generation; failed provider calls remain dismissible with the provider error
- `apps/web/src/components/revision-tree/compare-dialog.tsx` — modal with dual audio players + diff list
- `apps/web/src/lib/queries.ts::useRevisionTree, useCompare, useRepairTrackSidecar`
- `apps/web/src/lib/api-client.ts::getRevisionTree, getTrackDiff, repairTrackSidecar`
- `services/api/app/runtime/revisions.py` — FastAPI routes
- `services/api/app/service/revisions.py::build_tree, get_track, diff_tracks` — load every sidecar, thread by `parent_track_id`, compute diff

## Canonical Files
- Tree builder: `services/api/app/service/revisions.py::build_tree`
- Diff function: `services/api/app/service/revisions.py::diff_tracks`

## Inputs
- `GET /projects/{id}/revisions` -> path: project_id
- `GET /projects/{id}/compare?a=...&b=...` -> a, b: track ids; must differ

## Outputs
- `GET /projects/{id}/revisions` -> `RevisionNode[]` (roots; each node carries a `track` + recursive `children` sorted oldest-first)
- `GET /projects/{id}/compare` -> `TrackDiff { a, b, prompt_changed, style_changed, negative_tags_changed, instrumental_changed, generation_mode_changed, continue_at_changed, audio_weight_changed, duration_changed, audio_metadata_changed }`

## Flow
- **Build tree**: service lists every `tracks/<id>/track.json` under the project prefix, plus project-track audio objects that have no sidecar. Sidecar-backed tracks and recoverable audio orphans are grouped by `parent_track_id`; roots are tracks whose parent is `None` OR points at a track id that isn't in the project. Children are sorted oldest-first so the visual timeline reads left-to-right; roots are sorted newest-first so the latest experiment is at the top.
- **Compare**: service loads both tracks (404 if either is missing), produces a `TrackDiff` with one boolean per field, including branch mode, extend timestamp, restyle source influence, avoid tags, and instrumental mode. `audio_metadata_changed` covers `duration_ms`, `sample_rate`, `channels`, `bit_depth`, `codec` — the union of fields that the audio-metadata extractor populates.
- **Render (tree)**: the UI maps `RevisionNode[]` to indented `TrackNode` rows. Depth is communicated visually via left padding; no SVG / d3-force in v1. Tracked in tech debt as a future upgrade for projects with deeply-branched trees.
- **Render (compare)**: dialog opens whenever both `compareA` and `compareB` state slots in `ProjectDetail` are set and differ. Clicking the same Compare A / Compare B button again clears that slot; picking a track for one slot clears it from the other slot so A and B never point at the same track. Each panel mounts its own `<audio controls>` fed by a presigned playback URL. The diff list shows a green dot for unchanged fields, attention-yellow for changed ones.

## Edge Cases
- **Project with no tracks** -> empty `RevisionNode[]` → UI shows EmptyState ("No tracks yet — Generate your first track…")
- **Orphan track (parent deleted)** -> surfaced as a new root rather than dropped, so no work is hidden
- **Compare with a == b** -> 400 from the API ("Cannot compare a track with itself")
- **Compare against missing track** -> 404 with `"Track not found"`
- **Audio object with no sidecar** -> surfaced as an orphan row with a Repair action that writes a minimal `track.json`
- **Malformed sidecar** -> logged WARN and skipped
- **B2 unreachable** -> 500; UI shows `ErrorState` with retry

## UX States
- Loading: skeleton card
- Empty: `EmptyState` with `GitMerge` icon and "Generate your first track above to seed the revision tree."
- Pending generation: a dashed `PendingTrackNode` appears as a root or child row while the queued job is running
- Loaded: indented tree of `TrackNode`s; selected compare-A / -B nodes get a `ring-2 ring-primary` border + an A/B badge
- Error: `ErrorState` with retry
- Compare dialog: dual `<audio>` players (loading skeleton while presigning) + per-field diff dots

## Verification
- Test files: `services/api/tests/test_revisions.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Projects](projects.md)
- [Generation](generation.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
