<!-- last_verified: 2026-05-28 -->
# Feature: Stems

## Purpose
Model and optionally generate per-track stems (vocals / drums / bass /
other). The storage shape is stable:
`projects/<id>/tracks/<track-id>/stems/<name>.wav`.

## Used By
- UI: `TrackNode` action row — **Generate Stems**
- API:
  - `GET /projects/{project_id}/tracks/{track_id}/stems`
  - `POST /projects/{project_id}/tracks/{track_id}/stems`
- Backend: `services/api/app/service/stems.py`, `services/api/app/types/project.py::Stem, Track.stems_keys`

## Core Functions
- `list_stems` — lists stem WAVs and returns populated `Stem[]`
- `split_stems` — runs the configured `STEM_SPLITTER_COMMAND`, uploads produced WAVs, and updates `track.json::stems_keys`

## Configuration
Stem generation is optional. When `STEM_SPLITTER_COMMAND` is empty, `POST`
returns 501 with a clear message. When set, the command receives `{input}`
and `{output}` placeholders and should write any of:
`vocals.wav`, `drums.wav`, `bass.wav`, `other.wav`.

## Edge Cases
- **No stems** -> `GET` returns `[]`
- **Splitter not configured** -> `POST` returns 501
- **Splitter produces no recognized WAVs** -> `POST` returns 502

## Verification
- Quick verify command: `pnpm test:api`

## Related Docs
- [Generation](generation.md)
- [Revision History](revision-history.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
