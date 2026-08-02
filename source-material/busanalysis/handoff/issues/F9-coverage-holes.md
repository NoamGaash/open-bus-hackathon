# Five operators never appear in the tracking feed — 2.3% of the national schedule is unmeasured

**Severity:** silent data loss — these operators are absent from every published statistic and from the enforcement basis
**Affected component:** SIRI ingestion coverage (which operators reach `siri_ride` at all)
**Window observed:** the entire 2023-01 → 2026-07 window
**Reported by:** external analysis of the open data (BusAnalysis), 2026-07

## What happens

Three operators are **never** present in the tracking feed across the whole 3.5-year window, and
two more are **under 1% covered**.
Together they carry **2.74M scheduled rides — about 2.3% of national planned volume**.

Their buses may be running perfectly well. Nothing reports them, so nothing about them can be
measured.

## Evidence

The five, with the share of their scheduled rides that has no matching real departure at ±5 min:

| operator | scheduled rides (window) | share absent from the record |
|---|---|---|
| Cable Express | 2.11M | 100% |
| Kfir | 0.37M | 100% |
| Carmelit | 0.18M | 100% |
| Dan Netivim | 0.05M | 100% |
| Metro Kav Taxis | 0.02M | 82% (partial coverage — a shared-taxi mode) |

Figure: `report/figures/findings/f9_coverage_holes.png` — drawn with a hatched no-data texture
rather than a performance colour, deliberately, because this is a missing instrument and not a
service result.

The set is **derived, not hardcoded**: an operator qualifies when its pooled matched share over
the whole window falls below 50%. On the current census that rule selects operator refs 20, 21,
33, 39 and 91.

## Why it matters

Three consequences, and the second is the one we would raise first:

1. **A naive national gap rate is inflated by ~2.2 percentage points** — 7.36% instead of 5.19% at
   ±5 min. Counting these rides as buses that never ran is most of the difference between the two
   figures.
2. **These operators are invisible to an AVL-based enforcement regime.** Non-execution is defined
   partly as the absence of a tracking signal, so an operator with no signal at all should in
   principle be in permanent violation — yet the volume persists. Either the feed is missing or
   the enforcement basis is not being applied to them; from outside we cannot tell which.
3. **Their riders have no service statistics at all.** Per our operator registry this includes an
   East Jerusalem cluster, so the gap is not evenly distributed across the population.

## Suggested fix

First establish which of these is true for each operator, because the fix differs completely:

- the operator is **contractually exempt** from AVL reporting — then the exemption should be
  documented so that consumers can exclude them explicitly rather than discovering it by
  analysis;
- the operator **should be reporting and is not** — then it is an ingestion or a compliance
  problem.

Either way, a published list of "operators known not to reach SIRI" would prevent every future
analyst from silently inflating the national rate, which is the error we nearly made ourselves.

## What we did instead (workaround in the external analysis)

We exclude any operator whose pooled matched share is below the 50% floor from every performance
rate, and report their absence as a finding in its own right rather than as failure.

The distinction is load-bearing: with these operators pooled in, one city's rate reads 26.1%
instead of its true 4.2%, purely because an untracked operator runs routes originating there.
