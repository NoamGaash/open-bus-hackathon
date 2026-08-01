# Planned vs actual rides — the worked example

**Author:** example (repo scaffolding, by Noam Gaash)
**Code:** [analyses/example_service_by_operator.py](../analyses/example_service_by_operator.py)
**Card:** `service-by-operator`
**Data:** Stride `/gtfs_rides_agg/group_by` + `/gtfs_agencies/list`

## What it answers

Daily count of rides planned (GTFS) against how many were actually observed (SIRI),
for the selected operators. **The gap is unrun service.**

This file exists to be copied — it is the template a hackathon participant reads
before writing their own analysis. It hits the real API, handles the empty case,
returns two different result kinds, and is deliberately short.

It has therefore ended up in an awkward position: **it is the clearest statement of
the question the whole hackathon is about, built on the one endpoint that cannot
answer it.**

## Algorithm

1. `stride.gtfs_rides_agg(date_from, date_to, group_by="operator_ref,gtfs_route_date")`
   — pre-aggregated server-side, much kinder than paging every individual ride.
2. Merge `stride.agencies()` for human-readable names; fall back to the numeric
   `operator_ref` where the name is missing.
3. Filter to `req.operators` if any are selected.
4. Resolve the planned and actual columns **by trying several names** —
   `_first_col(agg, ["total_planned_rides", "planned_rides", "num_planned_rides"])`
   and the same for actual.
5. Sum per day, melt to long form, render as a two-series line chart.

## Reasoning

**Why `gtfs_rides_agg` at all.** For a template, the pedagogically right move is to
show the cheap, pre-aggregated, server-side path rather than teach newcomers to page
raw rides against a shared community API. The instinct is correct and the guidance
in [CLAUDE.md](../CLAUDE.md) repeats it.

**Why `_first_col` tolerates renames.** *"Tolerate small API column renames instead
of hard-failing mid-demo."* The whole repo is built around one broken analysis not
taking the demo down, and this is that principle at the column level.

**Why it degrades to planned-only.** If no actual column is found it notes
*"No actual-rides column returned by /gtfs_rides_agg — showing planned only"* rather
than charting a misleading zero.

**Why `inputs=["operators", "dates"]` and not lines.** It aggregates across whatever
operators are selected, so a line filter would be misleading.

## Findings

### 1. The aggregate's actual-rides column is present but always zero — **confidence: High**

This card's own graceful degradation does not trigger, because the problem is not a
missing column. `total_actual_rides` **exists and is populated with 0** for every
row, network-wide, on every date sampled Nov 2025 → Jul 2026. See
[days-with-no-cancellations](days-with-no-cancellations.md) finding 1 for the
measurements and the control that rules out ingestion lag, and
[service-violations](service-violations.md) finding 2 for the independent
confirmation.

**The consequence for this card specifically:** the note it prints reads
*"Overall 0.0% of planned rides were observed"* and the chart draws a flat line at
zero beneath the planned series. To a viewer, that is a total collapse of Israeli bus
service. It is a broken column.

### 2. Graceful degradation designed against renames does not protect against wrong values — **confidence: High**

A design lesson worth stating plainly. `_first_col` guards the schema; nothing guards
the semantics. The card is *most* wrong precisely where it looks most confident,
because the defensive path it was given never fires.

### 3. Planned-ride counts from the aggregate are trustworthy — **confidence: Medium**

`num_planned_rides` is populated and, per orion's cross-check, **agrees closely with
the ride-level endpoint** (line 2259 / 2026-07-29: aggregate 123 planned vs 126 from
`/rides_execution/list`). That write-up also carries an explicit correction of an
earlier claim that the two disagreed. Medium: one line, one date, and 123 vs 126 is
close but not equal.

So the endpoint is usable **as a planned-ride denominator** — which is exactly the
recommendation orion's method doc lands on.

## Criticism

**As shipped, this card tells the audience that no bus in Israel ran.** It is the
example card, so it is the one most likely to be looked at first, and it has no note
warning that the actual series is a known-broken column. Every other card that
touched this endpoint documented the defect at length in its notes; the template did
not. Given the hackathon's presentation is the deliverable, that is the most
consequential single fix in the repo:

- add a note when `actual_total == 0` and `planned_total > 0` saying the aggregate's
  actual column is unpopulated on this deployment, linking the evidence; **or**
- drop the actual series and retitle the card to what the endpoint can honestly
  deliver — planned service volume per operator per day.

**It teaches the wrong first step.** A newcomer copying this file learns to reach for
`gtfs_rides_agg` for planned-vs-actual, which is the one thing it cannot do here.
`/rides_execution/list` (see [days-with-no-cancellations](days-with-no-cancellations.md))
is the endpoint that works, and the template does not point at it.

**No SIRI lag clamp.** Unlike essentially every other card, this one uses
`req.date_from`/`req.date_to` directly. With a healthy actual column it would show a
sharp fake decline over the last 3 days — a second way to read a data artifact as a
service collapse.

**`daily["Actual"] = agg.groupby(...).sum().to_numpy()`** assigns by position, not by
join key. It happens to be safe because both aggregations group the same frame by the
same column in the same sorted order, but it is a positional assignment in the file
that exists to be copied.
