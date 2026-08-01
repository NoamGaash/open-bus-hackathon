# Bus bunching — headway regularity

**Author:** team
**Code:** [analyses/bus_bunching.py](../analyses/bus_bunching.py)
**Card:** `bus-bunching`
**Data:** Stride `/siri_vehicle_locations/list`

## What it answers

Bunching is the classic frequent-service failure: a delayed bus picks up extra
passengers at every stop, falls further behind, and the bus behind it closes the
gap — until two buses arrive nose-to-tail followed by a long empty gap.

**The signal is not lateness, it is how uneven the spacing is.** A line where every
bus is reliably 6 minutes late is fine to wait for; a line whose 10-minute headway
is really 2-then-18 is not, even though its average is perfect.

## Algorithm

1. **Clamp** the window to `SIRI_LAG_DAYS = 3` behind today.
2. **Resolve** one `(line_ref, operator_ref)`. With no line requested, auto-discover
   from a 500-row ping sample, ranked by **distinct rides, not raw ping count** — a
   line that pings often but runs rarely has nothing to say about headways.
3. **Sample days** — up to `max_days` (default 2, `0` = all), weekdays only
   (Sun–Thu), **evenly spread** across the window via `np.linspace` so a capped
   sample represents the whole window rather than skewing to one end.
4. **Per day**: fetch pings, dedup, reduce to one row per ride —
   `scheduled = siri_ride__scheduled_start_time`, `first_ping = min(recorded_at_time)`.
5. **Headways** — within each day, sort scheduled times and actual first-pings
   separately and take consecutive `diff()` in minutes.
6. **Target headway** = `median(scheduled_headways)`, pooled across sampled
   days/hours.
7. **Classify** each actual headway:
   - **Bunched**: `< 0.25 × target` (nose-to-tail)
   - **Gapped**: `> 1.75 × target` (the hole bunching leaves behind)
   - **Normal**: in between
8. **Report** the coefficient of variation `CV = std/mean`, with ~0.5 as the usual
   bunching threshold.

## Reasoning

**Why CV and ratio buckets rather than mean delay.** Mean headway is invariant to
bunching — two buses at 2 and 18 minutes average the same as two at 10 and 10. CV
and the bucket split are the quantities that actually separate them.

**Why the median of scheduled gaps as the target.** A single "target" headway is a
blunt instrument, but it is what turns "13 minutes" into "bunched" or "fine" at a
glance, and the median is robust to the one huge first/last-run-of-day gap that
would wreck a mean.

**Why `_resolve_line` bypasses `stride.siri_rides()`.** Spot-checked live: the
`gtfs_route__route_short_name` join is null on most rows — a plainly-running line
came back empty when filtered on it. Line identity comes from GTFS route metadata
for a readable name, but the SIRI fetch filters on `siri_routes__line_ref` directly.

**Why weekends are dropped.** Israeli bus service is thin on Fri/Sat by design; a
handful of night-bus headways read as false bunching or gapping.

**Why `REQUEST_LIMIT = 15000`.** Spot-checked live: 15,000 succeeds, **20,000 500s
instantly** — an undocumented server-side cap somewhere between the two.

## Findings

### 1. `siri_rides`' `gtfs_route__route_short_name` join is null on most rows — **confidence: Medium**

A plainly-running line's `siri_rides` came back empty when filtered on it. Same
family as the broken stored-linkage columns found by
[service-violations](service-violations.md) and measured as a **21-month total
outage** by `lihay7/BusAnalysis` F1. Medium here only because this card spot-checked
rather than quantified; the underlying defect is High-confidence via those two.

### 2. An undocumented row cap sits between 15,000 and 20,000 — **confidence: High**

15,000 succeeds; 20,000 returns an immediate 500 rather than a truncated result or a
400. Reproducible and sharp. The source repo's `explore_gtfs_siri_coverage.py`
independently settled on the same 15,000.

### 3. Filtering on `recorded_at_time_from/to` 500s where `siri_rides__schedualed_start_time_from/to` succeeds — **confidence: Medium**

For a line with a busy full day, the same window filtered directly on
`recorded_at_time` 500s, while filtering through the ride's scheduled time works.
Spot-checked on one line; the same query shape is used by
[siri-coverage](siri-coverage.md) and [schedule-adherence](schedule-adherence.md),
so it is at least consistently necessary. Note
[route_divergence.py](../analyses/route_divergence.py) and
[gps_trace_map.py](../analyses/gps_trace_map.py) *do* use `recorded_at_time`
successfully over a 4-hour window — so the trigger is probably result-set size, not
the parameter itself.

### 4. A moderately busy Tel Aviv line generates ~8–10k pings per day, fetched in ~8 s — **confidence: High**

A measured cost figure, and the basis for `MAX_DAYS = 2`. Useful for anyone sizing
a batch job against this API.

### 5. Bunching rates on any specific line — **confidence: Low**

The card's actual output. With `MAX_DAYS = 2` by default, on one line, using
first-ping-as-departure, this is a demonstration of the method rather than a
measurement of the network.

## Criticism

**The departure proxy is the raw first ping — the exact artifact
[service-violations](service-violations.md) identified and corrected.** That card
found ~80% of raw first pings land at fixed −30 or −5 minute offsets with the
vehicle stationary at the origin. This card takes `min(recorded_at_time)` per ride
with no movement filter.

The damage is smaller than it would be for a punctuality measure — headways are
*differences* between consecutive first-pings, so a constant reporting lead time
cancels out. But it does not cancel if the lead time is bimodal (−30 **or** −5, per
that card's own finding): a ride reported 30 minutes ahead followed by one reported
5 minutes ahead produces a fabricated 25-minute swing in an otherwise regular
headway. Given the buckets are `<0.25×` and `>1.75×` of target, that is enough to
move rides between categories. **This is the most concrete correctness problem in
the card, and the fix already exists in the same repo.**

**Headways are computed between consecutive departures at the origin, not arrivals
at a stop.** Bunching is a phenomenon that *develops along the route* — buses leave
the terminal evenly and arrive downstream bunched. Measuring at the origin measures
dispatch regularity, which is the thing least likely to be bunched.
[poisson-arrival-regularity](poisson-arrival-regularity.md) has the right idea here
(CV *per stop index*, watching it climb downstream) and is currently broken; between
them they describe the analysis that should exist.

**The pooled target headway is acknowledged as wrong and shipped anyway.** The notes
say a line running every 6 min at rush hour and every 20 min off-peak will show
off-peak departures flagged "gapped" that are the timetable working as intended.
Since `target` is the median of *scheduled* gaps, roughly half the scheduled
headways exceed it by construction, and the gapped bucket absorbs normal off-peak
service. Bucketing each headway against its own local scheduled headway would fix
this and is not much more work.

**`MIN_HEADWAYS = 5` is a very low bar** for reporting a coefficient of variation.
The card does degrade to a metrics tile below it, but 5 observations is still barely
a CV.

**Default `max_days = 2`** means the headline number typically rests on two days of
one line, while the chart's axis reads "count of consecutive headways" — a number in
the hundreds, which looks like far more evidence than there is.
