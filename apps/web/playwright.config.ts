import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  globalTeardown: "./e2e/global-teardown.ts",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3010",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e-api.ps1",
      cwd: "../..",
      url: "http://127.0.0.1:8010/api/v1/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e-web.ps1",
      cwd: "../..",
      url: "http://127.0.0.1:3010",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
