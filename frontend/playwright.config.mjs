import { defineConfig } from "@playwright/test";
import { REPO_ROOT, resolveFrontendTarget } from "../scripts/frontend-targets.mjs";

const frontendTarget = resolveFrontendTarget(process.env);

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.mjs",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: frontendTarget.url,
    headless: true,
  },
  webServer: frontendTarget.start
    ? {
        command: frontendTarget.command,
        url: frontendTarget.healthUrl || frontendTarget.url,
        reuseExistingServer: true,
        cwd: REPO_ROOT,
        timeout: 60_000,
      }
    : undefined,
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
