"""Buses that left the planned route — how far off, and where.

One of the three questions the team wanted answered from open data: can we spot
a vehicle that diverged from its published route? Yes, and fairly directly —
the planned route's stop coordinates are in GTFS, and SIRI reports where the
bus actually was. For each GPS ping, the distance to the nearest planned stop
is how far off-route the bus was at that moment.

The measure is deliberately *nearest planned stop*, not "distance from the road
the route follows": GTFS shapes give the road geometry, but stop coordinates are
what this project already fetches everywhere else, and a bus that is 800m from
every stop on its own line is off-route by any reasonable reading. The cost is
that long stop spacing (intercity, or a highway stretch) inflates the distance
without the bus having gone anywhere wrong — which is why the threshold is an
option, the distribution is shown rather than just a pass/fail count, and the
notes say so plainly.

Two cards from one fetch:

* **route-divergence** — how far each sampled ride strayed, worst first.
* **route-divergence-map** — the planned stops against the pings that exceeded
  the threshold, so "where does this line go wrong" is answerable by looking.
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from openbus_hack import (
    AnalysisRequest,
    GeoLegend,
    OptionSpec,
    analysis,
    bar_chart,
    geo,
    metrics,
    stride,
)
from openbus_hack.diskcache import cached

ISRAEL_TZ = datetime.timezone(datetime.timedelta(hours=3))
# SIRI ingestion lags a few days behind live traffic.
LAG_DAYS = 3
# A bus reports roughly once a minute; a few hours of one line is a few thousand
# pings, which is plenty to characterise a route and still returns quickly.
WINDOW_HOURS = 4
MAX_RIDES = 40


def _haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great-circle distance in metres, broadcast over numpy arrays.

    Plain euclidean degrees would understate east-west distance by ~15% at
    Israel's latitude and make the threshold mean different things north to
    south, so the extra trig is worth it here.
    """
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * 6_371_000.0 * np.arcsin(np.sqrt(a))


def _load(line: str, operator: str, day: datetime.date):
    """Planned stops + deduplicated GPS pings for one line on one day."""

    key = ("v2-lineref", line, operator, day)

    def compute():
        start = datetime.datetime.combine(day, datetime.time(7, 0), tzinfo=ISRAEL_TZ)
        end = start + datetime.timedelta(hours=WINDOW_HOURS)

        routes = stride.routes(lines=[line], operators=[operator] if operator else None,
                               date_from=day, date_to=day, limit=50)
        if routes.empty:
            return None
        route = routes.iloc[0]
        line_ref = int(route["line_ref"])
        operator_ref = int(route["operator_ref"])
        label = f"{route.get('route_short_name', line)} {route.get('route_long_name', '')}".strip()

        # Planned stop coordinates. One day, one line — the endpoint rejects
        # wider ranges and times out unfiltered.
        plan_rows = stride.get("/route_timetable/list", {
            "line_refs": line_ref,
            "planned_start_time_date_from": start,
            "planned_start_time_date_to": end,
            "order_by": "planned_arrival_time",
            "limit": 15000,
        })
        if not plan_rows:
            return None
        plan = pd.DataFrame(plan_rows).dropna(subset=["lat", "lon"])
        # One row per distinct stop location is all the distance test needs, and
        # collapsing the repeats across rides keeps the distance matrix small.
        stops = plan.drop_duplicates(subset=["lat", "lon"])[["name", "lat", "lon"]]
        if stops.empty:
            return None

        # Filter by siri_routes__line_ref, NOT stride.siri_vehicle_locations'
        # `lines=` argument: that sets gtfs_route__route_short_name, which this
        # endpoint ignores, so it silently returns the whole country's pings.
        # Caught because divergence came back at 50km and 97.7% of pings — the
        # bus wasn't off route, the pings belonged to other lines entirely.
        ping_params = {
            "siri_routes__line_ref": line_ref,
            "recorded_at_time_from": start,
            "recorded_at_time_to": end,
            "order_by": "recorded_at_time",
            "limit": 15000,
        }
        if operator:
            ping_params["siri_routes__operator_ref"] = operator_ref
        ping_rows = stride.get("/siri_vehicle_locations/list", ping_params)
        if not ping_rows:
            return None
        pings = pd.DataFrame(ping_rows)
        for c in ("lat", "lon"):
            pings[c] = pd.to_numeric(pings[c], errors="coerce")
        pings = pings.dropna(subset=["lat", "lon"])
        # Overlapping SIRI snapshots repeat the same observation (~10% of rows);
        # left in, they'd weight a stationary bus more heavily than a moving one.
        pings = pings.drop_duplicates(
            subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])
        if pings.empty:
            return None
        return label, stops, pings

    return cached("route_divergence", key, compute)


def _fetch(req: AnalysisRequest):
    day = min(req.date_to, datetime.date.today() - datetime.timedelta(days=LAG_DAYS))
    while day.weekday() in (4, 5):  # Fri/Sat — thin service in Israel
        day -= datetime.timedelta(days=1)
    return _load(req.line or "23", req.operator or "דן", day), day


def _distances(stops: pd.DataFrame, pings: pd.DataFrame) -> np.ndarray:
    """Metres from each ping to its nearest planned stop."""
    slat = stops["lat"].to_numpy(dtype=float)[None, :]
    slon = stops["lon"].to_numpy(dtype=float)[None, :]
    plat = pings["lat"].to_numpy(dtype=float)[:, None]
    plon = pings["lon"].to_numpy(dtype=float)[:, None]
    return _haversine_m(plat, plon, slat, slon).min(axis=1)


_OPTIONS = [
    OptionSpec(
        key="threshold_m", label="Off-route threshold (m)", type="number", default=500,
        help="How far from the nearest planned stop counts as off-route. Raise it "
             "for intercity lines, where long gaps between stops put a perfectly "
             "on-route bus a long way from any of them.",
    ),
]
_TAGS = ["anomaly", "gps", "route", "interactive"]


def _no_data(day: datetime.date, line: str, operator: str):
    return metrics(("No data", 0), notes=[
        f"No planned timetable and GPS pair for line {line} ({operator or 'any operator'}) "
        f"on {day} 07:00-{7 + WINDOW_HOURS}:00 Israel time. Try another line, "
        "operator, or date."])


@analysis(
    name="route-divergence",
    title="Buses that strayed from the planned route",
    description="For each sampled ride, how far it got from the nearest stop on its "
                "own line. A ride that spends time far from every planned stop either "
                "detoured, was diverted, or is mis-assigned to this route.",
    author="team",
    tags=_TAGS,
    inputs=["lines", "operators", "dates"],
    options=_OPTIONS,
)
def run_divergence(req: AnalysisRequest):
    data, day = _fetch(req)
    if data is None:
        return _no_data(day, req.line or "23", req.operator or "דן")
    label, stops, pings = data
    threshold = float(req.opt("threshold_m", 500) or 500)

    pings = pings.copy()
    pings["off_route_m"] = _distances(stops, pings)

    per_ride = (pings.groupby("siri_ride__id")
                .agg(worst_m=("off_route_m", "max"),
                     median_m=("off_route_m", "median"),
                     pings=("off_route_m", "size"))
                .reset_index())
    # A ride with a handful of pings can look dramatic off one bad fix; the
    # median is only meaningful with a real trail behind it.
    per_ride = per_ride[per_ride["pings"] >= 5]
    if per_ride.empty:
        return _no_data(day, req.line or "23", req.operator or "דן")

    per_ride = per_ride.sort_values("worst_m", ascending=False).head(MAX_RIDES)
    per_ride["label"] = [f"ride {int(r.siri_ride__id)} · {int(r.pings)} pings"
                         for r in per_ride.itertuples()]

    long = pd.DataFrame({
        "ride": [*per_ride["label"], *per_ride["label"]],
        "kind": (["Worst point"] * len(per_ride)) + (["Typical (median)"] * len(per_ride)),
        "metres": [*per_ride["worst_m"].round(0), *per_ride["median_m"].round(0)],
    })

    over = int((per_ride["worst_m"] > threshold).sum())
    sustained = int((per_ride["median_m"] > threshold).sum())
    return bar_chart(
        long, x="ride", y="metres", series="kind", horizontal=True,
        title="Buses that strayed from the planned route",
        subtitle=f"{label} · {day} · {len(pings):,} pings across {len(per_ride)} rides",
        x_label="ride", y_label="metres from nearest planned stop",
        notes=[
            f"{over} of {len(per_ride)} rides passed more than {threshold:.0f}m from "
            f"every planned stop at some point; {sustained} were that far out on a "
            "typical ping, which is the stronger signal — one bad point is a GPS "
            "glitch, a whole ride out there is a real detour.",
            "Distance is to the nearest stop on the line, not to the road the route "
            "follows. On a line with long gaps between stops an on-route bus can sit "
            "hundreds of metres from all of them, so raise the threshold for "
            "intercity routes and read the median column, not the worst.",
            "Both columns are shown rather than a pass/fail count so the threshold "
            "stays the reader's to argue with.",
        ],
    )


@analysis(
    name="route-divergence-map",
    title="Where buses leave the route",
    description="The line's planned stops against every GPS ping that fell beyond "
                "the off-route threshold — so a recurring detour shows up as a "
                "cluster rather than a number.",
    author="team",
    tags=_TAGS,
    inputs=["lines", "operators", "dates"],
    options=_OPTIONS,
)
def run_divergence_map(req: AnalysisRequest):
    data, day = _fetch(req)
    if data is None:
        return _no_data(day, req.line or "23", req.operator or "דן")
    label, stops, pings = data
    threshold = float(req.opt("threshold_m", 500) or 500)

    pings = pings.copy()
    pings["off_route_m"] = _distances(stops, pings)
    stray = pings[pings["off_route_m"] > threshold]

    features: list[dict] = []
    for r in stops.itertuples():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r.lon), float(r.lat)]},
            "properties": {"color": "#2a78d6", "weight": 4, "popup": f"Planned stop · {r.name}"},
        })

    MAX_STRAY_MARKERS = 600
    stray_total = len(stray)
    if stray_total > MAX_STRAY_MARKERS:
        # Evenly spaced rather than the worst N, so the map still shows *where*
        # strays happen instead of only the single most extreme cluster.
        stray = stray.iloc[
            [round(i) for i in np.linspace(0, stray_total - 1, MAX_STRAY_MARKERS)]]

    if not stray.empty:
        # Colour by how far out, so a 600m wobble and a 5km detour don't read alike.
        worst = float(stray["off_route_m"].max())
        for r in stray.itertuples():
            frac = (r.off_route_m - threshold) / max(worst - threshold, 1.0)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(r.lon), float(r.lat)]},
                "properties": {
                    "color": "#e34948" if frac > 0.5 else "#eda100",
                    "weight": 5,
                    "popup": (f"Off route · {r.off_route_m:,.0f}m from nearest stop · "
                              f"ride {int(r.siri_ride__id)}"),
                },
            })

    pct = 100.0 * len(stray) / max(len(pings), 1)
    return geo(
        features,
        title="Where buses leave the route",
        subtitle=(f"{label} · {day} · {len(stray):,} of {len(pings):,} pings "
                  f"({pct:.1f}%) beyond {threshold:.0f}m"),
        legend=GeoLegend(
            label=f"pings beyond {threshold:.0f}m from any planned stop",
            colors=[],
            items=[
                {"label": "Planned stop", "color": "#2a78d6"},
                {"label": f"Off route (< {threshold * 1.5:.0f}m)", "color": "#eda100"},
                {"label": "Far off route", "color": "#e34948"},
            ],
        ),
        notes=[
            "Blue is where the timetable says the bus should stop; orange and red are "
            "actual GPS fixes that fell beyond the threshold from every one of them.",
            *([f"Showing {len(stray):,} of {stray_total:,} off-route pings, evenly "
               "sampled — every marker on a busy day would hang the browser."]
              if stray_total > len(stray) else []),
            "A tight cluster of strays in one place is the interesting result — that's "
            "a diversion the whole line takes, not a wandering driver. Scattered "
            "single points are usually GPS error.",
            "Distance is measured to the nearest planned stop, so a long stop-free "
            "stretch of an otherwise correct route can show up here. Raise the "
            "threshold on intercity lines before reading anything into it.",
        ],
    )
