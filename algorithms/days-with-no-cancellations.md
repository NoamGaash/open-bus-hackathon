# Days With Zero Cancellations — "Days with zero cancellations"

**Author:** orion (`author="orion"` in the registry)
**Code:** [analyses/days_with_no_cancellations.py](../analyses/days_with_no_cancellations.py) and core module [orion/days_with_no_cancellations.py](../orion/days_with_no_cancellations.py)
**Cards:** `days-with-no-cancellations` ("Days with zero cancellations")
**Data:** Stride `/rides_execution/list` (Option A - verified live)

## What it answers

- **On what fraction of service days did the line run with absolutely zero cancellations?** Evaluates reliability over a 15-day window, treating a day with $\ge 1$ cancellation as a failure (score 0) and a fully-operated day as a success (score 1).

## Algorithm

1. **Resolve Windows:** Sets a 15-day service-date window ending at yesterday (to prevent partial-day results from today looking like a wave of cancellations).
2. **Resolve Live Line Refs:**
   - Disambiguates `route_short_name` to its active `(line_ref, operator_ref)` pairs for the exact scoring window.
   - A single bus route number corresponds to multiple variants (up to 8 variants for Line 480 today). The set is time-varying; therefore, mapping is resolved dynamically rather than using a cached layout.
3. **Fetch Ride Executions:** `/rides_execution/list` retrieves the planned and actual start times for all resolved variant pairs.
4. **Clean and Deduplicate:**
   - Filters out rows with null `planned_start_time` (~3–6% of pings), which represent untracked actual rides.
   - Deduplicates departures on `planned_start_time` to prevent duplicate physical runs (which sometimes emit multiple `gtfs_ride_id`s) from creating false cancellation indicators.
5. **Classify and Score:**
   - For each service date (using `Asia/Jerusalem` timezone to handle Israel's daylight saving transitions), evaluates the cancellation status: a ride is cancelled if `actual_start_time` is null.
   - Evaluates each day: a day is "good" (1) if it has scheduled departures and 0 cancellations. If scheduled departures $>0$ and cancellations $\ge 1$, the day is "bad" (0). Days with zero scheduled departures are excluded.
   - `score = good_days / total_scheduled_days`.
6. **Operator Level View:** If no line filter is active, aggregates scores across the top 15 lines of a selected operator (e.g., Superbus).

## Reasoning

**Why `/rides_execution/list` instead of other endpoints.** Orion performed a rigorous comparative analysis of three API options:
- **Option A (`/rides_execution/list`):** Verified live. Provides individual ride execution rows. A null `actual_start_time` represents a cancellation.
- **Option B (`/gtfs_rides_agg/list`):** Ruled out. The server-side pre-aggregated column `num_actual_rides` returns **0 network-wide** across all dates (server-side bug), making aggregate cancellation detection impossible.
- **Option C (GTFS vs. SIRI Manual Diff):** Heavy and complex. Requires manual set diffs of stop timetables and GPS traces, generating millions of rows. Option A is far lighter and cleaner.

## Findings

### 1. `/gtfs_rides_agg` is broken network-wide — **confidence: High**
Independently confirmed by multiple team members: `num_actual_rides` is set to 0 for every row in the aggregate feed, even when live ride-level pings are fully populated in `/rides_execution/list`.

### 2. Line mapping sets are highly unstable over time — **confidence: High**
For example, Line 480 of Egged was mapped to 2 `line_ref`s in November 2025 but expanded to 8 `line_ref`s by July 2026. This proves that caching line-to-ref maps causes massive under-counting in historical analysis; ref-resolution must occur dynamically.

## Criticism

**Highly punitive for frequent lines.** A binary daily scoring model (any cancellation $\ge 1 = 0$) penalizes high-frequency lines disproportionately. A line running 100 times a day has a 99% probability of losing at least one run due to operational friction, giving it a score of 0. Conversely, a sparse line running twice a day is much easier to score a clean 1. A volume-weighted execution rate (e.g., total operated / total planned) would provide a fairer comparison.
