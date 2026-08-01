# Live re-verification, 2026-08-01 (before filing)

| Defect | Result | Evidence |
|---|---|---|
| A `total_actual_rides` = 0 | CONFIRMED | group_by, 4 dates: planned 121420/122088/53260/27327, actual 0/0/0/0 |
| B `route_short_name` ignored | CONFIRMED | 400 rows / 202 line_refs identical filtered vs unfiltered |
| E `actual_start_time` is a flag | CONFIRMED | 676 rows with both: 676 identical, 0 differing |
| E2 unplanned rides (planned null) | CONFIRMED, rate lower | 1.4% (write-up said 3-6%) |
| G1 route_timetable >1 day | CONFIRMED | 1-day OK; 3-day -> 500 |
| G3 row cap 15k/20k | CONFIRMED | 15000 OK; 20000 -> 500 |
| G4 silent default page size | CONFIRMED, varies | agg/list 1000, gtfs_routes 100, agencies 36 |
| H naive datetime | CONFIRMED | 500 Internal Server Error |

## Corrections to the hackathon write-ups (do NOT quote the old numbers)

1. orion's planned totals (3,498 / 3,510 / 3,227 / 3,927) were computed from
   `/gtfs_rides_agg/list` WITHOUT an explicit limit, so they are truncated
   samples of the default 1000-row page, not network totals. Real network
   planned totals via group_by are ~27k-122k. The actual=0 conclusion is
   unaffected and holds at every page size and via group_by.
2. The default page size is 1000 for /gtfs_rides_agg/list and 100 for
   /gtfs_routes/list - it varies per endpoint. The source repo's "~100 rows"
   was right for one endpoint, not universally.
3. Unplanned-ride rate measured at 1.4% on line 480 (write-up said 3-6% on
   line 2259). Both may be true per-line; quote as "1-6%, line-dependent".
