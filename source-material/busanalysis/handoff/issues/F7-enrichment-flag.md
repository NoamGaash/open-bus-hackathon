# An enrichment job stopped for 18 months, leaving first_vehicle_location_id 100% null

**Severity:** silent data loss — and the field is routinely misread as evidence that vehicles stopped transmitting
**Affected component:** the enrichment job that populates `siri_ride.first_vehicle_location_id` and `siri_ride.duration_minutes`
**Window observed:** 18 consecutive months, 2024-12 → 2026-05 (49,409,361 rides)
**Reported by:** external analysis of the open data (BusAnalysis), 2026-07

## What happens

For 18 consecutive months, `first_vehicle_location_id` is null for **every single ride, for every
operator** — 100.00% to two decimal places.
`duration_minutes` tracks the same pattern to within 0.006 per month.

The important part is the interpretation.
This field looks like it says "this vehicle never reported its position", and it is easy to build
a per-operator transmission metric on it.
It does not say that.
**It encodes whether stride's enrichment job has processed that day yet** — it is a
processing-state flag, not a property of the bus.

Overall, 49.21% of all `siri_ride` rows have this field null.

## Evidence

Four independent signs that this is a job outage rather than fleet behaviour:

1. **Perfect synchrony across all operators.** Every operator steps to 100% null in the same
   month and back out in the same month. Independent fleets from ~39 operators do not fail in
   lockstep to two decimal places.
2. In the era where the field *is* populated, the per-operator spread is only **2.6× wide** — far
   too narrow to support any per-operator transmission ranking.
3. **The nulls flip day-quantised during a 2026-06 backfill** — whole days change state at once,
   which is the signature of a batch job, not of vehicles.
4. `duration_minutes`, computed from the same enrichment, follows the identical curve.

Figure: `report/figures/findings/f7_enrichment_gap.png`.

## Why it matters

Any per-operator "transmission quality" or "vehicles going dark" metric built on this field is
**pure artifact** — it would rank operators by which days the enrichment job happened to reach.

This matters more than it first appears, because the enforcement regime treats absence of an AVL
signal as a violation. A metric that confuses "no enrichment record" with "no signal" could
attribute violations to operators that transmitted normally.

## Suggested fix

Two parts, and the second is the one we would prioritise:

1. Re-run the enrichment for 2024-12 → 2026-05 (a backfill appears to have started in 2026-06 —
   confirming whether it completed would be useful).
2. **Document the field's meaning in the schema** so no consumer builds a transmission metric on
   it. A name or comment that says "enrichment state" rather than something vehicle-shaped would
   prevent the error permanently.

## What we did instead (workaround in the external analysis)

We abandoned the field entirely.
Our planned per-operator transmission audit was **re-specified off the matched census** — that
is, off whether a planned departure has a matching actual ride within a stated time window —
rather than off any enrichment flag.

Worth recording as a near-miss: we initially assumed this field *was* transmission evidence and
had specified a metric on it. Finding that it is an enrichment flag turned a planned finding into
a negative result. Anyone else reading this column is likely to make the same assumption.
