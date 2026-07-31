"""Bus bunching: headway regularity for one resolved line + direction.

Bunching is the classic frequent-service failure: a delayed bus picks up extra
passengers at every stop, falls further behind, and the bus behind it closes
the gap — until two buses arrive nose-to-tail followed by a long empty gap.
The signal isn't lateness, it's how *uneven the spacing* between consecutive
buses is, so this compares consecutive-departure gaps (headways) against the
line's own scheduled spacing.

Data: SIRI GPS pings (/siri_vehicle_locations/list). Each ping carries both
``siri_ride__scheduled_start_time`` (constant per ride) and its own
``recorded_at_time``, so a ride's *first* ping is used as a proxy for its
actual departure — this module never observes a true "doors closed" moment,
only how often SIRI happened to ping.

This deliberately does NOT go through ``stride.siri_rides()`` /
``gtfs_route__route_short_name``: spot-checked live while building this, that
join is null on most rows (a plainly-running line's siri_rides came back
empty when filtered on it). Line identity is instead resolved from GTFS route
metadata (for a human-readable name) but the SIRI fetch itself filters on
``siri_routes__line_ref``/``siri_routes__operator_ref`` directly — the same
line_ref/operator_ref space, and the same working query pattern already used
by siri_coverage.py and schedule_adherence_average.py.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from openbus_hack import AnalysisRequest, OptionSpec, analysis, bar_chart, metrics, stride
from openbus_hack.diskcache import cached

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

# Each sampled day costs one GPS-ping fetch for one line+operator. Spot-checked
# live: a moderately busy Tel Aviv line's full day is ~8-10k pings, ~8s. Capped
# small so a dashboard card returns in well under a minute, not a batch scan.
MAX_DAYS = 2

# One GET per day, single page — the API returns up to `limit` rows in one
# response for this query shape (no auto-paging needed). 15000 matches
# siri_coverage.py / schedule_adherence_average.py's own value: spot-checked
# live while building this, 15000 succeeds but 20000 500s instantly (an
# undocumented server-side cap somewhere between the two).
REQUEST_LIMIT = 15000

# Bus service is thin on Fri/Sat in Israel; a handful of night-bus headways
# would read as false bunching or gapping, not a real reliability signal.
WEEKEND_WEEKDAYS = {4, 5}  # Python weekday(): Friday=4, Saturday=5

# SIRI ingestion lags a few days behind live — the dashboard's own default
# window reaches back only to yesterday, which is typically still landing.
# Spot-checked live while building this: a line resolved with plenty of
# routes/traffic came back with zero pings when the window wasn't clamped.
SIRI_LAG_DAYS = 3

# Standard headway-regularity thresholds: an actual gap under a quarter of the
# scheduled spacing is buses running nose-to-tail; over 1.75x is the empty gap
# left behind. Values in between are "normal" jitter, not a failure.
BUNCHED_RATIO = 0.25
GAPPED_RATIO = 1.75

# Below this many consecutive-headway observations, a coefficient of variation
# is mostly sampling noise — say so instead of drawing a confident-looking chart.
MIN_HEADWAYS = 5

# Used only when no line was requested: a small, line-unfiltered sample of
# recent pings, to find some (line_ref, operator_ref) that is both live-tracked
# AND runs often enough to have headways worth measuring (ranked by distinct
# rides, not raw ping count, since ping density varies with GPS reporting rate).
DISCOVERY_SAMPLE_LIMIT = 500


_OPTIONS = [
    OptionSpec(key="max_days", label="Max days to sample (0 = all)", type="number", default=2,
               help="The maximum number of weekdays to fetch GPS headways for. "
                    "Raise this to scan more days, or set to 0 to fetch every single "
                    "day in your date range (no sampling)!"),
]


@analysis(
    name="bus-bunching",
    title="Bus bunching: headway regularity",
    description=(
        "For one resolved line+direction, how evenly spaced consecutive buses "
        "actually were, against the line's own scheduled spacing. Buses "
        "arriving nose-to-tail (bunched) followed by a long gap is the classic "
        "frequent-service reliability failure."
    ),
    author="team",
    tags=["siri", "reliability", "bunching", "headway"],
    inputs=["lines", "operators", "dates"],
    options=_OPTIONS,
    draft=False,
)
def run(req: AnalysisRequest):
    orig_date_to = req.date_to
    req = _clamp_to_siri_lag(req)

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

    label = (f"Line {resolved['route_short_name']} (line_ref={resolved['line_ref']}), "
             f"direction {resolved['route_direction']}, operator "
             f"{resolved['agency_name']} (operator_ref={resolved['operator_ref']})")

    max_days = int(req.opt("max_days", 2) or 2)
    days, n_weekend_dropped = _sample_days(req, max_days)
    
    label_days_desc = (
        f"Fetched all {len(days)} requested day(s) (sampling disabled)."
        if max_days == 0
        else f"Sampled {len(days)} of {req.days} requested day(s), capped at {max_days} (to limit network cost)."
    )

    notes: list[str] = [
        label + ".",
        f"{label_days_desc} Each day costs one GPS-ping fetch for this line alone "
        "(see module docstring for why a full multi-day scan doesn't fit a "
        "dashboard card).",
    ]
    if orig_date_to != req.date_to:
        notes.append(
            f"Requested window reached to {orig_date_to}, which SIRI hasn't "
            f"necessarily finished ingesting yet — shifted to end {req.date_to} "
            f"({SIRI_LAG_DAYS} days behind today)."
        )
    if n_weekend_dropped:
        notes.append(
            f"{n_weekend_dropped} Friday/Saturday day(s) in the requested window "
            "were skipped when picking days to sample — thin weekend service "
            "reads as false bunching/gapping, not a real signal."
        )

    frames = [_fetch_day(resolved["line_ref"], resolved["operator_ref"], d) for d in days]
    per_ride = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if per_ride.empty:
        notes.append(
            "No SIRI GPS pings were found for this line on any sampled day — "
            "this can mean the line genuinely wasn't tracked (some "
            "operators/vehicle types aren't part of the real-time feed), or the "
            "sampled days are outside the SIRI archive window (ingestion lags a "
            "few days behind live)."
        )
        return metrics(("No data", 0), notes=notes)

    sched_headways: list[float] = []
    actual_headways: list[float] = []
    for _day, grp in per_ride.groupby("day"):
        sched = grp["scheduled"].dropna().sort_values()
        if len(sched) >= 2:
            sched_headways.extend((sched.diff().dropna().dt.total_seconds() / 60).tolist())
        actual = grp["first_ping"].dropna().sort_values()
        if len(actual) >= 2:
            actual_headways.extend((actual.diff().dropna().dt.total_seconds() / 60).tolist())

    n_rides = len(per_ride)
    if len(actual_headways) < MIN_HEADWAYS:
        notes.append(
            f"Only {n_rides} ride(s) yielding {len(actual_headways)} consecutive "
            f"gap(s) were observed — too few to say anything about headway "
            "regularity. Widen the date range or pick a higher-frequency line."
        )
        return metrics(("Rides observed", n_rides), ("Headways", len(actual_headways)), notes=notes)

    actual_arr = np.array(actual_headways)
    mean_actual = float(actual_arr.mean())
    std_actual = float(actual_arr.std())
    cv = std_actual / mean_actual if mean_actual else float("nan")

    # A single "target" headway is a blunt instrument — real service runs denser
    # at rush hour than off-peak — but the median of scheduled gaps, pooled
    # across sampled days/hours, is what turns "13 minutes" into "bunched" or
    # "fine" at a glance, and is robust to one huge first/last-run-of-day gap.
    target = float(np.median(sched_headways)) if sched_headways else float(np.median(actual_arr))

    bunched = actual_arr < BUNCHED_RATIO * target
    gapped = actual_arr > GAPPED_RATIO * target
    normal = ~bunched & ~gapped

    buckets = pd.DataFrame({
        "bucket": [
            f"Bunched (<{int(BUNCHED_RATIO * 100)}% of target)",
            "Normal",
            f"Gapped (>{int(GAPPED_RATIO * 100)}% of target)",
        ],
        "count": [int(bunched.sum()), int(normal.sum()), int(gapped.sum())],
    })

    notes.append(
        f"{n_rides} rides observed, {len(actual_headways)} consecutive headways "
        f"across {len(days)} sampled day(s). Mean actual headway "
        f"{mean_actual:.1f} min (scheduled target ≈ {target:.1f} min); "
        f"coefficient of variation (std/mean) {cv:.2f}" +
        (" — above ~0.5 is the usual sign of bunching." if cv > 0.5
         else " — below ~0.5, i.e. reasonably even spacing.")
    )
    notes.append(
        f"{int(bunched.sum())}/{len(actual_headways)} headways "
        f"({100 * bunched.mean():.0f}%) came in under "
        f"{int(BUNCHED_RATIO * 100)}% of the target headway (nose-to-tail "
        f"buses); {int(gapped.sum())} ({100 * gapped.mean():.0f}%) exceeded "
        f"{int(GAPPED_RATIO * 100)}% (the gap that bunching leaves behind)."
    )
    notes.append(
        "'Actual' departure is a ride's first matched GPS ping, not a measured "
        "stop-level arrival — a proxy only as precise as how often SIRI pings, "
        "not a stopwatch."
    )
    notes.append(
        "The scheduled 'target' headway is pooled across whichever hours/days "
        "were sampled, not read per time-of-day — a line that runs every 6 min "
        "at rush hour and every 20 min off-peak will show some off-peak "
        "departures flagged 'gapped' that are the timetable working as intended, "
        "not a reliability failure."
    )

    return bar_chart(
        buckets, x="bucket", y="count",
        title="Bus bunching: headway regularity",
        subtitle=f"{label} · {req.date_from} → {req.date_to}",
        x_label="headway vs. scheduled target", y_label="count of consecutive headways",
        notes=notes,
    )


def _clamp_to_siri_lag(req: AnalysisRequest) -> AnalysisRequest:
    """Pull date_to back to SIRI_LAG_DAYS behind today if the request reaches
    more recent than that, so line discovery and day-sampling don't land on a
    day that's still landing. Returns a copy — AnalysisRequest is immutable-by-
    convention here since it's shared with every other card on the page."""
    date_to = min(req.date_to, dt.date.today() - dt.timedelta(days=SIRI_LAG_DAYS))
    date_from = min(req.date_from, date_to)
    if date_to == req.date_to and date_from == req.date_from:
        return req
    return req.model_copy(update={"date_from": date_from, "date_to": date_to})


# ── Line resolution ──────────────────────────────────────────────────────────


def _resolve_line(req: AnalysisRequest) -> dict | None:
    """Pick the one (line_ref, operator_ref) this card will analyze.

    Mirrors siri_coverage.py's resolution: a requested line is looked up via
    GTFS route metadata (one line_ref per direction/alternative/operator, so
    the first match is taken); with no line requested, auto-discover one that
    is both live-tracked and running often enough to have headways worth
    measuring, rather than guessing blind.
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
    needed = {"siri_route__line_ref", "siri_route__operator_ref", "siri_ride__id"}
    if not needed.issubset(sample.columns):
        return None
    # Ranked by distinct rides, not raw ping count — a line that pings often but
    # runs rarely has nothing to say about headways.
    counts = sample.groupby(["siri_route__line_ref", "siri_route__operator_ref"])[
        "siri_ride__id"
    ].nunique()
    line_ref, operator_ref = counts.idxmax()
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


def _sample_days(req: AnalysisRequest, max_days: int = 2) -> tuple[list[dt.date], int]:
    """Up to max_days weekdays (Sun-Thu), evenly spread across the requested
    window, so a capped sample still represents the whole window instead of
    skewing toward one end. Returns (days, n_weekend_days_dropped).
    If max_days is 0, disables sampling and returns all weekdays in the window."""
    all_days = req.dates()
    weekdays = [d for d in all_days if d.weekday() not in WEEKEND_WEEKDAYS]
    dropped = len(all_days) - len(weekdays)
    # A window that's entirely Fri/Sat still gets sampled rather than returning
    # nothing — the notes above say so either way.
    pool = weekdays or all_days
    if max_days == 0 or len(pool) <= max_days:
        return sorted(pool), dropped
    idx = np.linspace(0, len(pool) - 1, max_days)
    return sorted({pool[int(round(i))] for i in idx}), dropped


def _day_bounds(day: dt.date) -> tuple[str, str]:
    """Tz-aware ISO bounds for one calendar day in Israel time. The API 500s
    with 'tzinfo is required' on naive datetimes for these endpoints."""
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=ISRAEL_TZ)
    end = dt.datetime.combine(day, dt.time(23, 59), tzinfo=ISRAEL_TZ)
    return start.isoformat(), end.isoformat()


# ── Per-day fetch ────────────────────────────────────────────────────────────


def _fetch_day(line_ref: int, operator_ref: int, day: dt.date) -> pd.DataFrame:
    """One day's GPS pings for one line+operator, reduced to one row per ride:
    its scheduled start time and its first ping (a proxy for actual departure).
    Disk-cached — a rehearsal re-run or dashboard reload shouldn't re-pay the fetch."""
    key = ("v1", line_ref, operator_ref, day.isoformat())

    def compute() -> pd.DataFrame:
        day_from, day_to = _day_bounds(day)
        try:
            rows = stride.get(
                "/siri_vehicle_locations/list",
                {
                    "siri_routes__line_ref": line_ref,
                    "siri_routes__operator_ref": operator_ref,
                    # Filtering through the ride's own scheduled time is what
                    # actually works live: the same window filtered directly on
                    # recorded_at_time_from/to instead 500s for a line with a
                    # busy full day (spot-checked against the live API while
                    # building this) — this is the same query shape
                    # siri_coverage.py / schedule_adherence_average.py already use.
                    "siri_rides__schedualed_start_time_from": day_from,  # sic — API spelling
                    "siri_rides__schedualed_start_time_to": day_to,
                    "order_by": "recorded_at_time",
                    "limit": REQUEST_LIMIT,
                },
            )
        except Exception:
            rows = []
        if not rows:
            return pd.DataFrame(columns=["siri_ride__id", "scheduled", "first_ping", "day"])

        df = pd.DataFrame(rows)
        df["recorded_at_time"] = pd.to_datetime(df["recorded_at_time"], utc=True)
        df["siri_ride__scheduled_start_time"] = pd.to_datetime(
            df["siri_ride__scheduled_start_time"], utc=True
        )
        # Overlapping SIRI snapshots report the same physical ping more than once
        # (~10% of rows in a sampled window) — undetected, a duplicated ping can
        # look like a ride's true first ping when it's really a repeat of one
        # already seen.
        df = df.drop_duplicates(subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])

        per_ride = (
            df.groupby("siri_ride__id")
            .agg(scheduled=("siri_ride__scheduled_start_time", "first"),
                 first_ping=("recorded_at_time", "min"))
            .reset_index()
        )
        per_ride["day"] = day.isoformat()
        return per_ride

    return cached("bus_bunching", key, compute)
