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

import { fmtNum, seriesColor, type AnalysisResult, type ChartType, type Series } from './api'

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
const ROW_LABEL_W = 200
const rowLabel = (v: string) => (v.length > 28 ? `${v.slice(0, 27)}…` : v)

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

function ChartLegend({ series, chartType }: { series: Series[]; chartType: ChartType }) {
  if (chartType === 'trajectories') {
    // A legend entry per ride would be noise, not information — only the
    // emphasized (planned) reference line gets one, plus a plain count.
    const emphasis = series.filter((s) => s.emphasis)
    const rides = series.length - emphasis.length
    if (!emphasis.length && !rides) return null
    return (
      <div className="legend">
        {emphasis.map((s) => (
          <span key={s.name} className="legend-item auto-dir">
            <i className="swatch" style={{ background: 'var(--ink)' }} />
            {s.name}
          </span>
        ))}
        {rides > 0 && (
          <span className="legend-item">
            <i className="swatch" style={{ background: 'var(--s1)', opacity: 0.4 }} />
            {rides} sampled ride{rides === 1 ? '' : 's'}
          </span>
        )}
      </div>
    )
  }
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

function TrajectoryTooltip({
  active,
  label,
  payload,
  yTickLabels,
}: {
  active?: boolean
  label?: string | number
  payload?: { name?: string; value?: number | null }[]
  yTickLabels: string[]
}) {
  if (!active || !payload?.length) return null
  const planned = payload.find((p) => p.name === 'Planned')
  const rides = payload.filter(
    (p) => p.name !== 'Planned' && p.value !== null && p.value !== undefined,
  ).length
  return (
    <div className="tooltip" style={{ position: 'static' }}>
      <div className="tt-x">{fmtNum(Number(label))} min elapsed</div>
      {planned?.value != null && (
        <div className="tt-row">
          <span>scheduled position</span>
          <b className="auto-dir">{yTickLabels[Math.round(planned.value)] ?? '—'}</b>
        </div>
      )}
      <div className="tt-row">
        <span>rides passing here</span>
        <b>{rides}</b>
      </div>
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

  const rows = chart_type === 'trajectories' ? [] : toRows(series)
  const stacked = chart_type === 'stacked_bar'
  const isBar = chart_type === 'bar' || chart_type === 'stacked_bar'
  const horizontal = isBar && result.horizontal
  // Long category labels (route/segment names) collide when rotated on the x
  // axis; running the bars left-to-right with categories on the y axis fixes
  // that, at the cost of needing more vertical room per row.
  const barsH = Math.max(H, rows.length * 30 + 50)
  // Gridlines run perpendicular to the categorical axis, whichever one that is.
  const grid = horizontal
    ? <CartesianGrid stroke="var(--grid)" horizontal={false} strokeWidth={0.8} />
    : <CartesianGrid stroke="var(--grid)" vertical={false} strokeWidth={0.8} />
  const xAxis = horizontal ? (
    <XAxis
      type="number"
      tickFormatter={(v: number) => fmtNum(v)}
      tick={{ fontSize: 9.5, fill: 'var(--muted)' }}
      axisLine={{ stroke: 'var(--grid)' }}
      tickLine={false}
    />
  ) : (
    <XAxis
      dataKey="x"
      tickFormatter={tickLabel}
      tick={{ fontSize: 9.5, fill: 'var(--muted)' }}
      axisLine={{ stroke: 'var(--grid)' }}
      tickLine={false}
      minTickGap={24}
    />
  )
  const yAxis = horizontal ? (
    <YAxis
      type="category"
      dataKey="x"
      tickFormatter={rowLabel}
      tick={{ fontSize: 10.5, fill: 'var(--ink-2)' }}
      width={ROW_LABEL_W}
      axisLine={false}
      tickLine={false}
      interval={0}
      className="auto-dir"
    />
  ) : (
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
  } else if (chart_type === 'trajectories') {
    // Many individual-ride lines (no shared x domain — each ride's elapsed
    // time is its own) plus one bold "Planned" reference. Each Line supplies
    // its own `data`, so there's no shared `rows` table here.
    const yLabels = result.y_tick_labels ?? []
    const faint = series.filter((s) => !s.emphasis)
    const emphasis = series.filter((s) => s.emphasis)
    const trajH = Math.max(H, yLabels.length * 22 + 60)
    plot = (
      <LineChart width={w} height={trajH}>
        <CartesianGrid stroke="var(--grid)" vertical={false} strokeWidth={0.8} />
        <XAxis
          type="number"
          dataKey="x"
          tick={{ fontSize: 9.5, fill: 'var(--muted)' }}
          axisLine={{ stroke: 'var(--grid)' }}
          tickLine={false}
          label={
            result.x_label
              ? { value: result.x_label, position: 'insideBottom', offset: -6,
                  fontSize: 10.5, fill: 'var(--muted)' }
              : undefined
          }
        />
        <YAxis
          type="number"
          dataKey="y"
          domain={[0, Math.max(1, yLabels.length - 1)]}
          ticks={yLabels.map((_, i) => i)}
          reversed
          tickFormatter={(v: number) => rowLabel(yLabels[Math.round(v)] ?? '')}
          tick={{ fontSize: 10, fill: 'var(--ink-2)' }}
          width={ROW_LABEL_W}
          axisLine={false}
          tickLine={false}
          interval={0}
          className="auto-dir"
        />
        <Tooltip
          content={<TrajectoryTooltip yTickLabels={yLabels} />}
          cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }}
          wrapperStyle={{ pointerEvents: 'none' }}
        />
        {faint.map((s) => (
          <Line
            key={s.name}
            type="linear"
            data={s.points.map((p) => ({ x: p.x, y: p.y }))}
            dataKey="y"
            name={s.name}
            stroke="var(--s1)"
            strokeOpacity={0.16}
            strokeWidth={1.3}
            dot={false}
            legendType="none"
            connectNulls
            isAnimationActive={false}
          />
        ))}
        {emphasis.map((s) => (
          <Line
            key={s.name}
            type="linear"
            data={s.points.map((p) => ({ x: p.x, y: p.y }))}
            dataKey="y"
            name={s.name}
            stroke="var(--ink)"
            strokeWidth={2.5}
            strokeDasharray="6 4"
            dot={false}
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
      <BarChart
        data={rows}
        width={w}
        height={horizontal ? barsH : H}
        layout={horizontal ? 'vertical' : 'horizontal'}
        barGap={2}
        barCategoryGap="28%"
      >
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
      <ChartLegend series={series} chartType={chart_type} />
      {plot}
      {result.y_label && (
        <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
          {result.y_label}
        </div>
      )}
    </div>
  )
}
