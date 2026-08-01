# SIRI GPS coverage vs planned stops, by hour

**Author:** yuvalko1 — [github.com/yuvalko1/talpiot-hackathon-public-transportation](https://github.com/yuvalko1/talpiot-hackathon-public-transportation), from `open-bus-stride-client-main/scripts/explore_gtfs_siri_coverage.py`
**Code:** [analyses/siri_coverage.py](../analyses/siri_coverage.py)
**Card:** `siri-coverage`
**Data:** Stride `/route_timetable/list` + `/siri_vehicle_locations/list`

## What it answers

For one resolved line + direction: **what fraction of planned GTFS stops actually
got a matching real-time SIRI GPS ping, broken down by hour of day?**

This is a data-quality question wearing a service-quality costume. It measures the
*feed*, not the buses — and that distinction is what makes it one of the more
important cards here, because every other planned-vs-actual card depends on the
answer.

## Algorithm

The source script answers this across the **entire** network with a three-stage
design (stage 0: discover which of the last ~90 days have data; stage 1: a cheap
per-line ride-volume screen to find "worthy" lines; stage 2: the expensive per-stop
matching, sampled over ~20 days) — estimated by its author at **1–2 hours of
wall-clock time** for a full run.

This port keeps the one piece of real algorithmic logic — `compute_ride_coverage`,
ported as `_ride_coverage` with the logic unchanged — and applies it live to **one**
line + direction over at most **3** days.

Per sampled day:

1. **Plan** — `/route_timetable/list` for the line, one day, `limit=15000`.
2. **Actual** — `/siri_vehicle_locations/list` filtered on `siri_routes__line_ref`
   + `siri_routes__operator_ref` + `siri_rides__schedualed_start_time_from/to`.
3. **Per planned ride** (grouped by `gtfs_ride_id`):
   - Match SIRI rides on exact `scheduled_start_time == gtfs_line_start_time`.
   - `_largest_group` — if the scheduled time coincidentally matches more than one
     `siri_ride__id`, keep the biggest rather than mixing pings from unrelated
     vehicles.
   - **`_ride_coverage`**: build the full ping × stop distance matrix, mask it to
     `time_gap <= 20 min`, take `argmin` per ping, and count **distinct** stops
     reached: `n_covered = len(set(nearest_idx[has_match]))`.
4. **Aggregate** by hour of the ride's scheduled start (Israel time):
   `coverage_pct = 100 × Σ covered / Σ planned`.

## Reasoning

**Why the time tolerance is not optional.** Without it, routes that loop back near
their own path match a much-later ping to an early stop, inflating coverage. Ported
unchanged at 20 minutes.

**Why one line, one day at a time.** Two hard API constraints, both discovered by
the author and documented in the source repo's own gotchas list:
`route_timetable/list` **rejects date ranges over a single day** and times out
unfiltered regardless of range; `siri_vehicle_locations/list` accepts **only a
single `line_ref` per request**. The one-line-one-day loop is not a design choice.

**Why auto-discovery when no line is requested.** Guessing a `line_ref` blind risks
landing on an operator or vehicle type outside the real-time feed entirely, and the
default "click the card with no filters" view would show 0% coverage as if it were
a finding. A 300-row unfiltered ping sample finds something actually tracked.

**Why every request sets an explicit `limit`.** `stride.get()` does one raw call
with no auto-paging, and **the server silently defaults to a small page**
(~100 rows) otherwise — the same trap the source repo documents for
`stride.iterate()`'s client-side-only `limit=` kwarg.

## Findings

### 1. `route_timetable/list` rejects any date range over one day, and times out unfiltered — **confidence: High**

Load-bearing for every card in this repo: it is why nothing here does a
multi-day timetable pull in one call. Directly observed by the source author and
re-hit independently by [service-violations](service-violations.md), which routes
around it via `/gtfs_rides/list`.

### 2. `siri_vehicle_locations/list` accepts only one `line_ref` per request — **confidence: High**

While `route_timetable/list`'s `line_refs` *does* accept a comma-separated batch.
The asymmetry is undocumented and is what forces the per-line loop.

### 3. `stride.iterate()`'s `limit=` kwarg is client-side only — **confidence: High**

The server silently defaults to ~100 rows unless `limit` is *also* passed inside
the request params. A silent truncation, not an error: an analysis that does not
know this gets a plausible-looking answer computed from the first 100 rows.
**This is the most dangerous of the three because it fails quietly.**

### 4. Usable historical data spans about the last 90 days — **confidence: High**

Ending 2026-07-30 at the time of the hackathon. Determined by the source script's
stage-0 scan across the whole window.

### 5. A full-network coverage scan is a 1–2 hour batch job — **confidence: High**

The author's own measured estimate, and the reason the three-stage screen exists.
Relevant to anyone proposing this as a live upstream feature: it is not one.

### 6. Coverage varies by hour of day on a given line — **confidence: Low**

What the card draws. With `MAX_DAYS = 3` and hours flagged below 3 rides as
low-confidence, most hour buckets on most lines rest on a handful of rides. The
*shape* may be indicative; no individual hour's percentage is.

### 7. Some lines have zero SIRI coverage entirely — **confidence: Medium**

The card handles this case explicitly and warns that it means the line is not in
the real-time feed rather than that service collapsed. Corroborated by
`lihay7/BusAnalysis` F9, which identifies **five operators — 2.74M scheduled rides,
~2.3% of national planned volume — that never appear in the tracking feed** across
3.5 years. Medium here (this card sees one line at a time); High in the
[BusAnalysis](../docs/busanalysis.md) census.

## Criticism

**The nearest-stop match has no distance ceiling.** `_ride_coverage` masks on time
and then takes `argmin` over distance — but never asks whether that minimum is
*small*. A ping 4 km from every stop on the route still "covers" whichever stop is
least far away, provided it falls inside the 20-minute window. `bus_times` (see
[bus-arrival-reliability.md](bus-arrival-reliability.md)) uses a **150 m** loose-match
threshold and a **300 m** drop threshold for the same operation. Coverage here is
therefore an **upper bound**, and the gap between it and a distance-gated figure is
unmeasured.

**Distances are Euclidean in raw lon/lat degrees**
([siri_coverage.py:364](../analyses/siri_coverage.py#L364)), so east-west distance is
understated by ~15% at Israel's latitude. Same defect as
[schedule-adherence](schedule-adherence.md); [route-divergence](route-divergence.md)
gets it right with haversine. Minor next to the missing distance ceiling, but it
compounds with it.

**"Covered" counts distinct nearest-stops, not stops the bus was observed at.**
`len(set(nearest_idx[has_match]))` counts how many stops won an `argmin` — a
different quantity from "how many stops did we see the bus reach". A ride with
dense pings over half the route can claim coverage of stops it merely passed near
on the way.

**`MAX_DAYS = 3` against the source's ~20.** The port is honest about this in its
notes, but the resulting per-hour bars carry roughly a sixth of the evidence the
original design considered a minimum.

**The card reads as a service metric.** Titled "SIRI GPS coverage vs planned stops"
with a y-axis of "coverage %", a low bar looks like a failing bus service. It is a
statement about feed completeness. The notes get this right; the chart does not.
