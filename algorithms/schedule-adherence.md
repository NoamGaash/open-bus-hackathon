# Schedule adherence — day-to-day variation, geographically, and per day

**Author:** yuvalko1 — [github.com/yuvalko1/talpiot-hackathon-public-transportation](https://github.com/yuvalko1/talpiot-hackathon-public-transportation), branch `main`, from `compare_gtfs_siri_average.ipynb`. Vendored at [repos/talpiot-hackathon-public-transportation](../repos/talpiot-hackathon-public-transportation/).
**Code:** [analyses/schedule_adherence_average.py](../analyses/schedule_adherence_average.py)
**Cards:** `schedule-adherence-average`, `schedule-adherence-map`, `schedule-adherence-by-day`
**Data:** Stride `/route_timetable/list` + `/siri_vehicle_locations/list`

## What it answers

Take *one* departure — the same line, the same time of day — and watch it across
many days.

- **Stringline** — each matched day as a faint trace, with the GTFS plan and the
  cross-day average bold over them. The fan between them is the day-to-day
  unreliability of that single departure.
- **Map** — the same comparison geographically: the planned route dashed at its
  timetable coordinates, and the *measured* route solid, where each stop sits at a
  distance-weighted average of the real GPS pings that matched it.
- **By day** — total journey time for each matched day against the schedule, so
  "which day ran worst" is answerable without reading a fan of traces.

## Algorithm

1. **Anchor on a real departure time.** Scan back up to 10 days for the first
   departure at or after the requested hour on a day that has any timetable for the
   line. That clock time becomes the fixed target for every subsequent day.
2. **Per day, back `days_back` days** (default 21, the notebook used 90):
   - Pull the plan in a **1-minute window** around the target time.
   - Keep the largest `gtfs_ride_id` group.
   - Compute the **canonical stop signature** = `tuple(plan["name"])`.
   - **Skip the day if the signature differs from the reference day's.**
   - Pull GPS for the same 1-minute scheduled-start window; dedup; keep the largest
     `siri_ride__id` group.
3. **Match pings to stops** — nearest planned stop by Euclidean distance in
   lon/lat, **masked to ±20 minutes** of that stop's planned elapsed time.
4. **Per-stop elapsed** per day = mean elapsed of the pings assigned to that stop.
5. **Average across days**, with two guards (below), and render.

### The two guards on the average

**Minimum days per stop.** Days cover very different subsets of the route (GPS
drops out, trails start late). A naive per-stop mean can take stop 12 from a slow
day and stop 13 from a fast one, producing an "average" trip that runs *backwards*
along the route — a journey no bus ever made. Stops measured on fewer than
`max(2, (n_days+1)//2)` days are excluded from the average and counted in the notes.

**Monotonic clamp.** Whatever survives should still climb: a bus cannot reach a
later stop earlier. Residual dips are nearest-stop mis-assignment, not a reversing
bus, so they are clamped forward and the count is reported.

### The map's weighting

Pings are pooled per stop across all matched days and averaged with weight
`1 / (distance + 1e-6)`, so pings that passed closest to a stop dominate its
position. **This is why the measured route can bow away from the planned one** —
it is rebuilt from where buses actually were, not the timetable's coordinates.

## Reasoning

**Why the canonical stop signature matters.** One `line_ref` serves several stop
patterns. Averaging across them silently blends two different journeys into a
number describing neither. The notebook's check is ported faithfully and skipped
days are reported by category (`no_plan` / `route_mismatch` / `no_actual`) so
"different journey" is visibly distinct from "missing data".

**Why nearest-stop matching is gated by time.** Distance alone mis-assigns pings on
routes that loop back near themselves — a much-later ping matches an early stop.
The ±20 min mask is ported unchanged.

**Why the by-day card compares to the plan *up to the same stop*.** A day whose GPS
died halfway would otherwise be scored as an impossibly quick trip. Each day is
measured to its **last resolved stop**, and the plan is truncated to match.

**Why the window shrank from 90 days to 21.** The notebook demanded 20 matched days
before averaging; that is minutes of API calls. A dashboard card cannot make
someone wait. The shape of the result is the same, the confidence is lower, and the
notes say exactly that.

## Findings

### 1. One `line_ref` runs several distinct stop patterns, and they must not be averaged together — **confidence: High**

The signature check exists because it fires. Days are routinely skipped as
`route_mismatch` — the same line number, the same departure minute, a different
journey. Any planned-vs-actual analysis that groups by line number alone is mixing
these. Mechanistically clear and visible in the per-run skip counts.

### 2. Nearest-stop matching produces route-order violations even after the time mask — **confidence: High**

The monotonic clamp fires on real data. Averaged trajectories dip backwards along
the route, which is physically impossible and therefore definitely mis-assignment.
The clamp count is reported per run.

### 3. GPS coverage of a single departure is patchy enough that a naive per-stop mean is invalid — **confidence: High**

The minimum-days-per-stop guard exists for the same reason and reports how many
stops it excluded. Both guards are self-documenting: they print what they caught.

### 4. Duplicate pings materially bias a distance-weighted average — **confidence: Medium**

Unlike a `min()` or `max()` aggregation where duplicates are harmless, a duplicated
ping carries its weight **twice** here, pulling the measured route toward whatever
happened to be reported twice. Measured at ~10% of rows repo-wide. Medium because
the mechanism is certain but the resulting positional bias was not quantified.

### 5. On a given line, where a departure is habitually late — **confidence: Medium**

The output the card exists for. Where the average sits right of the dashed plan,
that stop is habitually reached late, and the spread of the faint lines is how
consistent that is. Medium: typically well under the notebook's own 20-day
threshold, one route variant, one departure time.

### 6. The measured route bows away from the planned route in places — **confidence: Low**

Visually striking on the map, and it *may* show real deviation. But the weighted
average is over pings assigned by nearest-stop matching, which finding 2 shows
mis-assigns. A bow could be a genuine detour or an assignment artifact, and this
card cannot distinguish them. [route-divergence.md](route-divergence.md) measures
deviation properly, with haversine distance and no assignment step.

## Criticism

**Distance is Euclidean in raw lon/lat degrees**
([schedule_adherence_average.py:276](../analyses/schedule_adherence_average.py#L276)).
At Israel's latitude a degree of longitude is ~15% shorter than a degree of
latitude, so "nearest stop" is systematically biased toward east-west neighbours.
[route_divergence.py](../analyses/route_divergence.py) uses haversine for exactly
this reason and says so — the two cards disagree about how to measure the same
thing, and this one is wrong. The bias is small relative to the ±20 min time mask
doing most of the work, but it is free to fix.

**The monotonic clamp hides rather than reports the error.** Clamping forward makes
the line physically possible and the count is disclosed, but the clamped points are
still drawn as if measured. A gap would be more honest than a flat segment
fabricated to preserve monotonicity.

**`line_ref` defaults to a hardcoded `"18663"`** with a dropdown of 8 "well-tracked"
lines ([schedule_adherence_average.py:289](../analyses/schedule_adherence_average.py#L289)).
Fine for a demo, but a card whose default is a known-good line will systematically
overstate how well the method works on an arbitrary line.

**`ISRAEL_TZ` is a fixed `UTC+3`**
([schedule_adherence_average.py:61](../analyses/schedule_adherence_average.py#L61)),
not `ZoneInfo("Asia/Jerusalem")`. Israel is UTC+2 in winter. Every other module in
the repo uses `ZoneInfo`, and [orion's caveat 5](days-with-no-cancellations.md)
documents a fixed +3 spilling a 16th day into a 15-day November window. With a
21-day default window in August this is currently harmless; on a winter date range
it shifts the anchor hour by an hour and will silently anchor on a different
departure. **This is a live bug, not a stylistic difference.**

**The 1-minute matching window is brittle.** A day whose departure was retimed by
even 90 seconds in the published GTFS is counted as `no_plan` — indistinguishable
in the skip counts from a day the line genuinely did not run.

**Three cards, one fetch, three chances to mislead.** All three read the same
`_load` result, so any resolution error propagates identically to all of them. Three
agreeing cards look like corroboration and are not.
