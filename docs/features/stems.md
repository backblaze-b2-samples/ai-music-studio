<!-- last_verified: 2026-05-26 -->
# Feature: Stems (placeholder)

## Purpose
Model the per-track stem (vocals / drums / bass / other) shape so the UI
can render a stems panel and a future implementation can plug in without
changing wire types. **In v1 the actual stem-split operation is stubbed**
— the data model is live, the listing helper is live, but
`split_stems(...)` raises `NotImplementedError` and the UI surfaces a
disabled "Generate Stems (coming soon)" button.

## Used By
- UI: `TrackNode` action row — the **Generate Stems** button is rendered disabled with a tooltip
- API: not currently exposed via a route; the data shape and helpers are public
- Backend: `services/api/app/service/stems.py`, `services/api/app/types/project.py::Stem, Track.stems_keys`

## Core Functions
- `services/api/app/service/stems.py::list_stems` — lists `projects/<id>/tracks/<track-id>/stems/` and returns `Stem[]` (empty in v1)
- `services/api/app/service/stems.py::split_stems` — **raises `NotImplementedError`** with a docstring pointing at the wiring spot
- `services/api/app/types/project.py::Stem` — `{ stem_id, track_id, name, audio? }`
- `services/api/app/types/project.py::Track.stems_keys` — list of B2 keys, populated by a future real implementation

## Canonical Files
- Stub location (the wiring spot): `services/api/app/service/stems.py::split_stems`

## Inputs
- `list_stems(project_id, track_id)` — both validated against the project-id regex
- `split_stems(project_id, track_id)` — same; currently always raises

## Outputs
- `list_stems` -> `Stem[]` (in v1, always `[]`)
- `split_stems` -> would return `Stem[]`; currently raises `NotImplementedError`

## Why it's stubbed
Stem separation needs either a heavy in-process model (Demucs via
PyTorch) or a hosted API (LALAL.AI, AudioShake). Either path is real
engineering — wrong fit for a v1 scaffold whose purpose is to
demonstrate the B2 storage pattern. The placeholder lets us:

- ship the data model so a real implementation slots in without a wire
  change
- demonstrate the prefix layout (`projects/<id>/tracks/<id>/stems/<name>.wav`)
- surface the UI affordance so users know stems are coming, not missing

When wiring a real implementation:

  1. Fetch `projects/<id>/tracks/<track-id>/audio.<ext>` from B2
  2. Run a stem-separation model (Demucs / LALAL.AI / AudioShake)
  3. Upload each stem to `projects/<id>/tracks/<track-id>/stems/<name>.wav`
  4. Update `track.json::stems_keys` so the revision tree knows the
     stems are available
  5. Return the populated `Stem` list

This is the *only* function that needs to change — everything downstream
(storage layout, listing, playback presign) already works.

## Edge Cases
- **Listing on a project with no stems** -> `[]` (the common case in v1)
- **`split_stems` called** -> `NotImplementedError` bubbles up — caller should translate to a 501 if exposed via a route

## UX States
- Disabled button labeled "Generate Stems (coming soon)" with a tooltip explaining the timing

## Verification
- Test files: none (the function is a documented stub)
- Pass criteria: the structural tests still pass; the disabled UI affordance is visible in the project detail page

## Related Docs
- [Generation](generation.md)
- [Revision History](revision-history.md)
- [tech-debt-tracker](../exec-plans/tech-debt-tracker.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
