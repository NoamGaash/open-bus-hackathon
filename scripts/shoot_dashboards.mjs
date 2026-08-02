// Capture per-feature panels from the three standalone hackathon dashboards, so
// each upstream porting ticket can show the specific chart it is asking for.
//
//   node scripts/shoot_dashboards.mjs <outdir>
//
// Run from frontend/ so @playwright/test resolves; needs ./dev serving :5173.
import { chromium } from '@playwright/test'
import fs from 'node:fs'

const OUT = process.argv[2]
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()

/** Screenshot a clipped band of a full page — panels have no stable ids. */
async function band(page, name, top, height) {
  const w = await page.evaluate(() => document.body.scrollWidth)
  await page.screenshot({
    path: `${OUT}/${name}.png`,
    clip: { x: 0, y: top, width: Math.min(w, 1500), height },
  })
  console.log(`  ${name}.png`)
}

async function open(url, waitMs = 12000) {
  const page = await browser.newPage({
    viewport: { width: 1500, height: 1000 },
    deviceScaleFactor: 1.5,
  })
  await page.goto(url, { waitUntil: 'networkidle', timeout: 180000 })
  await page.waitForTimeout(waitMs)
  return page
}

// ── bunching ────────────────────────────────────────────────────────────────
{
  const p = await open('http://localhost:5173/bunching-reasons.html')
  await band(p, 'bunch-header-kpis', 0, 260)      // headline + six KPI tiles
  await band(p, 'bunch-why-decomposition', 250, 190) // the causal split
  await band(p, 'bunch-hour-and-filters', 430, 240)
  await band(p, 'bunch-ranked-table', 660, 900)   // planned vs effective gap, waits
  await p.close()
}

// ── street speed ────────────────────────────────────────────────────────────
{
  const p = await open('http://localhost:5173/tlv-bus-speed.html')
  await band(p, 'speed-header-kpis', 0, 260)
  await band(p, 'speed-controls', 250, 220)
  await band(p, 'speed-map', 440, 900)            // the street-level map
  await band(p, 'speed-corridors', 1340, 700)     // bus-minutes-lost ranking
  await p.close()
}

// ── editorial ───────────────────────────────────────────────────────────────
{
  const p = await open('http://localhost:5173/editorial.html', 14000)
  await band(p, 'editorial-header', 0, 900)
  await p.close()
}

await browser.close()
console.log('done')
