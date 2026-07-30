"""SIRI GPS coverage vs planned GTFS stops, by hour of day, for one line+direction.

Ported (small, single-line, live-dashboard-sized slice) from a teammate's
system-wide batch pipeline:
  https://github.com/yuvalko1/talpiot-hackathon-public-transportation
  branch: main
  file:   open-bus-stride-client-main/scripts/explore_gtfs_siri_coverage.py
  author: yuvalko1

The source script answers the same question across the *entire* bus network:
for every line, what fraction of planned GTFS stops actually got a matching
real-time SIRI GPS ping? It does that with a three-stage design (stage 0:
discover which of the last ~90 days have any data at all; stage 1: a cheap
per-line ride-volume screen to find "worthy" lines; stage 2: the expensive
per-stop nearest-GPS matching, sampled across ~20 days) that the author
estimated at 1-2 hours of wall-clock time for a full run — a batch job, not
something a dashboard card can make someone wait on.

This port keeps the one piece of real algorithmic logic worth preserving
faithfully — the nearest-planned-stop + time-tolerance GPS matching in
``compute_ride_coverage`` (ported here as ``_ride_coverage``, logic
unchanged) — and applies it live to ONE resolved line+direction over a small,
capped set of days, aggregated by hour of day.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from openbus_hack import AnalysisRequest, analysis, bar_chart, metrics, stride

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

# A live dashboard card can't repeat the source pipeline's ~90-day, ~20-day-
# sampled, 1-2 hour batch scan. Every sampled day costs two paired API calls
# (planned timetable + actual GPS pings), so this is capped small on purpose
# — a handful of days is enough to show the *shape* of coverage by hour
# without turning a card click into a batch job.
MAX_DAYS = 3

# Ported unchanged from the source script: a SIRI ping only counts as
# covering a planned stop if it's within this many minutes of that stop's
# planned elapsed time (in addition to being the nearest stop by distance).
# Without the time check, routes that loop back near their own path can
# match a much-later ping to an early stop, inflating coverage.
MATCH_TOLERANCE_MIN = 20

# Every request explicitly sets its own 'limit' — the underlying stride.get()
# helper does one raw call per request (no auto-paging), and the server
# silently defaults to a small page otherwise. A single line's single-day
# timetable/pings are a few thousand rows at most, well under this.
REQUEST_LIMIT = 15000

# Used only when no line was requested: a small, line-unfiltered sample of
# recent GPS pings, just to find *some* (line_ref, operator_ref) that is
# actually being tracked live right now, instead of guessing a line blind
# and hitting one with zero SIRI coverage (e.g. a cable-car / non-tracked
# operator) for the default "click the card with no filters" demo case.
DISCOVERY_SAMPLE_LIMIT = 300


@analysis(
    name="siri-coverage",
    title="SIRI GPS coverage vs planned stops",
    description=(
        "For one resolved line+direction, what fraction of planned GTFS stops "
        "actually got a matching real-time SIRI GPS ping, by hour of day. "
        "Ported from yuvalko1's system-wide coverage pipeline, scoped down to "
        "one line and a few days so it fits inside a live dashboard card."
    ),
    author="yuvalko1",
    tags=["siri", "gtfs", "coverage", "reliability"],
    inputs=["lines", "operators", "dates"],
    draft=False,
)
def run(req: AnalysisRequest):
    resolved = _resolve_line(req)
    if resolved is None:
        return metrics(
            ("No data", 0),
            notes=[
                "Could not resolve a line+direction to analyze — no matching "
                "GTFS route found for the requested line/operator/date window, "
                "and (if no line was requested) no live-tracked line could be "
                "auto-discovered either."
            ],
        )

    days = _sample_days(req)
    notes: list[str] = [
        f"Line {resolved['route_short_name']} (line_ref={resolved['line_ref']}), "
        f"direction {resolved['route_direction']}, operator "
        f"{resolved['agency_name']} (operator_ref={resolved['operator_ref']}).",
        f"Sampled {len(days)} of {req.days} requested day(s) "
        f"(capped at {MAX_DAYS} — see module docstring: this mirrors the "
        "source pipeline's per-line-per-day fetch cost, kept small so a "
        "dashboard card returns in seconds, not hours).",
        "route_timetable/list rejects date ranges over a single day and "
        "times out unfiltered, and siri_vehicle_locations/list accepts only "
        "one line_ref per request — both endpoints are therefore queried one "
        "line, one day at a time.",
        f"A GPS ping only counts as covering a planned stop if it is both the "
        f"nearest stop AND within {MATCH_TOLERANCE_MIN} minutes of that stop's "
        "planned elapsed time — without the time check, routes that loop back "
        "near their own path would falsely match a later ping to an early stop.",
    ]

    rides: list[dict] = []
    any_siri = False
    for day in days:
        day_rides, day_had_siri = _process_line_day(resolved, day)
        rides.extend(day_rides)
        any_siri = any_siri or day_had_siri

    if not rides:
        notes.append("No planned GTFS timetable rows were found for this line on any sampled day.")
        return metrics(("No data", 0), notes=notes)
    if not any_siri:
        notes.append(
            "No SIRI GPS pings were found for this line on any sampled day — "
            "coverage is 0% everywhere below. This can mean the line genuinely "
            "wasn't tracked (some operators/vehicle types aren't part of the "
            "real-time feed), or the sampled days are outside the SIRI archive window."
        )

    rides_df = pd.DataFrame(rides)
    by_hour = (
        rides_df.groupby("hour", as_index=False)
        .agg(n_planned=("n_planned", "sum"), n_covered=("n_covered", "sum"), n_rides=("hour", "size"))
        .sort_values("hour")
    )
    by_hour["coverage_pct"] = np.where(
        by_hour["n_planned"] > 0, 100.0 * by_hour["n_covered"] / by_hour["n_planned"], np.nan
    )

    total_planned = int(rides_df["n_planned"].sum())
    total_covered = int(rides_df["n_covered"].sum())
    overall_pct = 100.0 * total_covered / total_planned if total_planned else 0.0
    notes.append(
        f"Overall: {total_covered:,}/{total_planned:,} planned stops matched a "
        f"SIRI ping ({overall_pct:.1f}%), across {len(rides_df):,} rides on "
        f"{len(days)} sampled day(s)."
    )
    thin_hours = by_hour.loc[by_hour["n_rides"] < 3, "hour"].tolist()
    if thin_hours:
        notes.append(
            f"Hour(s) {', '.join(str(h) for h in thin_hours)} are based on fewer than "
            "3 rides in the sample — treat as low-confidence."
        )

    return bar_chart(
        by_hour,
        x="hour",
        y="coverage_pct",
        title="SIRI coverage of planned stops, by hour",
        subtitle=(
            f"Line {resolved['route_short_name']} dir {resolved['route_direction']} "
            f"({resolved['agency_name']}) · {req.date_from} → {req.date_to}"
        ),
        x_label="hour of day (Israel time)",
        y_label="coverage %",
        notes=notes,
    )


# ── Line resolution ──────────────────────────────────────────────────────────


def _resolve_line(req: AnalysisRequest) -> dict | None:
    """Pick the one (line_ref, operator_ref) this card will analyze.

    If the caller asked for a specific line (optionally + operator), resolve
    it via GTFS route metadata — a "line" (route_short_name) is really many
    GTFS routes (one line_ref per direction/alternative/operator), so we take
    the first match, same as the source script's per-line_ref granularity.

    If no line was requested (e.g. the dashboard's default, filter-free
    view), auto-discover one that is actually being tracked live right now,
    rather than guessing a line_ref blind and possibly landing on one with no
    SIRI coverage at all.
    """
    if req.line:
        routes_df = stride.routes(
            lines=[req.line],
            operators=[req.operator] if req.operator else None,
            date_from=req.date_from,
            date_to=req.date_to,
            limit=200,
        )
        if routes_df.empty:
            return None
        row = routes_df.iloc[0]
        return {
            "line_ref": int(row["line_ref"]),
            "operator_ref": int(row["operator_ref"]),
            "agency_name": str(row.get("agency_name") or row["operator_ref"]),
            "route_short_name": str(row.get("route_short_name") or req.line),
            "route_direction": str(row.get("route_direction") or "?"),
        }

    sample_day = req.dates()[-1] if req.dates() else req.date_to
    day_from, day_to = _day_bounds(sample_day)
    try:
        rows = stride.get(
            "/siri_vehicle_locations/list",
            {"recorded_at_time_from": day_from, "recorded_at_time_to": day_to,
             "limit": DISCOVERY_SAMPLE_LIMIT},
        )
    except Exception:
        rows = []
    if not rows:
        return None
    sample = pd.DataFrame(rows)
    if "siri_route__line_ref" not in sample.columns or "siri_route__operator_ref" not in sample.columns:
        return None
    line_ref, operator_ref = sample.groupby(
        ["siri_route__line_ref", "siri_route__operator_ref"]
    ).size().idxmax()
    line_ref, operator_ref = int(line_ref), int(operator_ref)

    meta_rows = stride.get(
        "/gtfs_routes/list",
        {"line_refs": line_ref, "date_from": req.date_from, "date_to": req.date_to, "limit": 5},
    )
    if meta_rows:
        m = meta_rows[0]
        return {
            "line_ref": line_ref,
            "operator_ref": operator_ref,
            "agency_name": str(m.get("agency_name") or operator_ref),
            "route_short_name": str(m.get("route_short_name") or "?"),
            "route_direction": str(m.get("route_direction") or "?"),
        }
    return {
        "line_ref": line_ref, "operator_ref": operator_ref,
        "agency_name": str(operator_ref), "route_short_name": "?", "route_direction": "?",
    }


# ── Day sampling ─────────────────────────────────────────────────────────────


def _sample_days(req: AnalysisRequest) -> list[dt.date]:
    """Up to MAX_DAYS days, evenly spread across the requested window — mirrors
    the source script's evenly_spaced_sample(), so a capped sample still
    represents the whole window instead of skewing toward one end."""
    days = req.dates()
    if len(days) <= MAX_DAYS:
        return days
    idx = np.linspace(0, len(days) - 1, MAX_DAYS)
    return sorted({days[int(round(i))] for i in idx})


def _day_bounds(day: dt.date) -> tuple[str, str]:
    """Tz-aware ISO bounds for one calendar day in Israel time. The API 500s
    with 'tzinfo is required' on naive datetimes for these two endpoints."""
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=ISRAEL_TZ)
    end = dt.datetime.combine(day, dt.time(23, 59), tzinfo=ISRAEL_TZ)
    return start.isoformat(), end.isoformat()


# ── Per-day fetch + per-ride coverage (ported from process_line_day) ────────


def _process_line_day(resolved: dict, day: dt.date) -> tuple[list[dict], bool]:
    """Fetch one line's planned timetable + actual GPS pings for one day and
    compute per-ride stop coverage. Returns (records, had_any_siri_rows)."""
    day_from, day_to = _day_bounds(day)

    try:
        plan_rows = stride.get(
            "/route_timetable/list",
            {
                "line_refs": resolved["line_ref"],
                "planned_start_time_date_from": day_from,
                "planned_start_time_date_to": day_to,
                "limit": REQUEST_LIMIT,
            },
        )
    except Exception:
        plan_rows = []
    if not plan_rows:
        return [], False

    plan = pd.DataFrame(plan_rows)
    plan["planned_arrival_time"] = pd.to_datetime(plan["planned_arrival_time"], utc=True)
    plan["gtfs_line_start_time"] = pd.to_datetime(plan["gtfs_line_start_time"], utc=True)

    try:
        siri_rows = stride.get(
            "/siri_vehicle_locations/list",
            {
                "siri_routes__line_ref": resolved["line_ref"],
                "siri_routes__operator_ref": resolved["operator_ref"],
                "siri_rides__schedualed_start_time_from": day_from,  # sic — API's spelling
                "siri_rides__schedualed_start_time_to": day_to,
                "order_by": "recorded_at_time",
                "limit": REQUEST_LIMIT,
            },
        )
    except Exception:
        siri_rows = []

    if siri_rows:
        siri = pd.DataFrame(siri_rows)
        siri["recorded_at_time"] = pd.to_datetime(siri["recorded_at_time"], utc=True)
        siri["siri_ride__scheduled_start_time"] = pd.to_datetime(
            siri["siri_ride__scheduled_start_time"], utc=True
        )
    else:
        siri = pd.DataFrame(
            columns=["recorded_at_time", "siri_ride__scheduled_start_time", "lon", "lat", "siri_ride__id"]
        )

    records = []
    for gtfs_ride_id, ride_plan in plan.groupby("gtfs_ride_id"):
        ride_plan = ride_plan.sort_values("planned_arrival_time").reset_index(drop=True)
        ride_start = ride_plan["gtfs_line_start_time"].iloc[0]

        ride_siri = siri[siri["siri_ride__scheduled_start_time"] == ride_start]
        ride_siri = _largest_group(ride_siri, "siri_ride__id").sort_values("recorded_at_time")

        n_planned, n_covered = _ride_coverage(ride_plan, ride_siri)
        records.append({
            "gtfs_ride_id": gtfs_ride_id,
            "hour": ride_start.tz_convert(ISRAEL_TZ).hour,
            "n_planned": n_planned,
            "n_covered": n_covered,
        })
    return records, bool(siri_rows)


def _largest_group(df: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """Ported unchanged from the source script: if a ride's scheduled start
    time coincidentally matches more than one distinct siri_ride id, keep only
    the biggest one rather than mixing pings from unrelated vehicles."""
    if df.empty or df[id_column].nunique() <= 1:
        return df
    largest_id = df[id_column].value_counts().idxmax()
    return df[df[id_column] == largest_id]


def _ride_coverage(ride_plan: pd.DataFrame, ride_siri: pd.DataFrame) -> tuple[int, int]:
    """Nearest-planned-stop matching for one ride's GPS pings, gated by a time
    tolerance. Ported near-verbatim from compute_ride_coverage() in the source
    script — this is the one piece of real algorithmic logic this port exists
    to preserve; everything else here is new plumbing sized for a live request.
    """
    n_planned = len(ride_plan)
    if ride_siri.empty or n_planned == 0:
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
