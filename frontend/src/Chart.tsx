// Minimal SVG charts: line, bar, stacked bar. No chart library on purpose —
// three forms is all the dashboard needs, and it keeps npm install tiny.
//
// Design rules applied here: 2px lines, 4px rounded bar tops, a 2px surface gap
// between adjacent/stacked fills, recessive horizontal-only gridlines, a legend
// whenever there are >= 2 series, and a hover tooltip by default.

import { useMemo, useRef, useState } from 'react'

import { fmtNum, seriesColor, type AnalysisResult } from './api'

const PAD = { top: 8, right: 12, bottom: 26, left: 44 }
const H = 210

interface Hover {
  cx: number
  cy: number
  x: string
  rows: { name: string; value: number | null; color: string }[]
}

export function Chart({ result }: { result: AnalysisResult }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(520)
  const [hover, setHover] = useState<Hover | null>(null)

  // Track width without a ResizeObserver dependency.
  const measure = (el: HTMLDivElement | null) => {
    if (el && el.clientWidth && Math.abs(el.clientWidth - w) > 4) setW(el.clientWidth)
  }

  const { series, chart_type } = result
  const stacked = chart_type === 'stacked_bar'

  const xs = useMemo(() => {
    const seen: (string | number)[] = []
    const set = new Set<string>()
    for (const s of series)
      for (const p of s.points) {
        const k = String(p.x)
        if (!set.has(k)) {
          set.add(k)
          seen.push(p.x)
        }
      }
    return seen
  }, [series])

  const lookup = useMemo(
    () => series.map((s) => new Map(s.points.map((p) => [String(p.x), p.y]))),
    [series],
  )

  const yMax = useMemo(() => {
    let m = 0
    if (stacked) {
      for (const x of xs) {
        let sum = 0
        for (const map of lookup) sum += map.get(String(x)) ?? 0
        m = Math.max(m, sum)
      }
    } else {
      for (const s of series) for (const p of s.points) m = Math.max(m, p.y ?? 0)
    }
    return m === 0 ? 1 : m * 1.08
  }, [series, lookup, xs, stacked])

  if (!series.length || !xs.length) return <p className="muted">No data to plot.</p>

  const innerW = Math.max(80, w - PAD.left - PAD.right)
  const innerH = H - PAD.top - PAD.bottom
  const xAt = (i: number) =>
    PAD.left + (xs.length === 1 ? innerW / 2 : (i / (xs.length - 1)) * innerW)
  const yAt = (v: number) => PAD.top + innerH - (v / yMax) * innerH

  // Y gridlines at 4 rounded steps.
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * yMax)

  // X labels: thin them out so they never collide.
  const step = Math.max(1, Math.ceil(xs.length / Math.max(2, Math.floor(innerW / 68))))

  const bandW = innerW / xs.length
  const barSlot = bandW * 0.72
  const barW = stacked ? barSlot : Math.max(2, barSlot / series.length - 2) // 2px gap

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect()
    const rel = e.clientX - box.left
    const i =
      chart_type === 'line' || chart_type === 'area'
        ? Math.round(((rel - PAD.left) / innerW) * (xs.length - 1))
        : Math.floor((rel - PAD.left) / bandW)
    const idx = Math.min(xs.length - 1, Math.max(0, i))
    const key = String(xs[idx])
    setHover({
      cx: e.clientX,
      cy: e.clientY,
      x: key,
      rows: series.map((s, si) => ({
        name: s.name,
        value: lookup[si].get(key) ?? null,
        color: seriesColor(si),
      })),
    })
  }

  return (
    <div
      ref={(el) => {
        wrapRef.current = el
        measure(el)
      }}
      style={{ minWidth: 0 }}
    >
      {series.length >= 2 && (
        <div className="legend">
          {series.map((s, i) => (
            <span key={s.name} className="legend-item auto-dir">
              <i className="swatch" style={{ background: seriesColor(i) }} />
              {s.name}
            </span>
          ))}
        </div>
      )}

      <svg width="100%" height={H} viewBox={`0 0 ${w} ${H}`} role="img"
        aria-label={result.title ?? 'chart'}>
        {/* gridlines + y axis labels */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD.left} x2={w - PAD.right} y1={yAt(t)} y2={yAt(t)}
              stroke="var(--grid)" strokeWidth={i === 0 ? 1 : 0.8}
            />
            <text
              x={PAD.left - 7} y={yAt(t) + 3.5} textAnchor="end"
              fontSize={9.5} fill="var(--muted)" style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              {fmtNum(t)}
            </text>
          </g>
        ))}

        {/* x labels */}
        {xs.map((x, i) =>
          i % step === 0 ? (
            <text
              key={i}
              x={chart_type === 'line' || chart_type === 'area'
                ? xAt(i)
                : PAD.left + i * bandW + bandW / 2}
              y={H - 8} textAnchor="middle" fontSize={9.5} fill="var(--muted)"
            >
              {String(x).length > 11 ? String(x).slice(5) : String(x)}
            </text>
          ) : null,
        )}

        {/* marks */}
        {chart_type === 'line' || chart_type === 'area'
          ? series.map((s, si) => {
              const pts = xs
                .map((x, i) => ({ i, y: lookup[si].get(String(x)) }))
                .filter((p) => p.y !== undefined && p.y !== null) as { i: number; y: number }[]
              if (!pts.length) return null
              const d = pts.map((p, k) => `${k ? 'L' : 'M'}${xAt(p.i)} ${yAt(p.y)}`).join(' ')
              return (
                <g key={s.name}>
                  {chart_type === 'area' && (
                    <path
                      d={`${d} L${xAt(pts[pts.length - 1].i)} ${yAt(0)} L${xAt(pts[0].i)} ${yAt(0)} Z`}
                      fill={seriesColor(si)} opacity={0.12}
                    />
                  )}
                  <path
                    d={d} fill="none" stroke={seriesColor(si)} strokeWidth={2}
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                  {pts.length === 1 && (
                    <circle cx={xAt(pts[0].i)} cy={yAt(pts[0].y)} r={4}
                      fill={seriesColor(si)} stroke="var(--surface)" strokeWidth={2} />
                  )}
                </g>
              )
            })
          : xs.map((x, i) => {
              let acc = 0
              return (
                <g key={i}>
                  {series.map((s, si) => {
                    const v = lookup[si].get(String(x))
                    if (v === undefined || v === null) return null
                    const bx = stacked
                      ? PAD.left + i * bandW + (bandW - barSlot) / 2
                      : PAD.left + i * bandW + (bandW - barSlot) / 2 + si * (barW + 2)
                    const y0 = stacked ? yAt(acc + v) : yAt(v)
                    const y1 = stacked ? yAt(acc) : yAt(0)
                    acc += stacked ? v : 0
                    const h = Math.max(1, y1 - y0 - (stacked ? 2 : 0)) // 2px surface gap
                    return (
                      <rect
                        key={s.name} x={bx} y={y0} width={stacked ? barSlot : barW}
                        height={h} rx={4} fill={seriesColor(si)}
                      />
                    )
                  })}
                </g>
              )
            })}

        {/* hover crosshair */}
        {hover && (chart_type === 'line' || chart_type === 'area') && (
          <line
            x1={xAt(xs.findIndex((x) => String(x) === hover.x))}
            x2={xAt(xs.findIndex((x) => String(x) === hover.x))}
            y1={PAD.top} y2={PAD.top + innerH} stroke="var(--axis)" strokeWidth={1}
          />
        )}

        {/* invisible hit area — bigger than the marks */}
        <rect
          x={PAD.left} y={PAD.top} width={innerW} height={innerH} fill="transparent"
          onMouseMove={onMove} onMouseLeave={() => setHover(null)}
        />
      </svg>

      {hover && (
        <div
          className="tooltip"
          style={{
            left: Math.min(hover.cx + 12, window.innerWidth - 190),
            top: hover.cy - 12,
          }}
        >
          <div className="tt-x">{hover.x}</div>
          {hover.rows
            .filter((r) => r.value !== null)
            .map((r) => (
              <div className="tt-row" key={r.name}>
                <i className="swatch" style={{ background: r.color }} />
                <span className="auto-dir">{r.name}</span>
                <b>{fmtNum(r.value)}</b>
              </div>
            ))}
        </div>
      )}

      {result.y_label && (
        <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
          {result.y_label}
        </div>
      )}
    </div>
  )
}
