"""Fineable service failures: ghost rides, early departures, and late departures.

Israel's Ministry of Transport can fine operators for service that deviates
from the published timetable. Three distinct failure modes are detectable
from open data, at very different confidence levels:

* **Ghost ride / non-arrival** — a ride is in the GTFS plan but no SIRI GPS
  ping was ever recorded against its scheduled departure. The trip likely
  never ran, or ran completely untracked (see caveats below — this is the
  weakest-confidence category of the three).
* **Early departure** — the first GPS ping for a matched ride arrives
  materially *before* its scheduled time. Passengers cannot catch a bus that
  already left, which is why regulators tend to treat any material earliness
  as a violation, unlike lateness which usually gets a grace window.
* **Late departure** — the first GPS ping arrives materially *after* the
  scheduled time, beyond a tolerance.

Method (deliberately cheap, so this runs as a live dashboard card):

1. ``/gtfs_rides/list`` filtered by ``gtfs_route__line_refs`` +
   ``gtfs_route__operator_refs`` gives every *planned* ride's scheduled
   ``start_time`` for the whole window in one paged call — no per-day
   route-id juggling needed, unlike ``/route_timetable/list``.
2. ``/siri_vehicle_locations/list`` filtered by ``siri_routes__line_ref`` +
   ``siri_routes__operator_ref`` + ``siri_rides__schedualed_start_time_from/to``
   (sic — that's the API's own field spelling) gives every raw GPS ping for
   the same window in one paged call. Pings are grouped by
   ``siri_ride__id``; the earliest ``recorded_at_time`` in each group is
   used as a proxy for actual departure.
3. Planned rides are joined to SIRI ride-groups on exact
   ``start_time == siri_ride__scheduled_start_time`` equality — verified live
   (see module tests during authoring) to line up exactly for a sampled
   line/day, since both are drawn from the same GTFS-derived timetable slot.
   A planned ride with no matching group is the "ghost" case.

This intentionally bypasses ``/gtfs_rides_agg/group_by``'s ``total_actual_rides``
(which was verified, live, to return 0 for every row — a server-side
aggregation bug, not a real 0% arrival rate) and also bypasses
``/siri_rides/list``'s own derived ``first_vehicle_location_id`` /
``gtfs_ride_id`` columns (verified live to be inconsistently NULL — present
for some days, absent for others, for identical, genuinely-tracked rides).
Building the actual-departure signal from raw GPS pings instead sidesteps
both of those known-broken server-side joins.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from openbus_hack import AnalysisRequest, OptionSpec, analysis, bar_chart, metrics, stride
from openbus_hack.diskcache import cached

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

# SIRI ingestion lags a few days behind live — never analyze today or yesterday.
LAG_DAYS = 3
# Unlike the per-day-capped route_timetable-based analyses elsewhere in this repo,
# this one's two fetches are each a single paged multi-day call, so the window can
# be more generous — capped here mainly to bound payload size and API courtesy.
MAX_WINDOW_DAYS = 10
# A single raw stride.get() call is NOT auto-paged (unlike the stride.* wrapper
# functions) — walk offset/limit pages ourselves, same algorithm as
# stride.py's private _paged(), capped so one wildly busy line/window can't
# turn a dashboard card into a runaway fetch.
PAGE_SIZE = 2000
ROW_CAP = 30000
# Small, line-unfiltered sample used only to auto-discover a tracked line when
# the caller didn't select one — mirrors analyses/siri_coverage.py's approach.
DISCOVERY_SAMPLE_LIMIT = 300

DEFAULT_EARLY_MIN = 1.0
DEFAULT_LATE_MIN = 5.0

GHOST_LABEL = "Ghost / non-arrival"
ONTIME_LABEL = "On-time"


def _fmt_min(x: float) -> str:
    return f"{x:g}"


def _early_label(t: float) -> str:
    return f"Early (>{_fmt_min(t)} min)"


def _late_label(t: float) -> str:
    return f"Late (>{_fmt_min(t)} min)"


# ── Window & scope resolution ───────────────────────────────────────────────


def _window(req: AnalysisRequest) -> tuple[date, date]:
    date_to = min(req.date_to, date.today() - timedelta(days=LAG_DAYS))
    date_from = min(req.date_from, date_to)
    if (date_to - date_from).days + 1 > MAX_WINDOW_DAYS:
        date_from = date_to - timedelta(days=MAX_WINDOW_DAYS - 1)
    return date_from, date_to


def _bounds(day_from: date, day_to: date) -> tuple[str, str]:
    """Tz-aware ISO bounds. The API 500s on naive datetimes for these filters."""
    start = datetime.combine(day_from, time(0, 0), tzinfo=ISRAEL_TZ)
    end = datetime.combine(day_to, time(23, 59), tzinfo=ISRAEL_TZ)
    return start.isoformat(), end.isoformat()


def _resolve_scope(req: AnalysisRequest, date_from: date, date_to: date) -> dict | None:
    """Pick the one (line_ref, operator_ref) this card will analyze.

    If a line was requested, resolve it via GTFS route metadata (first match,
    same convention as siri_coverage.py / schedule_adherence_average.py). If
    only an operator was requested, auto-discover that operator's most-tracked
    line from a small SIRI GPS sample rather than guessing. If neither was
    requested, auto-discover across all operators.
    """
    if req.line:
        routes_df = stride.routes(
            lines=[req.line],
            operators=[req.operator] if req.operator else None,
            date_from=date_from, date_to=date_to, limit=200,
        )
        if routes_df.empty:
            return None
        row = routes_df.iloc[0]
        return {
            "line_ref": int(row["line_ref"]), "operator_ref": int(row["operator_ref"]),
            "agency_name": str(row.get("agency_name") or row["operator_ref"]),
            "route_short_name": str(row.get("route_short_name") or req.line),
            "route_direction": str(row.get("route_direction") or "?"),
            "auto_discovered": False,
        }

    operator_ref = None
    if req.operator:
        refs = stride.operator_refs_for([req.operator], date_from, date_to)
        if not refs:
            return None
        operator_ref = refs[0]

    rows: list = []
    span = (date_to - date_from).days + 1
    for back in range(min(span, 4)):
        sample_day = date_to - timedelta(days=back)
        start, end = _bounds(sample_day, sample_day)
        params = {"recorded_at_time_from": start, "recorded_at_time_to": end,
                  "limit": DISCOVERY_SAMPLE_LIMIT}
        if operator_ref is not None:
            params["siri_routes__operator_ref"] = operator_ref
        try:
            rows = stride.get("/siri_vehicle_locations/list", params)
        except Exception:
            rows = []
        if rows:
            break
    if not rows:
        return None

    sample = pd.DataFrame(rows)
    if "siri_route__line_ref" not in sample.columns or "siri_route__operator_ref" not in sample.columns:
        return None
    line_ref, op_ref = sample.groupby(
        ["siri_route__line_ref", "siri_route__operator_ref"]
    ).size().idxmax()
    line_ref, op_ref = int(line_ref), int(op_ref)

    meta_rows = stride.get("/gtfs_routes/list", {
        "line_refs": line_ref, "operator_refs": op_ref,
        "date_from": date_from, "date_to": date_to, "limit": 5,
    })
    if meta_rows:
        m = meta_rows[0]
        return {
            "line_ref": line_ref, "operator_ref": op_ref,
            "agency_name": str(m.get("agency_name") or op_ref),
            "route_short_name": str(m.get("route_short_name") or "?"),
            "route_direction": str(m.get("route_direction") or "?"),
            "auto_discovered": True,
        }
    return {"line_ref": line_ref, "operator_ref": op_ref, "agency_name": str(op_ref),
            "route_short_name": "?", "route_direction": "?", "auto_discovered": True}


# ── Fetch + classify ─────────────────────────────────────────────────────────


def _get_paged(path: str, params: dict) -> list[dict]:
    """Walk offset/limit pages of one raw endpoint, capped at ROW_CAP.

    stride.get() itself makes exactly one HTTP call per invocation (that's
    where its disk cache keys live); the paging loop has to happen here.
    """
    rows: list[dict] = []
    offset = 0
    while len(rows) < ROW_CAP:
        batch = stride.get(path, {**params, "limit": PAGE_SIZE, "offset": offset})
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += len(batch)
    return rows


def _load(line_ref: int, operator_ref: int, date_from: date, date_to: date,
          early_threshold: float, late_threshold: float):
    """Disk-cached: one planned-rides fetch + one GPS-pings fetch, joined and
    classified. Returns (per_ride DataFrame, diagnostics dict) or None if
    there is no GTFS plan at all for this scope/window."""

    key = ("v1", line_ref, operator_ref, date_from.isoformat(), date_to.isoformat(),
           early_threshold, late_threshold)

    def compute():
        planned_rows = _get_paged("/gtfs_rides/list", {
            "gtfs_route__line_refs": line_ref, "gtfs_route__operator_refs": operator_ref,
            "gtfs_route__date_from": date_from, "gtfs_route__date_to": date_to,
        })
        if not planned_rows:
            return None
        planned = pd.DataFrame(planned_rows).drop_duplicates(subset=["id"])
        planned["start_time"] = pd.to_datetime(planned["start_time"], utc=True)
        n_fetched = len(planned)
        # Verified live: a real minority of /gtfs_rides/list rows come back with
        # start_time (and end_time) null — a GTFS source data gap, not a SIRI
        # matching problem. A ride with no scheduled time can't be timed or
        # ghost-checked at all, so these are dropped up front rather than
        # falling through the join as a spurious unmatched "ghost".
        planned = planned.dropna(subset=["start_time"])
        n_no_schedule = n_fetched - len(planned)
        n_planned_raw = len(planned)
        # Two distinct GTFS journeys sharing the exact same scheduled minute
        # are indistinguishable from SIRI alone (SIRI rides are also keyed by
        # scheduled_start_time) — rare, but flagged rather than silently
        # double-counted against a single matched ping-group.
        dup_start_times = int(planned["start_time"].duplicated().sum())

        day_from, day_to = _bounds(date_from, date_to)
        ping_rows = _get_paged("/siri_vehicle_locations/list", {
            "siri_routes__line_ref": line_ref, "siri_routes__operator_ref": operator_ref,
            "siri_rides__schedualed_start_time_from": day_from,  # sic — API's own spelling
            "siri_rides__schedualed_start_time_to": day_to,
            "order_by": "recorded_at_time",
        })
        n_raw_pings = len(ping_rows)

        if ping_rows:
            pings = pd.DataFrame(ping_rows)
            pings["recorded_at_time"] = pd.to_datetime(pings["recorded_at_time"], utc=True)
            pings["siri_ride__scheduled_start_time"] = pd.to_datetime(
                pings["siri_ride__scheduled_start_time"], utc=True)
            before = len(pings)
            # Overlapping SIRI snapshots repeat the same physical observation
            # (~10% of rows, per repo experience) — harmless for a min()
            # aggregation, but dropped anyway so ping-count diagnostics (used
            # below for confidence, and shown in notes) aren't inflated.
            pings = pings.drop_duplicates(subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])
            n_dupe_pings = before - len(pings)
            grouped = (
                pings.groupby(["siri_ride__id", "siri_ride__scheduled_start_time"])
                .agg(first_ping=("recorded_at_time", "min"),
                     n_pings=("recorded_at_time", "size"),
                     n_vehicles=("siri_ride__vehicle_ref", "nunique"))
                .reset_index()
            )
            # First-ever ping is NOT a good departure proxy on its own — verified
            # live while building this card: for one sampled line, ~80% of
            # "first pings" landed at almost exactly -30 or -5 minutes before
            # scheduled time with distance_from_journey_start == 0 and
            # velocity == 0, i.e. the vehicle sitting at the origin stop before
            # departure (boarding), not moving. SIRI/operator feeds evidently
            # start reporting a vehicle against its *next* scheduled ride some
            # fixed lead time ahead of departure. Using that raw first ping as
            # "actual departure" would have made ~90% of matched rides look
            # early — a data artifact, not a real finding. Instead, the first
            # ping where the vehicle has actually started moving (nonzero
            # distance-from-start or nonzero velocity) is used as the
            # departure proxy; falls back to the raw first ping only if the
            # vehicle was never observed moving in the queried window at all
            # (flagged via 'stationary_only' below; the earliness threshold
            # can't apply to a ride that never confirmedly moved anyway).
            dist = pd.to_numeric(pings["distance_from_journey_start"], errors="coerce").fillna(0)
            vel = pd.to_numeric(pings["velocity"], errors="coerce").fillna(0)
            moving = pings[(dist > 0) | (vel > 0)]
            moving_first = (
                moving.groupby(["siri_ride__id", "siri_ride__scheduled_start_time"])
                ["recorded_at_time"].min().rename("first_moving_ping").reset_index()
            )
            grouped = grouped.merge(
                moving_first, on=["siri_ride__id", "siri_ride__scheduled_start_time"], how="left")
            grouped["stationary_only"] = grouped["first_moving_ping"].isna()
            grouped["departure_ping"] = grouped["first_moving_ping"].fillna(grouped["first_ping"])
            # If more than one siri_ride id coincidentally shares a scheduled
            # start time, keep the one with the most pings — same
            # largest-group convention used elsewhere in this repo — rather
            # than an arbitrary one.
            grouped = (grouped.sort_values("n_pings", ascending=False)
                       .drop_duplicates(subset=["siri_ride__scheduled_start_time"], keep="first"))
        else:
            n_dupe_pings = 0
            grouped = pd.DataFrame(columns=[
                "siri_ride__id", "siri_ride__scheduled_start_time",
                "first_ping", "n_pings", "n_vehicles", "departure_ping", "stationary_only"])

        merged = planned.merge(
            grouped, left_on="start_time", right_on="siri_ride__scheduled_start_time", how="left")
        merged["matched"] = merged["departure_ping"].notna()
        merged["stationary_only"] = merged["stationary_only"].fillna(False)
        merged["delta_min"] = (
            (merged["departure_ping"] - merged["start_time"]).dt.total_seconds() / 60.0)

        def classify(row) -> str:
            if not row["matched"]:
                return GHOST_LABEL
            d = row["delta_min"]
            if d < -early_threshold:
                return _early_label(early_threshold)
            if d > late_threshold:
                return _late_label(late_threshold)
            return ONTIME_LABEL

        merged["category"] = merged.apply(classify, axis=1)
        merged["date"] = merged["start_time"].dt.tz_convert(ISRAEL_TZ).dt.date.astype(str)

        diag = {
            "n_planned": n_planned_raw,
            "n_no_schedule": n_no_schedule,
            "n_raw_pings": n_raw_pings,
            "n_dupe_pings_removed": n_dupe_pings,
            "n_days": merged["date"].nunique(),
            "dup_start_times": dup_start_times,
            "any_siri": bool(n_raw_pings),
            "n_stationary_only": int(merged["stationary_only"].sum()),
        }
        out = merged[["date", "start_time", "matched", "delta_min", "category",
                      "n_pings", "stationary_only"]].copy()
        return out, diag

    return cached("service_violations", key, compute)


# ── Shared notes builder ─────────────────────────────────────────────────────


def _method_notes(scope: dict, diag: dict, early_t: float, late_t: float) -> list[str]:
    notes = []
    if scope.get("auto_discovered"):
        notes.append(
            f"No line was selected, so this auto-picked the most-tracked line for the "
            f"scope: {scope['route_short_name']} (line_ref={scope['line_ref']}), "
            f"operator {scope['agency_name']}. Pick a line/operator to pin this down."
        )
    notes.append(
        f"Thresholds used: departing more than {_fmt_min(early_t)} min before schedule counts "
        f"as 'early', more than {_fmt_min(late_t)} min after counts as 'late'. These are "
        "illustrative round numbers reflecting commonly cited regulatory practice (earliness "
        "tolerated far less than lateness) — they are NOT sourced from the Ministry of "
        "Transport's actual fine schedule, which was not available to this analysis. Treat "
        "the split between categories as indicative, not a legal finding."
    )
    notes.append(
        "'Actual departure' is a proxy: the timestamp of the first SIRI GPS ping recorded "
        "against a ride's scheduled slot, compared to that scheduled time. GPS pings land "
        "every ~30s-2min, so this proxy has roughly that much built-in noise, and a ride "
        "whose first ping happens to arrive after it was already moving will understate "
        "earliness. No per-stop arrival times were used (unlike other cards in this repo) — "
        "this only speaks to departure timing, not what happened along the route."
    )
    notes.append(
        f"IMPORTANT — ghost rides are the least certain category. {GHOST_LABEL!r} means no "
        "GPS ping matched that ride's scheduled slot in this scope+window; it does NOT "
        "confirm the bus never ran. A vehicle that ran but was never tracked by SIRI (feed "
        "gaps, some operators/vehicle types not participating in real-time reporting, or the "
        "ride's SIRI journey_ref simply not linking to this scheduled slot) looks identical to "
        "a ride that was genuinely cancelled. This analysis cannot tell those apart — it flags "
        "candidates for investigation, not confirmed non-arrivals."
    )
    if not diag["any_siri"]:
        notes.append(
            "No SIRI GPS pings at all were found for this line/operator in this window — every "
            "planned ride is showing as a ghost as a result. This is much more likely to mean "
            "the line isn't part of the real-time feed (or the window is outside SIRI's archive) "
            "than that 100% of trips were cancelled — treat the ghost count here as a data-gap "
            "warning, not evidence of a violation."
        )
    if diag["n_dupe_pings_removed"]:
        notes.append(
            f"{diag['n_dupe_pings_removed']:,} duplicate GPS ping rows (same ride, timestamp, "
            "and position, repeated across overlapping SIRI snapshots — a known ~10% rate) were "
            "removed before computing first-ping times."
        )
    if diag["dup_start_times"]:
        notes.append(
            f"{diag['dup_start_times']} planned ride(s) shared an exact scheduled-start minute "
            "with another planned ride on the same line/operator/day — SIRI can't distinguish "
            "them either, so they may be double-matched to the same GPS ping-group."
        )
    notes.append(
        f"Scope: line {scope['route_short_name']} (line_ref={scope['line_ref']}), operator "
        f"{scope['agency_name']} (operator_ref={scope['operator_ref']}). "
        f"{diag['n_planned']:,} planned rides over {diag['n_days']} day(s). Sample size caveat: "
        "a single line's failures do not represent the whole operator or the whole network."
    )
    notes.append(
        "gtfs_rides_agg/group_by's own 'total_actual_rides' column was checked live while "
        "building this card and returned 0 for every row (a server-side aggregation bug, not "
        "a real 0% arrival rate) — this analysis avoids that endpoint entirely and derives "
        "actual departures from raw SIRI GPS pings instead."
    )
    return notes


_OPTIONS = [
    OptionSpec(key="early_threshold_min", label="Early threshold (min)", type="number",
               default=DEFAULT_EARLY_MIN,
               help="Departing this many minutes before schedule (or more) counts as an "
                    "early-departure violation. Illustrative default, not a cited regulation."),
    OptionSpec(key="late_threshold_min", label="Late threshold (min)", type="number",
               default=DEFAULT_LATE_MIN,
               help="Departing this many minutes after schedule (or more) counts as a "
                    "late-departure violation. Illustrative default, not a cited regulation."),
]


def _fetch(req: AnalysisRequest):
    """Returns (scope, date_from, date_to, per_ride_df, diag) or raises _NoScope/_NoData."""
    date_from, date_to = _window(req)
    scope = _resolve_scope(req, date_from, date_to)
    if scope is None:
        raise _NoScope()
    early_t = float(req.opt("early_threshold_min", DEFAULT_EARLY_MIN) or DEFAULT_EARLY_MIN)
    late_t = float(req.opt("late_threshold_min", DEFAULT_LATE_MIN) or DEFAULT_LATE_MIN)
    result = _load(scope["line_ref"], scope["operator_ref"], date_from, date_to, early_t, late_t)
    if result is None:
        raise _NoData()
    df, diag = result
    return scope, date_from, date_to, df, diag, early_t, late_t


class _NoScope(Exception):
    pass


class _NoData(Exception):
    pass


def _no_scope_card(req: AnalysisRequest):
    return metrics(("No data", 0), notes=[
        "Could not resolve a line+operator to analyze from the given filters — no matching "
        "GTFS route was found, and (if no line was selected) no live-tracked line could be "
        "auto-discovered either. Try a specific line, a different operator, or widen the dates."
    ])


def _no_data_card(scope: dict):
    return metrics(("No data", 0), notes=[
        f"No planned GTFS rides found for line {scope['route_short_name']} "
        f"({scope['agency_name']}) in this window — try a different line/operator or widen "
        "the dates."
    ])


# ── Cards ─────────────────────────────────────────────────────────────────────


@analysis(
    name="service-violations",
    title="Fineable service failures: ghost rides, early & late departures",
    description=(
        "Every planned ride in one line/operator's schedule, classified as a ghost "
        "(no GPS ever matched), an early departure, a late departure, or on-time — "
        "the three failure modes the Ministry of Transport can fine for."
    ),
    author="team",
    tags=["violations", "reliability", "siri", "gtfs", "fines"],
    inputs=["lines", "operators", "dates"],
    options=_OPTIONS,
    draft=False,
)
def run_summary(req: AnalysisRequest):
    try:
        scope, date_from, date_to, df, diag, early_t, late_t = _fetch(req)
    except _NoScope:
        return _no_scope_card(req)
    except _NoData:
        # scope resolved but _load found nothing — re-resolve just for the message.
        d_from, d_to = _window(req)
        scope = _resolve_scope(req, d_from, d_to)
        return _no_data_card(scope) if scope else _no_scope_card(req)

    if df.empty:
        return _no_data_card(scope)

    order = [GHOST_LABEL, _early_label(early_t), _late_label(late_t), ONTIME_LABEL]
    counts = (df["category"].value_counts().reindex(order, fill_value=0)
              .rename_axis("category").reset_index(name="rides"))

    total = int(len(df))
    by_label = dict(zip(counts["category"], counts["rides"]))
    ghost_n = int(by_label.get(GHOST_LABEL, 0))
    early_n = int(by_label.get(_early_label(early_t), 0))
    late_n = int(by_label.get(_late_label(late_t), 0))
    ontime_n = int(by_label.get(ONTIME_LABEL, 0))

    notes = [
        f"{ghost_n}/{total} ({ghost_n / total:.1%}) planned rides had no matching SIRI GPS "
        f"ping at all — candidate non-arrivals (see caveat below on why this is a candidate, "
        f"not a confirmed count). {early_n}/{total} ({early_n / total:.1%}) departed "
        f"materially early, {late_n}/{total} ({late_n / total:.1%}) departed materially late, "
        f"{ontime_n}/{total} ({ontime_n / total:.1%}) were on-time under the thresholds below.",
    ]
    matched = df[df["matched"]]
    if not matched.empty:
        worst_early = matched.loc[matched["delta_min"].idxmin()]
        worst_late = matched.loc[matched["delta_min"].idxmax()]
        if worst_early["delta_min"] < 0:
            notes.append(
                f"Most extreme early departure observed: {abs(worst_early['delta_min']):.1f} "
                f"min before schedule, on {worst_early['date']}."
            )
        if worst_late["delta_min"] > 0:
            notes.append(
                f"Most extreme late departure observed: {worst_late['delta_min']:.1f} min "
                f"after schedule, on {worst_late['date']}."
            )
    weekend = pd.to_datetime(df["date"]).dt.weekday.isin([4, 5])  # Fri=4, Sat=5
    if weekend.any():
        notes.append(
            f"{int(weekend.sum())}/{total} planned rides in this window fall on Friday/Saturday, "
            "when Israeli bus service is thin by design — those rides can skew the ghost rate "
            "upward without reflecting a weekday failure."
        )
    notes.extend(_method_notes(scope, diag, early_t, late_t))

    return bar_chart(
        counts, x="category", y="rides",
        title="Fineable service failures: ghost rides, early & late departures",
        subtitle=(f"{scope['route_short_name']} ({scope['agency_name']}) · "
                  f"{date_from} → {date_to} · {total} planned rides"),
        x_label="failure type", y_label="rides",
        notes=notes,
    )


@analysis(
    name="service-violations-by-day",
    title="Which days had the worst service failures?",
    description=(
        "The same ghost/early/late/on-time breakdown as 'Fineable service failures', "
        "split by day, so a spike on one bad day isn't hidden inside a window average."
    ),
    author="team",
    tags=["violations", "reliability", "siri", "gtfs", "fines"],
    inputs=["lines", "operators", "dates"],
    options=_OPTIONS,
    draft=False,
)
def run_by_day(req: AnalysisRequest):
    try:
        scope, date_from, date_to, df, diag, early_t, late_t = _fetch(req)
    except _NoScope:
        return _no_scope_card(req)
    except _NoData:
        d_from, d_to = _window(req)
        scope = _resolve_scope(req, d_from, d_to)
        return _no_data_card(scope) if scope else _no_scope_card(req)

    if df.empty:
        return _no_data_card(scope)

    order = [GHOST_LABEL, _early_label(early_t), _late_label(late_t), ONTIME_LABEL]
    all_dates = sorted(df["date"].unique())
    grid = pd.MultiIndex.from_product([all_dates, order], names=["date", "category"])
    by_day = (
        df.groupby(["date", "category"]).size().reindex(grid, fill_value=0)
        .rename("rides").reset_index()
    )

    total = int(len(df))
    notes = [
        f"Same method and thresholds as 'Fineable service failures' (early >{_fmt_min(early_t)} "
        f"min, late >{_fmt_min(late_t)} min) — see that card's notes for the full caveats on "
        "the GPS-first-ping proxy and on ghost rides being candidates, not confirmed "
        "non-arrivals.",
    ]
    per_day_ghost = df[df["category"] == GHOST_LABEL].groupby("date").size()
    if not per_day_ghost.empty:
        worst_day = per_day_ghost.idxmax()
        notes.append(
            f"Worst day for ghost rides: {worst_day} ({int(per_day_ghost.max())} of that day's "
            "planned rides had no matching GPS ping)."
        )
    notes.extend(_method_notes(scope, diag, early_t, late_t))

    return bar_chart(
        by_day, x="date", y="rides", series="category", stacked=True,
        title="Which days had the worst service failures?",
        subtitle=(f"{scope['route_short_name']} ({scope['agency_name']}) · "
                  f"{date_from} → {date_to} · {total} planned rides over {len(all_dates)} day(s)"),
        x_label="day", y_label="rides",
        notes=notes,
    )
