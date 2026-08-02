# talpiot-hackathon-public-transportation

Exploring how well Israel's public transit SIRI (actual GPS) tracking matches the planned GTFS
schedule, using the [open-bus-stride-client](open-bus-stride-client-main/) API client.

## Notebooks (`open-bus-stride-client-main/notebooks/`)

- **`load gtfs timetable to pandas dataframe.ipynb`** / **`load siri vehicle locations to pandas dataframe.ipynb`** - the original example notebooks from the upstream project (loading one route's planned timetable / one vehicle's actual locations). Each got a plotting cell added: the route drawn on a matplotlib chart and on an interactive folium map, colored by time.
- **`compare gtfs planned vs siri actual.ipynb`** - unifies the two notebooks above: picks one ride, compares its planned stops against its actual recorded positions (matplotlib chart, folium map, and a stop-vs-time "stringline" diagram).
- **`compare_gtfs_siri_average.ipynb`** - the multi-day version. Samples a well-covered bus line, scans up to 90 days for every day that ran at the same time, and averages actual vs. planned per stop across all of them - both as a stringline chart and as a map where the "actual" route is a GPS-weighted spatial+temporal average, not just the plan re-colored.

## Script (`open-bus-stride-client-main/scripts/`)

- **`explore_gtfs_siri_coverage.py`** - a whole-system (bus-only) exploration: for every bus line, checks how much of its planned schedule actually got SIRI tracking. Runs in two stages - a cheap ride-volume scan to find which lines are worth the detailed check, then the expensive per-stop coverage computation only for those. Writes progress and results as live-updating CSVs under `scripts/output/`. See the script's own docstring for config and runtime notes.

## Notable gotchas found along the way

- `stride.iterate()`'s `limit=` kwarg is client-side only - the server silently defaults to ~100 rows unless `limit` is also passed inside the request params.
- `route_timetable/list` rejects any date range over 1 day; an unfiltered whole-system query times out server-side regardless of range.
- Nearest-stop GPS matching needs a time-plausibility check (not just distance) - a route that loops back near its own path can otherwise match a much-later ping to an early stop.
- `siri_vehicle_locations/list` only accepts a single `line_ref` per request; `route_timetable/list`'s `line_refs` does accept a comma-separated batch.
- This environment's usable historical data spans about the last 90 days, ending 2026-07-30.
