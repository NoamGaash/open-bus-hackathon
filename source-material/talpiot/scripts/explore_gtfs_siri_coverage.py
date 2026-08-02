"""
Data exploration (buses only): query the database first to work out which
lines/days are actually worth analyzing, then compute GTFS-planned vs actual
SIRI stop-level coverage only for that worthy subset, grouped into "unique
routes" by (line_ref, operator, direction, hour).

Output: a single CSV next to this script, in ./output/gtfs_siri_coverage_routes.csv

Two-stage design (found while exploring the API):
  Stage 0 - discover which days actually have service data at all, via a
    cheap gtfs_routes get_count per day (fast-skip empty days).
  Stage 1 - for every bus line_ref (route_type=3) active on those days, make
    ONE lightweight call to /rides_execution/list spanning the whole
    real-data window, to learn each line's total ride volume and how many
    rides have *any* recorded actual position. This is far cheaper than
    pulling raw SIRI pings (tiny payload: just planned/actual start times).
    A line only proceeds to stage 2 if it clears MIN_RIDES_FOR_WORTHY.
    Note: across a random sample, ride-level "any tracking" turned out to be
    near-universal for buses (min observed ~58%, most 100%) - it doesn't
    separate "worthy" from "unworthy" lines by itself. What it DOES give for
    free is the exact set of dates each line actually ran, and its true
    ride volume - so stage 2 below only fetches what's known to exist,
    instead of guessing across the whole scanned window.
  Stage 2 - only for lines that pass stage 1: for each specific day that
    line actually had rides (per stage 1, not every scanned day), fetch the
    planned GTFS timetable and actual SIRI pings and compute per-ride stop
    coverage (nearest-stop matching, with a time-plausibility tolerance so a
    route that loops back near its own path doesn't get a later ping
    falsely matched to an early stop).

Other scope notes:
  - route_timetable/list rejects requests spanning more than 1 day, and an
    unfiltered whole-system query (no line_refs) times out server-side.
  - siri_vehicle_locations/list only accepts a single line_ref per request
    (unlike route_timetable's line_refs, which accepts a comma-separated
    batch) and /rides_execution/list requires a single line_ref + operator_ref
    too - so everything here is fetched one line_ref at a time, concurrently
    (thread pool) to keep runtime reasonable.
  - Every request explicitly sets 'limit' inside the params dict itself -
    stride.iterate()/get()'s own limit handling is either client-side only
    or absent, and the server silently defaults to ~100 rows otherwise.
"""
import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dateutil import tz as _tz
from tqdm import tqdm

from stride import common as stride_common
from stride import config as stride_config

# ---- configuration ----
ROUTE_TYPE = "3"          # GTFS route_type - "3" is Bus. Rail (2), light rail/cable (0/5), taxi (8) excluded.
REFERENCE_DATE = datetime.date(2026, 7, 30)   # day-discovery scan starts here and goes backward
MAX_DAYS_TO_SCAN = 90                          # ~3 months
MIN_RIDES_FOR_WORTHY = 5  # a line needs at least this many planned rides across the whole real-data
                           # window to bother with the detailed (expensive) per-stop analysis
SAMPLE_DAYS_TARGET = 20   # stage 2 (expensive) only runs on this many days, evenly spread across the
                           # full scanned range, instead of every single day - full 3-month x all-lines
                           # stage 2 was estimated at ~20-30 hours; this keeps it in the ~1-2 hour range
MAX_WORKERS = 16          # concurrent requests - kept modest, this is a shared nonprofit API
MATCH_TOLERANCE_MIN = 20  # a SIRI ping only counts as covering a stop if within this many minutes of
                           # that stop's planned elapsed time - without this, routes that loop back near
                           # their own path can match a much-later ping to an early stop (false coverage)
REQUEST_LIMIT = 15000     # explicit server-side limit on every request (see module docstring)
CHECKPOINT_EVERY = 100    # rewrite OUTPUT_CSV every N completed stage-2 jobs, so it's live-updating
                           # instead of only appearing once the whole (~1-2 hour) stage 2 run finishes
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_CSV = OUTPUT_DIR / "gtfs_siri_coverage_routes.csv"           # stage 2 - live-updated
STAGE1A_CSV = OUTPUT_DIR / "gtfs_siri_stage1a_bus_routes.csv"       # stage 1a - live-updated
STAGE1B_CSV = OUTPUT_DIR / "gtfs_siri_stage1b_ride_execution.csv"   # stage 1b - live-updated
STAGE1_CSV = OUTPUT_DIR / "gtfs_siri_coverage_stage1_lines.csv"     # stage 1 combined - live-updated

TZ = "Israel"
_session = requests.Session()


def api_get(path, params=None):
    """Same behavior as stride.get(), but reuses one requests.Session for
    connection pooling - meaningfully faster across thousands of calls."""
    url = stride_config.STRIDE_API_BASE_URL + path
    params = stride_common.parse_params(dict(params or {}))
    res = _session.get(url, params=params, timeout=60)
    if res.status_code == 200:
        return stride_common.parse_res(json.loads(res.text))
    raise RuntimeError(f"{path} failed ({res.status_code}): {res.text[:300]}")


def to_israel(df, columns):
    df = df.copy()
    for c in columns:
        df[c] = pd.to_datetime(df[c]).dt.tz_convert(TZ)
    return df


def largest_group(df, id_column):
    if df.empty or df[id_column].nunique() <= 1:
        return df
    largest_id = df[id_column].value_counts().idxmax()
    return df[df[id_column] == largest_id]


# ---- Stage 0: which days actually have (bus) service data at all ----

def discover_real_days():
    real_days = []
    for days_back in tqdm(range(MAX_DAYS_TO_SCAN), desc="stage 0: discovering real days"):
        day = REFERENCE_DATE - datetime.timedelta(days=days_back)
        count = api_get("/gtfs_routes/list", {
            "date_from": day.isoformat(), "date_to": day.isoformat(),
            "route_type": ROUTE_TYPE, "get_count": True,
        })
        if count:
            real_days.append(day)
    return sorted(real_days)


# ---- Stage 1: cheap per-line ride volume + tracking signal ----

def dedup_route_meta(frames):
    routes = pd.concat(frames, ignore_index=True)
    return routes.drop_duplicates(subset="line_ref").set_index("line_ref")


def fetch_bus_route_meta(real_days):
    OUTPUT_DIR.mkdir(exist_ok=True)
    frames = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(api_get, "/gtfs_routes/list", {
                "date_from": day.isoformat(), "date_to": day.isoformat(),
                "route_type": ROUTE_TYPE, "limit": REQUEST_LIMIT,
            }): day
            for day in real_days
        }
        for fut in tqdm(as_completed(futures), total=len(futures), desc="stage 1a: fetching bus route metadata per day"):
            rows = fut.result()
            if rows:
                frames.append(pd.DataFrame(rows))
                dedup_route_meta(frames).to_csv(STAGE1A_CSV)
    return dedup_route_meta(frames)


def stage1_line_summary(line_ref, operator_ref, date_from, date_to):
    try:
        rows = api_get("/rides_execution/list", {
            "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
            "operator_ref": str(operator_ref), "line_ref": str(line_ref),
            "limit": REQUEST_LIMIT,
        })
    except Exception:
        return line_ref, pd.DataFrame(columns=["planned_start_time", "actual_start_time", "gtfs_ride_id"])
    rows = [r for r in rows if r["planned_start_time"] is not None]
    return line_ref, pd.DataFrame(rows)


def build_stage1b_df(summaries):
    rows = []
    for line_ref, rides in summaries.items():
        total = len(rides)
        tracked = int(rides["actual_start_time"].notna().sum()) if total else 0
        rows.append({
            "line_ref": line_ref, "total_rides": total, "tracked_rides": tracked,
            "tracked_rate": tracked / total if total else np.nan,
        })
    return pd.DataFrame(rows).set_index("line_ref").sort_index()


def build_stage1_df(route_meta, summaries):
    stage1b = build_stage1b_df(summaries)
    combined = route_meta.loc[stage1b.index, ["operator_ref", "agency_name", "route_short_name", "route_direction"]].join(stage1b)
    combined["worthy"] = combined["total_rides"] >= MIN_RIDES_FOR_WORTHY
    return combined.sort_index()


def run_stage1(route_meta, date_from, date_to):
    OUTPUT_DIR.mkdir(exist_ok=True)
    summaries = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(stage1_line_summary, line_ref, route_meta.loc[line_ref, "operator_ref"], date_from, date_to): line_ref
            for line_ref in route_meta.index
        }
        completed = 0
        for fut in tqdm(as_completed(futures), total=len(futures), desc="stage 1b: ride-execution scan (all bus lines)"):
            line_ref, rides = fut.result()
            summaries[line_ref] = rides
            completed += 1
            if completed % CHECKPOINT_EVERY == 0 or completed == len(futures):
                build_stage1b_df(summaries).to_csv(STAGE1B_CSV)
                build_stage1_df(route_meta, summaries).to_csv(STAGE1_CSV)
    return summaries


# ---- Stage 2: detailed per-stop coverage, worthy lines only ----

def compute_ride_coverage(ride_plan, ride_siri):
    n_planned = len(ride_plan)
    if ride_siri.empty:
        return n_planned, 0

    ride_start = ride_plan["gtfs_line_start_time"].iloc[0]
    planned_elapsed = ((ride_plan["planned_arrival_time"] - ride_start).dt.total_seconds() / 60).to_numpy()
    plan_xy = ride_plan[["lon", "lat"]].to_numpy()

    actual_elapsed = ((ride_siri["recorded_at_time"] - ride_start).dt.total_seconds() / 60).to_numpy()
    actual_xy = ride_siri[["lon", "lat"]].to_numpy()

    dists = np.linalg.norm(actual_xy[:, None, :] - plan_xy[None, :, :], axis=2)
    time_gap = np.abs(actual_elapsed[:, None] - planned_elapsed[None, :])
    dists_masked = np.where(time_gap <= MATCH_TOLERANCE_MIN, dists, np.inf)

    has_match = np.isfinite(dists_masked.min(axis=1))
    nearest_idx = dists_masked.argmin(axis=1)
    n_covered = len(set(nearest_idx[has_match]))
    return n_planned, n_covered


def process_line_day(line_ref, meta, day, day_has_tracked_ride):
    """Fetch one line's plan (+ actual, if stage 1 saw any tracked ride that day) for one day."""
    day_from = datetime.datetime.combine(day, datetime.time(0, 0), tzinfo=_tz.gettz("Israel"))
    day_to = datetime.datetime.combine(day, datetime.time(23, 59), tzinfo=_tz.gettz("Israel"))

    try:
        plan_rows = api_get("/route_timetable/list", {
            "line_refs": line_ref,
            "planned_start_time_date_from": day_from,
            "planned_start_time_date_to": day_to,
            "order_by": "gtfs_line_start_time, planned_arrival_time",
            "limit": REQUEST_LIMIT,
        })
    except Exception:
        return []
    if not plan_rows:
        return []
    plan = to_israel(pd.DataFrame(plan_rows), ["planned_arrival_time", "gtfs_line_start_time"])

    if day_has_tracked_ride:
        try:
            siri_rows = api_get("/siri_vehicle_locations/list", {
                "siri_routes__line_ref": line_ref,
                "siri_routes__operator_ref": int(meta["operator_ref"]),
                "siri_rides__schedualed_start_time_from": day_from,
                "siri_rides__schedualed_start_time_to": day_to,
                "order_by": "recorded_at_time",
                "limit": REQUEST_LIMIT,
            })
        except Exception:
            siri_rows = []
    else:
        siri_rows = []  # stage 1 already told us nothing was tracked this day - skip the fetch entirely

    if siri_rows:
        siri = to_israel(pd.DataFrame(siri_rows), ["recorded_at_time", "siri_ride__scheduled_start_time"])
    else:
        siri = pd.DataFrame(columns=["recorded_at_time", "siri_ride__scheduled_start_time",
                                      "lon", "lat", "siri_ride__id"])

    records = []
    for gtfs_ride_id, ride_plan in plan.groupby("gtfs_ride_id"):
        ride_plan = ride_plan.sort_values("planned_arrival_time").reset_index(drop=True)
        ride_start = ride_plan["gtfs_line_start_time"].iloc[0]

        ride_siri = siri[siri["siri_ride__scheduled_start_time"] == ride_start]
        ride_siri = largest_group(ride_siri, "siri_ride__id").sort_values("recorded_at_time")

        n_planned, n_covered = compute_ride_coverage(ride_plan, ride_siri)
        records.append({
            "line_ref": line_ref,
            "operator_ref": int(meta["operator_ref"]),
            "agency_name": meta["agency_name"],
            "route_short_name": meta["route_short_name"],
            "route_direction": meta["route_direction"],
            "gtfs_ride_id": gtfs_ride_id,
            "hour": ride_start.hour,
            "n_planned_stops": n_planned,
            "n_siri_covered_stops": n_covered,
            "rate_siri_covered_stops": n_covered / n_planned if n_planned else np.nan,
        })
    return records


def evenly_spaced_sample(days, target_count):
    """Pick ~target_count days evenly spread across the full sorted range, not
    just the most recent ones - keeps stage 2 representative of the whole
    scanned window instead of skewing toward whichever end it starts from."""
    days = sorted(days)
    if len(days) <= target_count:
        return days
    indices = np.linspace(0, len(days) - 1, target_count)
    return sorted({days[int(round(i))] for i in indices})


def build_routes_df(records):
    rides_df = pd.DataFrame(records)
    if rides_df.empty:
        return rides_df
    group_cols = ["line_ref", "operator_ref", "agency_name", "route_short_name", "route_direction", "hour"]
    return (
        rides_df
        .groupby(group_cols, as_index=False)
        .agg(
            count=("gtfs_ride_id", "size"),
            n_planned_stops=("n_planned_stops", "mean"),
            n_siri_covered_stops=("n_siri_covered_stops", "mean"),
            rate_siri_covered_stops=("rate_siri_covered_stops", "mean"),
        )
        .sort_values(["line_ref", "hour"])
        .reset_index(drop=True)
    )


def run_stage2(worthy_line_refs, route_meta, stage1_summaries, sampled_days):
    OUTPUT_DIR.mkdir(exist_ok=True)
    # build the exact (line_ref, day, has_tracked_ride) work list - only sampled days each line actually ran
    sampled_days = set(sampled_days)
    jobs = []
    for line_ref in worthy_line_refs:
        rides = stage1_summaries[line_ref]
        rides_by_day = rides.copy()
        rides_by_day["day"] = pd.to_datetime(rides_by_day["planned_start_time"]).dt.tz_convert(TZ).dt.date
        for day, day_rows in rides_by_day.groupby("day"):
            if day not in sampled_days:
                continue
            has_tracked = day_rows["actual_start_time"].notna().any()
            jobs.append((line_ref, day, has_tracked))

    records = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(process_line_day, line_ref, route_meta.loc[line_ref], day, has_tracked): (line_ref, day)
            for line_ref, day, has_tracked in jobs
        }
        completed = 0
        for fut in tqdm(as_completed(futures), total=len(futures), desc="stage 2: per-stop coverage (worthy lines)"):
            records.extend(fut.result())
            completed += 1
            if completed % CHECKPOINT_EVERY == 0 or completed == len(futures):
                build_routes_df(records).to_csv(OUTPUT_CSV, index=False)
    return records


def main():
    real_days = discover_real_days()
    print(f"Stage 0: found {len(real_days)} days with bus service data: "
          f"{[d.isoformat() for d in real_days]}")
    if not real_days:
        raise RuntimeError("No days with bus service data found - widen MAX_DAYS_TO_SCAN or check REFERENCE_DATE")
    date_from, date_to = real_days[0], real_days[-1]

    route_meta = fetch_bus_route_meta(real_days)
    print(f"Stage 0: {len(route_meta)} distinct bus line_refs active on those days")

    stage1_summaries = run_stage1(route_meta, date_from, date_to)
    stage1_df = build_stage1_df(route_meta, stage1_summaries)
    stage1_df.to_csv(STAGE1_CSV)  # final, complete snapshot (was already live-updating during stage 1b)

    worthy = stage1_df.index[stage1_df["worthy"]].tolist()
    print(f"Stage 1: {len(worthy)}/{len(route_meta)} bus lines have >= {MIN_RIDES_FOR_WORTHY} rides "
          f"in the real-data window and are considered worthy of detailed analysis - see {STAGE1_CSV}")
    total_rides_all = int(stage1_df["total_rides"].sum())
    total_tracked_all = int(stage1_df["tracked_rides"].sum())
    print(f"Stage 1: {total_tracked_all}/{total_rides_all} rides across all bus lines have "
          f"*some* recorded actual position ({total_tracked_all/total_rides_all:.1%}) - "
          f"note this is a coarse ride-level signal, not the detailed stop-level rate computed next")

    sampled_days = evenly_spaced_sample(real_days, SAMPLE_DAYS_TARGET)
    print(f"Stage 2: sampling {len(sampled_days)} days spread across the {len(real_days)}-day real-data "
          f"window: {[d.isoformat() for d in sampled_days]}")

    all_records = run_stage2(worthy, route_meta, stage1_summaries, sampled_days)
    routes_df = build_routes_df(all_records)
    routes_df.to_csv(OUTPUT_CSV, index=False)  # final, complete snapshot (was already live-updating)
    print(f"\nStage 2: {len(all_records)} ride records collected")
    print(f"Wrote {len(routes_df)} route-group rows to {OUTPUT_CSV}")
    print(routes_df.head(20).to_string())


if __name__ == "__main__":
    main()
