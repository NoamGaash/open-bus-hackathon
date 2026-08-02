# Metric M2 - Timetable Fidelity Index

**How late buses actually depart requires stop-level AVL data - measurable, not yet mirrored; roadmap item.** Nothing below is a lateness figure: every number is about whether a published departure was served, and what the resulting gaps cost a waiting rider.

**Manager meaning: what the timetable costs a rider in waiting.**  A published departure that never happens does not cost its own single trip - it costs everyone who arrived expecting it the wait until the next one. This metric is the difference between the wait the timetable promised and the wait the service delivered, for a rider arriving at a random time.

expected wait = sum(gap^2) / (2 x span). One long gap hurts far more than the same total time split evenly, which is exactly why a missing departure is not 'one trip lost'.

It is NOT an on-time measure, and cannot be: the open record holds no actual departure time. `delta_t_seconds` is scheduled-vs-scheduled and is exactly 0 on 98.6% of matched pairs, so any percentile of it measures record agreement, not punctuality. A waiting measure needs only which published departures were served and when they were published for - both of which are in hand.

The choice of a wait-based rather than a threshold-based measure also follows the evidence: a 2025 Journal of Public Transportation study of Winnipeg found deviation-based reliability outperforms on-time-performance at explaining route-level ridership (finding F2 in the findings ledger). A threshold hides the distribution riders actually experience.

## The grade bands (a stated judgement, not a measurement)

| grade | excess wait a rider incurs |
|---|---|
| A | up to 1 min |
| B | 1 to 3 min |
| C | 3 to 5 min |
| D | 5 to 10 min |
| E | more than 10 min |

## Scope: tracked operators only (finding F9)

4 operator(s) with a whole-record non-execution rate at or above 99% - refs 33, 21, 20, 39, 2,714,696 scheduled rides - are EXCLUDED. They have no SIRI feed at all, so every one of their departures reads as unserved and their excess wait would be the whole service span: a coverage fact, not a rider experience. Left in, one of them (ref 33, 2.1M rides) alone dominates the national wait. They are listed with their volumes in report/metrics/enforcement_gap/coverage_holes.parquet; their riders have no service statistics at all, which is F9's finding rather than this metric's.

## National, per month

| month | published departures | served | within +-5 min | only +-5 to +-60 min | wait promised | wait delivered | excess | inflation | grade |
|---|---|---|---|---|---|---|---|---|---|
| 2023-01 | 2,816,631 | 93.09% | 93.04% | 0.07% | 49.2 | 60.5 | 11.3 | 1.23x | E |
| 2023-02 | 2,495,950 | 93.30% | 93.25% | 0.08% | 49.4 | 59.2 | 9.8 | 1.20x | D |
| 2023-03 | 2,749,255 | 95.02% | 94.95% | 0.14% | 49.3 | 55.5 | 6.2 | 1.13x | D |
| 2023-04 | 2,167,286 | 95.17% | 95.08% | 0.13% | 50.2 | 56.1 | 5.9 | 1.12x | D |
| 2023-05 | 2,720,643 | 95.99% | 95.84% | 0.21% | 49.9 | 53.3 | 3.3 | 1.07x | C |
| 2023-06 | 2,595,133 | 95.73% | 95.59% | 0.20% | 51.8 | 55.6 | 3.7 | 1.07x | C |
| 2023-07 | 2,730,365 | 94.63% | 94.50% | 0.20% | 53.8 | 58.9 | 5.2 | 1.10x | D |
| 2023-08 | 2,874,952 | 94.34% | 94.19% | 0.23% | 54.3 | 59.9 | 5.7 | 1.10x | D |
| 2023-09 | 2,382,936 | 95.39% | 95.23% | 0.24% | 49.1 | 52.3 | 3.2 | 1.06x | C |
| 2023-10 | 2,514,387 | 86.05% | 84.94% | 1.21% | 48.6 | 72.2 | 23.6 | 1.48x | E |
| 2023-11 | 2,687,112 | 96.58% | 96.37% | 0.28% | 45.8 | 49.1 | 3.3 | 1.07x | C |
| 2023-12 | 2,731,597 | 95.93% | 95.80% | 0.19% | 49.1 | 53.4 | 4.4 | 1.09x | C |
| 2024-01 | 2,929,986 | 96.61% | 96.44% | 0.25% | 48.5 | 51.4 | 2.9 | 1.06x | B |
| 2024-02 | 2,706,243 | 95.35% | 95.25% | 0.16% | 48.3 | 53.1 | 4.8 | 1.10x | C |
| 2024-03 | 2,769,064 | 94.37% | 94.23% | 0.25% | 48.0 | 53.5 | 5.5 | 1.11x | D |
| 2024-04 | 2,434,549 | 96.01% | 95.85% | 0.24% | 49.2 | 52.0 | 2.8 | 1.06x | B |
| 2024-05 | 2,860,809 | 92.65% | 92.54% | 0.18% | 48.6 | 58.8 | 10.2 | 1.21x | E |
| 2024-06 | 2,476,212 | 95.45% | 95.22% | 0.29% | 49.8 | 53.9 | 4.1 | 1.08x | C |
| 2024-07 | 2,975,758 | 96.76% | 96.65% | 0.17% | 51.6 | 54.3 | 2.6 | 1.05x | B |
| 2024-08 | 2,829,797 | 96.22% | 96.07% | 0.21% | 52.2 | 55.5 | 3.3 | 1.06x | C |
| 2024-09 | 2,915,076 | 95.86% | 95.67% | 0.26% | 48.0 | 50.8 | 2.7 | 1.06x | B |
| 2024-10 | 2,487,631 | 94.60% | 94.46% | 0.23% | 48.2 | 55.2 | 7.0 | 1.15x | D |
| 2024-11 | 2,769,713 | 95.50% | 95.37% | 0.21% | 47.9 | 55.6 | 7.7 | 1.16x | D |
| 2024-12 | 3,036,834 | 96.68% | 96.56% | 0.18% | 48.0 | 51.4 | 3.4 | 1.07x | C |
| 2025-01 | 2,988,563 | 97.74% | 97.65% | 0.14% | 48.4 | 50.4 | 2.1 | 1.04x | B |
| 2025-02 | 2,714,983 | 98.53% | 98.46% | 0.11% | 47.8 | 48.9 | 1.1 | 1.02x | B |
| 2025-03 | 2,828,612 | 97.19% | 97.08% | 0.20% | 48.1 | 50.9 | 2.8 | 1.06x | B |
| 2025-04 | 2,765,525 | 97.52% | 97.42% | 0.15% | 48.7 | 50.8 | 2.1 | 1.04x | B |
| 2025-05 | 2,847,388 | 93.55% | 93.44% | 0.17% | 48.5 | 58.9 | 10.4 | 1.21x | E |
| 2025-06 | 2,204,234 | 85.27% | 83.94% | 1.45% | 46.8 | 73.6 | 26.7 | 1.57x | E |
| 2025-07 | 3,059,331 | 96.28% | 96.17% | 0.16% | 51.1 | 55.8 | 4.7 | 1.09x | C |
| 2025-08 | 2,866,857 | 96.86% | 96.73% | 0.20% | 51.6 | 54.8 | 3.3 | 1.06x | C |
| 2025-09 | 2,694,553 | 86.60% | 86.50% | 0.17% | 47.9 | 88.5 | 40.7 | 1.85x | E |
| 2025-10 | 2,512,654 | 95.69% | 95.57% | 0.19% | 48.8 | 53.0 | 4.2 | 1.09x | C |
| 2025-11 | 2,861,273 | 97.78% | 97.70% | 0.14% | 48.0 | 49.7 | 1.8 | 1.04x | B |
| 2025-12 | 3,044,363 | 94.44% | 94.32% | 0.20% | 48.0 | 55.0 | 7.0 | 1.15x | D |
| 2026-01 | 2,906,377 | 96.55% | 96.42% | 0.19% | 48.1 | 53.3 | 5.1 | 1.11x | D |
| 2026-02 | 2,693,136 | 97.15% | 97.06% | 0.14% | 48.3 | 50.7 | 2.4 | 1.05x | B |
| 2026-03 | 2,048,457 | 85.36% | 83.63% | 1.95% | 44.8 | 65.6 | 20.8 | 1.46x | E |
| 2026-04 | 2,350,197 | 95.31% | 94.82% | 0.60% | 46.2 | 51.3 | 5.1 | 1.11x | D |
| 2026-05 | 2,674,067 | 97.19% | 96.98% | 0.28% | 48.4 | 50.8 | 2.4 | 1.05x | B |
| 2026-06 | 2,942,697 | 95.62% | 95.41% | 0.30% | 49.0 | 51.8 | 2.8 | 1.06x | B |
| 2026-07 | 2,774,625 | 97.54% | 97.44% | 0.17% | 50.5 | 52.4 | 1.8 | 1.04x | B |

The window ladder (`within +-5 min`, `only +-5 to +-60 min`) is a statement about THE RECORD, not about a bus. A ride whose only counterpart is 5-60 min from its published slot has either drifted in stride's own bookkeeping (hasadna issue #390) or is a different trip than the one published - and the two are indistinguishable here, because neither side of the comparison is an observed departure. It is not 'ran far off its slot'.

## Route-month grades (107,119 route-months with a measurable wait)

| grade | route-months | share |
|---|---|---|
| A | 51,415 | 48.00% |
| B | 21,803 | 20.35% |
| C | 9,916 | 9.26% |
| D | 11,291 | 10.54% |
| E | 12,694 | 11.85% |

15,699 route-months have no measurable headway at all (a single published departure, or every departure at the same second) and are null rather than graded E.

## Operator, latest month in the record

| operator_ref | published departures | served | excess wait | inflation | grade |
|---|---|---|---|---|---|
| 3 | 526,899 | 99.29% | 0.4 | 1.01x | A |
| 18 | 305,834 | 97.90% | 0.7 | 1.01x | A |
| 16 | 283,536 | 97.38% | 0.5 | 1.01x | A |
| 15 | 283,222 | 98.01% | 2.4 | 1.05x | B |
| 5 | 274,286 | 98.87% | 0.2 | 1.01x | A |
| 25 | 188,611 | 97.36% | 1.1 | 1.02x | B |
| 14 | 142,223 | 97.46% | 3.0 | 1.06x | B |
| 31 | 132,092 | 97.51% | 4.8 | 1.11x | C |
| 38 | 79,799 | 87.43% | 2.4 | 1.08x | B |
| 35 | 67,310 | 95.95% | 1.3 | 1.02x | B |
| 32 | 66,838 | 99.21% | 0.2 | 1.02x | A |
| 34 | 63,013 | 87.98% | 9.9 | 1.15x | D |
| 4 | 52,758 | 97.30% | 3.1 | 1.04x | C |
| 6 | 48,779 | 99.45% | 0.2 | 1.01x | A |
| 37 | 43,875 | 99.52% | 0.1 | 1.01x | A |

## Caveats that travel with every number above

- The excess is a LOWER BOUND. A rider left with no later departure at all is charged only the wait to the day's last published departure, not an infinite one, so a line whose evening service collapses scores better than it deserves.
- 'Served' means a published departure kept an assigned SIRI ride within +-30 min. That says the trip existed, not that it was punctual.
- A MONTH WHOSE `served` SHARE FALLS FAR BELOW THE ~94% NORM IS NOT AUTOMATICALLY A SERVICE COLLAPSE. Three mechanisms produce the same signature and this metric cannot separate them: buses genuinely not running (war periods), a SIRI feed blackout with the buses running normally (e.g. 2024-03-23 recorded 15 actual rides against a normal published schedule), and a reduced-service holiday where the published schedule also drops. Candidate blackout days are listed in data/warehouse/audit/siri_outage_candidate_days.parquet - a CANDIDATE list, not a validated one, which is why no day is excluded here rather than filtered on an unproven rule. Before quoting any month with a served share below ~90%, check it against that file.
- Match rate correlates with service density (96.3% busiest vs 85.0% sparsest, finding F1), so on sparse lines part of the unserved count is an instrument artefact. Read this beside the density control in metrics/gap_series.py.
- The ABSOLUTE waits are weighted by published service span, one second of a twice-daily rural line counting the same as one second of a 6-minute urban line, so the national `wait promised` is dominated by low-frequency line-days and is NOT 'the average Israeli's wait' - demand weighting would need the tikufim join. The EXCESS and the INFLATION ratio are the columns to read across grains; the absolute waits are context for them.
- Prior art: expected-wait and excess-wait measures are standard (Transport for London publishes route-level Excess Wait Time). What does not exist anywhere is one for Israel, because the planned-to-actual link it needs has been broken nationally since 2024-10 (finding F1) and is supplied here by reconstruction.
