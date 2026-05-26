import { test, expect } from "@playwright/test";

/**
 * E2E smoke for the music-studio projects flow.
 *
 * **Currently `test.skip`** — the full flow requires the dev API to be
 * running with `MUSIC_PROVIDER=mock` so the generation step returns a
 * pre-baked WAV. Tracked under `docs/exec-plans/tech-debt-tracker.md`:
 * wire this into CI once a deterministic mock-driven harness is in
 * place.
 */
test.describe.skip("Projects flow", () => {
  test("create project → generate → see node → branch → see child", async ({ page }) => {
    await page.goto("/projects");
    await page.getByRole("button", { name: /New project/i }).click();
    await page.getByLabel("Name").fill("E2E smoke");
    await page.getByRole("button", { name: /Create/i }).click();
    await expect(page.getByText("E2E smoke")).toBeVisible();

    // Click into the new project.
    await page.getByText("E2E smoke").click();

    // Generate first track.
    await page.getByLabel("Prompt").fill("ambient calm pad");
    await page.getByRole("button", { name: /Generate/i }).click();
    await expect(page.getByText(/mock/)).toBeVisible({ timeout: 15_000 });

    // Branch from the new node.
    await page.getByRole("button", { name: /Branch/i }).first().click();
    await page.getByLabel("Prompt").fill("ambient calm pad with bells");
    await page.getByRole("button", { name: /Generate/i }).click();

    // Two track nodes should now be visible.
    await expect(page.getByText(/track-/).first()).toBeVisible();
  });
});
