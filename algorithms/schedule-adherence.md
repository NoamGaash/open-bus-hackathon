# Multi-Day Schedule Adherence — "How much does the same departure vary?"

**Author:** yuvalko1 (`author="yuvalko1"` in the registry)
**Code:** [analyses/schedule_adherence_average.py](../analyses/schedule_adherence_average.py)
**Cards:** `schedule-adherence-average` ("How much does the same departure vary, day to day?"), `schedule-adherence-map` ("Planned route vs. where buses actually were"), `schedule-adherence-by-day` ("Which day ran worst?")
**Data:** Stride `/route_timetable/list` (planned) + `/siri_vehicle_locations/list` (actual)

## What it answers

- **How much does the same departure vary day to day?** Displays a stringline diagram of a single daily departure time tracked across multiple weeks.
- **Where are the physical stop coordinates in reality?** Maps the GTFS planned route dashed against a solid actual route, where stop coordinates are derived from physical GPS pings.
- **Which specific days had the worst service failures?** Displays total journey times across individual matched days against the schedule to identify outliers.

## Algorithm

1. **Reference Selection:** Resolves a user-selected or default `line_ref` to extract its scheduled departures.
2. **Day-by-Day Historical Scan:** Walks backward in time (up to `days_back` limit, default 21) to find occurrences of the same daily departure time.
3. **Canonical Stop Signature Filter:**
   - A day is included in the multi-day average **only if its scheduled stop sequence matches the reference day's sequence exactly**.
   - One `line_ref` can serve multiple route alternatives or express sub-variants. If stop signatures were not filtered, the algorithm would average different physical journeys together.
4. **Time-Gated Nearest-Stop Matching:**
   - Matches GPS pings to planned stops. A ping matches the closest stop only if it is within `MATCH_TOLERANCE_MIN = 20` minutes of the stop's planned elapsed travel time.
   - This time gate prevents false-matching on routes that loop back or pass near their own stops earlier/later in the journey.
5. **Distance-Weighted Geographic Interpolation:**
   - For the physical map, stop coordinates are calculated as an inverse-distance weighted average ($1 / \text{distance}$) of all matching GPS pings.
   - Pings passing closest to the stop coordinates dominate the averaged position, resulting in a smooth actual route shape.
6. **Largest Group Keep:** When a single time window catches multiple ride IDs, the algorithm keeps only the largest group to avoid blending unrelated vehicle telemetry.

## Reasoning

**Why stop signature verification is essential.** Buses on the same route number often bypass specific stations on certain days or runs (such as school variants or weekend detours). Averaging these runs together would result in "merged" ghost stops and nonsense durations. Signature verification preserves analytical purity.

**Why inverse-distance weighted averaging.** Simple centroid averaging of GPS pings near a stop would shift the derived coordinate toward the side of the street where the bus spends more time idling or where the ping cadence happens to land. Inverse-distance weighting anchors the derived stop coordinate directly to the point of closest physical approach.

## Findings

### 1. Daily schedule adherence is highly volatile even for the same operator and driver slot — **confidence: High**
Stringline diagrams reveal that the "unreliability fan" expands rapidly as the route progresses. Buses that leave the terminal on schedule drift apart by up to 15–20 minutes by the end of an urban route.

### 2. Physical bus stop coordinates consistently diverge from GTFS coordinates — **confidence: High**
The schedule-adherence map shows that actual GPS closest approaches are frequently offset by 15–80 meters from their published GTFS coordinates. These offsets are due to temporary station relocation, bus bay geometry, or GTFS entry errors.

## Criticism

**Extremely high API request cost.** Fetching 21 days of history requires scanning back day-by-day, costing 2 API requests (1 timetable + 1 GPS ping fetch) per scanned day. This represents ~42 API requests per card load. The live dashboard card is limited to a 21-day window, whereas the original notebook scanned 90 days.

**Discards multi-vehicle runs.** By keeping only the largest `siri_ride__id` group, the algorithm discards secondary vehicles running in tandem on the same schedule slot (such as overloaded high-frequency school buses or relief services), hiding the true operational capacity.
