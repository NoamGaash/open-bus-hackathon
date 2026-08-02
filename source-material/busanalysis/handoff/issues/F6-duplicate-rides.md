# 2.6% of siri_ride rows are duplicate journeys; the rate has quadrupled since 2023

**Severity:** corrupts derived metrics — any count of raw tracking rows overstates real service
**Affected component:** `siri_ride` row creation, downstream of the `scheduled_start_time` drift bug (hasadna issue #390)
**Window observed:** 2022-12-30 → 2026-08-01 (full census, 116,335,248 rows)
**Reported by:** external analysis of the open data (BusAnalysis), 2026-07

## What happens

The same real bus journey is stored more than once.
When a journey's scheduled start time drifts, a **new** `siri_ride` row is written instead of the
existing row being updated, so one physical journey ends up with several rows that differ only in
that timestamp.

## Evidence

Measured over the complete mirrored population, not a sample:

- **3.93%** of rides sit in a duplicated `(siri_route_id, journey_ref, service day)` group.
- **2.56%** of all rows are *surplus* duplicates — i.e. rows beyond the first in their group.
- The rate is **66× skewed across operators**.
- It has roughly **quadrupled from 2023 to 2026** (national share of rides in duplicate groups
  rises from ~1.4% to ~5.9%).

Figure: `report/figures/findings/f6_duplication_trend.png` (national line plus the three worst
operators carrying at least 1M rides; 2026-07 excluded as a partial month).
The shares are **lower bounds** — the grouping key is conservative.

Because this is a census rather than a sample, the count itself needs no coverage-bias
correction. The operator skew does matter, though: it makes per-operator raw-ride counts
differentially wrong, so the error does not cancel out in a league table.

## Why it matters

Two distinct downstream failures:

1. **Any pipeline that counts raw `siri_ride` rows overstates actual service** — by 2.6%
   nationally, and by much more for the worst-affected operators.
2. Under a 1:1 planned↔actual match, every surplus row is an actual ride with no planned
   counterpart, so it reads as a **phantom "unplanned ride"**. No unplanned-ride statistic is
   publishable until the duplicates are removed.

## Suggested fix

The root cause is issue #390: update the existing row on drift rather than inserting a new one.

If changing the write path is too invasive, the next-best option is a deduplicating view over
`siri_ride` keyed on `(siri_route_id, journey_ref, service day)` that downstream consumers use
instead of the raw table — so that consumers cannot accidentally count duplicates.

We are not certain which is preferable in your architecture; the choice depends on whether any
consumer legitimately needs the drift history.

## What we did instead (workaround in the external analysis)

Our extractor deduplicates on `(operator, line, journey_ref)` per service day before matching,
keeping one row per group.
Deduplication removed roughly 3.2M rows across the census.
This runs *before* the planned↔actual assignment, which is what stops surplus rows from surfacing
as phantom unplanned rides in our numbers.
