// Types mirroring openbus_hack/contract.py. Keep them in sync.

export type ResultKind = 'metrics' | 'chart' | 'table' | 'image' | 'heatmap' | 'geo' | 'error'
export type ChartType = 'line' | 'bar' | 'stacked_bar' | 'area' | 'scatter' | 'trajectories'

export interface OptionSpec {
  key: string
  label: string
  type: 'number' | 'text' | 'select' | 'bool'
  default: unknown
  choices: unknown[]
  help: string | null
}

export interface AnalysisMeta {
  name: string
  title: string
  description: string
  author: string
  tags: string[]
  inputs: ('lines' | 'operators' | 'dates')[]
  draft: boolean
  module: string
  options: OptionSpec[]
}

export interface Metric {
  label: string
  value: number | string
  unit: string | null
  delta: number | null
  delta_is_good: boolean | null
  help: string | null
}

export interface Point {
  x: string | number
  y: number | null
  /** Optional error-bar range around y (e.g. a p25/p75 spread). */
  low: number | null
  high: number | null
}
export interface Series {
  name: string
  points: Point[]
  /** chart_type "trajectories" only: bold + legended vs. faint + unlegended. */
  emphasis: boolean
  /** Dashes an emphasized line, so two bold series stay distinguishable. */
  dashed: boolean
  /** Overrides the renderer's default color for an emphasized series. */
  color: string | null
}
export interface Table {
  columns: string[]
  rows: unknown[][]
}

export interface GeoLegendData {
  label: string
  /** Ordered low→high; painted as a continuous ramp. */
  colors: string[]
  min_label: string | null
  max_label: string | null
  /** Extra swatches the ramp doesn't cover, e.g. dashed "planned" vs solid. */
  items: { label?: string; color?: string; dashed?: boolean }[]
}

export interface HeatmapCell {
  row: number
  col: number
  value: number | null
  count: number | null
  /** Measured but under-sampled — drawn hatched, never hidden. */
  weak: boolean
}

export interface HeatmapData {
  row_labels: string[]
  col_labels: string[]
  /** Sparse: absent cells mean "no data", which is distinct from a measured zero. */
  cells: HeatmapCell[]
  row_axis_label: string | null
  col_axis_label: string | null
  /** Neutral point for a diverging scale (e.g. 1.0 for a ratio); null = sequential. */
  center: number | null
  value_label: string | null
  value_suffix: string | null
}

export interface AnalysisResult {
  kind: ResultKind
  title: string | null
  subtitle: string | null
  metrics: Metric[]
  chart_type: ChartType
  series: Series[]
  x_label: string | null
  y_label: string | null
  x_is_temporal: boolean
  /** bar/stacked_bar only: categories on the y axis, bars running left-to-right. */
  horizontal: boolean
  /** chart_type "trajectories" only: labels for integer y ticks 0..N-1. */
  y_tick_labels: string[] | null
  /** Parallel to y_tick_labels: true where that tick's own data is weak. */
  y_tick_weak: boolean[] | null
  table: Table | null
  image_png: string | null
  image_alt: string | null
  heatmap: HeatmapData | null
  geojson: unknown | null
  geo_legend: GeoLegendData | null
  notes: string[]
  error_message: string | null
  error_traceback: string | null
}

export interface RunBody {
  lines: string[]
  operators: string[]
  date_from: string
  date_to: string
  options: Record<string, unknown>
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`)
  return res.json() as Promise<T>
}

// The API runs each analysis in a worker thread (FastAPI's threadpool, 40 slots).
// A dashboard of ~10 cards that all fire on load — and re-fire on every filter
// change — can occupy every slot with minute-long analyses, at which point even
// /api/health queues behind them and the whole server looks hung. Cap how many
// analysis runs are in flight at once so the box stays responsive; total wall
// time barely changes, since the slow part is upstream API calls that the
// analyses already share through a server-side single-flight cache.
const MAX_CONCURRENT_RUNS = 3
let active = 0
const waiting: (() => void)[] = []

async function withRunSlot<T>(fn: () => Promise<T>): Promise<T> {
  if (active >= MAX_CONCURRENT_RUNS) {
    await new Promise<void>((resolve) => waiting.push(resolve))
  }
  active++
  try {
    return await fn()
  } finally {
    active--
    waiting.shift()?.()
  }
}

export const api = {
  analyses: () =>
    json<{ analyses: AnalysisMeta[]; import_problems: string[] }>('/api/analyses'),

  agencies: () =>
    json<{ agencies: { operator_ref: number; name: string }[]; error?: string }>(
      '/api/agencies',
    ),

  run: (name: string, body: RunBody) =>
    withRunSlot(() =>
      json<AnalysisResult>(`/api/analyses/${encodeURIComponent(name)}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    ),
}

// Categorical slots, in fixed assignment order — must match theme.css / theme.py.
export const SERIES_VARS = [
  'var(--s1)',
  'var(--s2)',
  'var(--s3)',
  'var(--s4)',
  'var(--s5)',
  'var(--s6)',
  'var(--s7)',
  'var(--s8)',
]

/** Color for series index i. Clamps at 8 — fold the tail into "Other" upstream. */
export const seriesColor = (i: number) => SERIES_VARS[Math.min(i, SERIES_VARS.length - 1)]

export const fmtNum = (v: number | string | null | undefined): string => {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'string') return v
  if (!Number.isFinite(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (abs >= 10_000) return (v / 1000).toFixed(0) + 'k'
  if (Number.isInteger(v)) return v.toLocaleString()
  return v.toFixed(abs < 10 ? 2 : 1)
}

export const isoDaysAgo = (n: number): string => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}
