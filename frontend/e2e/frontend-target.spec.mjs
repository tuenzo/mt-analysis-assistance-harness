import { expect, test } from "@playwright/test";
import { resolveFrontendTarget } from "../../scripts/frontend-targets.mjs";

const frontendTarget = resolveFrontendTarget(process.env);
const isDedicatedTestTarget =
  frontendTarget.name === "test" || frontendTarget.url.includes(":4180");

function isIgnorableConsoleError(text) {
  return text.startsWith("Failed to load resource:");
}

test.describe("frontend target", () => {
  test("loads selected target without page errors", async ({ page }) => {
    const consoleErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => consoleErrors.push(error.message));

    await page.goto(frontendTarget.url);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(1_000);

    const bodyText = await page.locator("body").innerText();
    expect(bodyText.trim().length).toBeGreaterThan(0);
    expect(consoleErrors.filter((text) => !isIgnorableConsoleError(text))).toHaveLength(0);
  });
});

test.describe("dedicated harness test frontend", () => {
  test.skip(!isDedicatedTestTarget, "Only applies to the fixed 4180 test target.");

  test("renders the agent analysis test harness", async ({ page }) => {
    await page.goto(frontendTarget.url);
    await expect(page.getByText("Agent Analysis Test Harness")).toBeVisible();
    await expect(page.getByText("Observed Contract")).toBeVisible();
    await expect(page.locator("textarea[placeholder='Enter an agent analysis prompt']")).toBeVisible();
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible();
  });
});
