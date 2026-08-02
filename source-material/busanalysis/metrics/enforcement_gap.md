# Metric M1 - Enforcement Reality Gap

**Manager meaning: how much service failure the enforcement system does not see, does not price, and does not collect on.**  The state publishes the violation rates its fines are computed from; this puts the open-data rate beside them. `gap_pp` is OURS MINUS THEIRS in percentage points, so positive = failure the system is not capturing.

## Definition mapping (read before quoting any number)

MoT non-execution (electronic control, Golan 30/2024 Annex Z): no AVL departure+arrival signal, OR >20 min late, OR >=10 min early, OR departure after the next scheduled trip. OURS: a planned ride with no SIRI ride assigned within +-1800 s. Only the AVL leg is reachable from open data, and only as this proxy - the record holds no actual departure time, so the three punctuality legs are MISSING from our rate, which is therefore an under-count of their definition. delta_t_seconds is scheduled-vs-scheduled (exactly 0 on 98.6% of matched pairs) and is NOT a lateness measure.

So our rate covers ONE of MoT's four legs, and covers it by proxy. It is an under-count of their definition by construction, which makes a positive gap the conservative direction: if the open record already sees more failure than the enforcement system reports while missing three of its four legs, the true shortfall is larger.

## Ours against theirs, national, per half year

| period | metric | open data | MoT published | gap |
|---|---|---|---|---|
| 2023-H1 | early_plus_non_execution | 5.30% | n/a | n/a |
| 2023-H1 | late_5_20min | n/a | n/a | n/a |
| 2023-H2 | early_plus_non_execution | 6.11% | n/a | n/a |
| 2023-H2 | late_5_20min | n/a | n/a | n/a |
| 2024-H1 | early_plus_non_execution | 4.95% | 1.53% | +3.42 pp |
| 2024-H1 | late_5_20min | n/a | 2.67% | n/a |
| 2024-H2 | early_plus_non_execution | 4.02% | n/a | n/a |
| 2024-H2 | late_5_20min | n/a | n/a | n/a |
| 2025-H1 | early_plus_non_execution | 4.67% | n/a | n/a |
| 2025-H1 | late_5_20min | n/a | n/a | n/a |
| 2025-H2 | early_plus_non_execution | 5.32% | n/a | n/a |
| 2025-H2 | late_5_20min | n/a | n/a | n/a |
| 2026-H1 | early_plus_non_execution | 5.07% | n/a | n/a |
| 2026-H1 | late_5_20min | n/a | n/a | n/a |
| 2026-H2 | early_plus_non_execution | 2.46% | n/a | n/a |
| 2026-H2 | late_5_20min | n/a | n/a | n/a |

MoT's published lateness rate (2.67% in the 5-20 minute band, H1 2024) is shown with our rate BLANK on purpose. not measurable in open data: the matched record carries no actual departure time. delta_t_seconds is stride's scheduled_start_time minus the GTFS start_time and is exactly 0 on 98.6% of matched pairs, so it measures record agreement, not punctuality. Actual departure times need siri_ride_stop / siri_vehicle_location.

## Coverage holes, excluded from every rate above and stated here (finding F9)

4 operator(s) carry a whole-record non-execution rate at or above 99%: they have no SIRI feed at all, so that rate is a COVERAGE FACT, NOT PERFORMANCE. They are removed from the national and per-operator rates - averaging them in inflates the national figure by ~2.2 points (headline_stats.md: naive 7.36% -> 5.19% at +-5 min) - and they cannot be compared against MoT's published rates, which come from an instrument that only sees the operators it covers. The flag is measured over the WHOLE record, not per period, so an operator cannot flip in and out between halves.

| operator_ref | planned rides | non-exec rate | days present |
|---|---|---|---|
| 33 | 2,114,748 | 100.00% | 1,177 |
| 21 | 369,002 | 99.83% | 1,293 |
| 20 | 177,226 | 100.00% | 1,265 |
| 39 | 53,720 | 100.00% | 79 |

Total excluded: 2,714,696 scheduled rides. Under MoT's own rule every one of them is an automatic violation (no signal = non-execution), yet the volume persists and the operators appear in no published statistic - that is F9's point, and it is deliberately NOT priced in the fines bound below, which covers tracked operators only.

## What a raised non-execution rate is NOT, on its own

Three mechanisms raise this rate and it cannot separate them: buses genuinely not running, a SIRI feed blackout with the buses running normally (2024-03-23 recorded 15 actual rides nationally against a normal published schedule), and the matcher failing to pair a ride that ran. Candidate blackout days are listed in data/warehouse/audit/siri_outage_candidate_days.parquet - a CANDIDATE list, not a validated one, so no day is excluded here rather than filtered on an unproven rule. War periods (2023-H2, 2025-H1) mix the first two. Check any period before quoting it, and prefer the operator ranking within a period to the absolute level across periods.

## National bands per half year

`no match +-30min` is the metric. The three scheduled-time columns are a DIAGNOSTIC of the drift bug (hasadna issue #390, finding F6) seen from the matching side - they are NOT early or late departures.

| period | days | planned (tracked ops) | no match +-30min | same, all operators (naive) | records agree exactly | records disagree | disagree >10min |
|---|---|---|---|---|---|---|---|
| 2023-H1 | 181 | 15,544,898 | 5.30% | 7.50% | 94.54% | 0.16% | 0.05% |
| 2023-H2 | 184 | 15,921,349 | 6.11% | 8.44% | 93.15% | 0.73% | 0.13% |
| 2024-H1 | 182 | 16,176,863 | 4.95% | 7.22% | 94.78% | 0.27% | 0.09% |
| 2024-H2 | 184 | 17,014,809 | 4.02% | 6.22% | 95.75% | 0.23% | 0.08% |
| 2025-H1 | 181 | 16,349,305 | 4.67% | 6.77% | 94.77% | 0.56% | 0.11% |
| 2025-H2 | 184 | 17,039,031 | 5.32% | 7.40% | 94.51% | 0.17% | 0.07% |
| 2026-H1 | 181 | 15,614,931 | 5.07% | 6.93% | 94.02% | 0.91% | 0.18% |
| 2026-H2 | 29 | 2,774,625 | 2.46% | 5.23% | 97.40% | 0.14% | 0.07% |

## Per operator and half year (top 15 by planned rides)

| period | operator_ref | planned | non-exec rate | min-service surcharge implied |
|---|---|---|---|---|
| 2023-H2 | 3 | 3,465,934 | 3.36% | 0.1M |
| 2023-H1 | 3 | 3,426,846 | 3.57% | 0.1M |
| 2024-H1 | 3 | 3,321,391 | 2.91% | 0.1M |
| 2024-H2 | 3 | 3,308,559 | 2.56% | 0.0M |
| 2025-H2 | 3 | 3,295,412 | 3.98% | 0.2M |
| 2025-H1 | 3 | 3,173,938 | 3.19% | 0.1M |
| 2026-H1 | 3 | 3,050,634 | 2.74% | 0.1M |
| 2023-H1 | 18 | 2,122,681 | 7.97% | 0.6M |
| 2023-H2 | 18 | 1,969,485 | 9.34% | 0.7M |
| 2025-H2 | 18 | 1,914,022 | 6.74% | 0.5M |
| 2024-H2 | 18 | 1,878,616 | 3.54% | 0.1M |
| 2025-H1 | 18 | 1,829,093 | 5.14% | 0.3M |
| 2024-H2 | 15 | 1,804,106 | 3.58% | 0.1M |
| 2024-H1 | 18 | 1,796,151 | 3.23% | 0.1M |
| 2025-H2 | 15 | 1,773,860 | 4.54% | 0.2M |

The surcharge column is what the minimum-service-level clause implies at that half-year rate (10,000 NIS per 0.1 pp above 2.1%). It is the clause applied to OUR rate, not a figure the ministry levied.

## Implied fines - an ORDER-OF-MAGNITUDE BOUND, not an audit

The one fully documented banded ladder (Golan cluster tender 30/2024 Annex Z, CPI base Sep 2024) applied to our own daily non-execution counts. No late or early component is computed: those ladders are documented at their endpoints only, and the quantities they price cannot be measured from open data. Below a 1% DAILY non-execution share the price is ZERO, so the `free` column is real failure that carries no agreed compensation at all.

| year | non-exec events | of them in the free band | implied NIS | published levied NIS |
|---|---|---|---|---|
| 2023 | 1,796,837 | 2.03% | 286.7M | n/a |
| 2024 | 1,485,278 | 3.48% | 226.7M | 159.0M |
| 2025 | 1,669,685 | 4.08% | 259.0M | 184.9M |
| 2026 | 859,182 | 3.86% | 132.6M | n/a |

The published totals bundle safety, cleanliness and discrimination violations this reconstruction cannot see; cluster tariff schedules differ; approved event-log exemptions silently remove events; and the historical bid multiplier (up to x5) may or may not still apply. A mismatch under x5 in either direction proves nothing. `fines_benchmark.parquet` carries the published figures with their sources.
