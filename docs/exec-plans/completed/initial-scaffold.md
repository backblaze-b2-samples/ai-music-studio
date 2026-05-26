<!-- Scaffold plan for ai-music-studio -->
<!-- Generated 2026-05-26 -->
<!-- Source override: ai-audio-starter-kit (NOT vibe-coding-starter-kit) -->

# Scaffold Plan — `ai-music-studio`

> ⚠️ **Source override.** The user explicitly directed this scaffold to derive
> from `ai-audio-starter-kit`, not the skill's default `vibe-coding-starter-kit`.
> The fresh clone is at
> `.claude/scratch/vcsk-7817bca5-4e25-4069-9511-6f9ca7a2657d/` (skill-mandated
> path — the dir name says "vcsk" but the contents are `ai-audio-starter-kit`).
> All keep/trim/add deltas below are against `ai-audio-starter-kit`, and the
> rename table targets `ai-audio-starter-kit` identifiers.

> ⚠️ **No `../CLAUDE.md` at the workspace root.** The skill and the
> `b2-sample-builder` agent both reference parent standards at
> `../CLAUDE.md`. The workspace at `/Users/epavez/Documents/sampleapps/` has
> no such file — the standards live inside each sample's own
> `AGENTS.md` / `CLAUDE.md`. The builder must treat
> `ai-audio-starter-kit`'s `AGENTS.md` (full content, copied into the new
> sample, then rewritten for music-studio) plus the `b2-doctor` skill as
> the authoritative standards source for this build.

---

## 1. Purpose

`ai-music-studio` is a B2 sample that demonstrates a **Suno/Udio-style AI
music generator with first-class revision history**. Users open or create a
*project*, generate a track from a prompt + style controls, then iteratively
*branch* — every regeneration, remix, and stem split is captured as a child
node in a revision tree against the project, so two variants can be compared
side-by-side, the lineage of a final mix is visible, and nothing is ever
lost. Audio files (full tracks and stems) and project metadata (JSON
manifests) all live in B2 under a stable `projects/<project-id>/…` prefix,
making B2 the durable system of record. The sample is for developers
building AI music tools who need to see how object storage handles
fast-multiplying media artifacts (variants × stems × remixes) in a way
that stays browsable, branchable, and auditable.

## 2. Architecture Delta from `ai-audio-starter-kit`

The starter is already an audio-focused FastAPI + Next.js monorepo with a
strict layered backend, audio metadata extraction, audio Library, upload
pipeline, full bucket explorer, and structural enforcement tests. That is
~80% of what `ai-music-studio` needs. The delta is mostly **add** (generation
provider, projects, revision tree, compare UI) and a small **trim**
(remove the `/design` showcase and a few audio-only assumptions baked into
the starter's UX copy).

### Keep (as-is, modulo rename + minor adaptation)

| Surface | Why we keep it |
|---|---|
| `services/api/app/types/` + `config/` + `repo/` + `service/` + `runtime/` layered architecture | Music-studio inherits the entire layering discipline. New work lands in the same layers — `types/project.py`, `service/projects.py`, `repo/music_provider.py`, `runtime/projects.py`. |
| `services/api/app/repo/b2_client.py` (generic S3 helpers) and `b2_audio.py` (audio-prefix helpers) | Every S3 op music-studio needs is already wrapped (put/list/head/delete/presign). `b2_audio.py` becomes `b2_tracks.py` and gains a project-scoped prefix variant. |
| S3 client construction with `user_agent_extra="b2ai-ai-audio-starter-kit"` | Pattern stays; the string changes per rename table (§6). |
| Audio metadata extraction (`service/audio_metadata.py` — stdlib `wave` + `mutagen`) | Reused verbatim: every generated track gets duration/sample-rate/channels/codec stamped onto its B2 object as S3 user metadata. |
| Upload pipeline (`service/upload.py`, `runtime/upload.py`) | Repurposed for **reference-track uploads** inside a project (users upload an inspiration clip; provider conditions on it). Same sanitization, same chunked streaming, same metadata stamping — new destination prefix. |
| **Bucket Explorer** at `/files` — full-bucket tree-view (`apps/web/src/components/files/file-browser.tsx` + `runtime/files.py`) | **Non-negotiable keep** per skill. The full-bucket explorer stays as the ops-style "see everything" tab, exactly as today. No prefix scoping change here. |
| Playback / download presigning split (inline vs `Content-Disposition: attachment`) | Reused for tracks, stems, and reference uploads. |
| `service/library.py::get_audio_aggregates()` parallel-HEAD pattern | Reused for project-scoped aggregates (total duration of all tracks in a project, etc.). |
| Health + metrics + structured JSON logging + CORS allowlist + request tracing | All carry over unchanged. Generation jobs and provider calls emit JSON logs through the existing logger. |
| Structural tests (`tests/test_structure.py`) — no backward imports, boto3 only in repo/, <300-line files, all layers exist | Carry over unchanged; new files must obey. |
| Frontend data-fetching discipline — every API call flows through `apps/web/src/lib/queries.ts` + `lib/api-client.ts`, no bare `useEffect+fetch` | New endpoints obey this discipline (new hooks added to `queries.ts`). |
| shadcn/ui component library, Tailwind v4 design tokens, dark mode, design-system primitives (`AudioAssetCard`, ErrorState, EmptyState, blaze loader) | Reused. `AudioAssetCard` is the building block of the revision-tree node. |
| `infra/railway/` deployment template + `scripts/doctor.mjs` preflight + `pnpm doctor` | Carry over unchanged. |

### Trim (remove from starter)

| Surface | Why trim |
|---|---|
| `/design` route (`apps/web/src/app/design/page.tsx`) and the design-system showcase wiring | Design-system-showcase pages are demo material for the starter, not the music-studio. The shadcn primitives themselves stay (they're consumed by other pages); only the showcase route is removed. |
| Audio-centric copy in `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/app-workflows.md`, every `docs/features/*.md` | Rewritten for music-studio (see §5). |
| Dashboard content that's audio-asset-centric (`apps/web/src/app/page.tsx`, `apps/web/src/components/dashboard/*`) | The dashboard *infrastructure* (cards, recharts wiring, query hooks) is kept; the *content* is rewritten for music-studio metrics (projects, tracks, variants, generation activity, total minutes generated). |
| `/upload` standalone top-level route | The upload primitive is kept inside project pages (reference-track upload); the standalone top-level demo route is removed. Nav loses the "Upload" item. |
| `docs/features/file-upload.md` (as-is) | Rewritten as `docs/features/reference-upload.md` to reflect new flow. |
| Audio-only seed copy in `apps/web/src/app/library/page.tsx` describing "audio asset grid" | Rewritten — `/library` becomes the **cross-project Track Library** (every generated track, every variant) with project-tag chips on each card and a "filter to project" control. The component shell is kept; the framing changes. |
| README "Core Features" list and tech-stack tagline | Rewritten in §5. |
| `docs/exec-plans/completed/*` from the starter's own history (initial scaffold, restructure, dashboard, etc.) | Removed — they're the starter's history, not ours. Replaced with a single `initial-scaffold.md` that this plan becomes after Phase 5. |

### Add (new for `ai-music-studio`)

| Surface | What it is |
|---|---|
| `services/api/app/types/project.py` | Pydantic models: `Project`, `Track`, `TrackVariant`, `Stem`, `GenerationRequest`, `GenerationStatus`, `ProjectManifest`. `Track` carries `parent_track_id` for the revision tree. |
| `services/api/app/repo/b2_projects.py` | Project-scoped B2 helpers: `read_manifest(project_id)`, `write_manifest(project_id, manifest)`, `list_project_tracks(project_id)`, `list_project_stems(project_id, track_id)`. Each uses `list_objects_v2`/`get_object`/`put_object` with the `projects/<id>/` prefix. |
| `services/api/app/repo/music_provider.py` | Provider-abstraction interface (`MusicProvider.generate(prompt, style, duration, **kwargs) -> GenerationJob`) with two implementations: `MockMusicProvider` (default — returns a pre-baked sample track from `services/api/app/repo/_mock_tracks/`, so the sample is runnable with zero external creds) and `SunoMusicProvider` (stub class with `NotImplementedError` and a docstring pointing to where the real Suno API call goes). Selected via `MUSIC_PROVIDER` env var. |
| `services/api/app/service/projects.py` | Business logic: create project, load project, list projects, archive project. Reads/writes `projects/<id>/project.json` via `b2_projects.py`. |
| `services/api/app/service/generation.py` | Business logic: create generation request, drive the provider, store the resulting audio under `projects/<id>/tracks/<track-id>/audio.<ext>`, write a `track.json` next to it (carries `parent_track_id`, prompt, provider, generation_ms, audio_metadata). Returns `GenerationStatus`. |
| `services/api/app/service/revisions.py` | Revision-tree helpers: `build_tree(project_id) -> RevisionNode` (nests tracks by `parent_track_id`), `diff_tracks(track_a, track_b) -> TrackDiff` (compares prompts, style, duration, audio metadata). |
| `services/api/app/service/stems.py` | Stem-handling helpers. `list_stems(project_id, track_id) -> list[Stem]`. The actual stem-split operation is **stubbed**: `split_stems(track_id)` raises `NotImplementedError` and the UI surfaces it as a disabled "Generate Stems (coming soon)" button. **Open question 1 resolved → punted.** |
| `services/api/app/runtime/projects.py` | `GET /projects`, `POST /projects`, `GET /projects/{id}`, `DELETE /projects/{id}`. |
| `services/api/app/runtime/generation.py` | `POST /projects/{id}/generate` (body: `{prompt, style, duration, parent_track_id?}`), `GET /projects/{id}/tracks/{track_id}`, `GET /projects/{id}/tracks/{track_id}/playback`, `GET /projects/{id}/tracks/{track_id}/download`, `DELETE /projects/{id}/tracks/{track_id}`. |
| `services/api/app/runtime/revisions.py` | `GET /projects/{id}/revisions` (tree), `GET /projects/{id}/compare?a={track_a}&b={track_b}` (diff). |
| `apps/web/src/app/projects/page.tsx` | Projects list (cards, create-new button). |
| `apps/web/src/app/projects/[id]/page.tsx` | Project detail: prompt + style controls, revision tree, currently-selected-track player, "branch from here" button, "compare" toggle. |
| `apps/web/src/components/revision-tree/` | New component family: `RevisionTree.tsx` (graph layout — start with a simple indented-tree, not d3-force), `TrackNode.tsx` (reuses `AudioAssetCard` internally), `CompareDialog.tsx` (side-by-side dual player + diff list). |
| `apps/web/src/components/generation/` | `GenerateForm.tsx` (prompt textarea, style dropdown, duration slider, reference-clip upload). Submits to `POST /projects/{id}/generate`, drives a live "generating…" state via TanStack Query polling on `GET /projects/{id}/tracks/{track_id}`. |
| `apps/web/src/components/projects/ProjectAssetExplorer.tsx` | **Sample-specific asset explorer** (skill non-negotiable). Reuses `file-browser.tsx` from the starter, scoped to `prefix="projects/<id>/"`. Renders inside the project page as a "Project Files" tab so the user can see exactly what landed in B2 for their project (tracks/, stems/, reference/, manifest). Distinct from the global `/files` route, which keeps the **full-bucket** explorer (non-negotiable keep). |
| `apps/web/src/lib/queries.ts` additions | `useProjects()`, `useProject(id)`, `useGenerate()`, `useRevisionTree(id)`, `useCompare(a, b)`, `useProjectAssets(id)`. |
| `packages/shared/src/types.ts` additions | `Project`, `Track`, `TrackVariant`, `Stem`, `GenerationStatus`, `RevisionNode`, `TrackDiff`. Mirrors backend Pydantic. |
| `services/api/app/repo/_mock_tracks/` | Three small pre-baked **WAV** files (~200-400 KB each, ~5 s of sine/sawtooth tone at varied frequencies — generated deterministically by the builder via stdlib `wave` so no external audio is sourced) + a `manifest.json` mapping (prompt_keywords → file). The `MockMusicProvider` deterministically returns one of these so the sample is runnable end-to-end with no real Suno key. WAV chosen over MP3 because the builder can synthesize it with no external dependencies (stdlib `wave`), and the existing metadata extractor (`service/audio_metadata.py::_extract_wav_metadata`) already handles it. The files are committed; they're tiny and they're the difference between "works on first `pnpm dev`" and "looks broken without external creds." |
| `.env.example` additions (non-secret) | `MUSIC_PROVIDER=mock` (one of `mock`, `suno`), `SUNO_API_KEY=` (commented placeholder, required only when `MUSIC_PROVIDER=suno`), `MUSIC_PROVIDER_DEFAULT_DURATION_SEC=30`. The five B2_* keys stay unchanged. |
| `docs/features/projects.md` | Inputs, outputs, flows, edge cases for the project lifecycle. |
| `docs/features/generation.md` | Generation pipeline, provider abstraction, mock vs real, polling behavior, error states. |
| `docs/features/revision-history.md` | Revision tree data model, branching semantics, compare flow. |
| `docs/features/stems.md` | Stems data model + "Generate Stems is coming soon" rationale, with pointers to where the real implementation slots in (`services/api/app/service/stems.py::split_stems`). |
| `docs/features/project-asset-explorer.md` | The per-project scoped bucket view. Why both `/files` (full) and the in-project view (scoped) exist. |
| `docs/exec-plans/completed/initial-scaffold.md` | This file, moved by Phase 5. |
| New e2e Playwright test stub (`apps/web/e2e/projects.spec.ts`) | Smoke: create project → generate (mock) → see node appear in tree → branch → see child node. Marked `.skip` until mock provider lands; documented in tech-debt-tracker. |

## 3. B2 Surface

All operations are **S3-only**. No b2-native calls. The single S3 client
construction in `repo/b2_client.py` retains the custom user-agent
(`b2ai-ai-music-studio` after rename — §6).

| S3 op | Where used | Notes |
|---|---|---|
| `PutObject` | Track audio upload (mock provider returns bytes; real provider URL → fetch → put), stems, reference-clip upload, `project.json` manifest writes, `track.json` per-track sidecar | Existing helper `upload_file()` reused; new helper `put_json(key, payload)` added for manifests. |
| `GetObject` | Reading `project.json` and `track.json` manifests when listing projects / building revision trees | New helper `get_json(key)`. |
| `ListObjectsV2` | List projects (`prefix=projects/`, `Delimiter=/`), list tracks in a project, list stems for a track, list reference clips, full-bucket explorer (unchanged) | All via existing `list_files(prefix)` pattern. |
| `HeadObject` | Per-track presign + existence check, parallel HEAD for project aggregates (total duration, total bytes) | Reuses `head_audio_objects_parallel` pattern (will be renamed to `head_track_objects_parallel`). |
| `DeleteObject` | Delete a single track variant (does **not** cascade — children become orphans, surfaced in UI) | Existing helper. |
| `DeleteObjects` (batch) | Archive/delete a whole project (deletes everything under `projects/<id>/`) | Existing helper, called with paginated chunks of 1000 keys. |
| `generate_presigned_url` | Inline playback for tracks + stems, attachment download for tracks + stems + project archive | Existing helper. |
| `HeadBucket` | `/health` endpoint connectivity check (unchanged) | |

**No multipart upload, no lifecycle management, no bucket-level config in
v1** — keeps the sample focused on the demo's "every artifact is a B2
object" story.

**B2-native:** **none.** Flagged as a hard rule in `AGENTS.md` after
rename.

## 4. Key Features (seed for README + `docs/features/`)

1. **Projects** — create, name, describe, list, archive. Each project is a
   single `project.json` manifest in B2 plus a tree of track artifacts under
   its prefix. (`docs/features/projects.md`)
2. **Music Generation** — prompt + style + duration → audio track stored in
   B2 with full provenance (prompt, provider, parent track) recorded in a
   sidecar `track.json`. Mock provider ships in-the-box; real Suno (or
   other) provider is a one-class swap. (`docs/features/generation.md`)
3. **Revision History** — every regeneration is a child node of the track
   it branched from, building a tree. Click any node to play it; click two
   to compare; click "branch from here" to spawn the next iteration.
   (`docs/features/revision-history.md`)
4. **Side-by-side Compare** — A/B two tracks: dual audio players + a diff
   panel (prompt diff, style diff, duration diff, audio-metadata diff).
   (`docs/features/revision-history.md`)
5. **Stems (placeholder)** — data model and UI ready; real split is
   stubbed and clearly marked "coming soon." Wiring point is documented.
   (`docs/features/stems.md`)
6. **Project Asset Explorer + Full-Bucket Explorer** — every project has a
   scoped view of its own B2 prefix (tracks/stems/reference); the global
   `/files` route keeps the unmodified full-bucket tree-view from the
   starter. (`docs/features/project-asset-explorer.md`)

## 5. Doc Transforms

| Starter doc | Action | Result |
|---|---|---|
| `README.md` | **Rewrite** | New tagline ("AI music generator with revision history, durable on B2"), new "What you get out of the box" list (Projects, Generation, Revision Tree, Compare, Stems-placeholder, Project Asset Explorer, Full Bucket Explorer), updated screenshots-TODO note (real PNGs deferred per skill rule "ask before binary assets"), updated Quick Start (adds `MUSIC_PROVIDER=mock` step), updated Tech Stack tagline ("Suno-compatible provider abstraction"). UTM tags updated per §6. |
| `AGENTS.md` | **Rewrite §1 Repository Map, §2 Invariants, §5 Commands** | §1 reflects new routes (`/projects`, `/projects/[id]`) and new backend modules. §2 keeps every existing invariant (layering, S3-only, no boto3 outside repo/, file size <300, custom user agent — now `b2ai-ai-music-studio`); adds two music-specific invariants: (a) **B2 prefix layout is canonical** (`projects/<project-id>/{project.json, tracks/<track-id>/{audio.<ext>, track.json, stems/<stem-name>.wav}, reference/<safe-filename>}`), (b) **`MusicProvider` interface is the only place a real generation API is allowed to be called** (parallel to "boto3 only in repo/"). §5 keeps all commands; no new ones needed. |
| `ARCHITECTURE.md` | **Rewrite Components, Data Stores, Data Flows, Canonical Files** | Components list adds projects/generation/revisions modules. Data Stores section spells out the B2 prefix layout. Data Flows section adds: generate flow (browser → POST /projects/{id}/generate → service drives provider → repo writes audio + sidecar → polling response), revision-tree flow (build_tree from `track.json` sidecars), compare flow. Canonical Files updated. |
| `docs/app-workflows.md` | **Rewrite** | New user journey: open studio → create project → write prompt → generate → listen → branch → compare → archive. |
| `docs/dev-workflows.md` | **Keep, append** | Existing testing/lint guidance kept; new section "Adding a new music provider" — points to `MusicProvider` interface and how to register the implementation. |
| `docs/design-system.md` | **Keep, append** | Add a short "RevisionTree" + "CompareDialog" entry to the primitives list. |
| `docs/SECURITY.md` | **Keep, append** | Add: provider API keys are server-side only, never leaked to the browser; generation endpoint rate-limit TODO (tech-debt). |
| `docs/RELIABILITY.md` | **Keep, append** | Add: generation jobs are long-running (10–60s for mock; minutes for real Suno) — polling pattern documented; timeouts; partial-failure semantics (manifest write retried, audio re-fetched on next list if sidecar missing). |
| `docs/features/audio-library.md` | **Replace with `docs/features/track-library.md`** | Same shape; framing changes from "audio assets" to "generated tracks across projects." |
| `docs/features/audio-playback.md` | **Replace with `docs/features/track-playback.md`** | Same shape; presigned-URL pattern unchanged. |
| `docs/features/audio-metadata.md` | **Keep** as-is | Extraction logic unchanged — both for uploaded reference clips and for generated tracks (their audio bytes are HEAD'd and parsed identically). |
| `docs/features/file-upload.md` | **Rewrite as `docs/features/reference-upload.md`** | Upload primitive scoped to project's `reference/` prefix. |
| `docs/features/file-browser.md` | **Keep** as-is | The full-bucket explorer's behavior is unchanged. |
| `docs/features/dashboard.md` | **Rewrite** | Metrics list updated: total projects, total tracks, total minutes generated, recent generation activity chart, provider breakdown (mock vs real). |
| `docs/features/_template.md` | **Keep** as-is | Template stays for future feature docs. |
| `docs/features/projects.md` | **New (stub)** | |
| `docs/features/generation.md` | **New (stub)** | |
| `docs/features/revision-history.md` | **New (stub)** | |
| `docs/features/stems.md` | **New (stub)** | |
| `docs/features/project-asset-explorer.md` | **New (stub)** | |
| `docs/exec-plans/completed/*` (starter history) | **Delete** | Replaced by `initial-scaffold.md` (this plan, after Phase 5). |
| `docs/exec-plans/tech-debt-tracker.md` | **Reset + append** | Existing starter-era debt removed; new entries added: (a) real Suno provider implementation, (b) real stem split implementation, (c) generation-endpoint rate limiting, (d) multi-user/shared-projects, (e) revision-tree graph rendering (replace indented list with d3-force or similar), (f) e2e test currently `.skip`. |
| `docs/images/dashboard.png`, `docs/images/library.png` | **Delete** | They show the starter's UI, not music-studio's. README is updated to reference *future* screenshot paths and notes that real images are deferred — skill says to ask before binary assets. |

## 6. Rename Table

Apply across every text file in the tree (skipping `node_modules`,
`.venv`, `dist`, `build`, `.next`, `.git`). Case-sensitive matches; the
table is ordered longest-first to avoid partial replacements.

| Old | New | Where it appears |
|---|---|---|
| `b2ai-ai-audio-starter-kit` | `b2ai-ai-music-studio` | `repo/b2_client.py` user-agent extra; every UTM `utm_content` tag in README links; any image alt-text tags that include it |
| `@ai-audio-starter-kit/web` | `@ai-music-studio/web` | `apps/web/package.json` `name`; `apps/web/package.json` workspace refs |
| `@ai-audio-starter-kit/shared` | `@ai-music-studio/shared` | `packages/shared/package.json` `name`; consumers in `apps/web/package.json` and any imports |
| `ai-audio-starter-kit` (kebab) | `ai-music-studio` | Root `package.json` `name`; `pnpm-workspace.yaml` (none currently, but check); `pnpm test:e2e` filter (`pnpm --filter @ai-audio-starter-kit/web exec playwright install chromium`); GitHub repo URLs in README; clone instructions; Railway service names in `infra/railway/`; LICENSE references; docker image tags if any (none currently); doctor.mjs identifiers |
| `ai_audio_starter_kit` (snake) | `ai_music_studio` | Any Python module names, env-var fallbacks, or test fixture names (currently none observed but search-and-replace to be safe) |
| `AI Audio Starter Kit` (Title Case) | `AI Music Studio` | README H1, AGENTS.md H1, ARCHITECTURE.md H1, docs/* headings, frontend brand text in `apps/web/src/app/layout.tsx` and any nav components |
| `Build AI audio applications…` (README tagline) | `Generate music with first-class revision history, durable on B2.` | README top paragraph |
| `audio-library` (route + feature doc + nav label) | `track-library` (route stays `/library` to minimize churn; doc filename + nav label change) | `apps/web/src/app/library/page.tsx` copy; nav config; doc filename |
| `audio-playback` (doc + module) | `track-playback` (doc); backend module renamed to `track_playback` where it stands alone | doc filename; any module names |
| `audio-asset-card` (component family) | **Kept** (it's a generic primitive — the *visual* card for any audio asset; tracks render through it) | no change |
| `audio/` (B2 prefix used by the Library) | **Kept** for backward-compat with the upload pipeline if a user uploads a reference clip via the legacy route, but **the music-studio canonical prefix is `projects/<project-id>/…`** | mostly documentation; backend code keeps `audio/` recognized by the legacy library lister so the sample remains runnable if someone seeds the bucket directly |
| `head_audio_objects_parallel` | `head_track_objects_parallel` | `repo/b2_audio.py` → renamed file `repo/b2_tracks.py`; all callers updated |
| `b2_audio.py` | `b2_tracks.py` | filename + imports |
| `AudioAsset` (type) | **Kept** (still the right shape for a generic audio file row) — but **the `Track` type is the music-studio first-class entity** (carries `project_id`, `parent_track_id`, `prompt`, etc., and embeds an `AudioAsset` for the file half) | `packages/shared/src/types.ts`; `services/api/app/types/library.py` |
| `last_verified: 2026-05-21` (in markdown frontmatter comments) | `last_verified: 2026-05-26` | every doc top-of-file |

UTM content tag: **`b2ai-ai-music-studio`** (used in every Backblaze
referral link in README and feature docs).

## 7. Open Questions — resolved in this plan

1. **Stem separation in-pipeline or punt?** → **Punt.** v1 ships the data
   model (`Stem` type, `stems_keys` on `Track`) and a disabled "Generate
   Stems (coming soon)" button. `services/api/app/service/stems.py::split_stems`
   raises `NotImplementedError` with a docstring pointing at the wiring
   spot. Added to `docs/exec-plans/tech-debt-tracker.md`.
2. **Collaboration (shared projects) v1 or later?** → **Later.** v1 is
   single-user (no auth). Project IDs are UUIDs; nothing in the data model
   prevents adding owner/ACL fields in v2. Added to the tech-debt tracker
   with a note that the manifest schema is forward-compatible.

## 8. Handoff to Phase 2 (b2-sample-builder)

The builder will be told **explicitly**:
- Source path: `.claude/scratch/vcsk-7817bca5-4e25-4069-9511-6f9ca7a2657d/`
  (contents are `ai-audio-starter-kit`, not the default
  `vibe-coding-starter-kit` the agent's prompt was written for).
- Plan file: this file.
- Parent CLAUDE.md does **not** exist at `../CLAUDE.md`. Use the starter
  kit's own `AGENTS.md` (copied + rewritten per §5) as the standards
  source, plus the `b2-doctor` skill self-check.
- All rename strings must come from §6 of this plan, not from the agent's
  hard-coded list of `vibe-coding-starter-kit` variants.
