# Metric 6.1 - national gap series (reconstructed)

A **gap** is a planned ride on its own service-day snapshot with no actual ride assigned within the stated tolerance (`quality/filters.py`).  Every rate below names its tolerance in seconds; there is no default.

## Whole covered window

| days | planned | gap_rate_180s | gap_rate_300s | gap_rate_600s |
|---|---|---|---|---|
| 1,306 | 119,150,507 | 7.48% | 7.36% | 7.25% |

## By era (boundary 2024-09-01)

The boundary is a label, not a cliff: stride's own matching decayed over 2024-09 to 2024-12 rather than stopping on one day, so the two eras are not homogeneous populations.  The 2024-09 month in operator_monthly.parquet is labelled 'reconstruction' but is in fact mixed - 15 days of healthy stored matching, 7 at exactly zero, 8 partial - so that one month is not a clean era observation and should not anchor an era comparison.

| era | days | planned | gap_rate_180s | gap_rate_300s | gap_rate_600s |
|---|---|---|---|---|---|
| reconstruction | 697 | 64,397,852 | 7.24% | 7.09% | 6.97% |
| stored_match | 609 | 54,752,655 | 7.77% | 7.67% | 7.58% |

## Against the published figures

| source | tolerance_s | gap rate |
|---|---|---|
| reconstructed (this pipeline) | 180 | 7.48% |
| reconstructed (this pipeline) | 300 | 7.36% |
| reconstructed (this pipeline) | 600 | 7.25% |
| official (stride exact-equality join) | - | 5.00% |
| State Comptroller 2019 | - | 2.40% |

## Density control - gap rate by planned-rides-per-day decile

Deciles are cut within each service day (decile 1 = sparsest).  Unmatched rate correlates with service density, so a gap rate that falls monotonically across deciles is partly an instrument effect and must not be read as periphery no-shows.

| decile | line_days | planned/day min | planned/day max | planned | gap_rate_180s | gap_rate_300s | gap_rate_600s |
|---|---|---|---|---|---|---|---|
| 1 | 729,516 | 1 | 2 | 729,663 | 39.11% | 39.10% | 39.07% |
| 2 | 729,375 | 1 | 4 | 750,006 | 7.31% | 7.27% | 7.22% |
| 3 | 729,238 | 1 | 7 | 1,159,068 | 5.67% | 5.61% | 5.53% |
| 4 | 729,112 | 1 | 11 | 2,167,612 | 5.38% | 5.33% | 5.27% |
| 5 | 728,994 | 1 | 15 | 3,740,862 | 4.82% | 4.77% | 4.71% |
| 6 | 728,865 | 1 | 21 | 6,025,207 | 4.84% | 4.78% | 4.72% |
| 7 | 728,727 | 1 | 30 | 9,962,552 | 4.62% | 4.57% | 4.50% |
| 8 | 728,587 | 1 | 41 | 17,439,237 | 4.95% | 4.88% | 4.78% |
| 9 | 728,446 | 7 | 57 | 27,850,514 | 5.11% | 4.99% | 4.84% |
| 10 | 728,326 | 9 | 1,261 | 49,325,786 | 10.49% | 10.31% | 10.21% |

## Per operator, whole window

| operator_ref | days | planned | gap_rate_180s | gap_rate_300s | gap_rate_600s |
|---|---|---|---|---|---|
| 3 | 1,303 | 23,569,613 | 3.40% | 3.29% | 3.19% |
| 18 | 1,306 | 13,570,960 | 6.29% | 6.21% | 6.12% |
| 5 | 1,300 | 11,742,690 | 3.88% | 3.69% | 3.62% |
| 15 | 1,300 | 11,281,728 | 4.93% | 4.75% | 4.63% |
| 16 | 1,304 | 10,353,861 | 4.80% | 4.66% | 4.58% |
| 25 | 1,299 | 7,938,600 | 5.23% | 5.13% | 5.03% |
| 14 | 1,306 | 5,955,365 | 5.36% | 5.29% | 5.20% |
| 31 | 1,301 | 5,295,280 | 5.74% | 5.62% | 5.48% |
| 32 | 1,300 | 3,098,407 | 5.49% | 5.27% | 5.13% |
| 38 | 1,299 | 2,880,239 | 7.18% | 7.01% | 6.90% |
| 34 | 1,299 | 2,758,300 | 11.56% | 11.28% | 10.87% |
| 4 | 1,299 | 2,675,237 | 4.44% | 4.38% | 4.29% |
| 35 | 1,299 | 2,599,624 | 4.59% | 4.42% | 4.32% |
| 6 | 1,306 | 2,547,444 | 2.91% | 2.90% | 2.89% |
| 33 | 1,177 | 2,114,748 | 100.00% | 100.00% | 100.00% |
| 37 | 1,299 | 1,874,670 | 1.86% | 1.80% | 1.73% |
| 7 | 1,306 | 1,754,464 | 3.45% | 3.44% | 3.43% |
| 23 | 1,306 | 1,279,773 | 4.24% | 4.10% | 4.03% |
| 135 | 833 | 835,487 | 3.44% | 3.38% | 3.26% |
| 42 | 1,306 | 617,968 | 6.95% | 6.72% | 6.56% |
| 2 | 1,302 | 616,557 | 47.55% | 47.54% | 47.50% |
| 8 | 1,306 | 474,601 | 2.45% | 2.42% | 2.41% |
| 22 | 1,132 | 424,959 | 21.71% | 21.60% | 21.51% |
| 24 | 1,300 | 385,004 | 6.78% | 6.70% | 6.65% |
| 21 | 1,293 | 369,002 | 99.83% | 99.83% | 99.83% |
| 45 | 1,301 | 325,039 | 15.36% | 15.19% | 14.83% |
| 50 | 1,305 | 298,082 | 34.24% | 34.05% | 33.47% |
| 49 | 1,306 | 286,086 | 9.45% | 9.16% | 8.94% |
| 44 | 1,304 | 269,458 | 6.53% | 6.35% | 6.07% |
| 47 | 1,165 | 247,593 | 15.57% | 15.14% | 14.43% |
| 40 | 595 | 218,756 | 21.47% | 21.39% | 21.29% |
| 20 | 1,265 | 177,226 | 100.00% | 100.00% | 100.00% |
| 51 | 1,300 | 128,798 | 25.45% | 25.14% | 24.27% |
| 39 | 79 | 53,720 | 100.00% | 100.00% | 100.00% |
| 10 | 1,098 | 49,384 | 12.12% | 12.04% | 11.97% |
| 98 | 1,156 | 31,047 | 25.91% | 25.91% | 25.88% |
| 93 | 970 | 18,342 | 10.11% | 10.04% | 9.91% |
| 97 | 1,113 | 16,318 | 10.38% | 10.35% | 10.18% |
| 91 | 1,114 | 16,077 | 82.24% | 82.24% | 82.24% |
