# Questions only you can answer

Eight questions where an answer from inside hasadna would either confirm a finding, remove a
caveat, or change what we built.
Each one states why it matters and what we assumed in the meantime, so nothing is blocked on you —
but several of our stated caveats exist only because these are open.

Ordered by how much the answer would change.

---

## 1. Was a matching-strategy migration started in September 2024?

`journey_gtfs_ride_id` and `route_gtfs_ride_id` are marked *Deprecated* upstream.
A deliberate migration would explain why the SIRI→GTFS match *decayed* across September–December
2024 rather than stopping on one day — and it would change the fix from "restart the stalled job"
to "finish the migration".
A clue pointing the same way: SIRI parse failures dropped roughly 50× in 2024-07/08.

**Why it matters:** it decides whether [F1](issues/F1-stored-linkage.md) is an unattended job
failure or an incomplete migration. We wrote the issue as the former.
**What we assumed meanwhile:** a stalled job, because the inputs are all present and the match
reconstructs at 97.7% on a day stored as zero.

## 2. Does the ministry's published non-execution rate credit authorized cancellations or war-emergency exemptions?

This is the single unresolved attribution in our metric M1.
We compute 4.95% non-execution for 2024-H1 from the open record against the 1.53% the ministry
published from its own electronic system — a gap of 3.42 percentage points, at the same ±30 min
basis.

**Why it matters:** if authorized exemptions are silently credited in the published figure, part
of that gap is definitional rather than enforcement leakage. 2024-H1 overlaps the war, so the
effect could be material.
**What we assumed meanwhile:** we publish the gap as *computed* and label its full attribution to
enforcement leakage as unproven (the claim's proof card is marked PARTIAL, 7/10 confidence, for
exactly this reason). If you know the answer, one sentence from you removes our largest caveat.

## 3. Is the ~5% "rides that didn't run" figure still being published, and computed from what?

Given [F1](issues/F1-stored-linkage.md), the stored match has been empty since October 2024, so
any figure computed from `scheduled_time_gtfs_ride_id` has had no basis for ~21 months.

**Why it matters:** if the figure is still circulating, it is either computed from a different
path (the live `rides_execution` join, which has its own exact-equality problem) or it is stale.
Both are worth knowing publicly.
**What we assumed meanwhile:** that the number kept circulating without a computable basis, which
is the premise of our whole reconstruction. If we are wrong about that, say so — it is the
project's central framing.

## 4. Which operator codes are *expected* to have no SIRI feed?

We identify five (refs 20, 21, 33, 39, 91) carrying 2.3% of national scheduled volume with no
tracking data at all — see [F9](issues/F9-coverage-holes.md).

**Why it matters:** contractual exemption and non-compliance look identical from outside, and they
need opposite responses. It also determines whether the riders of those operators simply have no
statistics, or should have.
**What we assumed meanwhile:** we exclude them from every performance rate by a derived rule
(pooled matched share below 50%) and report the absence as a finding rather than as failure.

## 5. Is the 2024-12 → 2026-05 enrichment outage known and logged?

`first_vehicle_location_id` is 100.00% null for 18 consecutive months (49.4M rides), and the nulls
flip day-quantised during what looks like a 2026-06 backfill — see
[F7](issues/F7-enrichment-flag.md).

**Why it matters:** we would like to know whether the backfill completed, and whether the field's
meaning ("enrichment state", not "vehicle transmitted") is documented anywhere. We nearly built a
per-operator transmission metric on it before catching the artifact; anyone else will too.
**What we assumed meanwhile:** the field is unusable for any per-operator claim, and our
transmission audit was re-specified off the matched census instead.

## 6. Is `siri_ride.journey_ref` a stable join key, or does it drift like `scheduled_start_time`?

**Why it matters:** our deduplication for [F6](issues/F6-duplicate-rides.md) keys on
`(operator, line, journey_ref)` per service day. If `journey_ref` itself drifts, our dedup is
under-collapsing and the 2.56% surplus figure is a floor rather than an estimate.
**What we assumed meanwhile:** stable within a service day. We report the duplication shares as
lower bounds partly because of this uncertainty.

## 7. Is there an authoritative `operator_ref` → operator-name table?

We hand-built `src/busanalysis/registry.py` from observed data because we could not find a
canonical mapping.

**Why it matters:** we name operators in the analysis. A wrong name attached to a real number is
the most embarrassing kind of error, and it is entirely avoidable if the mapping exists.
Our registry also carries a `NAME_CHANGED` set (operators we exclude from longitudinal charts
because their identity shifts) — that too should come from an authoritative source.
**What we assumed meanwhile:** our own registry, and we exclude renamed operators from
time-series comparisons.

## 8. Has anyone inside hasadna already analysed execution quality against ridership for Israel?

**Why it matters:** it is our cheapest possible novelty check. Our claim that no open project
joins execution to demand rests on external sweeps; you would know instantly if that is wrong.
**What we assumed meanwhile:** unoccupied ground, based on a worldwide and an Israel-specific
prior-art sweep recorded in `data/registry/prior_art.md`.

---

## One question we are answering ourselves, for completeness

Friday and Saturday gap rates read far higher than weekdays (dense lines 37% / 49%).
We do **not** publish these: the short-service-day envelope derivation and Sabbath-eve schedule
structure could inflate them mechanically, so they are flagged as unverified pending a dedicated
pass.
If you already know that weekend delivery genuinely collapses, that would be useful — but we are
not asking you to do our verification.
