// Client-rendered heatmap for AnalysisResult.kind === 'heatmap', via Recharts
// (a categorical ScatterChart with a custom square "shape" — Recharts has no
// native heatmap primitive, so the grid/axes/tooltip are Recharts', the cell
// rendering is custom).
//
// Three cell states are drawn differently on purpose: solid (enough samples),
// hatched (measured but under-sampled), and absent (no data at all). Collapsing
// "one observation" and "no data" into one appearance hides exactly the thing
// worth knowing.

import { useMemo, useState } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip } from 'recharts'

import { fmtNum, type AnalysisResult, type HeatmapCell } from './api'

const PAD = { top: 8, right: 12, bottom: 44 }
const CELL_MIN = 26
// Capped well below the available width on a wide screen: a route can run to a
// couple of dozen segments, and taller rows would make the grid taller than
// the viewport before it was any more readable.
const CELL_MAX = 46
const ROW_LABEL_W = 210

// Diverging arms, nearest-neutral first. Index picked by magnitude, so the
// midpoint always reads as "nothing" — never a hue at the centre.
const NEG = ['var(--div-neg-0)', 'var(--div-neg-1)', 'var(--div-neg-2)', 'var(--div-neg-3)']
const POS = ['var(--div-pos-0)', 'var(--div-pos-1)', 'var(--div-pos-2)', 'var(--div-pos-3)']

interface Point {
  row: string
  col: string
  rowIndex: number
  colIndex: number
  cell: HeatmapCell | null
}

export function Heatmap({ result }: { result: AnalysisResult }) {
  const hm = result.heatmap!
  const [w, setW] = useState(900)
  const measure = (el: HTMLDivElement | null) => {
    if (el && el.clientWidth && Math.abs(el.clientWidth - w) > 4) setW(el.clientWidth)
  }

  const nRows = hm.row_labels.length
  const nCols = hm.col_labels.length

  const byKey = useMemo(() => {
    const m = new Map<string, HeatmapCell>()
    for (const c of hm.cells) m.set(`${c.row}:${c.col}`, c)
    return m
  }, [hm.cells])

  // Full row x col grid, including absent cells — Recharts only knows about
  // points we hand it, so a missing cell has to be an explicit null-value
  // point rather than an omission, or it silently disappears instead of
  // rendering as "no data".
  const points: Point[] = useMemo(() => {
    const out: Point[] = []
    for (let i = 0; i < nRows; i++) {
      for (let j = 0; j < nCols; j++) {
        out.push({
          row: hm.row_labels[i],
          col: hm.col_labels[j],
          rowIndex: i,
          colIndex: j,
          cell: byKey.get(`${i}:${j}`) ?? null,
        })
      }
    }
    return out
  }, [hm.row_labels, hm.col_labels, byKey, nRows, nCols])

  const extent = useMemo(() => {
    const centre = hm.center ?? 0
    let max = 0
    for (const c of hm.cells) {
      if (c.value === null || c.value === undefined) continue
      max = Math.max(max, Math.abs(c.value - centre))
    }
    return max || 1
  }, [hm.cells, hm.center])

  if (!nRows || !nCols) return <p className="muted">No data to plot.</p>

  const gridW = Math.max(120, w - ROW_LABEL_W - PAD.right)
  const cell = Math.max(CELL_MIN, Math.min(CELL_MAX, gridW / nCols))
  const innerW = cell * nCols
  const H = PAD.top + cell * nRows + PAD.bottom
  const showCounts = cell >= 30

  const colorFor = (v: number | null | undefined): string => {
    if (v === null || v === undefined) return 'transparent'
    const centre = hm.center ?? 0
    const d = v - centre
    const arm = d < 0 ? NEG : POS
    const idx = Math.min(arm.length - 1, Math.floor((Math.abs(d) / extent) * arm.length))
    return Math.abs(d) < 1e-9 ? 'var(--div-mid)' : arm[idx]
  }
  const inkFor = (v: number | null | undefined): string => {
    if (v === null || v === undefined) return 'var(--muted)'
    const d = v - (hm.center ?? 0)
    const idx = Math.min(3, Math.floor((Math.abs(d) / extent) * 4))
    return idx >= 2 ? '#ffffff' : 'var(--ink)'
  }

  // Custom point renderer: Recharts gives us the pixel centre (cx, cy) for the
  // categorical (row, col) position; we draw the square ourselves.
  const renderCell = (props: { cx?: number; cy?: number; payload?: Point }) => {
    const { cx, cy, payload } = props
    if (cx === undefined || cy === undefined || !payload) return <g />
    const size = cell - 2 // 2px surface gap between adjacent fills
    const x = cx - size / 2
    const y = cy - size / 2
    const v = payload.cell?.value ?? null
    if (v === null) {
      return <rect x={x} y={y} width={size} height={size} rx={3} fill="none"
        stroke="var(--grid)" strokeWidth={1} />
    }
    return (
      <g>
        <rect x={x} y={y} width={size} height={size} rx={3} fill={colorFor(v)} />
        {payload.cell?.weak && (
          <rect x={x} y={y} width={size} height={size} rx={3} fill="url(#hm-weak)" />
        )}
        {showCounts && payload.cell?.count != null && (
          <text x={cx} y={cy + 3.5} textAnchor="middle" fontSize={10}
            fill={payload.cell.weak ? 'var(--ink)' : inkFor(v)}
            style={{ fontVariantNumeric: 'tabular-nums', pointerEvents: 'none' }}>
            {payload.cell.count}
          </text>
        )}
      </g>
    )
  }

  return (
    <div ref={measure} style={{ minWidth: 0, overflowX: 'auto' }}>
      <svg width={0} height={0}>
        <defs>
          {/* Texture is the accessibility channel for "measured but shaky" — it
              survives greyscale, print, and forced-colors where a tint does not. */}
          <pattern id="hm-weak" patternUnits="userSpaceOnUse" width="6" height="6"
            patternTransform="rotate(45)">
            <rect width="6" height="6" fill="var(--surface)" opacity="0.55" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink)" strokeWidth="1.4" opacity="0.5" />
          </pattern>
        </defs>
      </svg>

      <ScatterChart
        width={ROW_LABEL_W + innerW + PAD.right}
        height={H}
        margin={{ top: PAD.top, right: PAD.right, bottom: PAD.bottom, left: ROW_LABEL_W }}
      >
        <XAxis
          type="category" dataKey="col" name={hm.col_axis_label ?? 'column'}
          allowDuplicatedCategory={false} interval={0}
          tick={{ fontSize: 11, fill: 'var(--ink-2)' }}
          axisLine={{ stroke: 'var(--grid)' }} tickLine={false}
          label={hm.col_axis_label
            ? { value: hm.col_axis_label, position: 'insideBottom', offset: -8,
                fontSize: 11, fill: 'var(--muted)' }
            : undefined}
        />
        <YAxis
          type="category" dataKey="row" name={hm.row_axis_label ?? 'row'}
          allowDuplicatedCategory={false} interval={0} reversed
          tick={(p) => <RowTick {...p} />}
          axisLine={false} tickLine={false} width={ROW_LABEL_W - 10}
        />
        <Tooltip content={(props) => <HeatmapTooltip {...props} hm={hm} />} cursor={false}
          wrapperStyle={{ pointerEvents: 'none' }} />
        <Scatter data={points} shape={renderCell} isAnimationActive={false} />
      </ScatterChart>

      <Legend hm={hm} extent={extent} />
    </div>
  )
}

function RowTick(props: { x?: number | string; y?: number | string; payload?: { value: string } }) {
  const label = props.payload?.value ?? ''
  return (
    <text x={Number(props.x)} y={Number(props.y)} dy={3.5} textAnchor="end" fontSize={11}
      fill="var(--ink-2)" className="auto-dir">
      {label.length > 30 ? `${label.slice(0, 29)}…` : label}
    </text>
  )
}

interface RechartsTooltipProps {
  active?: boolean
  payload?: readonly { payload?: Point }[]
}

function HeatmapTooltip({
  active,
  payload,
  hm,
}: RechartsTooltipProps & { hm: AnalysisResult['heatmap'] }) {
  if (!active || !payload?.length || !hm) return null
  const p = payload[0]?.payload
  if (!p || !p.cell || p.cell.value === null) return null
  return (
    <div className="tooltip" style={{ position: 'static' }}>
      <div className="tt-x auto-dir">{p.row}</div>
      <div className="tt-row">
        <span className="auto-dir">{hm.col_axis_label ?? 'column'}</span>
        <b>{p.col}</b>
      </div>
      <div className="tt-row">
        <span>{hm.value_label ?? 'value'}</span>
        <b>
          {fmtNum(p.cell.value)}
          {hm.value_suffix ?? ''}
        </b>
      </div>
      {p.cell.count !== null && p.cell.count !== undefined && (
        <div className="tt-row">
          <span>samples</span>
          <b>{p.cell.count}</b>
        </div>
      )}
      {p.cell.weak && (
        <div className="tt-row" style={{ color: 'var(--muted)' }}>
          too few samples — treat as indicative
        </div>
      )}
    </div>
  )
}

function Legend({ hm, extent }: { hm: AnalysisResult['heatmap']; extent: number }) {
  if (!hm) return null
  const centre = hm.center ?? 0
  const swatches = [...NEG].reverse().concat(['var(--div-mid)'], POS)
  return (
    <div className="legend" style={{ marginTop: 10, alignItems: 'center' }}>
      <span className="muted" style={{ fontSize: 11 }}>
        {fmtNum(centre - extent)}
        {hm.value_suffix ?? ''}
      </span>
      <span style={{ display: 'inline-flex', gap: 2 }}>
        {swatches.map((c, i) => (
          <i key={`${c}-${i}`} className="swatch"
            style={{ background: c, borderRadius: 2, width: 16, height: 12 }} />
        ))}
      </span>
      <span className="muted" style={{ fontSize: 11 }}>
        {fmtNum(centre + extent)}
        {hm.value_suffix ?? ''}
      </span>
      <span className="legend-item" style={{ marginInlineStart: 14 }}>
        <i className="swatch" style={{
          borderRadius: 2, width: 16, height: 12,
          border: '1px solid var(--grid)', background: 'transparent',
        }} />
        no data
      </span>
      <span className="legend-item">
        <i className="swatch" style={{
          borderRadius: 2, width: 16, height: 12,
          background: 'repeating-linear-gradient(45deg, var(--muted) 0 1.4px, transparent 1.4px 6px)',
        }} />
        too few samples
      </span>
    </div>
  )
}
