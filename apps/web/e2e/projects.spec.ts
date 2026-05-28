import { expect, test } from "@playwright/test";

const projectId = "123e4567-e89b-42d3-a456-426614174000";
const trackId = "track-e2e";

const project = {
  project_id: projectId,
  name: "E2E smoke",
  description: null,
  created_at: "2026-05-28T12:00:00Z",
  archived: false,
  track_count: 1,
  owner_id: "local",
  shared_with: [],
};

const track = {
  track_id: trackId,
  project_id: projectId,
  prompt: "ambient calm pad",
  style: null,
  negative_tags: null,
  make_instrumental: false,
  generation_mode: "create",
  continue_at_sec: null,
  audio_weight: null,
  duration_sec: 30,
  provider: "musicapi",
  provider_task_id: "task-e2e",
  provider_clip_id: "clip-e2e",
  parent_track_id: null,
  generation_ms: 1000,
  created_at: "2026-05-28T12:00:10Z",
  is_orphaned: false,
  audio: {
    key: `projects/${projectId}/tracks/${trackId}/audio.mp3`,
    size_bytes: 100,
    size_human: "100 B",
    content_type: "audio/mpeg",
    created_at: "2026-05-28T12:00:10Z",
    duration_ms: 30000,
    sample_rate: 44100,
    channels: 2,
    bit_depth: null,
    codec: "mp3",
    title_preview: "track-e2e.mp3",
    project_id: projectId,
    track_id: trackId,
    source: "project",
  },
  variants: [],
  stems_keys: [],
};

test("create project, queue generation, and render generated node", async ({ page }) => {
  let created = false;
  let generated = false;

  await page.route("**/projects", async (route) => {
    const request = route.request();
    if (request.method() === "GET") {
      await route.fulfill({ json: created ? [project] : [] });
      return;
    }
    created = true;
    await route.fulfill({ json: project });
  });
  await page.route(`**/projects/${projectId}`, async (route) => {
    await route.fulfill({ json: project });
  });
  await page.route(`**/projects/${projectId}/revisions`, async (route) => {
    await route.fulfill({ json: generated ? [{ track, children: [] }] : [] });
  });
  await page.route(`**/projects/${projectId}/generate`, async (route) => {
    generated = true;
    await route.fulfill({
      json: {
        project_id: projectId,
        track_id: trackId,
        state: "queued",
        started_at: "2026-05-28T12:00:05Z",
        finished_at: null,
        error: null,
      },
    });
  });
  await page.route(`**/projects/${projectId}/generations/${trackId}`, async (route) => {
    await route.fulfill({
      json: {
        project_id: projectId,
        track_id: trackId,
        state: "succeeded",
        started_at: "2026-05-28T12:00:05Z",
        finished_at: "2026-05-28T12:00:10Z",
        error: null,
      },
    });
  });
  await page.route(`**/files?prefix=projects/${projectId}%2F**`, async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto("/projects");
  await page.getByRole("button", { name: /New project/i }).click();
  await page.getByLabel("Name").fill("E2E smoke");
  await page.getByRole("button", { name: /^Create$/i }).click();
  await expect(page.getByText("E2E smoke")).toBeVisible();

  await page.getByText("E2E smoke").click();
  await page.getByLabel("Prompt").fill("ambient calm pad");
  await page.getByRole("button", { name: /^Generate$/i }).click();

  await expect(page.getByText("ambient calm pad")).toBeVisible();
  await expect(page.getByText("musicapi")).toBeVisible();
});
