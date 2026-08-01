# GPS trace map — one real bus's actual path

**Author:** yuvalko1 — from `load siri vehicle locations to pandas dataframe.ipynb` ([github.com/yuvalko1/talpiot-hackathon-public-transportation](https://github.com/yuvalko1/talpiot-hackathon-public-transportation))
**Code:** [analyses/gps_trace_map.py](../analyses/gps_trace_map.py)
**Card:** `gps-trace-map`
**Data:** Stride `/siri_vehicle_locations/list`

## What it answers

A single real ride's raw GPS trail on a map, coloured by elapsed time.

This is the simplest card in the repo and makes no analytical claim. Its job is
**ground truth for the eye**: every other card turns pings into statistics, and this
one shows what the pings actually look like — so a reader can see the reporting
interval, the gaps, the clustering when a bus sits still.

## Algorithm

1. **Pick a day** — clamped 3 days back for SIRI lag, walked backwards past Fri/Sat.
   Window is 07:00 + 4 hours Israel time: a multi-hour late-morning window maximises
   the odds of catching a bus actually moving, rather than picking one exact minute
   and finding nothing.
2. **Resolve** `route_short_name` → `line_ref` via `/gtfs_routes/list` **before**
   fetching pings (see finding 1).
3. **Fetch** pings on `siri_routes__line_ref` + `siri_routes__operator_ref` +
   `recorded_at_time_from/to`, `limit=15000`.
4. **Dedup** on `(siri_ride__id, recorded_at_time, lat, lon)`.
5. **Pick one ride** — the `siri_ride__id` with the most pings in the window, the
   same "richest trail" choice the source notebook made.
6. **Render** — one LineString per consecutive pair plus one Point per ping, each
   coloured by normalised elapsed time along a viridis-style gradient
   (`#440154 → #31688e → #35b779 → #fde725`), matching the notebook's `branca`
   colormap. Every point's popup is its Israel-time timestamp.

## Reasoning

**Why segment-per-pair rather than one polyline.** Colour has to vary along the
trail, so each segment carries its own colour. A purple-to-yellow jump over a short
distance is the bus moving fast there; a dense cluster of one colour is it sitting
still. The gradient is doing analytical work, not decoration.

**Why the ride with the most pings.** A ride with 8 pings and one with 200 look
equally like "a trace" until you plot them; picking the richest gives the reader the
best available picture of what the feed actually provides.

**Why `geo()` rather than a baked folium export.** The notebook exported static
folium HTML. Porting onto `openbus_hack`'s client-rendered Leaflet helper keeps it
inside the shared contract, themed with everything else, and lets the frontend own
presentation.

## Findings

### 1. `stride.siri_vehicle_locations(lines=…)` maps to a filter this endpoint ignores — **confidence: High**

Same defect as [route-divergence](route-divergence.md) finding 1, documented
independently here: `lines=` sets `gtfs_route__route_short_name`, which
`/siri_vehicle_locations/list` ignores, so it hands back the whole country's pings.
For this card the consequence is spelled out precisely — *"this card would then label
some unrelated bus as line 23"*. Two authors hitting the same trap in two cards is
itself the argument for fixing it upstream rather than documenting around it.

### 2. `siri_ride__id` never spans two `vehicle_ref`s — **confidence: High**

Checked across **6,326 rides**. This is a genuinely useful schema invariant: it means
grouping by ride is safe without also keying on the vehicle plate, which several
other cards rely on implicitly. A census over a real population, not a spot check —
and the only card here that verified an assumption rather than asserting it.

### 3. Duplicate pings run ~10% of rows — **confidence: Medium**

Measured in a sample window. Here the effect is visible rather than statistical:
duplicates inflate the ping count in the subtitle and add zero-length map segments.
Corroborated by `lihay7/BusAnalysis` **F6** (2.56% surplus duplicate *rows* over a
116M-row census) — note the figures measure different things (duplicate ping rows
within a snapshot overlap vs. duplicate ride records), so they are consistent rather
than contradictory.

### 4. What a real SIRI trail looks like — **confidence: High, and not really a finding**

Pings roughly once a minute, gaps where the feed drops, clustering at stops. Directly
observable and the reason the card exists.

## Criticism

**It analyses nothing, by design — but it is presented alongside cards that do.**
On a dashboard grid it reads as one more piece of evidence. It is one bus, on one
morning, chosen for being the best-tracked. Nothing generalises from it, and the
notes do not warn against generalising.

**"The ride with the most pings" is a biased sample of exactly the wrong kind.** For
a card whose purpose is showing feed quality, selecting the best-covered ride in the
window shows the feed at its best. The honest complement — the *median* ride, or a
worst-tracked ride — would be more informative about what the data usually looks
like, and costs nothing.

**Defaults are hardcoded to line 23 / operator דן**, with no auto-discovery fallback
(unlike [siri-coverage](siri-coverage.md) or [bus-bunching](bus-bunching.md)). If
that line is untracked on the chosen day the card shows a no-data tile and suggests
trying another line, when it could have found one.

**The colour gradient is normalised per-ride** (`t_start` → `t_end` of that ride
only), so the legend's min/max labels change with every render. Two rides of very
different duration produce visually identical gradients, and a reader comparing two
loads of the card would be comparing different scales.

**Viridis is a sequential colormap used for a cyclic-ish quantity** (time of day
within one trip). That is fine here, but the same gradient is reused in
[schedule-adherence](schedule-adherence.md)'s map for "minutes since departure"
across *pooled* days — where the two cards' identical-looking legends mean
different things.
