# SIRI GPS Coverage Analysis — "SIRI GPS coverage vs planned stops"

**Author:** yuvalko1 (`author="yuvalko1"` in the registry)
**Code:** [analyses/siri_coverage.py](../analyses/siri_coverage.py)
**Cards:** `siri-coverage` ("SIRI GPS coverage vs planned stops")
**Data:** Stride `/route_timetable/list` (planned stops) + `/siri_vehicle_locations/list` (actual GPS pings)

## What it answers

- **What fraction of planned stops actually got a matching GPS ping?** Measures the completeness of the real-time tracking feed along a bus line, aggregated by hour of day.

## Algorithm

1. **Resolve Route:** Disambiguates `route_short_name` to a specific `line_ref` and `operator_ref` using GTFS.
2. **Sample Dates:** Samples up to 3 days (excluding Friday/Saturday) to bound network fetch costs.
3. **Fetch Timetable and Pings:** Fetches the planned timetable stop list from `/route_timetable/list` and the actual GPS coordinates from `/siri_vehicle_locations/list`.
4. **Time-Gated Coverage Matching:**
   - For each planned stop, scans the raw GPS pings.
   - A ping is matched to a stop if it is the closest ping by distance **and** the time difference is within `MATCH_TOLERANCE_MIN = 20` minutes of the scheduled arrival time.
   - The time check prevents false matches on lines that loop back or return close to their origin stops.
5. **Aggregate by Hour:** Groups the matched stops by the planned departure hour of the ride and calculates the fraction of stops that successfully received at least one matching GPS ping.

## Reasoning

**Porting from a batch pipeline to a live card.** The original system-wide script scanned 90 days of data and performed expensive nearest-stop calculations, taking 1–2 hours to execute. This port keeps the exact core matching logic (`_ride_coverage`) but limits the sample to a maximum of 3 days. This reduces the response time to a few seconds, making it appropriate for a live dashboard card.

## Findings

### 1. Tracking coverage is highly uneven across lines, operators, and hours — **confidence: High**
Certain bus lines and operators exhibit consistent tracking "blackouts" where the real-time coverage drops below 40% during specific hours, while other lines maintain 95%+ coverage. This indicates systematic issues in on-vehicle GPS tracking devices or cellular network transmission rather than actual service failures.

## Criticism

**Conflates tracking failure with non-operation.** A bus that ran perfectly but had a broken GPS unit, or passed through a cellular dead zone (cellular canyons), will report 0% coverage. This is indistinguishable in the tracking feed from a cancelled ride (ghost ride). It should be reported strictly as a tracking feed quality metric, not as a transit service reliability metric.
