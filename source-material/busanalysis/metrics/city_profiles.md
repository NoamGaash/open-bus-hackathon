# Metric 6.5 — per-city service profiles

Every locality that a line departs from in route snapshot `routes_full_2025-06-11.parquet`, over 1,306 service days and 116,435,811 scheduled rides on covered operators. 270 localities carry attributed volume; 97.5% of national covered planned volume could be attributed to an origin locality at all, and the rest belongs to `route_mkt` values absent from that one snapshot.

## The coverage cut, first — because it decides every rate below

An operator is excluded when its whole-window matched share at ±3600 s is below 1%: it emits no usable SIRI signal, so all of its scheduled rides would score as "gaps" that measure the instrument rather than its buses (finding F9). The set is derived from the mart, not hardcoded.

| excluded operator_ref | name | planned rides | matched share ±3600 s |
|---|---|---|---|
| 33 | Cable Express | 2,114,748 | 0.00% |
| 21 | Kfir | 369,002 | 0.17% |
| 20 | Carmelit | 177,226 | 0.00% |
| 39 | Dan Netivim | 53,720 | 0.00% |

4 operator(s) cut, 2,714,696 scheduled rides; 35 operator(s) kept, 116,435,811 scheduled rides. The cut removes 2.28% of all scheduled volume in the mart.

**Against the frozen headline, reconciled exactly.** `headline_stats.md` states **5.19% at ±5 min over 116.4 M rides on 34 covered operators**. This module's derived cut keeps **35 operators and 116,435,811 rides at 5.197%**. The whole difference is **one operator: ref 91, Metro Kav Taxis** — a shared-taxi concession with 16,077 scheduled rides, which the frozen pass also cut and this module keeps. Cutting it as well gives 5.186%, i.e. exactly the frozen 5.19%; keeping it gives 5.197%, i.e. 5.20%. **The two figures are the same measurement on populations differing by 0.014% of national volume**, and the gap is a rounding boundary, not a disagreement.

This module keeps ref 91 because it is **18.3% covered** by SIRI — far above the 1% coverage floor — so cutting it would not be a coverage-hole exclusion but a mode exclusion (it is a shared taxi, not a bus). Mode is handled by the `planned_non_bus` column instead, so the two reasons for dropping an operator never get conflated into one silent filter. Anyone quoting 5.19% and anyone quoting 5.20% is right; state which population you used.

## Highest gap rate at ±5 min (cities with ≥ 100,000 planned rides)

The volume floor is **100,000 planned rides over the whole window**, stated because without it both ends of this ranking are hamlets with a few hundred rides and the list says nothing. 99 of 270 localities clear it.

| city | gap rate ±5 min | planned rides | lines | share of national |
|---|---|---|---|---|
| בית דגן | 17.77% | 299,123 | 6 | 0.26% |
| אבו סנאן | 9.91% | 122,541 | 2 | 0.11% |
| עראבה | 9.84% | 103,153 | 1 | 0.09% |
| מודיעין עילית | 9.41% | 2,117,576 | 33 | 1.82% |
| מטה בנימין | 9.20% | 167,773 | 6 | 0.14% |
| בת ים | 9.10% | 166,629 | 2 | 0.14% |
| טמרה | 7.48% | 319,719 | 8 | 0.27% |
| חריש | 7.09% | 272,337 | 7 | 0.23% |
| יגור | 6.59% | 128,776 | 1 | 0.11% |
| רמלה | 6.49% | 586,428 | 24 | 0.50% |

## Lowest gap rate at ±5 min (same floor)

| city | gap rate ±5 min | planned rides | lines | share of national |
|---|---|---|---|---|
| רמת רחל | 2.49% | 151,108 | 1 | 0.13% |
| כפר מנדא | 2.55% | 119,146 | 5 | 0.10% |
| דימונה | 2.63% | 609,882 | 16 | 0.52% |
| קרית גת | 2.65% | 823,794 | 24 | 0.71% |
| סאג'ור | 2.67% | 131,095 | 2 | 0.11% |
| נצרת | 2.69% | 1,360,324 | 32 | 1.17% |
| אזור | 2.75% | 307,735 | 5 | 0.26% |
| נחף | 2.77% | 102,705 | 1 | 0.09% |
| סח'נין | 2.78% | 358,741 | 8 | 0.31% |
| נתניה | 2.81% | 3,298,080 | 70 | 2.83% |

## Tel Aviv-Yafo versus Be'er Sheva versus Tiberias, in plain sentences

1. Tel Aviv-Yafo (תל אביב יפו) is the largest of the pinned origins with 12,584,412 scheduled rides over the window (10.8% of all covered national volume), and 4.23% of them have no matching real departure at ±5 min.
2. Be'er Sheva (באר שבע) schedules 0.37 times Tel Aviv-Yafo (תל אביב יפו)'s volume (4,640,627 rides) and misses 4.68% — worse by 0.45 percentage points.
3. Tiberias (טבריה) schedules 0.13 times Tel Aviv-Yafo (תל אביב יפו)'s volume (1,589,211 rides) and misses 3.84% — better by 0.39 percentage points.
4. Ordered best to worst at ±5 min: Tiberias (טבריה) 3.84%, Tel Aviv-Yafo (תל אביב יפו) 4.23%, Be'er Sheva (באר שבע) 4.68%.
5. Before reading any of that as a municipal ranking: the rate is attributed to the locality a line DEPARTS from, the sparse/dense columns show how much of the spread is a density effect the matcher partly creates, and these cities do not have the same operator mix — so this is a comparison of route populations, not of city halls.

## Caveats

- **Attribution is by route ORIGIN city.** A line's whole missing count lands on the locality it departs from, not on wherever along the route the ride actually failed. A Tel Aviv-origin route serves many cities; these rows are not a statement about service *inside* the named city.
- **The route-to-city map comes from ONE GTFS snapshot date** (named in the run output), applied across the whole window. Lines added, retired or re-pathed outside that date are missed or mis-assigned.
- **A two-direction line has one `route_mkt`** whose two origins are each other's destinations; the lowest-`id` row wins, deterministically. Roughly 1,542 of 2,682 `route_mkt` values in the 2025-06-11 snapshot are ambiguous this way, so an intercity pair's volume is attributed wholly to one end.
- **Operators with no SIRI feed are excluded** (finding F9). Their scheduled rides score as 100% "gap" because nothing tracks them — a coverage fact, not skipped service. Cities served mainly by such an operator therefore have **no service statistics at all**, which is itself the finding; they are absent here rather than shown as failing.
- **A high gap rate is not proof an operator or a municipality is failing.** Sparse service raises it partly mechanically (fewer anchors for the matcher), which is why the sparse/dense split is reported beside the headline rate rather than under it.
- **Rail is inside the denominator** (`operator_ref` 2), matching the frozen national figure; `planned_non_bus` per city says how much of a city's volume is not a bus.
- **Δt is drift, not delay.** `Δt` is `actual_scheduled_start_time - planned_start_time`: how far the actual record's own copy of the scheduled start drifted from the planned record's (hasadna issue #390). **It is not lateness** — both sides are scheduled times. A large drift means the published exact-equality "didn't run" figure is most wrong there. Lateness against the timetable is a different metric and is not in this directory.
- **`p85_delta_t_s_3600s_planned_weighted_median_of_line_day_p85` is not a pooled 85th percentile.** It is the planned-weighted median of per-line-day p85 drift values (pairs within ±3600 s), no interpolation, because a pooled percentile cannot be recovered from per-group percentiles without the underlying pairs. 99.2% of line-days have zero drift, so this column is 0 s for almost every city; `planned_share_line_days_p85_drift_nonzero` is the one that discriminates.
