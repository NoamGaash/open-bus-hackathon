# GPS Trace Map — "One bus, actual GPS trace"

**Author:** yuvalko1 (`author="yuvalko1"` in the registry)
**Code:** [analyses/gps_trace_map.py](../analyses/gps_trace_map.py)
**Cards:** `gps-trace-map` ("One bus, actual GPS trace")
**Data:** Stride `/siri_vehicle_locations/list` (actual GPS pings)

## What it answers

- **What does the physical path of a single bus ride look like?** Plots a single real ride's raw GPS pings on an interactive map, colored chronologically to trace the vehicle's progress.

## Algorithm

1. **Resolve Route:** Disambiguates `route_short_name` to a `line_ref` and `operator_ref` using GTFS.
2. **Define Window:** Sets a 4-hour morning window on a recent service day (excluding Friday/Saturday) to maximize the probability of capturing a moving bus.
3. **Fetch GPS Pings:** `/siri_vehicle_locations/list` fetches all GPS pings for that line/operator within the time window.
4. **Select Single Ride:** Groups pings by `siri_ride__id` and keeps the ride with the largest number of pings to guarantee a complete visual trail.
5. **Deduplicate:** Drops duplicate pings matching on `(siri_ride__id, recorded_at_time, lat, lon)`.
6. **Chronological Gradient Coloring:**
   - Normalizes each ping's timestamp relative to the ride's total duration to a value $t \in [0, 1]$.
   - Linearly interpolates hexadecimal colors along a Viridis-style gradient: `#440154` (purple, start) $\rightarrow$ `#31688e` (blue) $\rightarrow$ `#35b779` (green) $\rightarrow$ `#fde725` (yellow, end).
7. **Map Rendering:** Exports the coordinates and hex colors as a GeoJSON FeatureCollection containing colored points and a connecting line, which is rendered on an interactive Leaflet map.

## Reasoning

**Why chronological gradient coloring.** A uniform line color shows the path but hides speed and direction. By mapping elapsed time to a color gradient, the map shows where the bus was moving quickly (pings spaced widely in the same color range) and where it was delayed/stuck (clusters of pings sharing identical colors).

## Findings

### 1. Raw GPS pings are highly detailed but subject to transmission lag and coordinate jitter — **confidence: High**
Visualizing raw trails reveals that while pings generally align with road geometry, there are frequent GPS offsets (jumping across blocks) and tracking dropouts of several minutes, illustrating the necessity of interpolation in segment-duration calculations.

## Criticism

**Exploratory, not analytical.** While the map is visually impressive, it shows only a single ride. It provides no aggregate statistics about route reliability or operator performance. It is a powerful presentation tool but offers zero diagnostic power for network-wide transit planning.
