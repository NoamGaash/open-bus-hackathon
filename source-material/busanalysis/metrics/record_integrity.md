# Metric M3 - Record Integrity Index

**Manager meaning: can the ministry measure its own network at all?**  This is the precondition metric - the one that has to be read before any planned-vs-actual number is believed.  0-100, monthly, national; 100 means the record is intact for that month.

It scores the DATA, not the buses.  Three of the four components measure stride (hasadna's database) and one measures stride's GTFS import; none of them measures a vehicle or an operator.

## The four components

| component | weight | grain | source |
|---|---|---|---|
| linkage | 0.25 | national month (measured months only) | FINDINGS_LEDGER.md F1 month scans, restated as STRIDE_STORED_LINKAGE |
| uniqueness | 0.25 | national month, and per operator x month | data/warehouse/audit/duplication_by_operator_month.parquet (F6) |
| schedule_cleanliness | 0.25 | national month | data/warehouse/audit/divergence_daily.parquet, flagged by viz.findings_charts.flag_duplicated_schedule_days (F8) |
| enrichment_availability | 0.25 | national month | data/warehouse/audit/transmission_by_operator_month.parquet (F7) |

Full caveats per component: `components.parquet`.

## Components at zero (a month that cannot be measured on that axis)

| component | months at exactly 0 |
|---|---|
| linkage | 2025-03, 2025-06, 2025-12, 2026-03, 2026-06..2026-07 |
| enrichment_availability | 2025-01..2026-04 |

And at or below 0.05 - the same outage read at the two decimal places the findings are written in (99.99% null is not literally zero but is the same broken month):

| component | months at or below 0.05 |
|---|---|
| linkage | 2024-10, 2024-12, 2025-03, 2025-06, 2025-12, 2026-03, 2026-06..2026-07 |
| enrichment_availability | 2024-12..2026-05 |

## Whole record

| months | index min | index median | index max | months with all 4 components |
|---|---|---|---|---|
| 43 | 47.8 | 65.5 | 99.5 | 11 |

32 of 43 months carry a PARTIAL index (fewer than four components measured). `integrity_index` is the mean over the components that exist; `integrity_index_strict` is null on those months. The missing component is almost always `linkage`: stride's stored coverage was scanned for 11 months only, and nothing between two scanned months may be inferred from them.

## Monthly series

| month | index | strict | n comp | linkage | uniqueness | sched clean | enrichment | achievable link |
|---|---|---|---|---|---|---|---|---|
| 2023-01 | 99.5 | n/a | 3 | n/a | 98.6 | 100.0 | 100.0 | 99.57% |
| 2023-02 | 99.5 | n/a | 3 | n/a | 98.5 | 100.0 | 100.0 | 99.43% |
| 2023-03 | 99.5 | n/a | 3 | n/a | 98.5 | 100.0 | 100.0 | 99.34% |
| 2023-04 | 99.4 | n/a | 3 | n/a | 98.3 | 100.0 | 100.0 | 98.91% |
| 2023-05 | 98.9 | n/a | 3 | n/a | 96.8 | 100.0 | 100.0 | 99.04% |
| 2023-06 | 98.9 | n/a | 3 | n/a | 97.0 | 100.0 | 99.7 | 99.08% |
| 2023-07 | 99.0 | n/a | 3 | n/a | 96.9 | 100.0 | 100.0 | 99.05% |
| 2023-08 | 98.9 | n/a | 3 | n/a | 96.8 | 100.0 | 100.0 | 98.75% |
| 2023-09 | 98.8 | n/a | 3 | n/a | 96.5 | 100.0 | 100.0 | 98.60% |
| 2023-10 | 98.5 | n/a | 3 | n/a | 95.4 | 100.0 | 100.0 | 98.22% |
| 2023-11 | 99.0 | n/a | 3 | n/a | 96.9 | 100.0 | 100.0 | 98.09% |
| 2023-12 | 96.7 | n/a | 3 | n/a | 96.6 | 93.5 | 100.0 | 98.15% |
| 2024-01 | 98.9 | n/a | 3 | n/a | 96.8 | 100.0 | 100.0 | 98.35% |
| 2024-02 | 98.9 | n/a | 3 | n/a | 96.6 | 100.0 | 100.0 | 98.39% |
| 2024-03 | 98.7 | n/a | 3 | n/a | 96.2 | 100.0 | 100.0 | 98.16% |
| 2024-04 | 97.6 | n/a | 3 | n/a | 96.2 | 96.7 | 100.0 | 98.39% |
| 2024-05 | 98.6 | n/a | 3 | n/a | 95.9 | 100.0 | 100.0 | 98.89% |
| 2024-06 | 98.6 | n/a | 3 | n/a | 95.7 | 100.0 | 100.0 | 98.34% |
| 2024-07 | 98.6 | n/a | 3 | n/a | 95.9 | 100.0 | 100.0 | 98.85% |
| 2024-08 | 98.0 | 98.0 | 4 | 96.1 | 95.7 | 100.0 | 100.0 | 98.48% |
| 2024-09 | 86.0 | 86.0 | 4 | 50.8 | 96.1 | 100.0 | 97.3 | 98.92% |
| 2024-10 | 54.4 | 54.4 | 4 | 0.0 | 96.1 | 96.8 | 24.8 | 98.23% |
| 2024-11 | 50.4 | 50.4 | 4 | 0.3 | 95.7 | 100.0 | 5.4 | 98.22% |
| 2024-12 | 49.0 | 49.0 | 4 | 0.0 | 96.1 | 100.0 | 0.0 | 98.01% |
| 2025-01 | 65.5 | n/a | 3 | n/a | 96.5 | 100.0 | 0.0 | 98.11% |
| 2025-02 | 65.4 | n/a | 3 | n/a | 96.3 | 100.0 | 0.0 | 98.05% |
| 2025-03 | 48.2 | 48.2 | 4 | 0.0 | 96.1 | 96.8 | 0.0 | 97.90% |
| 2025-04 | 63.1 | n/a | 3 | n/a | 96.0 | 93.3 | 0.0 | 98.56% |
| 2025-05 | 64.2 | n/a | 3 | n/a | 95.7 | 96.8 | 0.0 | 98.71% |
| 2025-06 | 47.8 | 47.8 | 4 | 0.0 | 94.7 | 96.7 | 0.0 | 98.41% |
| 2025-07 | 65.3 | n/a | 3 | n/a | 95.8 | 100.0 | 0.0 | 99.11% |
| 2025-08 | 65.2 | n/a | 3 | n/a | 95.7 | 100.0 | 0.0 | 98.41% |
| 2025-09 | 65.2 | n/a | 3 | n/a | 95.5 | 100.0 | 0.0 | 98.73% |
| 2025-10 | 64.0 | n/a | 3 | n/a | 95.3 | 96.8 | 0.0 | 98.15% |
| 2025-11 | 65.1 | n/a | 3 | n/a | 95.2 | 100.0 | 0.0 | 98.22% |
| 2025-12 | 48.7 | 48.7 | 4 | 0.0 | 94.9 | 100.0 | 0.0 | 97.98% |
| 2026-01 | 64.0 | n/a | 3 | n/a | 95.3 | 96.8 | 0.0 | 98.27% |
| 2026-02 | 60.3 | n/a | 3 | n/a | 95.1 | 85.7 | 0.0 | 98.21% |
| 2026-03 | 48.5 | 48.5 | 4 | 0.0 | 94.1 | 100.0 | 0.0 | 97.43% |
| 2026-04 | 64.8 | n/a | 3 | n/a | 94.3 | 100.0 | 0.0 | 97.71% |
| 2026-05 | 64.8 | n/a | 3 | n/a | 94.5 | 100.0 | 0.0 | 98.46% |
| 2026-06 | 55.1 | 55.1 | 4 | 0.0 | 94.7 | 83.3 | 42.4 | 98.98% |
| 2026-07 | 59.4 | 59.4 | 4 | 0.0 | 95.8 | 93.3 | 48.6 | 98.85% |

## Per operator (uniqueness only)

`operator_monthly.parquet` carries the ONE component with an honest operator grain. Linkage and schedule-cleanliness are measured nationally. Enrichment availability is deliberately not split by operator: finding F7 showed the field discriminates between operators by 2.6x around 1.5 per 10,000 in the era where it is populated, so a per-operator enrichment league table would be pure artifact. Even the uniqueness split ranks exposure to a stride-side bug (scheduled_start_time drift, hasadna issue #390), NOT operator conduct.

Rows: 1,445 (operator x month).
