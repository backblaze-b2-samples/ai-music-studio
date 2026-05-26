<!-- last_verified: 2026-05-26 -->
# AI Music Studio

Generate music with first-class revision history, durable on Backblaze B2.

A B2 sample app that demonstrates a Suno/Udio-style AI music generator
where **every regeneration, remix, and branch is captured as a node in a
revision tree against a project**. Audio (full tracks and stems) and
project manifests live under a stable `projects/<project-id>/…` prefix
in **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-ai-music-studio)**
via the S3-compatible API — already integrated.

**What you get out of the box:**
- `/projects` — create projects, see every one's revision tree, branch, compare A/B
- `/projects/[id]` — prompt + style + duration form, "generating…" state, currently-selected-track player, Project Files tab scoped to `projects/<id>/`
- `/library` — cross-project Track Library: every generated track in one grid, with inline playback, download, and delete
- `/files` — full B2 bucket explorer (tree view, preview, download, delete) — unchanged from the underlying starter
- `/` (Dashboard) — total tracks, total minutes generated, daily generation activity, format breakdown
- A `MusicProvider` interface with a built-in `MockMusicProvider` (returns a pre-baked WAV from `services/api/app/repo/_mock_tracks/`) so the sample is runnable end-to-end with **zero external credentials**. Drop in a `SunoMusicProvider` (stub included) when you're ready to plug into the real Suno API.
- FastAPI backend with strict layered architecture (`types -> config -> repo -> service -> runtime`) and structural tests that enforce it
- Agent-optimized docs — your AI coding agent can read the repo and start contributing immediately

> **Screenshots TBD** — sample is runnable; capture once UI is live.
> (The starter's `docs/images/{dashboard,library}.png` were removed because
> they showed the underlying starter's UI, not music-studio's.)

## Agent-First Architecture

This repo is optimized for coding agents. Point your agent at it and start building.

The structure follows the principle that **repository knowledge is the system of record**. Anything an agent can't access in-context doesn't exist — so everything it needs to reason about the codebase is versioned, co-located, and discoverable from the repo itself.

### How it works

**[AGENTS.md](AGENTS.md) is the single source of truth for all coding agents.** A ~100 line entry point gives agents the repository layout, architectural invariants, commands, conventions, and pointers to deeper docs. Agent-specific files (CLAUDE.md, etc.) are thin pointers back to AGENTS.md.

**Architecture is enforced mechanically, not by convention.** Layering rules, import boundaries, file size limits, SDK containment, **and the "generation API calls only in `MusicProvider`" boundary** are verified by structural tests and lints that run on every change.

**The knowledge base is structured for progressive disclosure:**

```
AGENTS.md              Single source of truth — layout, invariants, commands, conventions
ARCHITECTURE.md        System layout, layering rules, data flows
docs/
  features/            Feature docs (projects, generation, revisions, stems, asset-explorer, …)
  app-workflows.md     User journeys
  dev-workflows.md     Engineering workflows and testing
  SECURITY.md          Security principles
  RELIABILITY.md       Reliability expectations
  exec-plans/          Execution plans and tech debt tracker
```

### Key design decisions

| Principle | Implementation |
|-----------|---------------|
| Give agents a single source of truth | AGENTS.md ~100 lines — layout, invariants, commands, conventions |
| Enforce invariants mechanically | Structural tests + ruff + ESLint verify boundaries |
| DRY documentation | Each fact lives in one place; no redundant files to drift |
| Strict layered architecture | `types -> config -> repo -> service -> runtime`, enforced by tests |
| Single boundary for external generation APIs | `MusicProvider` interface — verified by structural test (mirror of "boto3 only in repo/") |
| Prefer boring, composable libraries | stdlib `wave` + `mutagen` for audio metadata, no ffmpeg |
| Contain external SDKs | `boto3` only in `repo/` layer — verified by structural test |
| Keep files agent-sized | 300-line limit per file, enforced by test |
| Docs updated with code | Same-PR requirement prevents documentation rot |
| Structured observability | JSON logging, `/metrics` endpoint, request tracing |

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-ai-music-studio)**.

### Start a new project

**Option 1: GitHub Template (recommended)**

Click the green **"Use this template"** button at the top of this repo, name your project, then:

```bash
git clone https://github.com/yourorg/my-music-app.git
cd my-music-app
```

**Option 2: Clone and reinitialize**

```bash
git clone https://github.com/backblaze-b2-samples/ai-music-studio.git my-music-app
cd my-music-app
rm -rf .git
git init
git add .
git commit -m "Initial commit from ai-music-studio"
```

### Setup

**1. Install dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

**3. Add your B2 credentials and pick a music provider**

Set up your local `.env`:

```bash
cp .env.example .env
```

Open `.env`. The `MUSIC_PROVIDER=mock` default lets you run the sample
end-to-end with no external generation-API credentials; only the B2
keys are required.

Then head to the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-ai-music-studio) and:

1. **Create a bucket.** B2 will show three values — paste each into `.env`:
   - **Bucket Unique Name** -> `B2_BUCKET_NAME`
   - **Endpoint** -> `B2_ENDPOINT`
   - **Region** (the path segment of the endpoint, e.g. `us-west-004`) -> `B2_REGION`
2. **Create an application key** with `Read and Write` permission. B2 will show two values — paste each into `.env`:
   - **keyID** -> `B2_KEY_ID`
   - **applicationKey** -> `B2_APPLICATION_KEY` *(only shown once — paste it now)*

> Want a walkthrough? See the docs for [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-ai-music-studio) and [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-ai-music-studio).

**4. Run it**

```bash
pnpm dev
```

That's it. Frontend at `localhost:3000`, API at `localhost:8000`. Open
`/projects`, create a project, write a prompt, hit Generate — the
`MockMusicProvider` returns a pre-baked tone in ~1s and the new track
shows up in the revision tree.

`pnpm dev` runs `pnpm doctor` first — a preflight check that catches the common setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, ports already taken) and tells you exactly how to fix each one. Run it standalone any time with `pnpm doctor`.

## Core Features

- [Projects](docs/features/projects.md) — create / list / archive / delete; every project lives at `projects/<id>/project.json` in B2
- [Generation](docs/features/generation.md) — prompt + style + duration → `projects/<id>/tracks/<track-id>/audio.<ext>`; `MusicProvider` abstraction with `MockMusicProvider` (default) and `SunoMusicProvider` (stub)
- [Revision History](docs/features/revision-history.md) — every regeneration is a child node of its parent track; the tree is reconstructed from `track.json` sidecars in B2
- [Compare](docs/features/revision-history.md) — A/B two tracks: dual audio players + a diff list (prompt / style / duration / audio-metadata)
- [Stems (placeholder)](docs/features/stems.md) — data model live, generation stubbed (`NotImplementedError`); UI surfaces a disabled "Generate Stems (coming soon)" button
- [Project Asset Explorer](docs/features/project-asset-explorer.md) — per-project scoped view of the project's B2 prefix; complements the unmodified full-bucket explorer at `/files`
- [Track Library](docs/features/track-library.md) — cross-project library: every generated track in one grid with inline playback / download / delete
- [Audio Metadata Extraction](docs/features/audio-metadata.md) — duration, sample rate, channels, bit depth, codec. Stdlib `wave` + `mutagen`; no ffmpeg
- [Bucket Explorer](docs/features/file-browser.md) — full B2 bucket tree view (unchanged from the underlying starter)
- [Dashboard](docs/features/dashboard.md) — total tracks, total minutes generated, generation activity chart, recent tracks table

Plus the cross-cutting essentials inherited from the underlying starter:
- Inline error handling — fetch failures surface *what's wrong* (API offline, 401, 5xx) and offer a Retry
- Single-source config — one `.env` at the repo root powers both API and web app, validated at startup
- Centralized data layer — every fetch goes through TanStack Query hooks in `apps/web/src/lib/queries.ts`
- Structural tests — verify layering rules, import boundaries, SDK containment, file size limits, **and the MusicProvider-only generation-API rule**
- Structured JSON logging — every request traced with `request_id` and timing
- `/health` endpoint — B2 connectivity check
- `/metrics` endpoint — Prometheus-format counters (request count, latency, uploads)

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry, stale-while-revalidate for every fetch
- Python 3.11+, FastAPI, boto3, Pydantic v2, `mutagen` (pure-Python audio metadata)
- Suno-compatible provider abstraction — `mock` ships in-the-box; `suno` slot is a one-class swap
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @ai-music-studio/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (projects, generation, revisions, stems, asset explorer, library, dashboard, metadata, file browser) |
| [docs/design-system.md](docs/design-system.md) | Design tokens, primitives, AI elements, loader, the `AudioAssetCard` |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## Contributing

Start with [AGENTS.md](AGENTS.md). It's the map — everything else is discoverable from there.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
