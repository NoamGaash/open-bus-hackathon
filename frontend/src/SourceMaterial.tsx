// A reviewer-facing appendix: the original notebooks/scripts each ported
// analysis was built from, fetched straight from GitHub raw content and
// rendered as code, so "what we built" can be compared against "what the
// team member actually wrote" without leaving the dashboard.
//
// Fetched lazily (only when a file is expanded) and only once per file —
// nine files, one of them normally 3.8MB before its embedded map-image
// outputs are stripped, isn't worth pulling in on every page load.

import { useState } from 'react'

interface RepoGroup {
  repo: string
  branch: string
  url: string
  author: string
  files: { path: string; builtInto: string }[]
}

const GROUPS: RepoGroup[] = [
  {
    repo: 'noamf2001/PublicTransportHackathon',
    branch: 'analyze-per-subsequent-stops',
    url: 'https://github.com/noamf2001/PublicTransportHackathon/tree/analyze-per-subsequent-stops',
    author: 'noamf2001',
    files: [
      {
        path: 'examples/generate_charts.py',
        builtInto: 'analyses/bus_arrival_reliability.py — segment reliability, Marey diagram, hourly heatmap',
      },
      {
        path: 'examples/explore.ipynb',
        builtInto: 'analyses/bus_arrival_reliability.py (exploratory precursor to generate_charts.py)',
      },
    ],
  },
  {
    repo: 'yuvalko1/talpiot-hackathon-public-transportation',
    branch: 'main',
    url: 'https://github.com/yuvalko1/talpiot-hackathon-public-transportation/tree/main',
    author: 'yuvalko1',
    files: [
      {
        path: 'open-bus-stride-client-main/scripts/explore_gtfs_siri_coverage.py',
        builtInto: 'analyses/siri_coverage.py — ported near-verbatim (nearest-stop + time-tolerance matching), scoped down from a system-wide batch scan to one live line',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/compare_gtfs_siri_average.ipynb',
        builtInto: 'analyses/schedule_adherence_average.py — the day-to-day stringline, the planned-vs-measured map, and a which-day-ran-worst chart',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/compare gtfs planned vs siri actual.ipynb',
        builtInto: 'Covered by schedule_adherence_average.py — each faint trace on the stringline IS one ride\'s plan-vs-actual, and schedule-adherence-by-day names the worst single day',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/load gtfs timetable to pandas dataframe.ipynb',
        builtInto: 'Covered by schedule-adherence-map — its dashed layer is exactly this: the planned route at GTFS coordinates, colored by time',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/load siri vehicle locations to pandas dataframe.ipynb',
        builtInto: 'analyses/gps_trace_map.py — one ride\'s GPS trail on a Leaflet map, same time-of-day gradient',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/siri accessibility analysis using UrbanAccess.ipynb',
        builtInto: 'Not ported — urbanaccess pulls ~10 heavy deps (pandana, osmnet, scipy, scikit-learn) and its own notebook warns the network build is slow; that is a batch job, not a live card',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/Load route rides to dataframe.ipynb',
        builtInto: 'Exploratory — unmodified upstream example, no chart',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/getting all arrivals to all stops of a given line in a given day.ipynb',
        builtInto: 'Exploratory — data loading only, no chart',
      },
      {
        path: 'open-bus-stride-client-main/notebooks/algorithm for getting data to calculate routes between points.ipynb',
        builtInto: 'Exploratory — unfinished trip-planning sketch, no chart',
      },
    ],
  },
  {
    // Contributed as a notebook rather than a repo, so it lives at this repo's
    // root and is read back from here — same viewer, no special case.
    repo: 'NoamGaash/open-bus-hackathon',
    branch: 'main',
    url: 'https://github.com/NoamGaash/open-bus-hackathon',
    author: 'team',
    files: [
      {
        path: 'busline_usage_anomaly.ipynb',
        builtInto:
          'analyses/busline_usage_anomaly.py — peer-group ridership z-score. NOTE: the ' +
          'notebook read a station-level data.gov.il resource that has no line column, so its ' +
          'per-line metro score was the same global data for every line; the port uses the ' +
          "ministry's own cluster grouping from the per-line resource instead.",
      },
    ],
  },
]

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; cells: Cell[] }

interface Cell {
  kind: 'code' | 'markdown' | 'text'
  source: string
}

// Both source repos are private, so the browser can't hit GitHub directly (no
// auth to carry, and a token has no business living in frontend JS anyway) —
// this goes through our own API, which proxies via the gh CLI's server-side
// auth. See openbus_hack/source_material.py.
function sourceApiUrl(repo: string, branch: string, path: string): string {
  const q = new URLSearchParams({ repo, branch, path })
  return `/api/source-material?${q.toString()}`
}

function SourceFileView({ file, repo, branch }: { file: { path: string; builtInto: string }; repo: string; branch: string }) {
  const [open, setOpen] = useState(false)
  const [state, setState] = useState<LoadState>({ status: 'idle' })
  const filename = file.path.split('/').pop()!

  const load = async () => {
    if (state.status !== 'idle') return
    setState({ status: 'loading' })
    try {
      const res = await fetch(sourceApiUrl(repo, branch, file.path))
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const data: { cells?: Cell[]; error?: string } = await res.json()
      if (data.error) throw new Error(data.error)
      setState({ status: 'ready', cells: data.cells ?? [] })
    } catch (e) {
      setState({ status: 'error', message: (e as Error).message })
    }
  }

  return (
    <details
      className="source-file"
      onToggle={(e) => {
        const next = (e.target as HTMLDetailsElement).open
        setOpen(next)
        if (next) void load()
      }}
    >
      <summary>
        <code className="auto-dir">{filename}</code>
        <span className="muted"> → {file.builtInto}</span>
      </summary>
      {open && (
        <div className="source-file-body">
          {state.status === 'loading' && <p className="muted">loading…</p>}
          {state.status === 'error' && (
            <p className="err">
              Couldn't load from GitHub: {state.message}
            </p>
          )}
          {state.status === 'ready' &&
            state.cells.map((c, i) => (
              <pre key={i} className={`source-cell source-cell-${c.kind}`}>
                <code>{c.source}</code>
              </pre>
            ))}
        </div>
      )}
    </details>
  )
}

export function SourceMaterial() {
  return (
    <section className="source-material">
      <h2>Source material</h2>
      <p className="muted">
        The original notebooks and scripts each ported analysis is built from — for comparing
        what a team member wrote against what ended up on the dashboard.
      </p>
      {GROUPS.map((g) => (
        <div key={g.repo} className="source-group">
          <h3>
            <a href={g.url} target="_blank" rel="noreferrer">
              {g.repo}
            </a>
            <span className="byline"> · {g.author} · branch {g.branch}</span>
          </h3>
          {g.files.map((f) => (
            <SourceFileView key={f.path} file={f} repo={g.repo} branch={g.branch} />
          ))}
        </div>
      ))}
    </section>
  )
}
