import { test, expect } from "@playwright/test";

test.describe("Smoke", () => {
  test("dashboard renders", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("projects page renders", async ({ page }) => {
    await page.goto("/projects");
    await expect(page).toHaveURL(/projects/);
  });

  test("files page renders", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });
});
