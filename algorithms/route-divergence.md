# Route Divergence Analysis — "Buses that strayed from the planned route"

**Author:** team (`author="team"` in the registry)
**Code:** [analyses/route_divergence.py](../analyses/route_divergence.py)
**Cards:** `route-divergence` ("Buses that strayed from the planned route"), `route-divergence-map` ("Where buses leave the route")
**Data:** Stride `/route_timetable/list` (planned stops) + `/siri_vehicle_locations/list` (actual GPS pings)

## What it answers

- **Did a vehicle detour or stray from its published route?** Measures the physical distance of actual bus coordinates from their planned route stops to identify unauthorized detours or feed mis-assignments.
- **Where did the detour happen?** Maps planned stops alongside the physical clusters of off-route GPS pings.

## Algorithm

1. **Resolve Route:** Disambiguates `route_short_name` to its `line_ref` and `operator_ref` using GTFS.
2. **Define Window:** Sets a 4-hour morning window (07:00–11:00 Israel Time) on a recent service weekday.
3. **Fetch Coordinates:**
   - Planned stop coordinates are fetched from `/route_timetable/list` and deduplicated to construct the stop location universe.
   - Actual GPS coordinates are fetched from `/siri_vehicle_locations/list` and deduplicated to drop repeated pings.
4. **Distance Calculation:**
   - For each GPS ping, calculates the distance to every stop in the planned stop universe using the **Haversine great-circle distance** formula.
   - Takes the minimum distance as that ping's "off-route distance."
5. **Classify Divergence:**
   - A ping is classified as "off-route" if its minimum distance exceeds `threshold_m` (default 500m).
   - Groups pings by ride. Keeps rides with $\ge 5$ pings to filter out isolated GPS noise.
6. **Rendering:**
   - **Bar Chart:** Shows the maximum (worst) off-route distance per sampled ride, sorted worst-first.
   - **Interactive Map:** Plots planned stops as blue points and off-route pings as red points.

## Reasoning

**Why the Haversine formula instead of Euclidean degrees.** Israel lies at a latitude of approximately 31°N–33°N, where a degree of longitude is shorter than a degree of latitude by about 15%. Simple Euclidean calculations would systematically underestimate east-west distances compared to north-south distances, making the threshold mean different things in different parts of the country.

**Why nearest stop instead of nearest shape line.** Calculating the shortest perpendicular distance to a complex GTFS road shape (polyline) is a heavy geometric operation. Comparing GPS pings directly to stop coordinates is extremely fast, requiring no spatial databases, and is perfectly suited for a lightweight live card.

## Findings

### 1. Route divergence patterns are highly clustered geographically — **confidence: High**
Plotting off-route pings on the map reveals tight geographical clusters along specific alternative streets rather than a random scatter. This proves that drivers are taking systematic detours (such as avoiding a congested junction or skipping a narrow street), which represents a deliberate operational change rather than GPS tracking noise.

### 2. GTFS database mis-assignments trigger false-positive alerts — **confidence: Medium**
Some "diverged" runs exhibit 100% off-route pings from start to finish. Investigating these runs reveals that the vehicle is operating a completely different route (such as Line 24 instead of Line 23) but is broadcasting under the wrong line identifier in the SIRI feed, revealing data registration errors rather than physical detours.

## Criticism

**Express segment distortion.** Measuring the distance to the "nearest stop" as a proxy for "distance from route" fails on express segments. An express bus traveling on a highway between two stops that are 10km apart is perfectly on-route, yet it may physically be 5km away from both stops. This creates massive false-positive divergence alerts unless the threshold is set to several kilometers, which in turn makes the algorithm blind to urban detours on the same line. The correct solution is to measure the perpendicular distance to the actual GTFS polyline route shape.
