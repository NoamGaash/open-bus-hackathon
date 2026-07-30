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

export function Heatmap({ result }: { result: AnalysisResult }) {
  const hm = result.heatmap!
  const [hover, setHover] = useState<Hover | null>(null)

  const byKey = useMemo(() => {
    const m = new Map<string, HeatmapCell>()
    for (const c of hm.cells) m.set(`${c.row}:${c.col}`, c)
    return m
  }, [hm.cells])

  // Scale extent: the largest deviation from centre in either direction, so the
  // two arms stay symmetric and a ratio of 2.0 reads as far from 1.0 as 0.5 does.
  const extent = useMemo(() => {
    const centre = hm.center ?? 0
    let max = 0
    for (const c of hm.cells) {
      if (c.value === null || c.value === undefined) continue
      max = Math.max(max, Math.abs(c.value - centre))
    }
    return max || 1
  }, [hm.cells, hm.center])

  if (!hm.row_labels.length || !hm.col_labels.length) {
    return <p className="muted">No data to plot.</p>
  }

  const armIndex = (v: number) =>
    Math.min(3, Math.floor((Math.abs(v - (hm.center ?? 0)) / extent) * 4))

  const colorFor = (v: number | null | undefined): string | undefined => {
    if (v === null || v === undefined) return undefined
    const d = v - (hm.center ?? 0)
    if (Math.abs(d) < 1e-9) return 'var(--div-mid)'
    return (d < 0 ? NEG : POS)[armIndex(v)]
  }

  // The outer steps of both arms are dark enough to need light text on them.
  const inkFor = (v: number | null | undefined): string =>
    v === null || v === undefined ? 'var(--muted)' : armIndex(v) >= 2 ? '#ffffff' : 'var(--ink)'

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
                  return (
                    <td
                      key={colLabel + j}
                      className={`hm-cell${cell?.weak ? ' hm-weak' : ''}`}
                      style={{ background: colorFor(v), color: inkFor(v) }}
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
          <i
            key={`${c}-${i}`}
            className="swatch"
            style={{ background: c, borderRadius: 2, width: 16, height: 12 }}
          />
        ))}
      </span>
      <span className="muted" style={{ fontSize: 11 }}>
        {fmtNum(centre + extent)}
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
