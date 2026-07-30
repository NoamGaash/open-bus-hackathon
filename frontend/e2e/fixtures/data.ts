// Hand-written fixtures shaped exactly like openbus_hack/contract.py's pydantic
// models (AnalysisResult, Heatmap, HeatmapCell, Series, Point, Table, Metric)
// and AnalysisSpec.to_json() in openbus_hack/registry.py.
//
// Kept in one place so dashboard.spec.ts can import a name and get a
// self-consistent {meta, result} pair without touching the real API.

import type { AnalysisMeta, AnalysisResult } from '../../src/api'

interface AnalysesListResponse {
  analyses: AnalysisMeta[]
  import_problems: string[]
}

interface AgenciesResponse {
  agencies: { operator_ref: number; name: string }[]
  error?: string
}

function meta(partial: Pick<AnalysisMeta, 'name' | 'title' | 'description'>): AnalysisMeta {
  return {
    name: partial.name,
    title: partial.title,
    description: partial.description,
    author: 'fixture-author',
    tags: [],
    inputs: ['lines', 'operators', 'dates'],
    draft: false,
    module: `analyses.${partial.name.replace(/-/g, '_')}`,
    options: [],
  }
}

// ── metrics card ─────────────────────────────────────────────────────────

export const METRICS_NAME = 'ontime-metrics'

export const metricsMeta: AnalysisMeta = meta({
  name: METRICS_NAME,
  title: 'On-time performance',
  description: 'Headline on-time stats for the selected window.',
})

export const metricsResult: AnalysisResult = {
  kind: 'metrics',
  title: 'On-time performance',
  subtitle: 'Last 7 days',
  metrics: [
    { label: 'On-time %', value: 87.5, unit: '%', delta: 2.3, delta_is_good: true, help: null },
    {
      label: 'Avg delay',
      value: 4.2,
      unit: 'min',
      delta: -0.5,
      delta_is_good: true,
      help: 'vs previous week',
    },
    { label: 'Total rides', value: 12345, unit: null, delta: null, delta_is_good: null, help: null },
  ],
  chart_type: 'line',
  series: [],
  x_label: null,
  y_label: null,
  x_is_temporal: false,
  horizontal: false,
  y_tick_labels: null,
  table: null,
  image_png: null,
  image_alt: null,
  heatmap: null,
  geojson: null,
  notes: ['Sample size: 3 days of SIRI data only.'],
  error_message: null,
  error_traceback: null,
}

// ── chart card (line, 2 series) ─────────────────────────────────────────

export const CHART_NAME = 'rides-per-day'

export const chartMeta: AnalysisMeta = meta({
  name: CHART_NAME,
  title: 'Rides per day',
  description: 'Daily ridership by line.',
})

export const chartResult: AnalysisResult = {
  kind: 'chart',
  title: 'Rides per day',
  subtitle: null,
  metrics: [],
  chart_type: 'line',
  series: [
    {
      name: 'Line 480',
      points: [
        { x: '2026-07-23', y: 10 },
        { x: '2026-07-24', y: 12 },
        { x: '2026-07-25', y: null },
        { x: '2026-07-26', y: 15 },
      ],
      emphasis: false,
    },
    {
      name: 'Line 1',
      points: [
        { x: '2026-07-23', y: 5 },
        { x: '2026-07-24', y: 7 },
        { x: '2026-07-25', y: 6 },
        { x: '2026-07-26', y: 9 },
      ],
      emphasis: false,
    },
  ],
  x_label: 'Date',
  y_label: 'Rides',
  x_is_temporal: true,
  horizontal: false,
  y_tick_labels: null,
  table: {
    columns: ['Date', 'Line 480', 'Line 1'],
    rows: [
      ['2026-07-23', 10, 5],
      ['2026-07-24', 12, 7],
      ['2026-07-25', null, 6],
      ['2026-07-26', 15, 9],
    ],
  },
  image_png: null,
  image_alt: null,
  heatmap: null,
  geojson: null,
  notes: [],
  error_message: null,
  error_traceback: null,
}

// ── heatmap card (4 rows x 3 cols, one weak cell, one absent cell) ───────

export const HEATMAP_NAME = 'delay-heatmap'

export const heatmapMeta: AnalysisMeta = meta({
  name: HEATMAP_NAME,
  title: 'Delay by segment & hour',
  description: 'Actual/planned travel-time ratio, stop x hour.',
})

export const heatmapResult: AnalysisResult = {
  kind: 'heatmap',
  title: 'Delay by segment & hour',
  subtitle: null,
  metrics: [],
  chart_type: 'line',
  series: [],
  x_label: null,
  y_label: null,
  x_is_temporal: false,
  horizontal: false,
  y_tick_labels: null,
  table: {
    columns: ['Stop', '07:00', '08:00', '09:00'],
    rows: [
      ['Stop A', 1.1, 1.3, 0.9],
      ['Stop B', 1.0, 1.2, null],
      ['Stop C', 0.8, 1.5, 1.1],
      ['Stop D', 0.95, null, 1.05],
    ],
  },
  image_png: null,
  image_alt: null,
  heatmap: {
    row_labels: ['Stop A', 'Stop B', 'Stop C', 'Stop D'],
    col_labels: ['07:00', '08:00', '09:00'],
    cells: [
      { row: 0, col: 0, value: 1.1, count: 20, weak: false },
      { row: 0, col: 1, value: 1.3, count: 15, weak: false },
      { row: 0, col: 2, value: 0.9, count: 2, weak: true },
      { row: 1, col: 0, value: 1.0, count: 25, weak: false },
      { row: 1, col: 1, value: 1.2, count: 18, weak: false },
      // (1, 2) intentionally absent — exercises the sparse "no data" cell.
      { row: 2, col: 0, value: 0.8, count: 30, weak: false },
      { row: 2, col: 1, value: 1.5, count: 22, weak: false },
      { row: 2, col: 2, value: 1.1, count: 12, weak: false },
      { row: 3, col: 0, value: 0.95, count: 5, weak: true },
      // (3, 1) intentionally absent too.
      { row: 3, col: 2, value: 1.05, count: 19, weak: false },
    ],
    row_axis_label: 'Stop',
    col_axis_label: 'Hour',
    center: 1.0,
    value_label: 'Actual/Planned ratio',
    value_suffix: null,
  },
  geojson: null,
  notes: [],
  error_message: null,
  error_traceback: null,
}

// ── horizontal bar chart card (2 series, long category labels) ────────────

export const HBAR_NAME = 'segment-times'

export const hbarMeta: AnalysisMeta = meta({
  name: HBAR_NAME,
  title: 'Segment times',
  description: 'Actual vs planned duration per segment.',
})

export const hbarResult: AnalysisResult = {
  kind: 'chart',
  title: 'Segment times',
  subtitle: null,
  metrics: [],
  chart_type: 'bar',
  series: [
    {
      name: 'Actual (median)',
      points: [
        { x: 'Central Station ← North Terminal', y: 3.2 },
        { x: 'North Terminal ← Market Square', y: 1.8 },
      ],
      emphasis: false,
    },
    {
      name: 'Planned',
      points: [
        { x: 'Central Station ← North Terminal', y: 2.5 },
        { x: 'North Terminal ← Market Square', y: 2.0 },
      ],
      emphasis: false,
    },
  ],
  x_label: 'segment',
  y_label: 'minutes',
  x_is_temporal: false,
  horizontal: true,
  y_tick_labels: null,
  table: {
    columns: ['segment', 'Actual (median)', 'Planned'],
    rows: [
      ['Central Station ← North Terminal', 3.2, 2.5],
      ['North Terminal ← Market Square', 1.8, 2.0],
    ],
  },
  image_png: null,
  image_alt: null,
  heatmap: null,
  geojson: null,
  notes: [],
  error_message: null,
  error_traceback: null,
}

// ── error card ────────────────────────────────────────────────────────────

export const ERROR_NAME = 'broken-analysis'

export const errorMeta: AnalysisMeta = meta({
  name: ERROR_NAME,
  title: 'Broken analysis',
  description: 'Deliberately fails, to exercise the error card.',
})

export const ERROR_MESSAGE =
  "KeyError: 'route_short_name' not found in GTFS feed for the selected date range."

export const errorResult: AnalysisResult = {
  kind: 'error',
  title: 'Analysis failed',
  subtitle: null,
  metrics: [],
  chart_type: 'line',
  series: [],
  x_label: null,
  y_label: null,
  x_is_temporal: false,
  horizontal: false,
  y_tick_labels: null,
  table: null,
  image_png: null,
  image_alt: null,
  heatmap: null,
  geojson: null,
  notes: [],
  error_message: ERROR_MESSAGE,
  error_traceback:
    'Traceback (most recent call last):\n' +
    '  File "analyses/broken_analysis.py", line 12, in run\n' +
    "    return line_chart(df, x='date', y=row['route_short_name'])\n" +
    "KeyError: 'route_short_name'",
}

// ── aggregate responses ────────────────────────────────────────────────────

export const analysesListResponse: AnalysesListResponse = {
  analyses: [metricsMeta, chartMeta, hbarMeta, heatmapMeta, errorMeta],
  import_problems: [],
}

export const agenciesResponse: AgenciesResponse = {
  agencies: [
    { operator_ref: 3, name: 'אגד' },
    { operator_ref: 5, name: 'דן' },
  ],
}

export const RESULTS_BY_NAME: Record<string, AnalysisResult> = {
  [METRICS_NAME]: metricsResult,
  [CHART_NAME]: chartResult,
  [HBAR_NAME]: hbarResult,
  [HEATMAP_NAME]: heatmapResult,
  [ERROR_NAME]: errorResult,
}
