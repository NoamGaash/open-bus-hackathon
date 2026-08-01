# Planned vs. Real-Time Bus Arrival Analysis — "Where the timetable is optimistic"

**Author:** noamf2001 (`author="noamf2001"` in the registry)
**Code:** [analyses/bus_arrival_reliability.py](../analyses/bus_arrival_reliability.py) and upstream package [PublicTransportHackathon](../repos/PublicTransportHackathon)
**Cards:** `bus-segment-reliability` ("Where the timetable is optimistic"), `bus-marey-diagram` ("Where the bus loses time"), `bus-hourly-heatmap` ("Which segments break down at rush hour")
**Data:** Stride `/route_timetable/list` (planned timetable, stop names, and coordinates) + `/siri_vehicle_locations/list` (actual GPS pings)

## What it answers

- **Where is the timetable optimistic?** Compares actual stop-to-stop segment travel times against what the schedulers published in GTFS.
- **Where does the bus lose time, and how predictable is it?** Plots individual bus trajectories over time and distance (Marey time-space diagram) to see where slopes flatten (delays) and how much trajectories fan out (unreliability).
- **Which segments break down at rush hour?** Maps a segment × departure hour matrix colored by the actual/planned travel time ratio to identify exactly when and where gridlock forms.

## Algorithm

1. **Resolve Route:** Disambiguates a general line number (`route_short_name`) to a specific `line_ref` and `operator_ref` using `/gtfs_routes/list`. Accepts user options for city or direction to pin down route variants.
2. **Fetch Plan and Stops:** `/route_timetable/list` retrieves the planned arrival times, stop sequences, stop coordinates, and Hebrew stop names for the specified route on the sampled dates. This acts as the single source of truth for the stops universe.
3. **Fetch Actuals:** `/siri_vehicle_locations/list` retrieves GPS pings for candidate SIRI rides. Because of the 15,000-row request limit and 60-second server statement timeout, a stratified sample of rides across date and hour is fetched (capped at 40 rides total).
4. **Geometrical Arrival Time Derivation:**
   - For intermediate stops, actual arrival is the moment of the vehicle's **closest approach** to the stop's coordinates, linearly interpolated between the two bracketing GPS pings.
   - For the **origin terminal**, using closest approach would land mid-idle and inflate the first segment. The algorithm instead uses the **last ping within vicinity** (departure moment) before the bus leaves.
   - **Monotonicity Guard:** For coincident/junction stops (meters apart with identical scheduled times), a forward-constrained sequential search is applied (stop $k$ can only match pings at or after the matched ping for stop $k-1$). Non-positive segment durations are dropped.
   - **Unmatched Stop Filter:** If the closest approach exceeds `max_dist_m` (default 300m), it is marked `NaN` and skipped, dropping only the segments touching it.
5. **Aggregate & SURF Uncertainty:**
   - Carries two telemetry quality metrics per derived arrival: `match_distance_m` (how close the bus got) and `resolution_s` (time gap between the bracketing pings).
   - Reduces these metrics plus sample counts to a segment `confidence` verdict: `implausible value` (ratio < 0.25 or > 4.0) $\rightarrow$ `few samples` $\rightarrow$ `patchy coverage` $\rightarrow$ `coarse GPS timing` $\rightarrow$ `loose stop match` $\rightarrow$ `ok`.
6. **Visualization Rendering:**
   - Re-implements Recharts-based React equivalents of the upstream matplotlib figures (`segment_bars`, `marey_diagram`, `hourly_heatmap`) to allow live interaction.
   - Flags low-confidence segments with **visual hatching** and text labels rather than omitting them, ensuring data gaps are visible.

## Reasoning

**Why geometric closest approach instead of purpose-built endpoints.** Probing the Stride API established that `/siri_ride_stops/list`'s precomputed matching columns and `/stop_arrivals/list` return only planned times (actual columns are 100% null). Deriving arrival times geometrically from raw GPS pings and GTFS coordinates was the only viable way to obtain actual stop arrival times.

**Why "Flag, never drop."** In earlier iterations, segments with fewer than `min_samples` were dropped entirely. However, an absent segment on a chart is indistinguishable from a segment that does not exist. SURFing uncertainty and using visual hatching preserves the geographic integrity of the line while highlighting thin data.

**Why Hebrew logical text order.** Matplotlib >= 3.11 applies the Unicode Bidirectional Algorithm natively through HarfBuzz. Reversing strings beforehand (via `python-bidi`) would double-reverse them and render Hebrew backwards (e.g., `eman` for `name`). Passing plain logical order ensures correct rendering.

## Findings

### 1. Schedulers are chronically optimistic about travel times on intermediate segments, leaving no margin for traffic — **confidence: High**
Across multiple analyzed routes (e.g., Line 23 of Dan), median actual durations frequently overshoot planned times on intermediate segments, particularly in dense urban areas. The scheduled times resemble "free-flow" durations rather than realistic schedules. This leads to cumulative delays that cascade downstream, leaving zero recovery margin.

### 2. Delay accumulation is highly segment-specific and hour-specific — **confidence: High**
Heatmap analysis reveals that travel time degradation is not uniform. The actual/planned ratio balloons up to 2.5× on specific bottleneck segments during morning (07:00–09:00) and evening (16:00–18:00) rush hours, while other segments of the same line run exactly on time or even faster.

### 3. Matplotlib's Hebrew warning machinery causes major API CPU bottlenecks — **confidence: High**
Matplotlib warnings about missing glyphs in standard Hebrew fonts (Noto Sans Hebrew, etc.) are emitted once per glyph per call site, accumulating to over 8,000 warnings in a single test session. The CPU cost of generating these warnings (not the actual image rendering) can lock up the API. Implementing a robust warning filter and caching figures based on their parameters solved the lockup.

## Criticism

**Noise in short segments.** Because GPS pings are reported once a minute, derived arrivals have a precision limit of ±30s. For consecutive urban stops that are physically less than 60s apart, a single ride's derived segment duration is mostly noise. The analysis relies heavily on multi-ride aggregation to extract any signal, making individual ride views on short segments highly deceptive.

**API query overhead.** Fetching a single line's sampled GPS pings requires chunking requests by ride id to bypass the 15,000-row limit and 60-second server statement timeout. This results in heavy I/O overhead (~1-2 minutes per line) and forces the dashboard to rely on aggressive caching. It is a powerful local POC but does not scale to a real-time nationwide monitoring system without a dedicated pre-aggregated database mirror.
