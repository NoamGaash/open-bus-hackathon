# The SIRI→GTFS ride-matching job has written zero matches since October 2024

**Severity:** blocks published statistics — every planned-vs-actual figure has had no usable input for ~21 months
**Affected component:** the population step that writes `siri_ride.gtfs_ride_id` (`stride-etl-siri-update-rides-gtfs`)
**Window observed:** healthy through 2024-08 · degrading 2024-09 · effectively zero 2024-10 → 2026-07
**Reported by:** external analysis of the open data (BusAnalysis), 2026-07

## What happens

The job that links each real bus ride to the scheduled ride it was meant to run has stopped
populating its output column.
The raw feed never stopped: roughly 2.9–3.1M `siri_ride` rows per month are still being created,
and about 42,000 tracking snapshots per month still land, right through July 2026.
Only the *link* between actual and planned is missing.

All four match columns fail together — `gtfs_ride_id`, `route_gtfs_ride_id`,
`scheduled_time_gtfs_ride_id`, and the deprecated `journey_gtfs_ride_id`.

## Evidence

Complete day-by-day scans of whole months against the production database (not samples — the
per-day match rate is bimodal, so sampling is unsafe here):

| month | days | days ≥80% matched | days at exactly 0 | rides | matched | overall |
|---|---|---|---|---|---|---|
| 2024-08 | 31 | **31** | 0 | 2,878,859 | 2,767,779 | **96.1%** |
| 2024-09 | 30 | 15 | 7 | 2,929,417 | 1,487,017 | 50.8% |
| 2024-10 | 31 | 0 | 19 | 2,485,854 | 44 | 0.0% |
| 2024-11 | 30 | 0 | 23 | 2,785,949 | 9,309 | 0.3% |
| 2024-12 | 31 | 0 | 26 | 3,086,370 | 6 | 0.0% |
| 2025-03 | 31 | 0 | **31** | 2,896,698 | **0** | 0.0% |
| 2025-06 | 30 | 0 | **30** | 2,010,462 | **0** | 0.0% |
| 2025-12 | 31 | 0 | **31** | 3,057,771 | **0** | 0.0% |
| 2026-03 | 31 | 0 | **31** | 1,891,116 | **0** | 0.0% |
| 2026-06 | 30 | 0 | **30** | 2,987,448 | **0** | 0.0% |
| 2026-07 | 30 | 0 | **30** | 2,945,201 | **0** | 0.0% |

Exactly zero for 19 consecutive months (2025-01 → 2026-07), no islands.
Affected rides 2024-10 → 2026-07: **~61.5 million**.

Independent corroboration: `gtfs_rides_agg_by_hour.num_actual_rides` reads 0 nationwide over the
same span while `num_planned_rides` stays healthy.

**The data is intact — this is a stalled job, not data loss.**
A controlled re-join (identical query, one working day and one dead day, 8 busiest lines):

| day | stored as matched | siri rides | exact re-join | ±5 min | ±60 min |
|---|---|---|---|---|---|
| 2024-08-14 (control) | 96% | 1,577 | 1,171 (74.3%) | 92.0% | 98.4% |
| **2026-07-20** | **0%** | 1,278 | **1,249 (97.7%)** | 98.7% | 99.4% |

On a day stored as zero matches the link **reconstructs at 97.7% exact** — better than the
control day.
Supporting checks on 2026-07-20: all 119,729 `siri_ride` rows have a `siri_route` with non-null
`operator_ref` and `line_ref`; 5,783 of 5,797 SIRI (operator, line) pairs (99.8%) exist in
`gtfs_route` that day; every sampled line has planned rides; timestamps align with no offset.
It generalises beyond the busiest lines: on 2026-07-20 with 25 lines per stratum, busiest 96.3%
exact, random 95.8%, sparsest (median 4 rides/line) 85.0%.

## Why it matters

The `/gtfs_rides_agg` endpoint and its `useGroupBy` consumers (the planned-vs-actual charts) read
`scheduled_time_gtfs_ride_id` and therefore return zeros for this whole period.

Scope correction worth stating precisely, because we initially got it wrong: **the `gaps` page is
not affected.**
`gapsService.ts` calls `ridesExecutionListGet()` → `/rides_execution/list`, which computes its
join live from `scheduled_start_time` equality and never reads the stalled columns.
So the blast radius is the aggregate endpoint and its consumers, not the whole front end.

Separately, this means Israel's national "rides that didn't run" statistic has had no computable
basis from this source since October 2024.

## Suggested fix

Re-run / backfill the population step for 2024-10 → present.
Because the inputs are all present and joinable, a backfill should restore ~21 months of
planned-vs-actual coverage without any schema change.

One question we could not answer from outside, and it changes the diagnosis: **was a matching
strategy migration started in 2024-09?**
`journey_gtfs_ride_id` and `route_gtfs_ride_id` are marked *Deprecated* upstream, and a
deliberate migration would explain the September–December *decay* shape rather than an instant
stop (a clue in the same direction: SIRI parse failures dropped ~50× in 2024-07/08).
If a migration is in progress, the fix is to finish it rather than to restart the old job.

## What we did instead (workaround in the external analysis)

We reconstructed the link offline for 1,306 service days: a per-day greedy 1:1 assignment of
actual→planned within a stated time window, partitioned by (operator, line), computed locally
from `siri_ride` × `siri_route` × `gtfs_route` × `gtfs_ride`.

Validation before use: precision 99.88% on 780k pairs against stride's own stored matches across
10 stratified days in the healthy era, recovering 5,472 rides stride had missed, 98.4%
forced-unique.
Judge the workaround for yourself — if it is sound, the reconstruction is directly usable as a
backfill reference; if it is not, our downstream numbers inherit its bias.

Related known upstream bug: hasadna issue **#390** (`scheduled_start_time` drift — only the first
value is kept).
It is not the same defect, but it is why exact-time matching is lossy in the first place: on the
control day, exact matching recovers 74.3% where a ±5 min window recovers 92.0%.
