# The GTFS import keeps the previous release alongside the current one, doubling planned counts

**Severity:** blocks published statistics — planned-ride counts are ~2× too high on affected dates
**Affected component:** the GTFS import that writes `gtfs_ride` / `gtfs_route`
**Window observed:** 2023-02-13 → 2026-07-26, scattered, no era pattern (census over all 1,307 mirrored days)
**Reported by:** external analysis of the open data (BusAnalysis), 2026-07

## What happens

On affected dates, `gtfs_ride` holds **two near-complete daily schedules under a single
`gtfs_route.date`**: the same trip, the same route row, the same `start_time`, with `journey_ref`
suffixes stamping the current release *and* the previous one.
The import retained the old release instead of replacing it.

On clean days those two release stamps are complementary halves of one schedule.
On broken days each stamp is a full day — so the date carries roughly twice the real schedule.

## Evidence

- 85% of days are clean (planned/actual ratio within [0.9, 1.1]).
- **50 days exceed 1.5×**, and **36 exceed 1.8×**.
- Affected dates are scattered across the whole window with **no era pattern**.
- Every major operator sits at approximately 2.0× on affected days — it is not
  operator-specific.
- The actual-ride count stays flat through every doubled day, which is what rules out "SIRI
  coverage halved" as an alternative explanation.

Figure: `report/figures/findings/f8_divergence_curve.png` (planned vs actual rides per service
day, with affected days flagged).

Also refuted along the way, so nobody repeats the work: route_alternative duplication (there are
zero duplicate route rows per date), genuinely-new-trips, and operator concentration.

A related import symptom: rides with a null `start_time`, first seen 2023-01-04 and present on
134 of 1,307 days. This is longstanding, not a recent regression.

## Why it matters

A naive planned-vs-actual gap rate on an affected day approaches **50% phantom gaps** — the
"missing" buses were never really scheduled.
In our national series, the worst such day reads about **42%** against a corrected national
figure of about 5%.

Any consumer of stride's `gtfs_ride` or planned counts — including hasadna's own dashboards —
overstates planned service on these dates.

Two fixes that look plausible but do **not** work, both tested:

1. Filtering rides with a null `start_time` does not fix it — the stale copy keeps 69–98% of its
   times on some days.
2. Filtering on the `journey_ref` date suffix is **not safe** — on clean days that discards half
   of the legitimate schedule.

## Suggested fix

Make the import replace the previous release rather than retain it.

For existing data, the working correction is to **deduplicate on `(gtfs_route_id, start_time)`**,
keeping one row per group.
We validated this against anchor days: corrected counts land within 4.4% of actual, and three of
five anchor days within 0.4%.
It carries a known cost of about 0.5% on clean days, where genuinely bunched identical departures
get collapsed — a small bias in the *safe* direction (it slightly under-counts planned rides,
which slightly under-states the gap rate).

## What we did instead (workaround in the external analysis)

We applied that same `(gtfs_route_id, start_time)` deduplication in our extractor and
re-extracted 491 affected days.
Effect on one smoke-test day: gap count fell from 86,867 to 5,051.

Our national headline carries the ~0.5% clean-day cost as a stated downward bias rather than
silently.
