<!-- last_verified: 2026-05-27 -->
# Extend and Restyle Branching

## Goal
Make revision-tree children derive from their parent track through
MusicAPI's provider-native operations:

- `extend_music` — continue a generated clip from a timestamp
- `cover_music` — restyle a generated clip while preserving source influence

## Scope
- Persist provider task/clip metadata on each `Track` sidecar.
- Add request fields for generation mode, extend timestamp, and restyle
  audio weight.
- Resolve the parent track inside the service layer before provider calls.
- Forward branch-mode payloads through `MusicApiProvider`.
- Add project UI controls for New Take / Extend / Restyle.
- Add focused tests for payloads and service validation.

## Out of Scope
- Upload-based extend/cover of arbitrary user audio.
- Async generation jobs or webhooks.
- Concatenating extension output back into a full song.
