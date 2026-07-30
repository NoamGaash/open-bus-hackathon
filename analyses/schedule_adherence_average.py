"""Multi-day average schedule adherence for one line + departure time.

Ported from yuvalko1's ``compare_gtfs_siri_average.ipynb``
(github.com/yuvalko1/talpiot-hackathon-public-transportation, branch main),
which is the multi-day extension of their single-ride comparison notebook.

Two cards come out of one fetch:

* **schedule-adherence-average** — a stringline: every matched day as a faint
  trace, the GTFS plan and the cross-day average drawn bold over them. The fan
  between them is how much the same departure varies day to day.
* **schedule-adherence-map** — the same comparison geographically: the planned
  route dashed, and the *measured* route solid, where each stop's position is a
  distance-weighted average of the real GPS pings that matched it rather than
  the timetable's fixed coordinate.

What's ported faithfully (the parts carrying the analytical risk):

* **Canonical stop signature.** A day only counts if its stop sequence matches
  the reference day's exactly. One line_ref serves several stop patterns, and
  averaging across them silently blends two different journeys.
* **Nearest-stop matching gated by time.** A ping matches the closest stop only
  if it is also within ``MATCH_TOLERANCE_MIN`` of that stop's planned elapsed
  time. Distance alone mis-assigns pings on routes that loop back near
  themselves.
* **Distance-weighted averaging** (``1 / distance``) for the map, so pings that
  passed closest to a stop dominate its averaged position.

What's deliberately scoped down: the notebook scans 90 days back and demands 20
matched days, which is a couple of minutes of API calls. A dashboard card can't
make someone wait on that, so the window and the day minimum are much smaller
and configurable — the shape of the result is the same, the confidence is lower,
and the notes say so.
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from openbus_hack import (
    AnalysisRequest,
    AnalysisResult,
    OptionSpec,
    Point,
    Series,
    GeoLegend,
    analysis,
    bar_chart,
    geo,
    metrics,
    stride,
)
from openbus_hack.diskcache import cached

_CREDIT = ("Ported from yuvalko1's compare_gtfs_siri_average.ipynb "
           "(github.com/yuvalko1/talpiot-hackathon-public-transportation).")

ISRAEL_TZ = datetime.timezone(datetime.timedelta(hours=3))
# Ported unchanged: a ping counts for a stop only if it's the nearest AND within
# this many minutes of that stop's planned elapsed time.
MATCH_TOLERANCE_MIN = 20
REQUEST_LIMIT = 15000
# SIRI ingestion lags a few days behind live.
LAG_DAYS = 3
# Viridis-style gradient, matching the notebook's branca colormap.
_GRADIENT = ["#440154", "#31688e", "#35b779", "#fde725"]


def _lerp(c1: str, c2: str, f: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))


def _color(t: float) -> str:
    t = min(1.0, max(0.0, t))
    seg = t * (len(_GRADIENT) - 1)
    i = min(int(seg), len(_GRADIENT) - 2)
    return _lerp(_GRADIENT[i], _GRADIENT[i + 1], seg - i)


def _largest_group(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ported unchanged: when one window catches more than one ride id, keep the
    biggest rather than blending pings from unrelated vehicles."""
    if df.empty or df[col].nunique() <= 1:
        return df
    return df[df[col] == df[col].value_counts().idxmax()]


def _load(line_ref: str, days_back: int):
    """Scan back day by day for the same departure time, keeping days whose plan
    matches the reference stop sequence and that have GPS. Disk-cached: this is
    2 API calls per scanned day."""

    key = ("v1", line_ref, days_back)

    def compute():
        ref_date = datetime.date.today() - datetime.timedelta(days=LAG_DAYS)

        routes = stride.get("/gtfs_routes/list", {
            "line_refs": line_ref,
            "date_from": (ref_date - datetime.timedelta(days=7)).isoformat(),
            "date_to": ref_date.isoformat(), "limit": 5,
        })
        if not routes:
            return None
        route = routes[0]
        operator_ref = route["operator_ref"]
        label = f"{route.get('route_short_name', line_ref)} {route.get('route_long_name', '')}".strip()

        # Anchor on a real departure time: the first departure on the most recent
        # day that has any timetable for this line.
        time_of_day = None
        for back in range(1, 10):
            day = ref_date - datetime.timedelta(days=back)
            rows = stride.get("/route_timetable/list", {
                "line_refs": line_ref,
                "planned_start_time_date_from": datetime.datetime.combine(
                    day, datetime.time(0, 0), tzinfo=ISRAEL_TZ),
                "planned_start_time_date_to": datetime.datetime.combine(
                    day, datetime.time(23, 59), tzinfo=ISRAEL_TZ),
                "order_by": "gtfs_line_start_time", "limit": 1,
            })
            if rows:
                time_of_day = pd.to_datetime(rows[0]["gtfs_line_start_time"]).tz_convert(
                    "Asia/Jerusalem").time()
                break
        if time_of_day is None:
            return None

        canonical_stops = None
        canonical_plan = None
        matched: list[dict] = []
        skipped = {"no_plan": 0, "route_mismatch": 0, "no_actual": 0}

        for back in range(days_back):
            day = ref_date - datetime.timedelta(days=back)
            w_from = datetime.datetime.combine(day, time_of_day, tzinfo=ISRAEL_TZ)
            w_to = w_from + datetime.timedelta(minutes=1)

            plan_rows = stride.get("/route_timetable/list", {
                "line_refs": line_ref,
                "planned_start_time_date_from": w_from,
                "planned_start_time_date_to": w_to,
                "order_by": "planned_arrival_time", "limit": REQUEST_LIMIT,
            })
            if not plan_rows:
                skipped["no_plan"] += 1
                continue

            plan = pd.DataFrame(plan_rows)
            for c in ("planned_arrival_time", "gtfs_line_start_time"):
                plan[c] = pd.to_datetime(plan[c], utc=True)
            plan = (_largest_group(plan, "gtfs_ride_id")
                    .sort_values("planned_arrival_time").reset_index(drop=True))
            signature = tuple(plan["name"])

            if canonical_stops is None:
                canonical_stops, canonical_plan = signature, plan
            elif signature != canonical_stops:
                skipped["route_mismatch"] += 1
                continue

            actual_rows = stride.get("/siri_vehicle_locations/list", {
                "siri_routes__line_ref": line_ref,
                "siri_routes__operator_ref": operator_ref,
                "siri_rides__schedualed_start_time_from": w_from,  # sic — API spelling
                "siri_rides__schedualed_start_time_to": w_to,
                "order_by": "recorded_at_time", "limit": REQUEST_LIMIT,
            })
            if not actual_rows:
                skipped["no_actual"] += 1
                continue

            actual = pd.DataFrame(actual_rows)
            actual["recorded_at_time"] = pd.to_datetime(actual["recorded_at_time"], utc=True)
            actual = (_largest_group(actual, "siri_ride__id")
                      .sort_values("recorded_at_time").reset_index(drop=True))
            matched.append({"date": day.isoformat(), "start": w_from, "actual": actual})

        if canonical_plan is None or not matched:
            return None
        return {
            "label": label, "time_of_day": time_of_day.strftime("%H:%M"),
            "plan": canonical_plan, "days": matched, "skipped": skipped,
            "scanned": days_back,
        }

    return cached("schedule_adherence", key, compute)


def _fetch(req: AnalysisRequest):
    line_ref = str(req.opt("line_ref", "18663") or "18663")
    days_back = int(req.opt("days_back", 21) or 21)
    return _load(line_ref, days_back)


def _per_stop_elapsed(data: dict):
    """Per matched day, the elapsed minutes at which each canonical stop was
    reached. Returns (per_day list, planned elapsed array, canonical xy)."""
    plan = data["plan"]
    planned_elapsed = (
        (plan["planned_arrival_time"] - plan["gtfs_line_start_time"]).dt.total_seconds() / 60
    ).to_numpy()
    canonical_xy = plan[["lon", "lat"]].to_numpy(dtype=float)

    per_day = []
    for day in data["days"]:
        actual = day["actual"]
        xy = actual[["lon", "lat"]].to_numpy(dtype=float)
        elapsed = ((actual["recorded_at_time"] - pd.Timestamp(day["start"]))
                   .dt.total_seconds() / 60).to_numpy()
        dists = np.linalg.norm(xy[:, None, :] - canonical_xy[None, :, :], axis=2)
        gap = np.abs(elapsed[:, None] - planned_elapsed[None, :])
        masked = np.where(gap <= MATCH_TOLERANCE_MIN, dists, np.inf)
        nearest = masked.argmin(axis=1)
        ok = np.isfinite(masked.min(axis=1))
        per_stop = (pd.Series(elapsed[ok], index=nearest[ok]).groupby(level=0).mean()
                    .reindex(range(len(plan))))
        per_day.append({"date": day["date"], "elapsed": per_stop,
                        "xy": xy, "raw_elapsed": elapsed, "masked": masked})
    return per_day, planned_elapsed, canonical_xy


_OPTIONS = [
    OptionSpec(key="line_ref", label="Line ref", type="text", default="18663",
               help="GTFS line_ref. The notebook's own pool of well-tracked lines: "
                    "18663, 40499, 29099, 10208, 11603, 29620, 40089, 36716."),
    OptionSpec(key="days_back", label="Days to scan", type="number", default=21,
               help="The notebook scanned 90; that's minutes of API calls. Each "
                    "scanned day costs two requests, cached after the first run."),
]


@analysis(
    name="schedule-adherence-average",
    title="How much does the same departure vary, day to day?",
    description="One line's same daily departure across many days: each faint line "
                "is one day, against the GTFS plan and the cross-day average. The "
                "width of the fan is the day-to-day unreliability.",
    author="yuvalko1",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=[],
    options=_OPTIONS,
)
def run_average(req: AnalysisRequest):
    data = _fetch(req)
    if data is None:
        return metrics(("No data", 0), notes=[
            "No day in the scanned window had both a matching timetable and GPS "
            "for this line — try another line_ref or a longer scan.", _CREDIT])

    per_day, planned_elapsed, _ = _per_stop_elapsed(data)
    n_stops = len(data["plan"])
    stop_names = data["plan"]["name"].tolist()

    series = [
        Series(name=f"day {d['date']}",
               points=[Point(x=float(v), y=float(i))
                       for i, v in d["elapsed"].items() if pd.notna(v)])
        for d in per_day
    ]
    series.append(Series(
        name="Planned (GTFS)", emphasis=True, dashed=True,
        points=[Point(x=float(v), y=float(i)) for i, v in enumerate(planned_elapsed)],
    ))
    avg = pd.concat([d["elapsed"] for d in per_day], axis=1).mean(axis=1, skipna=True)
    series.append(Series(
        name=f"Average actual (n={len(per_day)} days)", emphasis=True, color="var(--s2)",
        points=[Point(x=float(v), y=float(i)) for i, v in avg.items() if pd.notna(v)],
    ))

    sk = data["skipped"]
    return AnalysisResult(
        kind="chart", chart_type="trajectories", series=series,
        title="How much does the same departure vary, day to day?",
        subtitle=(f"{data['label']} · {data['time_of_day']} departure · "
                  f"{len(per_day)} matched of {data['scanned']} days scanned"),
        x_label="minutes since departure", y_tick_labels=stop_names,
        notes=[
            "Where the average sits right of the dashed plan, that stop is "
            "habitually reached late; the spread of the faint lines around it is "
            "how consistent that is.",
            f"Days skipped while scanning: {sk['no_plan']} with no timetable, "
            f"{sk['route_mismatch']} running a different stop pattern (a different "
            f"journey, not missing data), {sk['no_actual']} with no GPS.",
            f"Only {len(per_day)} days matched — the source notebook required 20 "
            "before averaging, so treat this as indicative unless you raise the "
            "scan window.",
            _CREDIT,
        ],
    ).ensure_table()


@analysis(
    name="schedule-adherence-map",
    title="Planned route vs. where buses actually were",
    description="The planned route dashed against the measured one solid, where "
                "each stop sits at a distance-weighted average of the real GPS "
                "pings that matched it — not at its timetable coordinate.",
    author="yuvalko1",
    tags=["reliability", "gps", "map", "interactive"],
    inputs=[],
    options=_OPTIONS,
)
def run_map(req: AnalysisRequest):
    data = _fetch(req)
    if data is None:
        return metrics(("No data", 0), notes=[
            "No day in the scanned window had both a matching timetable and GPS "
            "for this line — try another line_ref or a longer scan.", _CREDIT])

    per_day, planned_elapsed, canonical_xy = _per_stop_elapsed(data)
    plan = data["plan"]
    n_stops = len(plan)

    # Pool every matched ping per stop, weighted by 1/distance so the pings that
    # passed closest to a stop dominate its averaged position — ported from the
    # notebook, and the reason the measured route can bow away from the planned one.
    pooled = {i: {"lon": [], "lat": [], "elapsed": [], "w": []} for i in range(n_stops)}
    for d in per_day:
        nearest = d["masked"].argmin(axis=1)
        dist = d["masked"].min(axis=1)
        for j in np.where(np.isfinite(dist))[0]:
            s = int(nearest[j])
            pooled[s]["lon"].append(d["xy"][j, 0])
            pooled[s]["lat"].append(d["xy"][j, 1])
            pooled[s]["elapsed"].append(d["raw_elapsed"][j])
            pooled[s]["w"].append(1.0 / (dist[j] + 1e-6))

    def wmean(vals, w):
        return float(np.average(vals, weights=w)) if vals else float("nan")

    avg_lon = np.array([wmean(pooled[i]["lon"], pooled[i]["w"]) for i in range(n_stops)])
    avg_lat = np.array([wmean(pooled[i]["lat"], pooled[i]["w"]) for i in range(n_stops)])
    avg_el = np.array([wmean(pooled[i]["elapsed"], pooled[i]["w"]) for i in range(n_stops)])
    n_pings = np.array([len(pooled[i]["lon"]) for i in range(n_stops)])
    has_avg = ~np.isnan(avg_lon)

    vmax = float(max(planned_elapsed.max(), np.nanmax(avg_el))) or 1.0
    features: list[dict] = []

    # Planned: dashed, hollow, at the timetable's own coordinates.
    for i in range(n_stops - 1):
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [float(canonical_xy[i, 0]), float(canonical_xy[i, 1])],
                [float(canonical_xy[i + 1, 0]), float(canonical_xy[i + 1, 1])]]},
            "properties": {"color": _color(planned_elapsed[i] / vmax), "weight": 3,
                           "dashed": True},
        })
    for i in range(n_stops):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(canonical_xy[i, 0]), float(canonical_xy[i, 1])]},
            "properties": {"color": _color(planned_elapsed[i] / vmax), "weight": 4,
                           "popup": f"Planned · {plan['name'].iloc[i]} @ "
                                    f"{planned_elapsed[i]:.1f} min"},
        })

    # Measured: solid, at the weighted-average GPS position, sized by ping count.
    idxs = np.where(has_avg)[0]
    for a, b in zip(idxs[:-1], idxs[1:]):
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [float(avg_lon[a]), float(avg_lat[a])],
                [float(avg_lon[b]), float(avg_lat[b])]]},
            "properties": {"color": _color(avg_el[a] / vmax), "weight": 4},
        })
    for i in idxs:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(avg_lon[i]), float(avg_lat[i])]},
            "properties": {"color": _color(avg_el[i] / vmax),
                           "weight": int(4 + min(int(n_pings[i]), 50) ** 0.5),
                           "popup": f"Measured · stop {i} @ {avg_el[i]:.1f} min "
                                    f"(n={int(n_pings[i])} pings)"},
        })

    return geo(
        features,
        title="Planned route vs. where buses actually were",
        legend=GeoLegend(
            label="minutes since departure",
            colors=_GRADIENT,
            min_label="0",
            max_label=f"{vmax:.0f}",
            items=[
                {"label": "Planned (GTFS)", "color": "#666", "dashed": True},
                {"label": "Measured (GPS average)", "color": "#666", "dashed": False},
            ],
        ),
        subtitle=(f"{data['label']} · {data['time_of_day']} departure · "
                  f"{len(per_day)} days · {int(n_pings.sum())} matched pings"),
        notes=[
            "Dashed = the GTFS plan at its own stop coordinates. Solid = the same "
            "route rebuilt from real GPS, each stop placed at a distance-weighted "
            "average of the pings that matched it, and sized by how many did.",
            "Both are colored by minutes since departure (dark purple → yellow), so "
            "a color mismatch between the two lines at the same place is the bus "
            "running late there.",
            f"{int(has_avg.sum())}/{n_stops} stops had enough matched GPS to place; "
            "the rest are absent from the solid line.",
            _CREDIT,
        ],
    )


@analysis(
    name="schedule-adherence-by-day",
    title="Which day ran worst?",
    description="Total journey time for each matched day against the schedule. "
                "The stringline shows where time is lost; this shows which days "
                "lost it.",
    author="yuvalko1",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=[],
    options=_OPTIONS,
)
def run_by_day(req: AnalysisRequest):
    data = _fetch(req)
    if data is None:
        return metrics(("No data", 0), notes=[
            "No day in the scanned window had both a matching timetable and GPS "
            "for this line — try another line_ref or a longer scan.", _CREDIT])

    per_day, planned_elapsed, _ = _per_stop_elapsed(data)
    planned_total = float(planned_elapsed[-1])

    rows = []
    for d in per_day:
        reached = d["elapsed"].dropna()
        if reached.empty:
            continue
        # Last stop actually resolved, not the route's last stop — a day whose
        # GPS died halfway would otherwise look impossibly quick.
        rows.append({"day": d["date"], "kind": "Actual", "minutes": float(reached.iloc[-1]),
                     "last_stop": int(reached.index[-1])})
    if not rows:
        return metrics(("No data", 0), notes=[
            "No matched day resolved any stop from GPS.", _CREDIT])

    df = pd.DataFrame(rows)
    # Compare each day against the plan *up to the same stop*, so a truncated
    # GPS trail isn't scored as if it had run the whole route.
    df["planned"] = [float(planned_elapsed[i]) for i in df["last_stop"]]
    df["delta"] = (df["minutes"] - df["planned"]).round(1)
    df = df.sort_values("day")

    long = pd.DataFrame({
        "day": [*df["day"], *df["day"]],
        "kind": ["Actual"] * len(df) + ["Planned"] * len(df),
        "minutes": [*df["minutes"].round(1), *df["planned"].round(1)],
    })

    worst = df.loc[df["delta"].idxmax()]
    best = df.loc[df["delta"].idxmin()]
    return bar_chart(
        long, x="day", y="minutes", series="kind", horizontal=True,
        title="Which day ran worst?",
        subtitle=(f"{data['label']} · {data['time_of_day']} departure · "
                  f"{len(df)} matched days"),
        x_label="day", y_label="minutes to last resolved stop",
        notes=[
            f"Worst day {worst['day']}: {worst['delta']:+.1f} min vs schedule. "
            f"Best day {best['day']}: {best['delta']:+.1f} min.",
            "Each day is compared against the plan up to the last stop its GPS "
            "actually resolved, so a trail that cuts out early isn't scored as a "
            "fast trip.",
            f"Planned end-to-end run time is {planned_total:.0f} min.",
            _CREDIT,
        ],
    )
