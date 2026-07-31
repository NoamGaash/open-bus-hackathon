// Client-rendered heatmap for AnalysisResult.kind === 'heatmap'.
//
// A real HTML <table>, not an SVG scatter plot: the grid is genuinely tabular
// (segment x hour), so table layout gives correct non-overlapping cell
// placement for free, scrolls horizontally without extra work, keeps long
// Hebrew row labels legible in a sticky first column, and stays readable to
// screen readers. An earlier Recharts ScatterChart version computed
// overlapping cell positions once a route ran to a couple of dozen segments.
//
// Three cell states are drawn differently on purpose: solid (enough samples),
// hatched (measured but under-sampled), and empty (no data at all). Collapsing
// "one observation" and "no data" into one appearance hides exactly the thing
// worth knowing.

import { useMemo, useState } from 'react'

import { fmtNum, type AnalysisResult, type HeatmapCell } from './api'

// Diverging arms, nearest-neutral first. Index picked by magnitude, so the
// midpoint always reads as "nothing" — never a hue at the centre.
const NEG = ['var(--div-neg-0)', 'var(--div-neg-1)', 'var(--div-neg-2)', 'var(--div-neg-3)']
const POS = ['var(--div-pos-0)', 'var(--div-pos-1)', 'var(--div-pos-2)', 'var(--div-pos-3)']

interface Hover {
  cx: number
  cy: number
  rowLabel: string
  colLabel: string
  cell: HeatmapCell
}

const LIGHT_COLORS = {
  mid: '#f0efec',
  neg: ['#cde2fb', '#86b6ef', '#3987e5', '#1c5cab'],
  pos: ['#fbd6d6', '#e98c8b', '#dc5655', '#a82c2c'],
}

const DARK_COLORS = {
  mid: '#383835',
  neg: ['#1c5cab', '#3987e5', '#86b6ef', '#cde2fb'],
  pos: ['#a82c2c', '#dc5655', '#e98c8b', '#fbd6d6'],
}

function getThemeColors(): typeof LIGHT_COLORS {
  if (typeof document === 'undefined') return LIGHT_COLORS
  const theme = document.documentElement.getAttribute('data-theme')
  if (theme === 'dark') return DARK_COLORS
  if (!theme && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return DARK_COLORS
  }
  return LIGHT_COLORS
}

function parseHex(hex: string): [number, number, number] {
  const clean = hex.replace('#', '')
  const r = parseInt(clean.substring(0, 2), 16)
  const g = parseInt(clean.substring(2, 4), 16)
  const b = parseInt(clean.substring(4, 6), 16)
  return [r, g, b]
}

function interpolate(color1: string, color2: string, f: number): string {
  const [r1, g1, b1] = parseHex(color1)
  const [r2, g2, b2] = parseHex(color2)
  const r = Math.round(r1 + (r2 - r1) * f)
  const g = Math.round(g1 + (g2 - g1) * f)
  const b = Math.round(b1 + (b2 - b1) * f)
  return `rgb(${r}, ${g}, ${b})`
}

function getContinuousColor(value: number, extent: number): { bg: string; isDark: boolean } {
  if (value <= 0) {
    const colors = getThemeColors()
    return { bg: colors.mid, isDark: false }
  }

  const dev = value >= 1.0 ? (value - 1.0) : (1.0 / value - 1.0)
  if (dev < 1e-9) {
    const colors = getThemeColors()
    return { bg: colors.mid, isDark: false }
  }

  const colors = getThemeColors()
  const stops = value < 1.0 ? [colors.mid, ...colors.neg] : [colors.mid, ...colors.pos]

  // Use power scaling (square root) to stretch smaller deviations, making colors stand out more clearly
  const factor = Math.pow(Math.min(1.0, dev / extent), 0.5)
  const index = factor * 4
  const i = Math.min(3, Math.floor(index))
  const f = index - i

  const bg = interpolate(stops[i], stops[i + 1], f)
  const isDarkTheme = colors === DARK_COLORS
  const isDarkCell = isDarkTheme ? index < 2 : index >= 2

  return { bg, isDark: isDarkCell }
}

export function Heatmap({ result }: { result: AnalysisResult }) {
  const hm = result.heatmap!
  const [hover, setHover] = useState<Hover | null>(null)

  const byKey = useMemo(() => {
    const m = new Map<string, HeatmapCell>()
    for (const c of hm.cells) m.set(`${c.row}:${c.col}`, c)
    return m
  }, [hm.cells])

  // Scale extent: the largest deviation from 1.0, with symmetric 1/x mapping for values < 1.0
  const extent = useMemo(() => {
    let maxDev = 0
    for (const c of hm.cells) {
      const x = c.value
      if (x === null || x === undefined || x <= 0) continue
      const dev = x >= 1.0 ? (x - 1.0) : (1.0 / x - 1.0)
      maxDev = Math.max(maxDev, dev)
    }
    return maxDev || 1.0
  }, [hm.cells])

  if (!hm.row_labels.length || !hm.col_labels.length) {
    return <p className="muted">No data to plot.</p>
  }

  return (
    <div style={{ minWidth: 0 }}>
      <div className="hm-scroll">
        <table className="hm-table">
          <thead>
            <tr>
              <th className="hm-corner">{hm.row_axis_label ?? ''}</th>
              {hm.col_labels.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hm.row_labels.map((rowLabel, i) => (
              <tr key={rowLabel + i}>
                <th scope="row" className="hm-rowlabel auto-dir" title={rowLabel}>
                  {rowLabel}
                </th>
                {hm.col_labels.map((colLabel, j) => {
                  const cell = byKey.get(`${i}:${j}`)
                  const v = cell?.value ?? null
                  if (v === null) {
                    return <td key={colLabel + j} className="hm-cell hm-empty" aria-label="no data" />
                  }
                  const { bg, isDark } = getContinuousColor(v, extent)
                  return (
                    <td
                      key={colLabel + j}
                      className={`hm-cell${cell?.weak ? ' hm-weak' : ''}`}
                      style={{ background: bg, color: isDark ? '#ffffff' : 'var(--ink)' }}
                      onMouseEnter={(e) =>
                        setHover({ cx: e.clientX, cy: e.clientY, rowLabel, colLabel, cell: cell! })
                      }
                      onMouseMove={(e) =>
                        setHover({ cx: e.clientX, cy: e.clientY, rowLabel, colLabel, cell: cell! })
                      }
                      onMouseLeave={() => setHover(null)}
                    >
                      {cell?.count ?? ''}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hm.col_axis_label && (
        <div className="muted" style={{ fontSize: 11, marginTop: 6, textAlign: 'center' }}>
          {hm.col_axis_label}
        </div>
      )}

      <Legend hm={hm} extent={extent} />

      {hover && (
        <div
          className="tooltip"
          style={{
            left: Math.min(hover.cx + 12, window.innerWidth - 220),
            top: hover.cy - 12,
          }}
        >
          <div className="tt-x auto-dir">{hover.rowLabel}</div>
          <div className="tt-row">
            <span>{hm.col_axis_label ?? 'column'}</span>
            <b>{hover.colLabel}</b>
          </div>
          <div className="tt-row">
            <span>{hm.value_label ?? 'value'}</span>
            <b>
              {fmtNum(hover.cell.value)}
              {hm.value_suffix ?? ''}
            </b>
          </div>
          {hover.cell.actual !== null && hover.cell.actual !== undefined && (
            <div className="tt-row">
              <span>observed actual</span>
              <b>{fmtNum(hover.cell.actual)} min</b>
            </div>
          )}
          {hover.cell.planned !== null && hover.cell.planned !== undefined && (
            <div className="tt-row">
              <span>scheduled plan</span>
              <b>{fmtNum(hover.cell.planned)} min</b>
            </div>
          )}
          {hover.cell.count !== null && hover.cell.count !== undefined && (
            <div className="tt-row">
              <span>samples</span>
              <b>{hover.cell.count}</b>
            </div>
          )}
          {hover.cell.weak && (
            <div className="tt-row" style={{ color: 'var(--muted)' }}>
              too few samples — treat as indicative
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Legend({ hm, extent }: { hm: AnalysisResult['heatmap']; extent: number }) {
  if (!hm) return null
  const swatches = [...NEG].reverse().concat(['var(--div-mid)'], POS)
  return (
    <div className="legend" style={{ marginTop: 10, alignItems: 'center' }}>
      <span className="muted" style={{ fontSize: 11 }}>
        {fmtNum(1 / (1 + extent))}
        {hm.value_suffix ?? ''}
      </span>
      <span style={{ display: 'inline-flex', gap: 2 }}>
        {swatches.map((c, i) => (
          <i
            key={`${c}-${i}`}
            className="swatch"
            style={{ background: c, borderRadius: 2, width: 16, height: 12 }}
          />
        ))}
      </span>
      <span className="muted" style={{ fontSize: 11 }}>
        {fmtNum(1 + extent)}
        {hm.value_suffix ?? ''}
      </span>
      <span className="legend-item" style={{ marginInlineStart: 14 }}>
        <i
          className="swatch"
          style={{
            borderRadius: 2,
            width: 16,
            height: 12,
            border: '1px solid var(--grid)',
            background: 'transparent',
          }}
        />
        no data
      </span>
      <span className="legend-item">
        <i
          className="swatch hm-weak-swatch"
          style={{ borderRadius: 2, width: 16, height: 12 }}
        />
        too few samples
      </span>
    </div>
  )
}
