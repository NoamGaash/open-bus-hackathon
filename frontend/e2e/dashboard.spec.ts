import { expect, test } from '@playwright/test'

import {
  ERROR_MESSAGE,
  chartMeta,
  errorMeta,
  hbarMeta,
  heatmapMeta,
  metricsMeta,
} from './fixtures/data'
import { mockApi } from './fixtures/mockApi'

// Every test intercepts /api/** with local fixtures — no request here is
// allowed to reach the real API (it hits a public transit endpoint and takes
// 60-90s per call, which would make this suite unusable).
test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('dashboard loads and shows the masthead heading', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Open Bus — Hackathon' })).toBeVisible()
})

test('a card renders for each analysis in the mocked analyses list', async ({ page }) => {
  await page.goto('/')
  for (const m of [metricsMeta, chartMeta, hbarMeta, heatmapMeta, errorMeta]) {
    await expect(page.getByRole('heading', { level: 2, name: m.title })).toBeVisible()
  }
})

test('the metrics card shows its stat tiles', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, metricsMeta.title)
  await expect(card.getByText('On-time %')).toBeVisible()
  await expect(card.getByText('Avg delay')).toBeVisible()
  await expect(card.getByText('Total rides')).toBeVisible()
  // Three tiles rendered, one per fixture metric — not just the labels, but
  // stat tiles as a structural unit.
  await expect(card.locator('.tile')).toHaveCount(3)
  // The formatted headline value is rendered too, not just the label.
  await expect(card.locator('.tile-value', { hasText: '87.5' })).toBeVisible()
})

test('the chart card renders an svg', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, chartMeta.title)
  const svg = chartSvg(card)
  await expect(svg).toBeVisible()
  // The chart draws its own line paths; a real render has some.
  await expect(svg.locator('path')).not.toHaveCount(0)
})

test('the hbar card renders a horizontal bar chart with rect bars', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, hbarMeta.title)
  const svg = chartSvg(card)
  await expect(svg).toBeVisible()
  // Bars render as <rect> elements — 2 series x 2 categories = 4 bars.
  await expect(svg.locator('rect')).not.toHaveCount(0)
  // Horizontal layout puts the long category labels on the y axis (truncated
  // with an ellipsis past 28 chars by Chart.tsx's rowLabel — check a prefix
  // that survives the truncation, not the full untruncated string).
  await expect(svg.getByText('Central Station ←', { exact: false })).toBeVisible()
})

test('the heatmap card renders a colored cell table', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, heatmapMeta.title)
  // The heatmap is a real <table>, not an SVG — see Heatmap.tsx.
  const grid = card.locator('table.hm-table')
  await expect(grid).toBeVisible()
  // 4 rows x 3 cols in the fixture; 2 of those 12 are deliberately absent.
  await expect(grid.locator('td.hm-cell')).toHaveCount(12)
  await expect(grid.locator('td.hm-empty')).toHaveCount(2)
  // One under-sampled cell gets the hatched treatment, distinct from both
  // a solid cell and an absent one.
  await expect(grid.locator('td.hm-weak')).toHaveCount(2)
  // Row labels render in the sticky first column.
  await expect(grid.getByRole('rowheader', { name: 'Stop A' })).toBeVisible()
})

test('the error card shows its error message text', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, errorMeta.title)
  await expect(card.getByText(ERROR_MESSAGE)).toBeVisible()
})

test('the chart card "table" toggle switches to a relief table view', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, chartMeta.title)
  await expect(chartSvg(card)).toBeVisible()
  await expect(card.locator('table')).toHaveCount(0)

  await card.getByRole('button', { name: 'table', exact: true }).click()

  await expect(card.locator('table')).toBeVisible()
  await expect(chartSvg(card)).toHaveCount(0)
  // The relief table carries the series names as column headers.
  await expect(card.getByRole('columnheader', { name: 'Line 480' })).toBeVisible()
})

test('the heatmap card "table" toggle switches to a relief table view', async ({ page }) => {
  await page.goto('/')
  const card = cardFor(page, heatmapMeta.title)
  await expect(card.locator('table.hm-table')).toBeVisible()

  await card.getByRole('button', { name: 'table', exact: true }).click()

  // The relief view is a plain table; the colored heatmap grid goes away.
  await expect(card.locator('.table-wrap table')).toBeVisible()
  await expect(card.locator('table.hm-table')).toHaveCount(0)
  await expect(card.getByRole('columnheader', { name: '07:00' })).toBeVisible()
})

test('no uncaught page errors or console errors while exercising the dashboard', async ({
  page,
}) => {
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  page.on('pageerror', (err) => pageErrors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })

  await page.goto('/')

  // Wait for every mocked card to finish its run.
  for (const m of [metricsMeta, chartMeta, hbarMeta, heatmapMeta, errorMeta]) {
    await expect(page.getByRole('heading', { level: 2, name: m.title })).toBeVisible()
  }
  await expect(cardFor(page, metricsMeta.title).getByText('On-time %')).toBeVisible()
  await expect(chartSvg(cardFor(page, chartMeta.title))).toBeVisible()
  await expect(chartSvg(cardFor(page, hbarMeta.title))).toBeVisible()
  await expect(cardFor(page, heatmapMeta.title).locator('table.hm-table')).toBeVisible()
  await expect(cardFor(page, errorMeta.title).getByText(ERROR_MESSAGE)).toBeVisible()

  // Exercise the table toggles and the "run all" button too — the more of the
  // UI that runs in this pass, the more this assertion is actually worth.
  await cardFor(page, chartMeta.title).getByRole('button', { name: 'table', exact: true }).click()
  await cardFor(page, hbarMeta.title).getByRole('button', { name: 'table', exact: true }).click()
  await cardFor(page, heatmapMeta.title)
    .getByRole('button', { name: 'table', exact: true })
    .click()
  await page.getByRole('button', { name: 'Run all' }).click()
  for (const m of [metricsMeta, chartMeta, hbarMeta, heatmapMeta, errorMeta]) {
    await expect(page.getByRole('heading', { level: 2, name: m.title })).toBeVisible()
  }

  expect(pageErrors, `uncaught page errors: ${pageErrors.join('\n')}`).toEqual([])
  expect(consoleErrors, `console errors: ${consoleErrors.join('\n')}`).toEqual([])
})

function cardFor(page: import('@playwright/test').Page, title: string) {
  return page.locator('section.card', { has: page.getByRole('heading', { level: 2, name: title }) })
}

// The chart/heatmap components render via Recharts, whose <svg class="recharts-surface">
// is the actual plot. The heatmap additionally renders a 0x0 <svg> purely to hold a
// <defs><pattern> for the "weak cell" hatching, which is a real (if invisible) svg
// element — so a bare `svg` locator is ambiguous. Target the surface explicitly.
function chartSvg(card: import('@playwright/test').Locator) {
  return card.locator('svg.recharts-surface')
}
