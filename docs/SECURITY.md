<!-- last_verified: 2026-05-26 -->
# Security

Security principles and implementation for the ai-music-studio.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs for download (10-min expiry, `Content-Disposition: attachment`)

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, PDFs, text, archives, audio/video)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries

## Music Provider Credentials

- Provider API keys (e.g., `SUNO_API_KEY`) are loaded server-side only
  via `services/api/app/config/settings.py` and are **never** exposed to
  the browser. The browser talks only to `POST /projects/{id}/generate`
  — the backend handles all provider auth.
- `MUSIC_PROVIDER=mock` (default) requires no external credentials;
  the sample is runnable end-to-end on a fresh clone.
- **Tech debt — generation rate limiting.** `POST /projects/{id}/generate`
  has no per-IP rate limit. With a real (cost-bearing) provider this
  is a foot-gun. Add a token bucket in `runtime/generation.py` (or sit
  behind an external rate limiter) before pointing the sample at a
  paid backend. Tracked in `docs/exec-plans/tech-debt-tracker.md`.
