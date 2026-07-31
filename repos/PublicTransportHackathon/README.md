# PublicTransportHackathon

Analysis of **planned vs. real-time bus arrivals** in Israel, built on the
[Stride](https://open-bus-stride-api.hasadna.org.il/docs) open-data API.

One question, answered three ways:

> How long does a bus really take to get from each stop to the next, and how does that compare to
> the published timetable?

## Quick start

```bash
uv sync
uv run pytest                                  # 56 tests, no network
uv run python examples/generate_charts.py      # writes 9 PNGs to output/
```

Or explore interactively in `examples/explore.ipynb`.

## The charts

| Chart | Answers |
|---|---|
| `*_segments.png` | **Where is the timetable optimistic?** Median measured duration per segment with interquartile whiskers, against the planned duration. |
| `*_marey.png` | **Where does the bus lose time, and how predictable is it?** A time-space diagram: one trajectory per ride over the schedule. Steep = moving, flat = stuck, and the width of the fan is the unreliability. |
| `*_heatmap.png` | **Which segments break down at rush hour?** Segment × departure hour, coloured by the actual/planned duration ratio. |

All three render Hebrew stop names with correct glyphs and right-to-left ordering, in light or dark
mode (`--mode dark`).

### Which axis carries the stops

Every chart takes `stops_on_x`, and the script takes `--orientation {stops-y,stops-x,both}`
(default `both`, writing the transposed copy with a `_stopsx` suffix):

| | `stops-y` (default) | `stops-x` |
|---|---|---|
| Segment bars | horizontal bars, stop names flat on the y axis | vertical bars, names rotated 45° along the bottom |
| Marey | stops down the y axis, time rightward | stops along the bottom, elapsed time climbing |
| Heatmap | segments as rows, hours as columns | transposed — hours as rows, reading like a timetable |

`stops-y` is the default because Israeli stop names run 20–40 characters: on the y axis they sit flat
and fully legible, while rotating them 45° costs readability and a large slice of the canvas. In
`stops-x` the names are trimmed harder to compensate. Use whichever suits the page.

## Knowing where not to trust the chart

The underlying data is patchy and the arrival times are derived, so a chart that looked uniformly
confident would be lying. Every chart marks its own weak spots:

| Cue | Meaning |
|---|---|
| **Hatched, pale bar or cell** | The number is there but shaky — the note beside it names the reason. |
| **`n=…` beside every bar** | The ride count behind that mark, always visible, never inferred. |
| **Number inside every heatmap cell** | That cell's ride count. Solid = enough rides, hatched = too few, **blank = no data at all** — three distinct appearances, because "one ride" and "no data" must not look alike. |
| **Dimmed, italic stop label with a `%`** | On the Marey chart: the GPS resolved this stop on only that share of rides, so trajectories through it are interpolation more than measurement. |
| **Bottom caveat line** | E.g. `18/24 segments reliable · 4 patchy coverage · 2 coarse GPS timing`. |

Under-sampled segments are **flagged, not dropped**. A segment silently missing from a chart is
indistinguishable from a segment that does not exist, which is the most misleading failure available
here. `aggregate_segments` gives every segment a `confidence` verdict — worst first:

| Verdict | Trigger |
|---|---|
| `implausible value` | Median actual/planned ratio outside 0.25–4.0; almost always an artifact rather than traffic. |
| `few samples` | Fewer rides than `min_samples`. |
| `patchy coverage` | Under half the rides produced a usable value here. |
| `coarse GPS timing` | The pings bracketing the arrival were over 2 minutes apart, so the timestamp is barely constrained. |
| `loose stop match` | Closest approach exceeded 150 m — we cannot be sure which stop the bus was at. |

The thresholds live in `config.py`. `quality_summary()` renders the one-line verdict and
`stop_coverage()` the per-stop breakdown.

## Layout

```
src/bus_times/
  config.py      tunable defaults, most of them dictated by measured API limits
  lines.py       find_lines / resolve_line — get from "line 15 in Jerusalem" to a line_ref
  lowlevel.py    stride wrappers that force the server-side row limit
  fetch.py       all network calls; returns tidy DataFrames
  transform.py   the pure analysis core (arrival estimation, segments, aggregation)
  viz/           hebrew.py, theme.py, and one module per chart
examples/        generate_charts.py (CLI) and explore.ipynb
tests/           unit tests for the pure core; no network
```

The boundary between `fetch.py` and `transform.py` is deliberate: all the correctness risk lives in
the pure functions, which are unit-tested without touching the API.

## How actual arrival times are obtained

**The API does not serve them.** Probing established that on `/siri_ride_stops/list` every
`gtfs_stop__*`, `gtfs_ride_stop__*` and `nearest_siri_vehicle_location__*` field is null for all
available dates, and that `/stop_arrivals/list` and `/route_timetable/list` return planned times
only. So an arrival is *derived*:

> the moment of the vehicle's closest approach to a stop's coordinates, interpolated between the two
> nearest GPS pings.

Planned times, stop coordinates and Hebrew stop names all come from `/route_timetable/list`, which
keeps GTFS as the single stop universe and sidesteps the fact that SIRI stop identities cannot be
joined to GTFS ones.

**What this costs in accuracy:** pings arrive roughly once a minute, so each arrival is good to about
±30 s. Consecutive city stops are often less than a minute apart, so a single ride's short-segment
duration is mostly noise — the aggregate views are the point, and the charts always show spread and
sample counts. The first segment is the least trustworthy, since buses idle at the terminal.

Three artifacts are handled explicitly rather than hidden: terminal dwell (the origin stop resolves
to departure, not closest approach), coincident junction stops (a forward-constrained monotonic
search, and segments the timetable allots zero seconds are dropped), and stops the bus never came
within 300 m of (dropped, costing the two segments either side).

Full detail, including the measured API limits that shaped the fetch layer, is in
[`docs/superpowers/specs/2026-07-30-bus-arrival-analysis-design.md`](docs/superpowers/specs/2026-07-30-bus-arrival-analysis-design.md).

## Gotchas worth knowing

- `stride.iterate(path, params, limit=N)` — the `limit` kwarg is **client-side only**. Without
  `limit` in `params`, the server returns its default of 100 rows and raises nothing. `lowlevel.py`
  exists to make that impossible to get wrong.
- The server caps `limit` at 15000 and cancels any query over 60 s, so GPS fetches are chunked by
  ride id (~0.7 s per ride). That per-ride cost is why rides are sampled rather than exhausted.
- SIRI history is short — a few weeks — and the newest days are still being ingested, so date
  windows default to ending a few days back.
- `fig.savefig(...)` clips Hebrew labels that sit outside the axes. Use
  `bus_times.save_figure(fig, path)`.
- **Never pre-reorder Hebrew before handing it to matplotlib.** Matplotlib >= 3.11 lays text out
  through HarfBuzz and runs the Unicode Bidirectional Algorithm itself — Hebrew goes right-to-left,
  embedded digits stay left-to-right (`15`, not `51`), and brackets are mirrored correctly. Calling
  `python-bidi`'s `get_display` first reverses the string a *second* time and every label renders
  backwards, the Hebrew equivalent of `eman` for `name`. This code passes plain logical order, and
  `matplotlib>=3.11.1` in `pyproject.toml` is a hard floor because of it. (`python-bidi` was a
  dependency for exactly this reordering and has been removed.)
