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

- Provider API keys (`MUSICAPI_API_KEY`) are loaded server-side only
  via `services/api/app/config/settings.py` and are **never** exposed to
  the browser. The browser talks only to `POST /projects/{id}/generate`
  — the backend handles all provider auth.
- The MusicAPI free tier issues credits on signup with no card, so the
  sample can be run end-to-end without putting a real payment method
  online — but every generation still spends real credits from your
  account, so treat the key as a secret and don't commit `.env`.
- `POST /projects/{id}/generate` has a small per-client token bucket
  guard. Tune `GENERATION_RATE_LIMIT_CAPACITY` and
  `GENERATION_RATE_LIMIT_WINDOW_SEC` before exposing a real provider to
  untrusted users.
- Optional bearer-token auth is available through `STUDIO_AUTH_TOKEN`.
  Leaving it empty keeps local development single-user and open.
