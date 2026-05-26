<!-- last_verified: 2026-05-26 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)

## Music Generation

- The mock provider takes ~1s; real providers (Suno / Udio) typically
  take 30-90s. v1 runs generation **synchronously inside the request**
  because that's enough for the mock; a real provider needs a background
  worker (tracked in tech debt) and the UI is pre-wired to poll
  `GET /projects/{id}/tracks/{track_id}` for status.
- Timeouts: the mock provider sleeps under 1.2s; FastAPI's default
  request timeout (the platform default — uvicorn doesn't impose one)
  is fine for the mock. Add an explicit timeout in `generate_track`
  when wiring a real provider.
- Partial failure semantics:
  - If the audio upload to B2 succeeds but the `track.json` sidecar
    write fails, the audio remains in B2 but won't appear in the
    revision tree (the tree is built from sidecars). The endpoint
    returns 500; the caller can safely retry the generation. Tracked
    in tech debt — `build_tree` should surface the orphan audio key
    as a recoverable row.
  - `project.json::track_count` bumps are best-effort and logged WARN
    on failure; the persisted track is the source of truth, and a
    re-list rebuilds the count.
