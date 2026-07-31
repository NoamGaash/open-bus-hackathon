// The presentation dashboard: one card per registered analysis.
//
// Everyone's function shows up here automatically — the team never touches this
// file. Filters at the top apply to every card at once, which is what makes the
// demo flow ("here's line 480 across all of our analyses").

import { useCallback, useEffect, useRef, useState } from 'react'

import { Chart } from './Chart'
import { GeoMap } from './GeoMap'
import { Heatmap } from './Heatmap'
import { SourceMaterial } from './SourceMaterial'
import {
  api,
  fmtNum,
  isoDaysAgo,
  seriesColor,
  type AnalysisMeta,
  type AnalysisResult,
  type RunBody,
} from './api'

interface Filters {
  lines: string
  operators: string[]
  date_from: string
  date_to: string
}

export default function App() {
  const [metas, setMetas] = useState<AnalysisMeta[] | null>(null)
  const [problems, setProblems] = useState<string[]>([])
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [agencies, setAgencies] = useState<string[]>([])
  const [filters, setFilters] = useState<Filters>({
    lines: '',
    operators: [],
    date_from: isoDaysAgo(8),
    date_to: isoDaysAgo(1),
  })
  // Bumped to re-run every card at once.
  const [runToken, setRunToken] = useState(0)

  useEffect(() => {
    api
      .analyses()
      .then((d) => {
        setMetas(d.analyses)
        setProblems(d.import_problems ?? [])
      })
      .catch((e: Error) => setLoadErr(e.message))
    api
      .agencies()
      .then((d) => setAgencies(d.agencies.map((a) => a.name)))
      .catch(() => setAgencies([]))
  }, [])

  const shown = metas ?? []

  return (
    <div className="page">
      <header className="masthead">
        <h1>Open Bus — Hackathon</h1>
        <span className="sub">
          {metas ? `${shown.length} ${shown.length === 1 ? 'analysis' : 'analyses'}` : 'loading…'}
        </span>
        <span className="spacer" />
        <ThemeToggle />
      </header>

      <FilterBar
        filters={filters}
        agencies={agencies}
        onChange={setFilters}
        onRun={() => setRunToken((t) => t + 1)}
      />

      {loadErr && (
        <div className="err" style={{ marginBottom: 18 }}>
          <strong>Can't reach the analyses API.</strong> Is it running? Try <code>./dev</code>.
          <pre>{loadErr}</pre>
        </div>
      )}

      {problems.length > 0 && (
        <div className="err" style={{ marginBottom: 18 }}>
          <strong>{problems.length} analysis file(s) failed to import</strong> — they won't
          appear below.
          <pre>{problems.join('\n')}</pre>
        </div>
      )}

      {metas && shown.length === 0 && !loadErr && (
        <p className="muted">
          No analyses yet. Create one with <code>./dev new my-analysis</code>.
        </p>
      )}

      <div className="grid">
        {shown.map((m) => (
          <AnalysisCard key={m.name} meta={m} filters={filters} runToken={runToken} />
        ))}
      </div>

      <SourceMaterial />
    </div>
  )
}

function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null)
  useEffect(() => {
    if (dark === null) return
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  }, [dark])
  return (
    <button
      className="ghost"
      onClick={() =>
        setDark((d) =>
          d === null ? !window.matchMedia('(prefers-color-scheme: dark)').matches : !d,
        )
      }
      title="Toggle light/dark"
    >
      {dark ? '☀ light' : '☾ dark'}
    </button>
  )
}

function FilterBar({
  filters,
  agencies,
  onChange,
  onRun,
}: {
  filters: Filters
  agencies: string[]
  onChange: (f: Filters) => void
  onRun: () => void
}) {
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) =>
    onChange({ ...filters, [k]: v })

  return (
    <div className="filters">
      <div className="field">
        <label htmlFor="f-lines">Lines</label>
        <input
          id="f-lines"
          placeholder="480, 1, 18"
          value={filters.lines}
          onChange={(e) => set('lines', e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onRun()}
        />
      </div>

      <div className="field">
        <label htmlFor="f-op">Operator</label>
        <select
          id="f-op"
          className="auto-dir"
          value={filters.operators[0] ?? ''}
          onChange={(e) => set('operators', e.target.value ? [e.target.value] : [])}
        >
          <option value="">All operators</option>
          {agencies.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="f-from">From</label>
        <input
          id="f-from" type="date" value={filters.date_from}
          onChange={(e) => set('date_from', e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="f-to">To</label>
        <input
          id="f-to" type="date" value={filters.date_to}
          onChange={(e) => set('date_to', e.target.value)}
        />
      </div>

      <div className="field">
        <label>&nbsp;</label>
        <button className="primary" onClick={onRun}>
          Run all
        </button>
      </div>
    </div>
  )
}

interface Explanation {
  whatWeSee: string
  whoDidIt: string
  rationale: string
}

const EXPLANATIONS: Record<string, Explanation> = {
  'service-by-operator': {
    whatWeSee: 'A line chart tracking scheduled (planned) rides versus actual completed rides day-by-day across the country.',
    whoDidIt: 'example (worked baseline / boilerplate)',
    rationale: 'Establishes a high-level baseline of daily service execution, showing if the operator ran fewer trips than scheduled.',
  },
  'bus-hourly-heatmap': {
    whatWeSee: 'A segment-by-hour matrix. Red cells indicate that buses ran significantly slower than scheduled, blue is faster, and gray is on-time.',
    whoDidIt: 'noamf2001 (PublicTransportHackathon)',
    rationale: 'Identifies exact bottleneck locations at precise times of the day (such as morning/evening rush hours) rather than averaging performance across a whole day.',
  },
  'bus-marey-diagram': {
    whatWeSee: 'A stringline/time-space diagram showing individual bus trip trajectories as faint blue lines against the dashed scheduled plan.',
    whoDidIt: 'noamf2001 (PublicTransportHackathon)',
    rationale: 'The slope of each line represents speed (steep is moving, flat is stuck). The spread (width) of the blue lines shows the day-to-day unreliability of the schedule.',
  },
  'bus-segment-reliability': {
    whatWeSee: 'Horizontal bars showing actual travel times (with interquartile range whiskers) compared to the GTFS planned timetable.',
    whoDidIt: 'noamf2001 (PublicTransportHackathon)',
    rationale: 'Highlights which stop-to-stop segments are chronically late, pinpointing exactly where the timetable is too optimistic.',
  },
  'busline-usage-anomaly': {
    whatWeSee: 'Hourly ticketing validations scored as a standardized z-score against geographical and socioeconomic cluster peers.',
    whoDidIt: 'team (NoamGaash / busline_usage_anomaly.ipynb)',
    rationale: 'Isolates and highlights under-used or overcrowded bus runs relative to their peers, rather than comparing lines in completely different contexts (e.g. city center vs. rural).',
  },
  'gps-trace-map': {
    whatWeSee: 'An interactive map rendering the absolute, real-world GPS trace of a single selected bus ride, colored with a time-of-day gradient.',
    whoDidIt: 'yuvalko1 (talpiot-hackathon-public-transportation)',
    rationale: 'Provides ground-truth auditability. Visualizes missing GPS pings, trace drift, or deviations from the planned route.',
  },
  'schedule-adherence-average': {
    whatWeSee: 'A stringline diagram mapping arrival delay trends of a single departure across multiple days compared to the planned timetable.',
    whoDidIt: 'yuvalko1 (talpiot-hackathon-public-transportation)',
    rationale: 'Helps regular commuters understand if a specific daily run (e.g., the 8:00 AM departure) is chronically delayed and how much its arrival time fluctuates.',
  },
  'schedule-adherence-by-day': {
    whatWeSee: 'Total trip duration on each individual date compared to the planned scheduled run time.',
    whoDidIt: 'yuvalko1 (talpiot-hackathon-public-transportation)',
    rationale: 'Pinpoints specific calendar days that suffered catastrophic delay (e.g., due to accidents, protests, or extreme weather) to isolate them from systemic delay.',
  },
  'schedule-adherence-map': {
    whatWeSee: 'The planned path (dashed line) vs. the actual GPS-averaged route (solid line) mapped directly onto physical streets.',
    whoDidIt: 'yuvalko1 (talpiot-hackathon-public-transportation)',
    rationale: 'Shows exactly where buses lose physical distance on the road, highlighting delay hot-spots or detours.',
  },
  'siri-coverage': {
    whatWeSee: 'Percentage of planned stops that received a matching live GPS ping, grouped by hour of the day.',
    whoDidIt: 'yuvalko1 (talpiot-hackathon-public-transportation)',
    rationale: 'Measures telemetry data quality. Low coverage (less than 50%) means real-time ETA predictions for passengers will be unreliable.',
  },
  'days-with-no-cancellations': {
    whatWeSee: 'An operated vs. cancelled daily breakdown (single line) or a ranked bar chart of worst-performing lines for a given operator.',
    whoDidIt: 'orion (days_with_no_cancellations)',
    rationale: 'A cancellation is the ultimate service failure. By checking planned runs against GPS execution, we calculate a 15-day score representing the fraction of days with zero cancellations.',
  },
}

function AnalysisCard({
  meta,
  filters,
  runToken,
}: {
  meta: AnalysisMeta
  filters: Filters
  runToken: number
}) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)
  const [showTable, setShowTable] = useState(false)
  const [opts, setOpts] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(meta.options.map((o) => [o.key, o.default])),
  )

  const run = useCallback(async () => {
    setBusy(true)
    setFailed(null)
    const body: RunBody = {
      lines: filters.lines
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      operators: filters.operators,
      date_from: filters.date_from,
      date_to: filters.date_to,
      options: opts,
    }
    try {
      setResult(await api.run(meta.name, body))
    } catch (e) {
      setFailed((e as Error).message)
    } finally {
      setBusy(false)
    }
  }, [meta.name, filters, opts])

  // Run on mount and whenever "Run all" is pressed.
  useEffect(() => {
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runToken])

  // Re-run this card when its OWN options change — the global "Run all" button
  // doesn't know about per-card knobs, so without this a changed option updates
  // the control and nothing else. Debounced, so typing in a text option sends
  // one request when you stop rather than one per keystroke.
  const optsKey = JSON.stringify(opts)
  const mounted = useRef(false)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    const t = setTimeout(() => void run(), 600)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optsKey])

  const hasTable = !!result?.table?.rows?.length
  const isChart = result?.kind === 'chart'
  // Both plot kinds get the table toggle — the relief view is mandatory, since
  // some palette slots fall below 3:1 contrast in light mode.
  const isPlot = isChart || result?.kind === 'heatmap'

  const explanation = EXPLANATIONS[meta.name]

  return (
    <section className="card">
      <div className="card-head">
        <h2>{meta.title}</h2>
        {meta.draft && <span className="badge draft">draft</span>}
        <span className="spacer" />
        {meta.author && <span className="byline">{meta.author}</span>}
      </div>
      {meta.description && <p className="card-desc">{meta.description}</p>}

      {explanation && (
        <details className="card-explanation">
          <summary>💡 Demo Pitch & Technical Rationale</summary>
          <div className="explanation-content">
            <p><strong>What we see:</strong> {explanation.whatWeSee}</p>
            <p><strong>Rationale & Method:</strong> {explanation.rationale}</p>
            <p><strong>Original Draft Author:</strong> {explanation.whoDidIt}</p>
          </div>
        </details>
      )}

      {meta.options.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
          {meta.options.map((o) => (
            <div className="field" key={o.key}>
              <label htmlFor={`${meta.name}-${o.key}`}>{o.label}</label>
              {o.type === 'select' ? (
                <select
                  id={`${meta.name}-${o.key}`}
                  value={String(opts[o.key] ?? '')}
                  onChange={(e) => setOpts({ ...opts, [o.key]: e.target.value })}
                >
                  {o.choices.map((c) => (
                    <option key={String(c)} value={String(c)}>
                      {String(c)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={`${meta.name}-${o.key}`}
                  type={o.type === 'number' ? 'number' : 'text'}
                  value={String(opts[o.key] ?? '')}
                  title={o.help ?? undefined}
                  onChange={(e) =>
                    setOpts({
                      ...opts,
                      [o.key]:
                        o.type === 'number' ? Number(e.target.value) : e.target.value,
                    })
                  }
                />
              )}
            </div>
          ))}
        </div>
      )}

      <div className="card-body">
        {busy && <div className="skel" />}

        {!busy && failed && (
          <div className="err">
            <strong>Request failed.</strong>
            <pre>{failed}</pre>
          </div>
        )}

        {!busy && result && result.kind === 'error' && (
          <div className="err">
            <strong>{result.error_message}</strong>
            {result.error_traceback && <pre>{result.error_traceback}</pre>}
          </div>
        )}

        {!busy && result && result.kind === 'metrics' && <Tiles result={result} />}

        {!busy && result && isChart && !showTable && <Chart result={result} />}

        {!busy && result && result.kind === 'heatmap' && result.heatmap && !showTable && (
          <Heatmap result={result} />
        )}

        {!busy && result && result.kind === 'geo' && result.geojson != null && (
          <GeoMap result={result} />
        )}

        {!busy && result && result.kind === 'image' && result.image_png && (
          <img
            className="chart-img"
            src={`data:image/png;base64,${result.image_png}`}
            alt={result.image_alt ?? meta.title}
          />
        )}

        {!busy &&
          result &&
          (result.kind === 'table' || (isPlot && showTable)) &&
          hasTable && <TableView result={result} />}

        {!busy && result && result.notes.length > 0 && (
          <ul className="notes">
            {result.notes.map((n, i) => (
              <li key={i} className="auto-dir">
                {n}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card-foot">
        <button className="ghost" onClick={() => void run()} disabled={busy}>
          {busy ? 'running…' : '↻ rerun'}
        </button>
        {/* Table view is the relief for low-contrast palette slots in light mode. */}
        {isPlot && hasTable && (
          <button className="ghost" onClick={() => setShowTable((s) => !s)}>
            {showTable ? 'chart' : 'table'}
          </button>
        )}
        <span className="spacer" />
        <span className="byline">{meta.module.replace(/^analyses\./, '')}</span>
      </div>
    </section>
  )
}

function Tiles({ result }: { result: AnalysisResult }) {
  return (
    <div className="tiles">
      {result.metrics.map((m, i) => (
        <div className="tile" key={m.label}>
          <div className="tile-label auto-dir" title={m.help ?? undefined}>
            {m.label}
          </div>
          <div className="tile-value" style={{ color: seriesColor(i) }}>
            {fmtNum(m.value)}
            {m.unit && <span className="tile-unit">{m.unit}</span>}
          </div>
          {m.delta !== null && (
            <div
              className="tile-delta"
              style={{
                color:
                  m.delta_is_good === null
                    ? undefined
                    : m.delta_is_good
                      ? 'var(--good)'
                      : 'var(--critical)',
              }}
            >
              {m.delta > 0 ? '▲' : '▼'} {fmtNum(Math.abs(m.delta))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function TableView({ result }: { result: AnalysisResult }) {
  const t = result.table!
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {t.columns.map((c) => (
              <th key={c} className="auto-dir">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {t.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="auto-dir">
                  {typeof cell === 'number' ? fmtNum(cell) : String(cell ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
