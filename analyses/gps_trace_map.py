"""GPS trace map: one real bus's actual path on a map, colored by time of day.

Ported from yuvalko1's "load siri vehicle locations to pandas dataframe.ipynb"
(github.com/yuvalko1/talpiot-hackathon-public-transportation, branch main) — that
notebook plots one vehicle's raw GPS trail on a folium map, colored by elapsed
time via a viridis-style gradient. This ports the same idea onto openbus_hack's
own geo() helper (a client-rendered Leaflet map) instead of a baked folium HTML
export, using our own already-wrapped, disk-cached stride.siri_vehicle_locations()
rather than raw HTTP calls.

The companion notebooks that overlay a *planned* route on the same map
("load gtfs timetable...ipynb", "compare gtfs planned vs siri actual.ipynb") are
covered by ``analyses/schedule_adherence_average.py``'s map card, which draws the
GTFS plan dashed against a GPS-derived measured route.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from openbus_hack import AnalysisRequest, GeoLegend, analysis, geo, metrics, stride

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
_CREDIT = "Analysis by yuvalko1 (github.com/yuvalko1/talpiot-hackathon-public-transportation)."

# Same viridis-style gradient the source notebook used for its branca.colormap.
_GRADIENT = ["#440154", "#31688e", "#35b779", "#fde725"]


def _color_for(t: float) -> str:
    """t in [0, 1] -> interpolated hex color along the gradient."""
    if t <= 0:
        return _GRADIENT[0]
    if t >= 1:
        return _GRADIENT[-1]
    seg = t * (len(_GRADIENT) - 1)
    i = int(seg)
    frac = seg - i
    return _lerp_hex(_GRADIENT[i], _GRADIENT[min(i + 1, len(_GRADIENT) - 1)], frac)


def _lerp_hex(c1: str, c2: str, frac: float) -> str:
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = round(r1 + (r2 - r1) * frac)
    g = round(g1 + (g2 - g1) * frac)
    b = round(b1 + (b2 - b1) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


@analysis(
    name="gps-trace-map",
    title="One bus, actual GPS trace",
    description="A single real ride's raw GPS trail on a map, colored by time of "
                "day — pick a busier line/operator if the default window shows "
                "nothing.",
    author="yuvalko1",
    tags=["gps", "map", "interactive"],
    inputs=["lines", "operators", "dates"],
    draft=False,
)
def run(req: AnalysisRequest):
    line = req.line or "23"
    operator = req.operator or "דן"

    # SIRI ingestion lags a few days behind live, and a multi-hour late-morning
    # local window maximizes the odds of catching a bus that's actually moving
    # (vs. picking one exact minute and finding nothing running).
    day = min(req.date_to, datetime.date.today() - datetime.timedelta(days=3))
    while day.weekday() in (4, 5):  # Fri/Sat — thin bus service in Israel
        day -= datetime.timedelta(days=1)
    t1 = datetime.datetime.combine(day, datetime.time(7, 0), tzinfo=ISRAEL_TZ)
    t2 = t1 + datetime.timedelta(hours=4)

    # Resolve the line number to a line_ref first. stride.siri_vehicle_locations'
    # `lines=` argument maps to gtfs_route__route_short_name, which this endpoint
    # ignores — it would hand back the whole country's pings and this card would
    # then label some unrelated bus as line 23. Filter on siri_routes__line_ref,
    # which the endpoint does honour.
    routes = stride.routes(lines=[line], operators=[operator] if operator else None,
                           date_from=day, date_to=day, limit=50)
    if routes.empty:
        return metrics(
            ("No data", 0),
            notes=[f"No GTFS route for line {line} ({operator}) on {day}."],
        )
    line_ref = int(routes.iloc[0]["line_ref"])
    operator_ref = int(routes.iloc[0]["operator_ref"])

    ping_rows = stride.get("/siri_vehicle_locations/list", {
        "siri_routes__line_ref": line_ref,
        "siri_routes__operator_ref": operator_ref,
        "recorded_at_time_from": t1,
        "recorded_at_time_to": t2,
        "order_by": "recorded_at_time",
        "limit": 15000,
    })
    pings = pd.DataFrame(ping_rows)
    if not pings.empty:
        for c in ("lat", "lon"):
            pings[c] = pd.to_numeric(pings[c], errors="coerce")
        pings["recorded_at_time"] = pd.to_datetime(pings["recorded_at_time"], utc=True)
        pings = pings.dropna(subset=["lat", "lon"])
    if pings.empty:
        return metrics(
            ("No data", 0),
            notes=[f"No GPS pings for line {line} ({operator}) on {day} "
                   "07:00-11:00 Israel time — try a different line/operator."],
        )

    # SIRI snapshots overlap, so the same physical observation is reported more
    # than once — measured at ~10% of rows in a sample window. Left in, those
    # duplicates inflate the ping count and add zero-length map segments.
    # (siri_ride__id never spans two vehicle_refs — checked across 6326 rides —
    # so grouping by ride is safe without also keying on the plate.)
    before = len(pings)
    pings = pings.drop_duplicates(subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])
    duplicates = before - len(pings)

    # One ride: whichever siri_ride__id has the most pings in the window — same
    # pick the source notebook made ("the ride with the richest trail").
    ride_id = pings.groupby("siri_ride__id").size().idxmax()
    trace = (pings[pings["siri_ride__id"] == ride_id]
             .sort_values("recorded_at_time")
             .reset_index(drop=True))

    t_start = trace["recorded_at_time"].iloc[0]
    t_end = trace["recorded_at_time"].iloc[-1]
    span = (t_end - t_start).total_seconds() or 1.0

    coords = list(zip(trace["lon"], trace["lat"]))
    times = [(t - t_start).total_seconds() / span for t in trace["recorded_at_time"]]

    features: list[dict] = []
    for (lon1, lat1), (lon2, lat2), t in zip(coords[:-1], coords[1:], times[:-1]):
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[lon1, lat1], [lon2, lat2]]},
            "properties": {"color": _color_for(t), "weight": 4},
        })
    for (lon, lat), t, rec in zip(coords, times, trace["recorded_at_time"]):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"color": _color_for(t), "weight": 5,
                           "popup": rec.tz_convert(ISRAEL_TZ).strftime("%H:%M:%S")},
        })

    return geo(
        features,
        title="One bus, actual GPS trace",
        legend=GeoLegend(
            label="minutes into the ride",
            colors=_GRADIENT,
            min_label=t_start.tz_convert(ISRAEL_TZ).strftime("%H:%M"),
            max_label=t_end.tz_convert(ISRAEL_TZ).strftime("%H:%M"),
        ),
        subtitle=(f"Line {line} ({operator}) · ride {int(ride_id)} · "
                  f"{t_start.tz_convert(ISRAEL_TZ).strftime('%Y-%m-%d %H:%M')} "
                  f"Israel time · {len(trace)} pings"),
        notes=[
            "Color follows elapsed time (dark purple → yellow), the same gradient "
            "the source notebook used — a purple-to-yellow jump in one spot is "
            "the bus moving fast there; a cluster of one color is it sitting still.",
            f"Picked automatically: the ride with the most GPS pings among all "
            f"{pings['siri_ride__id'].nunique()} rides seen for this line "
            "in the sampled window.",
            f"{duplicates:,} duplicate ping(s) dropped before plotting — the same "
            "vehicle, instant and position reported in overlapping SIRI snapshots.",
            _CREDIT,
        ],
    )
