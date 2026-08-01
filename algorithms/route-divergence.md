# Route divergence — buses that strayed from the planned route

**Author:** team
**Code:** [analyses/route_divergence.py](../analyses/route_divergence.py)
**Cards:** `route-divergence`, `route-divergence-map`
**Data:** Stride `/route_timetable/list` (planned stop coordinates) + `/siri_vehicle_locations/list` (GPS)

## What it answers

One of the three questions the team wanted answered from open data: **can we spot a
vehicle that diverged from its published route?**

Yes, and fairly directly. GTFS has the planned stop coordinates; SIRI reports where
the bus actually was. For each GPS ping, the distance to the **nearest planned stop**
is how far off-route the bus was at that moment.

- **route-divergence** — how far each sampled ride strayed, worst first, showing
  both the worst point and the median.
- **route-divergence-map** — planned stops against every ping beyond the threshold,
  so "where does this line go wrong" is answerable by looking.

## Algorithm

1. **Pick a day** — `date_to` clamped 3 days back for SIRI lag, then walked
   backwards past Fri/Sat.
2. **Window** — 07:00 + 4 hours Israel time. A bus reports ~once a minute, so a few
   hours of one line is a few thousand pings: enough to characterise a route,
   quick enough for a card.
3. **Planned stops** — `/route_timetable/list`, one line, one day.
   `drop_duplicates(["lat","lon"])` → one row per distinct stop location, which is
   all the distance test needs and keeps the distance matrix small.
4. **Pings** — `/siri_vehicle_locations/list` filtered on `siri_routes__line_ref`
   (see below), deduped.
5. **Distance** — `_haversine_m` broadcast over (pings × stops), take the **row
   minimum**: metres from each ping to its nearest planned stop.
6. **Per ride** — `worst_m = max`, `median_m = median`, `pings = size`. Rides with
   **fewer than 5 pings are dropped** — a handful of pings can look dramatic off one
   bad fix.
7. **Report both columns**, worst-first, top 40 rides. The map colours strays by how
   far out and evenly samples down to 600 markers.

## Reasoning

**Why haversine and not Euclidean degrees.** From the code comment: *"Plain
euclidean degrees would understate east-west distance by ~15% at Israel's latitude
and make the threshold mean different things north to south, so the extra trig is
worth it here."* This is the only card in the repo that gets this right —
[siri-coverage](siri-coverage.md) and [schedule-adherence](schedule-adherence.md)
both use raw degree distance for the same kind of operation.

**Why nearest *stop* rather than distance from the route's road geometry.** GTFS
shapes give the road, but stop coordinates are what this project already fetches
everywhere else, and a bus 800 m from every stop on its own line is off-route by any
reasonable reading. The cost — long stop spacing inflates the distance without the
bus having gone anywhere wrong — is handled three ways rather than hidden: the
threshold is a user option, the **distribution** is shown rather than a pass/fail
count, and the notes say so plainly.

**Why both worst and median.** One bad point is a GPS glitch; a whole ride out there
is a real detour. Showing both makes the distinction the reader's to draw, and the
notes name the median as the stronger signal.

**Why ≥5 pings.** The median is only meaningful with a real trail behind it.

**Why the map samples evenly rather than taking the worst N.** So it still shows
*where* strays happen instead of only the single most extreme cluster.

## Findings

### 1. `stride.siri_vehicle_locations(lines=…)` silently returns the whole country's pings — **confidence: High**

**The most dangerous defect found during the hackathon.** The wrapper's `lines=`
argument maps to `gtfs_route__route_short_name`, which
`/siri_vehicle_locations/list` **ignores**. It does not error, does not warn, and
does not return an empty set — it returns *every* ping in the time window, from
every line in the country, which the caller then treats as belonging to their line.

How it was caught, per the code comment: divergence came back at **50 km and 97.7%
of pings**. The bus was not off route; the pings belonged to other lines entirely.

High confidence: reproducible, mechanism identified (a filter the endpoint ignores),
and the symptom is unmistakable *once you know to look*. The reason it matters is
that on a less extreme analysis it would not be unmistakable at all — it produces a
plausible wrong answer. [gps_trace_map.py](../analyses/gps_trace_map.py) carries the
same warning and would have mislabelled an unrelated bus as line 23.

### 2. Haversine vs Euclidean-degrees changes east-west distance by ~15% at Israel's latitude — **confidence: High**

Geometry, not measurement. Stated as the justification for the extra trig, and it
means the two cards using raw degrees carry a systematic direction-dependent bias.

### 3. Duplicate SIRI pings bias divergence toward stationary buses — **confidence: Medium**

Left in, duplicates weight a stationary bus more heavily than a moving one — a
different failure from the inflated-count problem other cards cite, because here
each ping is a *sample* of position. Mechanism is clear; magnitude unquantified.

### 4. Off-route rates and locations for any given line — **confidence: Low**

The card's output. One line, one day, one 4-hour window, and the threshold is an
arbitrary 500 m default. The card is explicitly built so the threshold "stays the
reader's to argue with", which is the right call — but it also means the card does
not itself assert a finding.

### 5. A tight cluster of strays in one place is a real diversion; scattered points are GPS error — **confidence: Medium**

An interpretive rule stated in the notes rather than a measured result. It is sound
reasoning — systematic deviation is structural, random deviation is noise — but no
clustering test is implemented, so the reader is doing the statistics by eye.

## Criticism

**Defaults are hardcoded to line 23, operator דן**
([route_divergence.py:138](../analyses/route_divergence.py#L138)). Unlike other cards
here, there is no auto-discovery of a tracked line, so the filter-free view always
shows the same route.

**One day, one 4-hour morning window, 40 rides.** Structurally cannot see a recurring
weekly diversion, an afternoon-only roadworks detour, or anything outside 07:00–11:00.
The subtitle states the window; the title ("Buses that strayed from the planned
route") does not.

**Nearest-stop distance conflates three different things** the card cannot separate:
a genuine detour, a long stop-free stretch of a correct route, and a ping
mis-assigned to this line. The notes cover the second and the title covers the
first — the third is only avoidable because finding 1 was caught.

**No distance ceiling on what counts as "the line's stops".** `drop_duplicates` on
lat/lon over a day's timetable will include every variant of the route that ran that
day, since `/route_timetable/list` is filtered by `line_refs` for the whole day. A
line whose alternatives fan out over a wide area therefore gets a *more* forgiving
off-route test than a line with one fixed path — the opposite of what you want.

**`threshold * 1.5` in the map legend does not match the code.** The legend labels
the orange bucket `Off route (< {threshold*1.5}m)`, but the actual split is on
`frac > 0.5` where `frac = (dist - threshold) / (worst - threshold)` — i.e. the
midpoint between the threshold and *the worst observed stray on that day*, which is
usually nowhere near `1.5 × threshold`. The legend is wrong, and it is wrong in a
data-dependent way, so it looks right on some days.
([route_divergence.py:274](../analyses/route_divergence.py#L274) vs
[:297](../analyses/route_divergence.py#L297))

**The operator filter is applied inconsistently.** `ping_params` only sets
`siri_routes__operator_ref` when `req.operator` is truthy, while the *plan* always
comes from `routes.iloc[0]` of a possibly operator-filtered lookup. With no operator
selected, pings from every operator running that `line_ref` are compared against one
operator's stop list.
