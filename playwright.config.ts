import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/ui',
  fullyParallel: false,  // Run tests sequentially (they modify shared state)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,  // Single worker to avoid race conditions
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'https://bookmark.gstoehl.dev/dev',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
