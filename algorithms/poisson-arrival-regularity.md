# Poisson arrival — headway regularity decay

> ⚠️ **This card is currently broken.** It renders as an error card on the
> dashboard. See [Status](#status) — the fix is one line.

**Author:** yuvalko1 / Yuval — from `open_bus_poisson_analysis_all_in_one.ipynb`
**Code:** [analyses/poisson_arrival_regularity.py](../analyses/poisson_arrival_regularity.py)
**Card:** `poisson-arrival-regularity`
**Data:** reuses [bus-arrival-reliability](bus-arrival-reliability.md)'s cached `_load` (Stride `/route_timetable/list` + `/siri_vehicle_locations/list`)

## What it answers

> Does bus interarrival spacing degenerate into a random Poisson process as buses
> travel downstream?

The theory: buses leave the terminal on a schedule, so headways at the origin are
near-deterministic and their coefficient of variation is near 0. Traffic, boarding
and bunching progressively randomise the spacing. A **memoryless (exponential)
interarrival distribution has CV = 1** — so as CV climbs toward 1, the timetable has
stopped meaning anything for waiting passengers, and arrivals are effectively random.

This is the sharpest framing of any card here: it turns "the buses are unreliable"
into a **falsifiable statement with a theoretical benchmark**, and it produces a
curve rather than a number, so the *shape* is the result.

## Algorithm

1. **Reuse** `bus_arrival_reliability._load(...)` → `stop_events` (one row per ride ×
   stop, with GPS-derived `actual_time`), so no extra fetching.
2. **Group by `stop_sequence`.** For each stop along the route:
   - Within each `ride_date`, sort `actual_time` and take consecutive `diff()` in
     minutes — **gaps are computed per day**, so an overnight gap between the last
     bus of one day and the first of the next never enters the sample.
   - Pool the day-gaps for that stop.
   - Require **≥3 gaps**, then compute `CV = std(ddof=1) / mean`.
3. **Plot CV against stop index**, with a horizontal reference line at **CV = 1**
   (the exponential benchmark).

## Reasoning

**Why CV against a theoretical benchmark rather than a threshold.** CV = 1 is not a
tuning parameter — it is the exact value for a Poisson process. Every other
reliability card in this repo picks a cutoff (0.25×, 1.75×, 5 minutes late, 500 m)
and has to defend it; this one does not.

**Why per-day gaps.** Concatenating arrivals across dates would insert an ~18-hour
overnight gap into the sample and dominate the standard deviation.

**Why `ddof=1`.** Sample standard deviation, correct for estimating a population CV
from a small sample — and the samples here are small.

**Why reuse `bus_arrival_reliability._load`.** That fetch is disk-cached and
single-flight, and it already derives per-stop arrival times, which is precisely what
per-stop headways need. Free correctness, free speed.

**Why per-stop and not per-line.** This is the design's real insight, and it is what
[bus-bunching](bus-bunching.md) is missing: bunching *develops along the route*. A
single line-level CV averages away the whole phenomenon.

## Status

Confirmed by running it:

```
kind:          error
error_message: AttributeError: 'LineSpec' object has no attribute 'short_name'
               analyses/poisson_arrival_regularity.py:133, in run_poisson
                 Series(name=f"Line {line.short_name} CV", points=points),
```

`bus_times.LineSpec` is a frozen dataclass with exactly three fields — `line_ref`,
`operator_ref`, `label`. There is no `short_name`. The same attribute is used again
at [:168](../analyses/poisson_arrival_regularity.py#L168), inside the matplotlib
`try/except`, so that one is swallowed; line 133 is not.

**Fix:** use `line.label` (or `line.line_ref`) at both sites. One line, no
behavioural change to the analysis.

Two secondary problems in the same function:

- The `try: … except NoMatch` around `_load` is **dead code** — `_load` never raises
  `NoMatch`; only `_fetch` does, and this module does not call it.
- `_load` is called with positional `req.date_from, req.date_to` **without the
  `_window()` clamp** that [bus_arrival_reliability.py:127](../analyses/bus_arrival_reliability.py#L127)
  applies. So this card requests a window reaching to *today* — inside the 3-day SIRI
  lag — and with a different cache key than the three cards sharing that fetch,
  meaning it also **misses the warm cache and pays the full ~80 s fetch**.

## Findings

**No findings have been produced by this card**, because it has never successfully
rendered. What follows is what it would be able to claim, and at what confidence,
once fixed.

### 1. CV rises with stop index along a route — **confidence: not yet established**

The hypothesis. It is well-supported in the transit literature and mechanically
plausible, but this card has produced no data.

### 2. Whether any Israeli line reaches CV ≈ 1 — **confidence: not yet established**

The interesting question, and the one worth presenting if it can be answered.

### Inherited findings

Everything the shared fetch rests on carries over from
[bus-arrival-reliability](bus-arrival-reliability.md): the API serves no actual
arrival times, derived arrivals are ±30 s, and single-ride short-segment durations
are noise. All **High** confidence, all independent of this card working.

## Criticism

**It is broken and shipped.** The card is registered with `draft` unset (so it
defaults to visible) and appears on the dashboard as an error tile. Given
`./dev check` only verifies that modules *import*, nothing in CI catches a card that
imports fine and raises at runtime. That is a gap worth closing — a smoke test that
runs every registered analysis once and asserts `kind != "error"` would have caught
this.

**The `_OPTIONS` are inherited but their defaults are not.** The module imports
`_OPTIONS` from `bus_arrival_reliability` (where `name_contains` and `direction`
both default to `""`), then calls `_load` with `req.opt("name_contains", "תל אביב")`
and `req.opt("direction", "1")`. So the dropdown shows "" as selected while the code
silently substitutes Tel Aviv, direction 1. A user who has not touched the options is
looking at a different route than the UI says.

**No minimum-sample guard beyond 3 gaps.** A CV from 3 observations is almost pure
noise, and it would be plotted with the same visual weight as one from 300. The
`n_gaps` column is in the relief table but nothing on the chart distinguishes a
well-evidenced point from a guess — which is exactly the failure mode
[bus-arrival-reliability](bus-arrival-reliability.md)'s hatching convention exists to
prevent, in the same codebase.

**Arrivals are GPS-derived at ±30 s, and CV is a ratio of a standard deviation to a
mean.** On a high-frequency line with 4-minute headways, ±30 s of independent noise
on each arrival inflates CV measurably — and inflation *toward* the CV = 1 benchmark
is precisely the direction that would produce a false positive. The card should
subtract the known measurement variance, or at minimum state the floor CV that
measurement error alone produces at a given headway.

**The benchmark line is drawn as a data series.** `Series(name="Exponential
Benchmark (CV=1)", points=[…y=1.0…])` gets a palette slot like any other series,
rather than being rendered as an annotation. Cosmetic, but it makes a theoretical
constant look like a measurement.
