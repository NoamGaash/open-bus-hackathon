# Data availability check — Method 1 (`days_wo_cancellation_score()`)

Goal of method 1: for a given bus line, score = (# days in the last 15 with **zero** cancellations) / (# days scored). A day with ≥1 cancellation counts 0, a fully-operated day counts 1.

## Which data is needed

There is no direct "cancellation" flag in Stride. A cancellation is **inferred**: a ride that was *planned* in the GTFS timetable but for which *no actual* activity exists. There are three ways to obtain that signal from the API — listed below from simplest to heaviest.

---

## Option A — `/rides_execution/list` (recommended for Method 1) ✅ VERIFIED

Purpose-built for planned-vs-actual at ride level. One endpoint gives everything.

- **Params (per the OpenAPI schema):** `line_ref` **(required, int)**, `operator_ref` **(required, int)**, `date_from` **(required)**, `date_to` **(required)**, `limit`, `offset`, `get_count`. There is **no `order_by`** and no other filter — all four filters must be supplied on every call.
- **Fields returned:** `planned_start_time`, `actual_start_time`, `gtfs_ride_id`. That is the whole model.
- **Cancellation signal:** a row where `actual_start_time` is **null** = that planned ride did not run.
- **Granularity:** one row per planned ride.
- **Verified live (2026-07-30):** line 2259 / operator 5 / 2026-07-15..29 → 1,790 rows, **6 nulls across 4 distinct days** → score 10/15. The signal is real and non-degenerate (contrast Option B). Date filter is by **Israel service date** (a `date_from=2026-07-29` row shows `planned_start_time` 2026-07-28 21:00 UTC = local midnight).
- **Full end-to-end run:** line 480, all 8 variants, 15 days → 1,355 rows over 8 requests, 7 cancellations, score 0.53. Historical windows work too (2025-11-01..15 → 0.81).

```python
# 1. resolve the line -> (line_ref, operator_ref) pairs FOR THIS WINDOW (see caveat below)
routes = stride.get('/gtfs_routes/list', {
    'route_short_name': '480', 'date_from': '2026-07-29', 'date_to': '2026-07-29',
})
pairs = {(r['line_ref'], r['operator_ref']) for r in routes}   # -> 8 pairs for line 480

# 2. one paged call per pair; union the rows
for line_ref, operator_ref in pairs:
    rows = stride.iterate('/rides_execution/list', {
        'line_ref': line_ref, 'operator_ref': operator_ref,
        'date_from': '2026-07-15', 'date_to': '2026-07-29',
    })
    # drop rows with no planned_start_time (see caveat), dedup on planned_start_time,
    # bucket by Asia/Jerusalem date
# per day: cancelled = [r for r in day_rows if not r['actual_start_time']]
# day_is_good = len(cancelled) == 0
```

Why it matches Method 1: the null check is an unambiguous per-ride cancellation, and query weight is trivial (one request per line variant per window, nowhere near the 15,000-row cap).

### Caveats specific to A (all confirmed live, all must be handled)

1. **`line_ref` is per direction+alternative, not per line.** "Line 480" is **8** distinct `line_ref`s today (7020, 7022, 7023, 7024, 7028, 7033, 7034, 10958 — all operator 3), each needing its own call, unioned per day. The set is **time-varying**: the same line had only **2** line_refs in Nov 2025. Resolve it via `/gtfs_routes/list` *for the window being scored* — do not cache one mapping and reuse it.
2. **`planned_start_time` is null on 3–6% of rows** (4–8/day on line 2259). These are actuals with no matching plan — the mirror image of a cancellation. They cannot be bucketed to a service date; filter them out before the day loop or it miscounts (or crashes on the date parse).
3. **Duplicate planned starts exist.** 2026-07-26 returned 259 rows for 127 distinct start times (some ×4) under 255 distinct `gtfs_ride_id`s — one physical departure emitted under several ride ids. Dedup on `planned_start_time` before counting, or a duplicated row with a null actual becomes a phantom cancellation. (In every sample checked the duplicates all had actuals filled, so it hasn't bitten yet — but the shape is live.)
4. **`actual_start_time` is a binary flag, not an observed time.** For all 1,726 non-null rows sampled, `actual_start_time == planned_start_time` to the second. Fine for the null check; but this endpoint can never be reused for delay/punctuality work, and "actual" here is not a ground-truth departure time.
5. **Use real `Asia/Jerusalem`, not a fixed UTC+3.** A hardcoded +3 spills a 16th day into a 15-day November window — Israel is UTC+2 in winter. The "Israel service date" note above only holds under summer time.

---

## Option B — `/gtfs_rides_agg/list` — ❌ NOT VIABLE on this deployment

Pre-aggregated planned-vs-actual counts. On paper the lightest option (one row per route×hour). **In practice it cannot detect cancellations on this API instance: `num_actual_rides` is always 0.**

- **Params:** `date_from` (required), `date_to` (required), `exclude_hours_from`, `exclude_hours_to`, `limit`, `offset`. No `line_ref`, `operator_ref`, or `gtfs_route_id` filter on `/list`.
- **Fields returned:** `gtfs_route_id`, `gtfs_route_hour`, `num_planned_rides`, `num_actual_rides`, `operator_ref`.
- **Cancellation signal (broken):** `num_planned_rides − num_actual_rides`.

**Live check (2026-07-30) — blocker:** across both `/list` and `/group_by`, on every date sampled from Nov 2025 → Jul 2026, `num_actual_rides` = **0 for every line, network-wide** while `num_planned_rides` is populated. The actual-rides column is never filled in this deployment, so the signal reports 100% cancellation everywhere.

| Date | Σ planned | Σ actual |
|---|---|---|
| 2026-07-01 | 3,498 | **0** |
| 2026-06-15 | 3,510 | **0** |
| 2026-04-01 | 3,227 | **0** |
| 2025-11-01 | 3,927 | **0** |

Not lag: line 2259 / 2026-07-29 shows `total_actual_rides=0` in the aggregate, yet Option A shows real `actual_start_time` values and 0 cancellations for the same line/date — actuals exist at ride level, just not rolled into the aggregate.

*(Correction, 2026-07-30: an earlier version of this doc claimed A returns 219 planned rows for that line/date vs the aggregate's 123, and used the mismatch as a second strike against B. A actually returns **126**, which matches the aggregate closely. The planned counts agree; B is ruled out solely because `num_actual_rides` is never populated.)*

**Silver lining (didn't rescue B):** `/gtfs_rides_agg/group_by` accepts `group_by=` any of `gtfs_route_date, gtfs_route_hour, operator_ref, day_of_week, line_ref`, returning `route_short_name`/`route_long_name` + `total_planned_rides`/`total_actual_rides`. So a clean per-line, per-day planned rollup *is* available (the earlier "no `line_ref` filter" caveat was wrong) — but with actuals stuck at 0 it still can't score cancellations.

```python
# What was tried:
rows = stride.get('/gtfs_rides_agg/group_by', {
    'date_from': '2026-07-29', 'date_to': '2026-07-29',
    'group_by': 'line_ref,gtfs_route_date',
})
# -> line 2259: total_planned_rides=123, total_actual_rides=0   (actual always 0)
```

---

## Option C — GTFS timetable vs SIRI diff (heaviest; only for degraded-ride detection)

Build the planned start-set and the actual start-set separately and diff them. This is the manual method demonstrated in the `compare gtfs planned vs siri actual` notebook.

- **Line identity (once):** `/gtfs_routes/list` with `route_short_name`, `operator_refs`, `agency_name`, `date_from`/`date_to` → `line_ref`, `operator_ref`.
- **Planned rides:** `/route_timetable/list` with `line_refs`, `planned_start_time_date_from`/`..._date_to` → distinct set of `gtfs_line_start_time`.
- **Actual rides:** `/siri_rides/list` (one row per ride; lighter) or `/siri_vehicle_locations/list`, filtered by `siri_route__line_refs`, `siri_route__operator_refs`, `scheduled_start_time_from`/`..._to` → distinct set of `scheduled_start_time`.
- **Cancellation signal:** `cancelled = planned_starts − actual_starts` (match on scheduled start-time).
- **Granularity:** one row per timetable stop / per SIRI location ping — the heaviest pull.
- **Only reason to use it:** it carries the full vehicle traces, so it can additionally flag *degraded* rides (started but died mid-route), which A and B cannot see.

---

## Comparison

| | A · `/rides_execution/list` | B · `/gtfs_rides_agg` | C · GTFS vs SIRI diff |
|---|---|---|---|
| Granularity | 1 row per ride | 1 row per route×hour (or per-line/day via group_by) | 1 row per stop / location ping |
| Rows for 1 line, 15 d | ~1,400–1,800 (measured) | ~hundreds | thousands (heaviest) |
| Cancellation signal | `actual_start_time` is null | `num_planned − num_actual` | planned start-set − actual start-set |
| Filter by line? | ✅ `line_ref` + `operator_ref` (both **required**; 1 call per line variant) | ⚠️ client-side (group_by `line_ref`) | ✅ direct |
| Matches Method 1 signature | ✅ after a `/gtfs_routes` line_ref lookup | ➖ needs client-side filter | ➖ two queries + manual diff |
| Detects fully-cancelled | ✅ | ❌ **actuals always 0** | ✅ |
| Detects degraded/partial | ❌ | ❌ | ⚠️ possible |
| Usable for delay/punctuality | ❌ `actual == planned` always | ❌ | ✅ |
| Query weight | light (8 requests for line 480 / 15 d) | lightest (if it worked) | heaviest |
| Verified working | ✅ live 2026-07-30, non-degenerate | ❌ **num_actual=0 network-wide** | notebook-confirmed |

**Recommendation:** Method 1 → **A**, confirmed by a live end-to-end run. Option B is ruled out on this deployment (actuals never populated), so Methods 2 & 3 (per-operator / cross-operator) also fall back to **A**. A is far lighter than the doc originally assumed, but it fans out per `line_ref`: Method 2 needs *every* line variant of an operator resolved from `/gtfs_routes/list` first, which is where the real request count lives. Use `/gtfs_rides_agg/group_by` only for planned-ride denominators. Reserve **C** for when degraded-ride detection or actual timing is wanted.

---

## The 15-day loop (applies to whichever option)

- Iterate the 15 service dates; derive per-day planned + cancelled counts.
- `score = (# good days) / (# scored days)`, where a good day has zero cancellations.
- Exclude days with **no planned rides at all** (line not in service / no timetable) from "# scored days" so they count as neither good nor bad.

## Edge cases / caveats to decide on

- **Matching key / timezone:** compare planned vs actual on scheduled *start*-time in the same timezone; the `date_from` filter is by Israel service date (see Option A note). Bucket days with `zoneinfo.ZoneInfo("Asia/Jerusalem")` — a fixed UTC+3 offset breaks on winter dates (A-caveat 5).
- **Partial rides:** a ride that started but died mid-route still has an `actual_start_time`, so A and B count it as operated. Only Option C can flag it. Note A cannot even tell you *when* it started — `actual_start_time` always equals `planned_start_time` (A-caveat 4).
- **Unplanned rides:** A returns rows with a null `planned_start_time` (~3–6%/day). Not cancellations — the opposite. Drop them (A-caveat 2).
- **Missing SIRI ingestion vs a real cancellation:** a day where actual data is globally absent (feed outage) looks like 100% cancellations. Consider a sanity floor (e.g. skip days where the operator has ~zero actuals across all lines).
- **`line_ref` / route variants:** one line number maps to several variants (line 480 → 8 today, 2 in Nov 2025) — resolve them per window and aggregate carefully so a variant that simply wasn't scheduled that day isn't read as a cancellation. Also dedup on `planned_start_time`: the same departure can appear under several `gtfs_ride_id`s (A-caveats 1 and 3).
- **Row limits:** a single request caps at 15,000 (server abuse guard); use `stride.iterate` (pages within that limit) rather than a large single `limit`.
