# Fineable service failures — ghost rides, early & late departures

**Author:** team (`author="team"` in the registry)
**Code:** [analyses/service_violations.py](../analyses/service_violations.py)
**Cards:** `service-violations`, `service-violations-by-day`
**Data:** Stride `/gtfs_rides/list` (planned) + `/siri_vehicle_locations/list` (actual)

## What it answers

Israel's Ministry of Transport can fine operators for service that deviates from
the published timetable. Three failure modes are detectable from open data, at
very different confidence levels:

- **Ghost ride / non-arrival** — planned in GTFS, no SIRI ping ever matched its
  scheduled departure slot.
- **Early departure** — the bus left materially *before* schedule. Passengers
  cannot catch a bus that already went, which is why regulators tolerate
  earliness far less than lateness.
- **Late departure** — first movement materially after schedule, beyond a
  tolerance.

## Algorithm

1. **Resolve scope** to exactly one `(line_ref, operator_ref)`. A requested line
   goes through `/gtfs_routes/list`; with no line requested, the card
   auto-discovers the most-tracked line from a 300-row unfiltered ping sample
   rather than guessing blind.
2. **Fetch the plan** — `/gtfs_rides/list` filtered on
   `gtfs_route__line_refs` + `gtfs_route__operator_refs` + date range. One paged
   call for the whole window. This is deliberately *not* `/route_timetable/list`,
   which rejects ranges over a single day.
3. **Drop plan rows with a null `start_time`** — a real minority of rows. A ride
   with no scheduled time cannot be timed *or* ghost-checked, and left in it
   falls through the join as a spurious ghost.
4. **Fetch the actuals** — `/siri_vehicle_locations/list` filtered on
   `siri_routes__line_ref` + `siri_routes__operator_ref` +
   `siri_rides__schedualed_start_time_from/to` (*sic* — the API's own
   misspelling). Paged manually at 2000/page, capped at 30,000 rows.
5. **Dedup pings** on `(siri_ride__id, recorded_at_time, lat, lon)`.
6. **Derive the departure proxy** — group pings by ride, and take the first ping
   *where the vehicle is actually moving* (`distance_from_journey_start > 0` or
   `velocity > 0`). Fall back to the raw first ping only if the vehicle was never
   seen moving, and flag those rides `stationary_only`.
7. **Join** plan to actual on exact `start_time == siri_ride__scheduled_start_time`
   equality — both derive from the same GTFS timetable slot. Unmatched = ghost.
8. **Classify** each ride: ghost / early (`delta < -1.0` min) / late
   (`delta > 5.0` min) / on-time. Both thresholds are user-editable options.

## Reasoning

**Why raw pings instead of the endpoints built for this.** Two purpose-built
server-side joins were checked live and found broken, so the card derives the
actual-departure signal from raw GPS instead:

- `/gtfs_rides_agg/group_by`'s `total_actual_rides` returned **0 for every row**
   — a server-side aggregation bug, not a real 0% arrival rate.
- `/siri_rides/list`'s own `first_vehicle_location_id` / `gtfs_ride_id` columns
  were **inconsistently NULL** — present for some days, absent for others, for
  identical, genuinely-tracked rides.

**Why exact-equality join and not a time window.** Both sides are drawn from the
same GTFS-derived timetable slot, so the scheduled times line up to the second.
A fuzzy window would introduce its own matching ambiguity for no gain. The cost
is that two GTFS journeys sharing a scheduled minute are indistinguishable —
counted and reported in `dup_start_times` rather than silently double-matched.

**Why the movement filter is the whole ballgame.** See the first finding below.

## Findings

### 1. SIRI reports a vehicle against its next ride ~30 or ~5 minutes before departure, while it is still parked — **confidence: High**

On a sampled line, **~80% of rides' raw first pings** landed at almost exactly
−30 or −5 minutes before scheduled time, with `distance_from_journey_start == 0`
and `velocity == 0`. That is the vehicle sitting at the origin stop boarding, not
departing.

Using the raw first ping as "actual departure" made **~90% of matched rides look
early**. Filtering to the first *moving* ping removed the effect entirely. The
two sharp clusters at fixed offsets, not a smooth distribution, are what make
this a feed convention rather than real early running.

High confidence because the mechanism is understood, the fix is verifiable, and
the pre/post distributions are qualitatively different rather than shifted.

> **This is the single most reusable result in the repo.** Any analysis that
> takes "first SIRI ping" as departure time is measuring the operator's
> reporting lead time, not the bus.

### 2. `/gtfs_rides_agg`'s `total_actual_rides` is 0 for every row — **confidence: High**

Verified live while building this card, and independently by
[orion](days-with-no-cancellations.md) across `/list` *and* `/group_by`, on every
date sampled Nov 2025 → Jul 2026, network-wide, while `num_planned_rides` is
populated normally. Not ingestion lag: the same line/date shows real
`actual_start_time` values through `/rides_execution/list`.

Two independent confirmations on different endpoints with a control that rules
out the obvious alternative explanation.

### 3. `/siri_rides/list`'s derived join columns are inconsistently NULL — **confidence: High**

`first_vehicle_location_id` and `gtfs_ride_id` are present for some days and
absent for others, for rides that are genuinely tracked. Corroborated
independently by `lihay7/BusAnalysis` (F7 and F1), which measured
`first_vehicle_location_id` at **100.00% null for 18 consecutive months**
(2024-12 → 2026-05, 49.4M rides) and the SIRI→GTFS link at zero matches since
2024-10.

Two independent projects, different method, same conclusion, with a census
behind the second.

### 4. A real minority of `/gtfs_rides/list` rows have a null `start_time` — **confidence: Medium**

A GTFS source data gap, not a SIRI matching problem. Medium rather than High
only because the card records the count per query rather than measuring a rate
across the network.

### 5. Ghost-ride rates on any single line — **confidence: Low**

The card reports them, and the notes say plainly why they are candidates rather
than confirmed non-arrivals: a bus that ran untracked looks identical to a bus
that was cancelled. On a line outside the real-time feed the ghost rate is 100%
and means nothing at all.

### Not a finding: ~90% early departures

See finding 1. This was the artifact, and it is recorded here so it is not
rediscovered.

## Criticism

**The thresholds are invented.** 1 minute early / 5 minutes late are described in
the notes as "illustrative round numbers reflecting commonly cited regulatory
practice" and explicitly *not* from the ministry's fine schedule. The card is
titled "**Fineable** service failures" and the description says "the three
failure modes the Ministry of Transport can fine for". That gap between title
and method is the biggest presentational risk in the repo — the chart looks like
a compliance report and is not one. Sourcing the real tolerances would change
this from indicative to citable, and is the highest-value follow-up here.

**Scope is one line.** Every rate is for a single auto-discovered or
user-selected `line_ref`, which is one direction × one route alternative × one
operator. The notes say so. Nothing about an operator or the network follows.

**Ghost and untracked are conflated by construction** and cannot be separated
with this data. That is honest in the notes, but the bar chart draws
`Ghost / non-arrival` in the same visual weight as the measured categories,
which reads as more equivalent than it is.

**The window cap is 10 days** and `MAX_WINDOW_DAYS` silently truncates from the
*start* of a longer request. A user who selects a month gets the last 10 days
with no visible indication in the subtitle beyond the printed date range.

**`stationary_only` rides keep a classification.** They fall back to the raw
first ping — the very artifact finding 1 identifies — and are then labelled
early/late/on-time anyway. The note flags them, but they would be better
excluded from the percentages than counted and caveated.

## Code pointers

- Departure proxy and the movement filter: [service_violations.py:270-302](../analyses/service_violations.py#L270-L302)
- The classification: [service_violations.py:316-326](../analyses/service_violations.py#L316-L326)
- Method notes shown on every card: [service_violations.py:349-437](../analyses/service_violations.py#L349-L437)
