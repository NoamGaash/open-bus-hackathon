// Line/area/bar/stacked-bar/scatter charts, via Recharts.
//
// Design rules preserved from the hand-rolled version: 2px lines, 4px rounded
// bars, recessive horizontal-only gridlines, a legend whenever there are >= 2
// series, and a hover tooltip by default — now delegated to Recharts'
// Tooltip/Legend/CartesianGrid with custom render content so the visual
// language matches the rest of the dashboard.

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useState } from 'react'

import { fmtNum, seriesColor, type AnalysisResult, type Series } from './api'

const H = 340

interface Row {
  x: string
  [seriesName: string]: string | number | null
}

function toRows(series: Series[]): Row[] {
  const xs: (string | number)[] = []
  const seen = new Set<string>()
  const maps = series.map((s) => new Map(s.points.map((p) => [String(p.x), p.y])))
  for (const s of series)
    for (const p of s.points) {
      const k = String(p.x)
      if (!seen.has(k)) {
        seen.add(k)
        xs.push(p.x)
      }
    }
  return xs.map((x) => {
    const row: Row = { x: String(x) }
    series.forEach((s, i) => {
      row[s.name] = maps[i].get(String(x)) ?? null
    })
    return row
  })
}

// Dates render as e.g. "2026-07-18" — the same trim the old chart used.
const tickLabel = (v: string) => (v.length > 11 ? v.slice(5) : v)

function ChartTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean
  label?: string
  payload?: { name?: string; value?: number | null; color?: string }[]
}) {
  if (!active || !payload?.length) return null
  const rows = payload.filter((p) => p.value !== null && p.value !== undefined)
  if (!rows.length) return null
  return (
    <div className="tooltip" style={{ position: 'static' }}>
      <div className="tt-x">{label}</div>
      {rows.map((r) => (
        <div className="tt-row" key={r.name}>
          <i className="swatch" style={{ background: r.color }} />
          <span className="auto-dir">{r.name}</span>
          <b>{fmtNum(r.value ?? null)}</b>
        </div>
      ))}
    </div>
  )
}

function ChartLegend({ series }: { series: Series[] }) {
  if (series.length < 2) return null
  return (
    <div className="legend">
      {series.map((s, i) => (
        <span key={s.name} className="legend-item auto-dir">
          <i className="swatch" style={{ background: seriesColor(i) }} />
          {s.name}
        </span>
      ))}
    </div>
  )
}

export function Chart({ result }: { result: AnalysisResult }) {
  // Recharts' own ResponsiveContainer needs a real layout engine (a
  // ResizeObserver) to size itself, which makes it silently render nothing
  // under SSR/headless rendering. Measuring the wrapper ourselves — same
  // pattern Heatmap.tsx uses — keeps this deterministic and testable.
  const [w, setW] = useState(700)
  const measure = (el: HTMLDivElement | null) => {
    if (el && el.clientWidth && Math.abs(el.clientWidth - w) > 4) setW(el.clientWidth)
  }

  const { series, chart_type } = result
  if (!series.length || !series.some((s) => s.points.length)) {
    return <p className="muted">No data to plot.</p>
  }

  const rows = toRows(series)
  const stacked = chart_type === 'stacked_bar'
  const grid = <CartesianGrid stroke="var(--grid)" vertical={false} strokeWidth={0.8} />
  const xAxis = (
    <XAxis
      dataKey="x"
      tickFormatter={tickLabel}
      tick={{ fontSize: 9.5, fill: 'var(--muted)' }}
      axisLine={{ stroke: 'var(--grid)' }}
      tickLine={false}
      minTickGap={24}
    />
  )
  const yAxis = (
    <YAxis
      tickFormatter={(v: number) => fmtNum(v)}
      tick={{ fontSize: 9.5, fill: 'var(--muted)' }}
      width={44}
      axisLine={false}
      tickLine={false}
    />
  )
  const tooltip = (
    <Tooltip
      content={<ChartTooltip />}
      cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }}
      wrapperStyle={{ pointerEvents: 'none' }}
    />
  )

  let plot: React.ReactElement
  if (chart_type === 'line' || chart_type === 'area') {
    const single = rows.length === 1
    plot =
      chart_type === 'area' ? (
        <AreaChart data={rows} width={w} height={H}>
          {grid}
          {xAxis}
          {yAxis}
          {tooltip}
          {series.map((s, i) => (
            <Area
              key={s.name}
              type="monotone"
              dataKey={s.name}
              name={s.name}
              stroke={seriesColor(i)}
              fill={seriesColor(i)}
              fillOpacity={0.12}
              strokeWidth={2}
              dot={single}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      ) : (
        <LineChart data={rows} width={w} height={H}>
          {grid}
          {xAxis}
          {yAxis}
          {tooltip}
          {series.map((s, i) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              name={s.name}
              stroke={seriesColor(i)}
              strokeWidth={2}
              dot={single ? { r: 4, fill: seriesColor(i), stroke: 'var(--surface)' } : false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      )
  } else if (chart_type === 'scatter') {
    plot = (
      <ScatterChart width={w} height={H}>
        {grid}
        {xAxis}
        {yAxis}
        {tooltip}
        {series.map((s, i) => (
          <Scatter
            key={s.name}
            name={s.name}
            data={rows.map((r) => ({ x: r.x, [s.name]: r[s.name] }))}
            dataKey={s.name}
            fill={seriesColor(i)}
            isAnimationActive={false}
          />
        ))}
      </ScatterChart>
    )
  } else {
    // bar / stacked_bar
    plot = (
      <BarChart data={rows} width={w} height={H} barGap={2} barCategoryGap="28%">
        {grid}
        {xAxis}
        {yAxis}
        {tooltip}
        {series.map((s, i) => (
          <Bar
            key={s.name}
            dataKey={s.name}
            name={s.name}
            fill={seriesColor(i)}
            stackId={stacked ? 'stack' : undefined}
            radius={4}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    )
  }

  return (
    <div ref={measure} style={{ minWidth: 0 }}>
      <ChartLegend series={series} />
      {plot}
      {result.y_label && (
        <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
          {result.y_label}
        </div>
      )}
    </div>
  )
}
