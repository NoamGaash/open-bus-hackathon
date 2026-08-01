# Bus arrival reliability — segments, Marey, rush-hour heatmap

**Author:** noamf2001 — [github.com/noamf2001/PublicTransportHackathon](https://github.com/noamf2001/PublicTransportHackathon), branch `analyze-per-subsequent-stops`, vendored at [repos/PublicTransportHackathon](../repos/PublicTransportHackathon/) and pulled in as the `bus_times` dependency
**Code:** [analyses/bus_arrival_reliability.py](../analyses/bus_arrival_reliability.py)
**Cards:** `bus-segment-reliability`, `bus-marey-diagram`, `bus-hourly-heatmap`
**Data:** Stride `/route_timetable/list` (planned + stop coordinates + Hebrew names) + `/siri_vehicle_locations/list` (GPS)

## What it answers

One question, three views:

> How long does a bus really take to get from each stop to the next, and how does
> that compare to the published timetable?

- **Where is the timetable optimistic?** Median measured duration per stop-to-stop
  segment against the planned duration, with the interquartile spread as a whisker.
- **Where does the bus lose time?** A Marey time-space diagram — one trajectory per
  sampled ride over the schedule. Steep = moving, flat = stuck, and the width of
  the fan is the route's unreliability.
- **Which segments break down at rush hour?** Segment × departure hour, coloured by
  the actual/planned duration ratio.

## Algorithm

The analytical core lives in the upstream `bus_times` package; this module owns
resolution, presentation and the caching.

1. **Resolve** `find_lines(short_name, …, agency_name, name_contains)` → candidate
   routes, filtered by direction if given.
2. **Fetch** `load_line_data(line, date_from, date_to)` → `stop_events` (one row per
   ride × stop) and `ride_segments` (one row per ride × segment).
3. **Derive arrival times.** *The API does not serve them.* An arrival is the moment
   of the vehicle's **closest approach to a stop's coordinates, interpolated between
   the two nearest GPS pings**.
4. **Aggregate** — `aggregate_segments(ride_segments, min_samples)` gives per-segment
   median / p25 / p75 actual, planned duration, and a `confidence` verdict;
   `segment_hour_matrix` gives the ratio and count matrices;
   `elapsed_profiles` / `stop_coverage` feed the Marey.
5. **Render** client-side through `openbus_hack.contract` (the upstream matplotlib
   plotters are kept only for the optional "static draft" view).

### The confidence ladder (upstream `aggregate_segments`)

Under-sampled segments are **flagged, not dropped** — a segment silently missing
from a chart is indistinguishable from a segment that does not exist, which is the
most misleading failure available here.

| Verdict | Trigger |
|---|---|
| `implausible value` | Median actual/planned ratio outside 0.25–4.0 — almost always an artifact rather than traffic |
| `few samples` | Fewer rides than `min_samples` |
| `patchy coverage` | Under half the rides produced a usable value here |
| `coarse GPS timing` | The pings bracketing the arrival were over 2 minutes apart |
| `loose stop match` | Closest approach exceeded 150 m — which stop the bus was at is uncertain |

## Reasoning

**Why derive arrivals at all.** Probing established that on `/siri_ride_stops/list`
every `gtfs_stop__*`, `gtfs_ride_stop__*` and `nearest_siri_vehicle_location__*`
field is null for all available dates, and that `/stop_arrivals/list` and
`/route_timetable/list` return planned times only. There is no served actual
arrival time to use.

**Why GTFS is the single stop universe.** Planned times, stop coordinates and Hebrew
names all come from `/route_timetable/list`, which sidesteps the fact that SIRI stop
identities cannot be joined to GTFS ones.

**Why ambiguous line matches resolve rather than fail.** `bus_times.resolve_line()`
raises when a description matches zero *or* several routes — right for a notebook,
wrong for a dashboard, where picking line "1" with no operator would produce an
error card. The port picks the first candidate deterministically and *says what it
chose and what it ignored*.

**Why one shared fetch.** Resolving a line and pulling timetable + sampled pings
costs ~1–2 minutes. The dashboard's global filter bar fires all three cards with
identical parameters, so `_load` is disk-cached and single-flight: the first caller
pays, the other two wait on its result.

## Findings

### 1. The Stride API serves no actual arrival times at all — **confidence: High**

Every candidate field is null across all available dates, on three separate
endpoints. This is why every planned-vs-actual card in this repo derives arrivals
from raw GPS. Directly probed, unambiguous, and independently re-hit by every other
author here.

### 2. Derived arrival times are good to about ±30 s — **confidence: High**

Pings arrive roughly once a minute; interpolating closest approach between the two
bracketing pings gives ~±30 s. This is a stated, propagated error bound rather than
an unquantified caveat — and it is the reason the aggregate views are the point.

### 3. Single-ride short-segment durations are mostly noise — **confidence: High**

Consecutive city stops are often less than a minute apart, which is inside the
error bar of the arrival estimate itself. Follows directly from finding 2 and is
handled structurally: the charts always show spread and sample counts.

### 4. The first segment is systematically the least trustworthy — **confidence: High**

Buses idle at the terminal, so the origin stop resolves to *departure* rather than
closest approach — a different quantity from every other stop on the route.
Handled explicitly upstream rather than hidden.

### 5. Three named artifacts, each handled explicitly — **confidence: High**

Terminal dwell; coincident junction stops (fixed with a forward-constrained
monotonic search, and segments the timetable allots zero seconds are dropped); and
stops the bus never came within 300 m of (dropped, costing the two segments either
side). Each is a mechanism, identified and mitigated, not a statistical guess.

### 6. On any given line, which segments are optimistically timetabled — **confidence: Medium**

The output the cards exist to produce. Medium because it rests on a ±30 s derived
proxy over a ≤10-day window on one route variant. Directionally reliable —
a segment that runs 1.5× its allotted time repeatedly is really slow — but the
exact ratio should not be quoted.

## Criticism

**The dependency is a private-ish vendored package.** All the correctness risk —
arrival derivation, segment aggregation, the confidence ladder — lives in
`bus_times`, outside this repo, pulled from a branch (`analyze-per-subsequent-stops`)
rather than a tag. The upstream has 56 network-free unit tests over its pure core,
which is more than anything here has, but the coupling means this card's behaviour
can change without a commit in this repo.

**Ambiguous-match resolution is deterministic, not correct.** Picking `df.iloc[0]`
when the filters match 12 routes is defensible for a demo and is disclosed in the
notes, but the reader has to actually read the note to know they are looking at one
arbitrary variant of "line 1".

**The `name_contains` city list is hardcoded** to 11 Hebrew city names
([bus_arrival_reliability.py:66](../analyses/bus_arrival_reliability.py#L66)). Any
line outside those cities needs the free-text path, which the dropdown replaced.

**The static-PNG path is a genuine performance trap, now fixed but worth knowing.**
matplotlib warns once per (glyph, call-site) for missing Hebrew glyphs — **8,465
warnings in one session** — and the warning machinery, not the rendering, made the
whole API unresponsive. A figure fully determined by its cache key was also being
redrawn on every request, costing 67 s on a card whose data was already warm. Both
are fixed here ([bus_arrival_reliability.py:86-124](../analyses/bus_arrival_reliability.py#L86-L124)),
but any future matplotlib+Hebrew work in this codebase will hit the same wall.

**The 9-day window cap** ([bus_arrival_reliability.py:135](../analyses/bus_arrival_reliability.py#L135))
is driven by fetch cost (~25 s/day for the timetable, ~0.7 s/ride for pings), not by
what makes a statistically sound sample. Rush-hour heatmap cells on a low-frequency
line can rest on very few rides — flagged by hatching, but the cap is what puts them
there.
