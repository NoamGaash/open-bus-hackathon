# Days with zero cancellations — a per-line quality score

**Author:** orion (group), integrated via PR #1
**Code:** [orion/days_with_no_cancellations.py](../orion/days_with_no_cancellations.py) (the analysis + CLI), [analyses/days_with_no_cancellations.py](../analyses/days_with_no_cancellations.py) (the dashboard card)
**Method write-up:** [orion/days_with_no_cancellations.md](../orion/days_with_no_cancellations.md) — a rigorous three-option data-availability study, the best piece of API archaeology in the repo
**Card:** `days-with-no-cancellations`
**Data:** Stride `/rides_execution/list`

## What it answers

> For a given bus line, score = (days in the last 15 with **zero** cancellations) /
> (days scored).

A day with ≥1 cancellation counts 0; a fully-operated day counts 1. Deliberately
harsh: it asks "did this line have a *clean* day", not "what fraction of rides ran".
One cancellation ruins the day, which is closer to how a passenger experiences a
line than a 99.4% completion rate is.

Three methods were specified; **1 and 2 are implemented**:

- **Method 1** — one line → a score, plus a per-day breakdown.
- **Method 2** — every line of one operator, worst first, as a bar chart.
- **Method 3** (compare operators) — specified, not built.

## Algorithm

There is **no cancellation flag in Stride**. A cancellation is *inferred*: a ride
planned in the GTFS timetable for which no actual activity exists.

1. **`score_window(days=15, end=None)`** — default window ends **yesterday**. Today
   is excluded because its actuals are still landing, so a live day looks like a
   wall of cancellations.
2. **`line_variants()`** — resolve `route_short_name` → the set of
   `(line_ref, operator_ref)` pairs **for this window**.
3. **`rides_execution()`** — page `/rides_execution/list` per variant. All four
   filters (`line_ref`, `operator_ref`, `date_from`, `date_to`) are required; there
   is no `order_by`.
4. **`daily_report()`** — the core:
   - Drop rows with no `planned_start_time` (unplanned rides, ~3–6%).
   - Key on `(line_ref, operator_ref, planned_start_time)` and let **any** observed
     actual mark the departure operated:
     `operated[key] = operated.get(key, False) or bool(row["actual_start_time"])`.
   - Bucket by **Israel service date** via `ZoneInfo("Asia/Jerusalem")`.
   - Re-filter to the window — the API's service-date filter is fuzzy at the edges.
   - Per day: `good = (cancelled == 0)`.
5. **Score** = `report["good"].mean()`, or **`None`** if the line had no planned
   rides at all — "unknown", explicitly not "perfect".
6. **Method 2** fans out over every line of an operator and flags
   `no_actuals = (cancelled == planned)` as unscoreable.

## Reasoning

The whole design is driven by five caveats, each confirmed live and each with a
matching `# caveat N` comment in the code:

| # | Caveat | What the code does |
|---|---|---|
| 1 | A "line" is many `line_ref`s (480 → **2** refs in Nov 2025, **8** in Jul 2026) and the set is time-varying | Resolve per window; never cache a mapping |
| 2 | `planned_start_time` is null on **3–6%** of rows — actuals with no plan, the *mirror image* of a cancellation | Filtered out before the day loop |
| 3 | Duplicate planned starts — 2026-07-26 returned **259 rows for 127 distinct start times** (some ×4) under 255 distinct `gtfs_ride_id`s | Key on the departure, OR the actuals together |
| 4 | `actual_start_time` is a **binary flag, not an observed time** | Used only for the null check |
| 5 | A fixed UTC+3 spills a 16th day into a 15-day November window | Real `ZoneInfo("Asia/Jerusalem")` |

**Why `or` rather than `all`** for caveat 3: one physical departure emitted under
several ride ids means a duplicated row with a null actual would otherwise invent a
phantom cancellation. Let any observed actual win.

**Why days with no planned rides are dropped entirely.** They are neither good nor
bad and must not land in the denominator — a line not scheduled on a Saturday is
not a line that failed on a Saturday.

**Why `no_actuals` lines are drawn grey and hatched.** Not one actual in 15 days is
an ingestion gap, not a company that cancelled every bus it ever scheduled. The
chart gives it a visually distinct, deliberately unreadable bar at 1.0 rather than
a score of 0.00 that a reader would take at face value.

## Findings

### 1. `/gtfs_rides_agg`'s `num_actual_rides` is 0 network-wide — **confidence: High**

The headline. Measured across both `/list` and `/group_by`, on every date sampled
from Nov 2025 → Jul 2026:

| Date | Σ planned | Σ actual |
|---|---|---|
| 2026-07-01 | 3,498 | **0** |
| 2026-06-15 | 3,510 | **0** |
| 2026-04-01 | 3,227 | **0** |
| 2025-11-01 | 3,927 | **0** |

**Not lag** — the control is decisive: line 2259 on 2026-07-29 shows
`total_actual_rides=0` in the aggregate while `/rides_execution/list` shows real
`actual_start_time` values and zero cancellations for the same line and date.
Actuals exist at ride level; they are simply not rolled into the aggregate. Nine
months of dates, two endpoints, and a control that rules out the alternative
explanation. Independently confirmed by
[service-violations](service-violations.md).

The consequence is not academic: **the aggregate reports 100% cancellation
everywhere.** Anything built on it is wrong.

### 2. `/rides_execution/list`'s `actual_start_time` is a flag, not a time — **confidence: High**

For **all 1,726** non-null rows sampled, `actual_start_time == planned_start_time`
to the second. Fine for the null check this method needs; it means the endpoint can
**never** be used for delay or punctuality work, and "actual" here is not a
ground-truth departure time. A census over the sample, not an inference.

### 3. A line number maps to a time-varying set of `line_ref`s — **confidence: High**

Line 480: **8** refs in Jul 2026 (7020, 7022, 7023, 7024, 7028, 7033, 7034, 10958,
all operator 3), **2** in Nov 2025. Directly enumerated. Corroborated independently
by [schedule-adherence](schedule-adherence.md)'s stop-signature mismatches.

### 4. `planned_start_time` is null on 3–6% of `/rides_execution/list` rows — **confidence: High**

4–8 per day on line 2259. These are actuals with no matching plan. Measured over
multiple days on a real line; both a rate and an absolute count.

### 5. The same departure appears under several `gtfs_ride_id`s — **confidence: High**

2026-07-26: 259 rows, 127 distinct start times, some ×4, 255 distinct ride ids.
Corroborated by `lihay7/BusAnalysis` **F6**, which measures **2.56% surplus
duplicate rows** over a full 116.3M-row census, quadrupling since 2023, and traces
it to the `scheduled_start_time` drift bug (hasadna issue #390).

> Honest note from the write-up: in every sample checked, the duplicates all had
> actuals filled, so this **has not yet bitten** — but the shape is live and the
> code guards against it.

### 6. Israel is UTC+2 in winter and a hardcoded +3 breaks the window — **confidence: High**

A fixed offset spills a 16th day into a 15-day November window. Directly
reproducible. **[schedule_adherence_average.py:61](../analyses/schedule_adherence_average.py#L61) still has this bug.**

### 7. Line 480's score is 0.53 over 15 days (7 cancellations, 1,355 rows, 8 variants); 0.81 for 2025-11-01..15 — **confidence: Medium**

A real end-to-end result. Medium because it is one line over one window, and
because the score's denominator depends on the caveat-1 variant resolution being
complete for that window.

### 8. Per-line and per-operator scores generally — **confidence: Low to Medium**

The card's actual output. Confidence depends entirely on whether SIRI ingestion was
healthy for that line and window — which is exactly what the method cannot see.
The `no_actuals` flag catches the total-blackout case; it cannot catch a line whose
feed was 30% degraded, which reads as a genuinely bad score.

## Criticism

**A feed outage is indistinguishable from a bad day, and this is the method's
central weakness.** The write-up names it and proposes a sanity floor ("skip days
where the operator has ~zero actuals across all lines") — **the floor was not
implemented.** Only the all-or-nothing `no_actuals` flag exists. A day when
ingestion was half-broken scores as a genuinely cancelled day, and the card will
say so with a confident red bar.

**Partial rides count as fully operated.** A ride that started and died mid-route
has an `actual_start_time`, so it scores as a success. Only Option C (GTFS vs SIRI
diff) could catch it, and it was not built. The score therefore measures *departure*
completeness, not *service* completeness, and the card's title does not say so.

**The 15-day window is asserted, not derived.** It comes from the original
motivation comment. There is no analysis of whether 15 days is enough to separate
lines, and with a binary per-day metric the score can only take 16 distinct values —
so lines cluster heavily and small differences in rank are not meaningful.

**Method 2 is capped at 15 lines in the card** (`max_lines=15`) and sorts lines by
`(len(name), name)` before truncating — so an operator's *shortest-named* 15 lines
are scored, an arbitrary selection presented as an operator overview. The cost that
forces this is real (~1,240 line_refs for אגד), but the selection bias is not
disclosed on the card.

**Method 3 was specified and never built,** so no cross-operator comparison exists —
which is the comparison a regulator would actually want.

**The dashboard card hardcodes `days_back = 15`** and ignores the dashboard's date
range except as an end-date clamp, so the global filter bar silently does less than
a user expects.

**Score `None` vs `0.0` is handled correctly in the library and lost in the card.**
`days_wo_cancellation_score` returns `None` for "no planned rides", with a docstring
warning callers not to average it in as 1.0 — but the card path uses `daily_report`
directly and shows an empty-state, so the distinction survives. Worth preserving if
Method 3 is ever built, since that is precisely where averaging would happen.
