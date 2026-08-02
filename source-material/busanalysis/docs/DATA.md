# Data sources, and what the repo does and does not ship

## The two datasets, in one paragraph

Israel publishes two national bus datasets, and this project's entire contribution is comparing
them.
The **timetable** is what operators commit to run — every scheduled departure, published as GTFS
files (the standard transit-schedule format).
The **tracking record** is what buses actually report while driving — position updates streamed as
SIRI (the standard real-time transit format).
Both reach this project through **stride**, hasadna's public database, which ingests and stores
them.
A "missing departure" in this analysis is a scheduled departure with no matching real departure in
the tracking record within a stated time window.

## Sources

| Source | Provides | Access | Licence | Read by |
|---|---|---|---|---|
| **stride** (hasadna) | GTFS planned rides + SIRI actual rides; the primary source for everything here | read-only Postgres (credentials) and a public REST API at `open-bus-stride-api.hasadna.org.il` | MIT code; data originates from the Ministry of Transport | `pipeline/db.py`, `pipeline/mirror.py` |
| **MoT tikufim** (data.gov.il) | ridership — clearing-house validations per station, annual files 2020→2026 | CKAN datastore (active, no download needed) | "אחר (פתוח)" — other (open) | not used in the shipped analysis (see below) |
| **GTFS archive** (S3) | route geometry, fare zones (`Tariff.zip`), `ClusterToLine.zip` — absent from stride | public S3 | MoT open data | geo prep for `viz/city_map.py` |
| **OpenStreetMap** | basemap tiles for the interactive map only | tile server at view time | ODbL | the map panel in the browser, not the pipeline |
| **MoT enforcement publications** | the published per-operator violation rates used as the M1 benchmark | published semi-annually | public | transcribed into `report/metrics/enforcement_gap/` |

Full detail, including endpoint quirks and verified join keys, is in
[`../data/registry/PROVENANCE.md`](../data/registry/PROVENANCE.md) — that file is authoritative
and this table is a summary of it.

**On tikufim:** the ridership join is *not* in the shipped analysis. The reason is structural and
worth knowing before anyone plans it: tikufim is **station × time-bucket × day** with **no line and
no operator dimension**, while execution is line/ride-level. So demand × execution can only be
joined at the stop level, which needs `siri_ride_stop` work. It is the biggest unoccupied piece of
ground this project identified and did not take.

## What ships, and what you must rebuild

**Committed (usable immediately, no credentials):**

| Path | Size | What it is |
|---|---|---|
| `src/`, `tests/` | small | the pipeline and its 395 tests |
| `report/dashboard/*.html` | 11.9 MB | **the deliverables** — both pages, self-contained |
| `report/metrics/**/*.parquet` | ~9 MB | every metric output; re-check any number without a rebuild |
| `report/metrics/**/summary.md` | small | a written summary per metric |
| `report/figures/**` | ~22 MB | every figure, static PNG + interactive HTML |
| `data/warehouse/marts/operator_month.parquet` | 90 KB | the one warehouse file the pages need, so a bare clone can rebuild them |
| `assistant/`, `plans/`, `docs/` | small | findings ledger, verification memos, decisions, dead ends, plans |

**Not committed (rebuild locally):**

| Path | Size | Rebuild with | Needs credentials |
|---|---|---|---|
| `data/warehouse/mirror/` | ~4.5 GB, 245M rows | `pipeline.mirror` | **yes** |
| `data/warehouse/matched/` | ~2.7 GB, 1,306 day partitions | `pipeline.stage1_days` | no |
| `data/warehouse/marts/route_day.parquet` | 87 MB, 8.4M rows | `pipeline.marts rebuild` | no |
| `data/raw/`, `resources/*.pdf` | varies | re-download from source | no |

Total warehouse footprint if you rebuild everything: **about 7 GB**.
Stage-by-stage commands, with which ones were verified by running them, are in
[REPRODUCE.md](REPRODUCE.md).

## Credentials

Five variables in a gitignored `.env` at the repo root:
`STRIDE_PGHOST`, `STRIDE_PGPORT`, `STRIDE_PGUSER`, `STRIDE_PGPASSWORD`, `STRIDE_PGDATABASE`.
Copy [`../.env.example`](../.env.example) and fill it in; ask in the hasadna Slack `#open-bus`
channel for read-only access.

`.env` has never been committed and is not present anywhere in this repository's git history —
verified before publication.
`src/busanalysis/pipeline/db.py` enforces the access etiquette rather than trusting callers:
`conn.read_only = True`, a 5-minute `statement_timeout`, an explicit `application_name` so the load
is identifiable in `pg_stat_activity`, and a fail-fast `connect_timeout`.
Only pipeline stages 1–2 need credentials at all.

## Data-model gotchas that will bite a newcomer

These are the four that cost this project the most time. Each is a property of the source data, not
of this code.

**1. GTFS tables are daily snapshots — route and stop identity are not stable across days.**
`gtfs_route.date` and `gtfs_stop.date` mean each day has its own rows. A `gtfs_route_id` from
Tuesday is not the same line as the same id on Wednesday.
*What breaks:* any longitudinal analysis keyed on `gtfs_route_id` silently compares different
lines.
*What this project does:* uses `route_mkt` for line identity over time.

**2. Arrival times are inferred, never observed.**
Stop-level timing comes from `siri_ride_stop.nearest_siri_vehicle_location_id` plus
`distance_from_siri_ride_stop_meters` — i.e. the nearest position report, at some distance.
*What breaks:* treating any stop time as an observed arrival. That distance column is the quality
gate for every stop-level metric.
*What this project does:* stays off stop-level timing entirely. It is why metric M2 measures
**waiting** rather than lateness, and why actual punctuality is on the roadmap rather than in the
findings.

**3. `scheduled_start_time` drifts, and only the first value is kept** (hasadna issue #390).
*What breaks:* exact-equality joins on scheduled time. On a healthy control day, exact matching
recovers 74.3% of rides where a ±5 min window recovers 92.0%. It also creates duplicate ride rows
— see [F6](../handoff/issues/F6-duplicate-rides.md).
*What this project does:* matches within explicit tolerance windows, never on equality, and
deduplicates first.

**4. `siri_vehicle_location` has roughly 6.4 billion rows.**
*What breaks:* any query that touches it, on a laptop or on shared infrastructure.
*What this project does:* never queries it. The design mirrors four slim ride-level tables instead
and does all matching locally — that constraint is what makes the whole reconstruction feasible.
See [ARCHITECTURE.md](ARCHITECTURE.md).

Also worth knowing: every stride timestamp this pipeline reads is `timestamp without time zone` on
a local clock, and `mirror.py` declares each column's PostgreSQL type explicitly to keep it that
way. A `timestamptz` would arrive UTC-aware and shift the whole service day, quietly corrupting
every time difference downstream.

## Aggregate-only policy

No vehicle- or driver-level identifier appears in any committed artifact. The coarsest committed
grain is route × month.

This is a hard rule, not a preference: SIRI data can identify individual drivers' shifts, and this
project will not be used that way. It was verified mechanically before publication — all 20
committed metric parquets were scanned for `vehicle_ref`, driver, ride-identity, plate and licence
columns. None present.
