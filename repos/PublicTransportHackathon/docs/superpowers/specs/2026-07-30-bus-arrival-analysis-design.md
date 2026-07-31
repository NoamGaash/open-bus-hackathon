# Planned vs. Real-Time Bus Arrival Analysis — Design

## Purpose

For a given Israeli bus line, measure how long the bus **actually** takes to travel between each
pair of consecutive stops, compare it against the **planned** (GTFS) timetable, and visualize the
result in charts that render Hebrew stop names correctly.

## What the API actually provides (probed 2026-07-30)

The obvious data path does not work. Probing the live Stride API established:

| Finding | Consequence |
|---|---|
| On `/siri_ride_stops/list?expand_related_data=true`, **every** `gtfs_stop__*`, `gtfs_ride_stop__*` and `nearest_siri_vehicle_location__*` field is 100% null for all available dates. Filtering by `gtfs_date_from/to` returns 0 rows. | The precomputed SIRI↔GTFS stop match and "nearest vehicle location" arrival time are unavailable. Actual arrival times must be derived from raw GPS. |
| `/stop_arrivals/list` and `/route_timetable/list` are documented as *"only planned time (gtfs) is returned"*. | No endpoint serves actual arrival times directly. |
| `stride.iterate(path, params, limit=N)` — the `limit` kwarg is **client-side only**; it sends no server `limit`, so the server default of 100 rows applies silently. | The server limit must be passed inside `params`. Getting this wrong caps every result at 100 rows with no error. |
| Server rejects `limit > 15000` ("maximum limit per request is 15000 items") and cancels any query exceeding a **60-second statement timeout**. | Ping fetches must be windowed/chunked. A full day of pings for one line times out. |
| `/siri_vehicle_locations/list` filtered by `siri_rides__ids` costs ~0.7 s per ride, and each ping row carries `siri_ride__id`, `siri_ride__scheduled_start_time`, `recorded_at_time`, `lat`, `lon`. | Actual movement is available, but the per-ride cost forces a **bounded, stratified ride sample** rather than "fetch everything". |
| SIRI ride retention is short — rides exist for roughly the last few weeks only, and dates older than ~1 month return nothing. | Default date window must be recent. |
| `/route_timetable/list` returns, per stop: Hebrew `name`, `city`, `lon`, `lat`, `planned_arrival_time`, `gtfs_ride_id`, `gtfs_line_start_time` — zero nulls, ~26 s for a full line-day. | This single endpoint supplies the entire planned side *including stop coordinates and Hebrew names*. |

### The resulting method

Because SIRI stop identities cannot be joined to GTFS stops, the design **uses GTFS stops as the
only stop universe** and derives actual arrival times geometrically:

> The actual arrival time at a stop is the timestamp of the vehicle's **closest approach** to that
> stop's coordinates, linearly interpolated between the two nearest GPS pings.

This sidesteps the stop-identity problem entirely — Hebrew names, coordinates and planned times all
come from one consistent source, and the GPS pings need no enrichment.

**Accuracy limits, measured:** ping cadence is ~60 s, so arrival times resolve to roughly ±30 s
even after interpolation. Closest-approach distances are typically 2–270 m. Consecutive city stops
are often <60 s apart, so a *single* ride's short-segment duration is noise-dominated; the charts
therefore aggregate over many rides and always display sample counts and spread.

Three artifacts of the method are handled explicitly rather than hidden:

1. **Terminal dwell.** Buses idle at the origin emitting pings from the same position, so the
   closest approach to the first stop lands mid-idle and inflates the first segment. For the origin
   stop the *departure* moment is used instead: the last ping within `max_dist_m` before the bus
   leaves the stop's vicinity.
2. **Coincident stops.** Junctions have distinct stop records metres apart with identical planned
   times, which yields tiny negative derived durations. A forward-constrained sequential search
   (stop *k* may only match pings at or after the ping matched for stop *k−1*) guarantees monotonic
   arrival times; non-positive segment durations are then dropped.
3. **Unmatched stops.** If closest approach exceeds `max_dist_m` (default 300 m) the stop is left
   `NaN` — a GPS gap or a skipped stop — and only the segments touching it are lost.

## Architecture

A hard boundary separates network I/O from computation, so the analysis core is unit-testable
without touching the API.

```
lines.py ─┐
fetch.py ─┴─► tidy DataFrames ─► transform.py (pure) ─► viz/*.py ─► matplotlib Figure
```

```
src/bus_times/
  config.py       ISRAEL_TZ, tunable defaults
  lines.py        find_lines() — line discovery/disambiguation; LineSpec
  lowlevel.py     stride_get/stride_iterate wrappers that force the server-side limit
  fetch.py        all network calls; returns tidy DataFrames
  transform.py    pure analysis core (arrival estimation, segments, aggregation)
  viz/
    hebrew.py     Hebrew font resolution + bidi reordering
    theme.py      shared matplotlib style and palette
    segment_bars.py / marey.py / heatmap.py
```

### Data model

Two tidy tables feed all three charts:

**`stop_events`** — one row per (ride, stop): `siri_ride_id`, `ride_date`, `scheduled_start_time`,
`departure_hour`, `stop_sequence`, `stop_name`, `city`, `planned_time`, `actual_time`, plus the two
quality measures `match_distance_m` and `resolution_s`.

**`ride_segments`** — one row per (ride, consecutive stop pair): `siri_ride_id`,
`scheduled_start_time`, `departure_hour`, `segment_index`, `from_name`, `to_name`,
`planned_duration_s`, `actual_duration_s`, and the worse of the two endpoints' `match_distance_m`
and `resolution_s`.

Segments are keyed by stop identity, not row position, so a ride missing one stop still contributes
every other segment.

### Sampling

`load_line_data()` fetches the planned timetable per day, lists candidate SIRI rides (cheap), then
draws a **stratified sample across (date, departure hour)** capped by `max_rides_per_hour` and
`max_rides`, so the hour axis of the heatmap stays populated while the run stays bounded (~2–3 min
per line). The realized sample and coverage are printed, never silently assumed.

## Surfacing uncertainty

Derived arrival times, a sampled ride list and patchy GPS mean the data quality varies *across* a
single chart. A chart that renders every mark identically therefore misrepresents its own evidence,
so uncertainty is a first-class output rather than a caveat in prose.

**Two measurements are carried from the geometry all the way to the charts**, per derived arrival:

- `match_distance_m` — how close the vehicle actually got to the stop. Answers "was it even there?"
- `resolution_s` — the gap between the two pings the arrival was interpolated from, i.e. that
  timestamp's own precision. Answers "how tightly is the moment pinned down?"

A segment inherits the *worse* of its two endpoints for both, since a duration is only as good as
its shakier end. `aggregate_segments` then reduces these plus sample count and coverage to one
`confidence` verdict per segment, naming the worst problem found so the reader learns which caveat
applies rather than a vague "uncertain": `implausible value` → `few samples` → `patchy coverage` →
`coarse GPS timing` → `loose stop match` → `ok`.

**Two design rules follow:**

1. **Flag, never drop.** Earlier versions filtered segments below `min_samples`. That is the worst
   available failure mode — a segment absent from a chart is indistinguishable from a segment that
   does not exist, so the reader cannot even know to ask. Insufficient segments are now kept and
   marked. (`drop_insufficient=True` remains for callers who want a filtered table.)
2. **"No data" and "thin data" must not look alike.** The heatmap therefore has three appearances,
   not two: solid, hatched, and blank. Blanking a one-ride cell would have merged it with the
   genuinely empty ones.

Hatching carries the flag rather than colour alone, so the caveat survives greyscale printing and
colour-vision deficiency — the texture channel the dataviz method reserves for exactly this. Ride
counts are printed on every bar and every heatmap cell, so no mark's weight of evidence is hidden,
and each chart carries a bottom caveat line summarising its own reliability.

## The three charts

Each is `plot_*(...) -> Figure` — returns the figure, never saves or shows, so the same function
serves both the script and the notebook.

1. **Segment travel time** — horizontal bars = median actual duration per segment in route order with
   interquartile whiskers, overlaid diamonds = planned GTFS duration. *Where is the timetable
   optimistic?* Horizontal because stop names run 20–40 characters and rotated Hebrew labels dominate
   the canvas while still reading badly; median because one broken GPS trail moves a mean enough to
   flatten every other segment on the axis.
2. **Marey time-space diagram** — y = stop sequence (Hebrew names), x = minutes elapsed since
   departure; one translucent trajectory per ride over a thick dashed planned reference. Flat
   stretches are congestion; the fan-out is the unreliability.
3. **Segment × departure-hour heatmap** — cell = median actual/planned ratio on a diverging colormap
   centered at 1.0 (a meaningful midpoint: on schedule). *Which segments break down at rush hour?*

### Hebrew rendering

One thing to do, and one emphatically **not** to do.

- **Do pick a Hebrew-capable font.** Matplotlib's default DejaVu Sans has no Hebrew coverage and
  renders tofu boxes. `resolve_hebrew_font()` returns the first installed font from a preference list.
- **Do not reorder the text.** Matplotlib >= 3.11 lays text out through HarfBuzz and applies the full
  Unicode Bidirectional Algorithm: Hebrew runs go right-to-left, embedded digits stay left-to-right,
  and mirrored punctuation such as brackets is flipped correctly. Labels are therefore built in plain
  logical order and passed through untouched, and brackets/commas/arrows can be used freely.

  This was originally implemented the other way round — applying `python-bidi`'s `get_display` on the
  assumption, true of older matplotlib, that no bidi pass existed. That **double-reversed every
  label**, rendering the Hebrew equivalent of `eman` for `name`. The unit tests asserted the reversal,
  so they described the implementation rather than the outcome and let the bug through; they now assert
  that no reordering occurs, and pin the matplotlib floor that makes logical order correct.
  `python-bidi` existed solely for that reordering and has been removed from the dependencies.

## Error handling

- No rides, no planned data, or no segment meeting `min_samples` → `ValueError` echoing the
  parameters, so the message is actionable.
- Missing rides/stops → dropped from aggregates and surfaced in the printed coverage summary and
  the per-segment sample counts the charts display.
- `StrideRequestFailedException` is not caught; it already carries the API's message.

## Testing

`transform.py` is pure and carries the correctness risk, so it is unit-tested against synthetic
data: arrival estimation (exact interpolation, reported resolution, monotonicity under coincident
stops, the origin-departure rule *and* its fallback when a trail starts away from the terminal,
unmatched stops beyond the distance threshold), segment construction, aggregation, the confidence
classifier for each verdict it can return, hour bucketing with counts, stop coverage, and elapsed
profiles. `sample_rides` and `weekdays_between` are pure too and covered in `test_fetch.py`.

The charts get render tests asserting the *uncertainty encoding* specifically — that flagged
segments are hatched and labelled with their reason, that thin heatmap cells hatch at one threshold
and not another, and that poorly covered stops are marked on the Marey axis. These catch the failure
where a caveat silently stops being drawn.

The network layer is not unit-tested (slow, flaky against a live public API); it is covered by
running the example script.

## Out of scope

Caching fetched data; cumulative-delay and reliability-ranking charts; holiday calendars beyond a
weekday filter; headway/bunching analysis.
