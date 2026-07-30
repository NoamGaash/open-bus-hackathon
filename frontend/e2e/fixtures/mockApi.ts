// Intercepts every /api/** call the dashboard makes and serves the fixtures in
// ./data.ts instead. The real analyses hit a public transit API and take
// 60-90s per call — completely unusable in CI — so tests must never let a
// request reach the network.

import type { Page } from '@playwright/test'

import { analysesListResponse, agenciesResponse, RESULTS_BY_NAME } from './data'

export async function mockApi(page: Page): Promise<void> {
  await page.route('**/api/analyses', async (route) => {
    // Only the bare list endpoint — /api/analyses/{name}/run is a longer path
    // and gets its own route below, but be defensive and only handle GET here.
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({ json: analysesListResponse })
  })

  await page.route('**/api/agencies', async (route) => {
    await route.fulfill({ json: agenciesResponse })
  })

  await page.route('**/api/analyses/*/run', async (route) => {
    const url = new URL(route.request().url())
    // .../api/analyses/<name>/run
    const parts = url.pathname.split('/').filter(Boolean)
    const name = decodeURIComponent(parts[parts.length - 2] ?? '')
    const result = RESULTS_BY_NAME[name]
    if (!result) {
      await route.fulfill({
        status: 404,
        json: { detail: `No fixture registered for analysis "${name}"` },
      })
      return
    }
    await route.fulfill({ json: result })
  })
}
