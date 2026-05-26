<!-- last_verified: 2026-05-26 -->
# Dev Workflows

Engineering workflows for this repo.

## New Feature

- [ ] Read `AGENTS.md` and `ARCHITECTURE.md`
- [ ] Read the relevant feature doc in `docs/features/`
- [ ] For non-trivial changes, create a plan in `docs/exec-plans/active/`
- [ ] Implement the smallest coherent change
- [ ] Add or update tests
- [ ] Run: `pnpm typecheck && pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- [ ] Update docs in the same PR (see AGENTS.md §8)
- [ ] Move plan to `docs/exec-plans/completed/` after validation

## Bugfix

- [ ] Add a failing test that reproduces the bug
- [ ] Confirm the test fails
- [ ] Implement the fix
- [ ] Rerun tests until green
- [ ] Update docs if behavior changed

## Refactor

- [ ] Read `ARCHITECTURE.md` — respect layering rules
- [ ] Ensure structural tests still pass: `pnpm check:structure`
- [ ] No behavior changes without updating feature docs

## Documentation Update

- [ ] Update only the canonical location (see AGENTS.md §8 doc update mapping)
- [ ] Never duplicate content — link instead
- [ ] Update `<!-- last_verified: YYYY-MM-DD -->` header

## Pull Request

- [ ] One coherent change per PR
- [ ] Run full lint + test suite before submitting
- [ ] Docs updated in the same PR as code changes
- [ ] Only change files relevant to the task — no drive-by improvements

## Testing

### Test types
- **Unit**: pure logic (service layer — key validation, audio metadata extraction)
- **Integration**: HTTP handlers, B2 connectivity (`tests/`)
- **Structural**: layering rules, import boundaries (`tests/test_structure.py`)
- **E2E**: Playwright browser-driven smoke tests

### Audio fixtures
Tests that need audio input can construct minimal RIFF WAV bytes inline (1
second of silence is enough to exercise `service/audio_metadata.py`). For
formats `mutagen` decodes (mp3 / flac / ogg / m4a / aac / opus) prefer
checked-in fixtures kept under 50 KB. Never ship copyrighted audio.

### Test placement
- Backend: `services/api/tests/`
- E2E: project root (Playwright)

### Commands
- Quick (backend): `pnpm test:api`
- Structure: `pnpm check:structure`
- Frontend typecheck: `pnpm typecheck`
- Frontend lint: `pnpm lint`
- Backend lint: `pnpm lint:api`
- Full suite: `pnpm typecheck && pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- E2E: `pnpm test:e2e` (run `pnpm --filter @ai-music-studio/web exec playwright install chromium` once first)

### When to run
- After behavior change: run relevant subset
- Before PR: run full suite

## Frontend Conventions

- Tailwind v4: config via CSS `@theme` blocks, NOT `tailwind.config.ts`
- Colors: OKLch format
- Dark mode: `next-themes` with `@custom-variant dark (&:is(.dark *))`
- Animations: `tw-animate-css` (not `tailwindcss-animate`)
- shadcn/ui components in `src/components/ui/` are generated — never modify them

## Data Fetching

All API reads/writes flow through TanStack Query hooks in
`apps/web/src/lib/queries.ts`. Don't add bare `useEffect + fetch` patterns
to components.

**Read** — use the hooks directly:

```tsx
const { data, isLoading, error, refetch } = useFiles(prefix, limit);
const { data: stats } = useFileStats();
```

Surface errors via `<ErrorState error={error} onRetry={() => refetch()} />`
rather than silently rendering empty UI.

**Write** — wrap mutations with `useMutation` and invalidate on success:

```tsx
const deleteMutation = useDeleteFile();
deleteMutation.mutate(file.key, {
  onSuccess: () => toast.success("Deleted"),
});
```

`useDeleteFile()` already calls `queryClient.invalidateQueries({ queryKey: qk.all })`
on success — every consumer of `useFiles` / `useFileStats` re-fetches lazily.

**Add a new endpoint** — three places to touch:
1. `services/api/app/runtime/<router>.py` — FastAPI route
2. `apps/web/src/lib/api-client.ts` — typed fetch wrapper
3. `apps/web/src/lib/queries.ts` — `useQuery` / `useMutation` hook + entry in `qk`

Defaults (in `apps/web/src/lib/query-client.tsx`):
- `staleTime: 30s` — file lists / stats don't change second-to-second
- `retry: 1` for transient errors; never retry 4xx (won't get better)
- `refetchOnWindowFocus`: on (TanStack default) — dashboard self-heals
  when the user comes back to the tab

## Adding a new music provider

Music-studio routes generation through `MusicProvider` in
`services/api/app/repo/music_provider.py`. This is the **only** module
allowed to call a real generation API (mirror of "boto3 only in repo/";
enforced by `tests/test_structure.py::test_generation_http_only_in_music_provider`).

To add a provider — e.g., Udio:

1. Subclass `MusicProvider` inside `music_provider.py` and set `name = "udio"`.
2. Implement `generate(prompt, style, duration_sec, **kwargs) -> GenerationResult`.
   - Return raw audio bytes, the file extension (`"mp3"`, `"wav"`, …),
     a fresh `track_id` (UUID-4 string), and `generation_ms`.
   - Read API keys from `settings` (declare them in `app/config/settings.py`
     and `.env.example`).
3. Add a branch to `get_provider()` so `MUSIC_PROVIDER=udio` resolves to
   your new class. Unknown names already fail fast with `ValueError`.
4. Update `docs/features/generation.md` (Provider abstraction section)
   and `.env.example` (new key + a comment on when it's required).
5. Add an entry to `docs/exec-plans/tech-debt-tracker.md` if anything
   ships as a stub.

The structural test for the MusicProvider boundary will catch any HTTP
client (`requests`, `httpx`) imported outside `music_provider.py` —
don't try to call your provider from `service/` or `runtime/` directly.
