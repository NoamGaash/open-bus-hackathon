import { defineConfig, devices } from '@playwright/test'

// All API calls are intercepted with page.route() and served from local
// fixtures (see e2e/fixtures/), so this only needs the Vite dev server —
// the Python API is never started for these tests.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  // Chromium only — keeps CI fast; the app has no browser-specific surface
  // area worth covering with Firefox/WebKit here.
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  webServer: {
    command: 'npm run dev -- --port 5173',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
