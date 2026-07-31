"""Planned-vs-actual bus arrival analysis, adapted from noamf2001's ``bus_times``
package (github.com/noamf2001/PublicTransportHackathon, `analyze-per-subsequent-stops`
branch, pulled in as a dependency in pyproject.toml).

The Stride API doesn't serve actual arrival times — they're derived here from GPS
pings interpolated against each stop, accurate to about ±30s. Because of that, every
chart marks its own weak spots (hatching, ride counts, coverage) instead of looking
uniformly confident. See the upstream README for the full method and its limits.

All charts here are client-rendered (raw data over the wire, drawn in the browser) —
the upstream package's own matplotlib plotting functions (plot_segment_times,
plot_marey, plot_segment_hour_heatmap) are intentionally unused; this module owns
presentation via openbus_hack.contract instead.

All three charts share one fetch (`_load`, disk-cached and single-flight): resolving
a line and pulling its timetable + sampled GPS pings costs ~1-2 minutes, and the
dashboard's global filter bar means all three cards usually run with identical
parameters.
"""

from __future__ import annotations

import datetime

import pandas as pd

import io
import base64
import warnings
from typing import Any, Callable
from bus_times import (
    LineSpec,
    aggregate_segments,
    elapsed_profiles,
    find_lines,
    load_line_data,
    quality_summary,
    segment_hour_matrix,
    stop_coverage,
)
from bus_times.viz.segment_bars import plot_segment_times
from bus_times.viz.marey import plot_marey
from bus_times.viz.heatmap import plot_segment_hour_heatmap
from bus_times.config import DEFAULT_LAG_DAYS, DEFAULT_MIN_SAMPLES

from openbus_hack import (
    AnalysisRequest,
    AnalysisResult,
    OptionSpec,
    metrics,
    Point,
    Series,
    analysis,
    bar_chart,
    heatmap,
)
from openbus_hack.diskcache import cached

_INPUTS = ["lines", "operators", "dates"]
_OPTIONS = [
    OptionSpec(
        key="name_contains",
        label="City / route contains",
        type="text",
        default="",
        help="A line number alone is often ambiguous (several cities run a line "
             "'1'). Leave empty to let the card pick the busiest match and tell "
             "you what else it could have chosen; set it (e.g. 'תל אביב') to pin "
             "one down.",
    ),
    OptionSpec(
        key="direction",
        label="Direction",
        type="select",
        default="",
        choices=["", "1", "2"],
    ),
]

_CREDIT = "Analysis by noamf2001 (github.com/noamf2001/PublicTransportHackathon)."
# Below this per-stop GPS match rate, a stop's own axis label is drawn dimmed/italic
# on the Marey chart — same threshold plot_marey's own min_coverage default used.
_WEAK_COVERAGE = 0.5


def _static_png(cache_key: tuple, make_fig: "Callable[[], Any]") -> str | None:
    """Render one bus_times matplotlib figure to a base64 PNG — cached, and quiet.

    The static "draft plot" view is a nice extra, but it was costing more than it
    looked. Two measured problems, both fixed here rather than by dropping the
    feature:

    * The figure is fully determined by its cache key, yet was redrawn on every
      request — 67s on a card whose data was already warm in the cache. Now it is
      drawn once and reused.
    * matplotlib lays Hebrew out through HarfBuzz and warns once per
      (glyph, call-site) rather than once per process, so a single render emits
      thousands of "Glyph N missing from font" warnings — 8,465 in one session.
      The glyphs render fine via fallback; it is the warning machinery that burns
      the CPU, which is what previously made the whole API unresponsive.

    Returns None on failure — a draft plot that won't draw must not take the
    card's real chart down with it.
    """

    def compute() -> str:
        import matplotlib
        matplotlib.use("Agg")  # no display in the container
        import matplotlib.pyplot as plt

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", category=UserWarning, message=r"Glyph \d+ .*missing from font")
            fig = make_fig()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=144, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    try:
        return cached("static_png", cache_key, compute)
    except Exception:
        return None


def _window(req: AnalysisRequest) -> tuple[datetime.date, datetime.date]:
    # SIRI ingestion lags a few days behind live traffic — DEFAULT_LAG_DAYS is the
    # upstream package's own finding, applied here since the dashboard's default
    # window (through yesterday) is more recent than that.
    date_to = min(req.date_to, datetime.date.today() - datetime.timedelta(days=DEFAULT_LAG_DAYS))
    date_from = min(req.date_from, date_to)
    # Fetch cost is dominated by the planned-timetable call (~25s/day) and sampled GPS
    # pings (~0.7s/ride) — bound the window so a card resolves in roughly a minute.
    date_from = max(date_from, date_to - datetime.timedelta(days=9))
    return date_from, date_to


def _load(line_short_name: str, operator: str, name_contains: str, direction: str,
          date_from: datetime.date, date_to: datetime.date):
    # Disk-backed and single-flight (see openbus_hack.diskcache): the dashboard's shared
    # filter bar means all three cards here usually fire with identical params at once,
    # so the first caller pays the ~80s fetch while the other two wait on its result
    # instead of repeating it — and a rehearsal re-run or dev-server reload later hits
    # disk instead of the network entirely.
    key = ("v2", line_short_name, operator, name_contains, direction, date_from, date_to)

    def compute():
        line, alternatives = _resolve(
            line_short_name, operator, name_contains, direction, date_from, date_to)
        if line is None:
            # alternatives here is the "what does exist for this number" list.
            return None, alternatives
        stop_events, ride_segments = load_line_data(line, date_from, date_to, verbose=False)
        rides = stop_events["siri_ride_id"].nunique()
        days = stop_events["ride_date"].nunique()
        subtitle = (f"{date_from.isoformat()}..{date_to.isoformat()} · {rides} rides over "
                    f"{days} days · arrival times derived from GPS, ±30s")
        return (line, stop_events, ride_segments, subtitle), alternatives

    return cached("bus_arrival", key, compute)


def _resolve(line_short_name: str, operator: str, name_contains: str, direction: str,
             date_from: datetime.date, date_to: datetime.date):
    """Pick one route, and say what else it could have been.

    bus_times.resolve_line() raises whenever a description matches zero *or*
    several routes. That's right for a notebook, but on a dashboard it turns an
    ordinary pick like line "1" with no operator into an error card. Here an
    ambiguous match picks the first candidate deterministically and returns the
    rest so the card can say what it chose and what it ignored; only a genuinely
    empty match fails, and then with the list of routes that *do* carry that
    number so the reader can fix their filters.
    """
    df = find_lines(line_short_name, date_from, date_to,
                    agency_name=operator or None, name_contains=name_contains or None)
    if direction and not df.empty:
        df = df[df["route_direction"].astype(str) == str(direction)]

    if df.empty:
        # Widen back out to show what this line number actually is, if anything.
        wide = find_lines(line_short_name, date_from, date_to)
        return None, [
            {"agency_name": r.agency_name, "route_long_name": r.route_long_name,
             "route_direction": str(r.route_direction)}
            for r in wide.head(12).itertuples()
        ]

    row = df.iloc[0]
    line = LineSpec(
        line_ref=int(row["line_ref"]),
        operator_ref=int(row["operator_ref"]),
        label=f"{row['route_short_name']} {row['route_long_name']}",
    )
    others = [
        {"agency_name": r.agency_name, "route_long_name": r.route_long_name,
         "route_direction": str(r.route_direction)}
        for r in df.iloc[1:].head(8).itertuples()
    ]
    return line, others


class NoMatch(Exception):
    """Raised when the filters describe no route at all. Carries the routes that
    *do* use that line number, so the card can tell the reader how to fix it."""

    def __init__(self, line: str, alternatives: list[dict]):
        self.line = line
        self.alternatives = alternatives
        super().__init__(f"no route matches line {line!r}")


def _fetch(req: AnalysisRequest):
    """Returns (line, stop_events, ride_segments, subtitle, alternatives)."""
    date_from, date_to = _window(req)
    result, alternatives = _load(
        line_short_name=req.line or "23",
        # Empty means "all operators" — the filter bar offers that explicitly, so
        # defaulting to a specific agency here would quietly contradict the user.
        operator=req.operator or "",
        name_contains=str(req.opt("name_contains", "") or ""),
        direction=str(req.opt("direction", "") or ""),
        date_from=date_from,
        date_to=date_to,
    )
    if result is None:
        raise NoMatch(req.line or "23", alternatives)
    return (*result, alternatives)


def _match_notes(line, alternatives: list[dict]) -> list[str]:
    """Say which route was picked when the filters left it ambiguous — silently
    charting one of several routes named "1" would be the worst outcome."""
    if not alternatives:
        return []
    listed = "; ".join(
        f"{a['agency_name']} · {a['route_long_name']} (dir {a['route_direction']})"
        for a in alternatives[:4]
    )
    more = f" and {len(alternatives) - 4} more" if len(alternatives) > 4 else ""
    return [f"Your filters matched {len(alternatives) + 1} routes; charting "
            f"{line.label}. Also matched: {listed}{more}. Narrow it with the "
            "operator picker or the 'City / route contains' box."]


def _no_match_card(exc: "NoMatch"):
    listed = [f"{a['agency_name']} · {a['route_long_name']} (dir {a['route_direction']})"
              for a in exc.alternatives]
    notes = [f"No route matches line {exc.line} with the filters you set."]
    if listed:
        notes.append("Routes that do use this line number: " + "; ".join(listed[:8])
                     + (f" (+{len(listed) - 8} more)" if len(listed) > 8 else ""))
        notes.append("Pick one of those operators, or clear the 'City / route "
                     "contains' box and the direction.")
    else:
        notes.append("No route carries this number in the selected date range at "
                     "all — try a different line or widen the dates.")
    return metrics(("No match", 0), notes=notes)


@analysis(
    name="bus-segment-reliability",
    title="Where the timetable is optimistic",
    description="Median measured travel time per stop-to-stop segment against the "
                "planned duration, with the interquartile spread as a whisker. Where "
                "a bar overshoots the marker, the schedule is optimistic about that "
                "stretch.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_segments(req: AnalysisRequest):
    try:
        line, _stop_events, ride_segments, subtitle, alts = _fetch(req)
    except NoMatch as exc:
        return _no_match_card(exc)
    aggregated = aggregate_segments(ride_segments, DEFAULT_MIN_SAMPLES).sort_values("segment_index")
    labels = [f"{r.from_name} ← {r.to_name}" for r in aggregated.itertuples()]

    # Long-format frame bar_chart() expects: one row per (segment, {Actual, Planned}).
    # Only the "Actual" rows carry a p25/p75 whisker — "Planned" is a single number,
    # nothing to spread.
    long = pd.DataFrame({
        "segment": [*labels, *labels],
        "kind": ["Actual (median)"] * len(aggregated) + ["Planned"] * len(aggregated),
        "minutes": [*(aggregated["actual_median_s"] / 60), *(aggregated["planned_duration_s"] / 60)],
        "p25": [*(aggregated["actual_p25_s"] / 60), *([None] * len(aggregated))],
        "p75": [*(aggregated["actual_p75_s"] / 60), *([None] * len(aggregated))],
    })

    weak = int((~aggregated["is_reliable"]).sum())
    notes = [
        quality_summary(aggregated),
        "The whisker on each Actual bar is the ride-to-ride interquartile spread "
        "(p25-p75), not a plain min-max range.",
        _CREDIT,
    ]
    if weak:
        notes.insert(1, f"{weak} of {len(aggregated)} segments rest on too little data — shown "
                        "anyway, since a missing bar reads as 'route doesn't exist' rather than "
                        "'not enough evidence'.")
    notes = [*_match_notes(line, alts), *notes]

    res = bar_chart(
        long, x="segment", y="minutes", series="kind", low="p25", high="p75", horizontal=True,
        title="Where the timetable is optimistic",
        subtitle=f"{line.label} · {subtitle}",
        x_label="segment", y_label="minutes",
        notes=notes,
    )
    res.image_png = _static_png(
        ("segments", line.line_ref, subtitle),
        lambda: plot_segment_times(aggregated, line.label, subtitle, mode="light", stops_on_x=False),
    )
    return res


@analysis(
    name="bus-marey-diagram",
    title="Where the bus loses time",
    description="A time-space diagram: one trajectory per sampled ride against the "
                "schedule. Steep = moving, flat = stuck, and the width of the fan is "
                "the route's unreliability.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_marey(req: AnalysisRequest):
    try:
        line, stop_events, _ride_segments, subtitle, alts = _fetch(req)
    except NoMatch as exc:
        return _no_match_card(exc)
    actual, planned = elapsed_profiles(stop_events)
    coverage = stop_coverage(stop_events)

    planned = planned.sort_values("stop_sequence")
    coverage_by_seq = coverage.set_index("stop_sequence")["coverage"]
    y_tick_labels = planned["stop_name"].tolist()
    y_tick_weak = [
        bool(coverage_by_seq.get(seq, 1.0) < _WEAK_COVERAGE)
        for seq in planned["stop_sequence"]
    ]

    # Same cap the static chart used (plot_marey's own max_rides default) — past
    # ~60 overlapping trajectories the fan turns into a solid block and every
    # extra ride costs payload without adding anything readable.
    max_rides = 60
    ride_ids = actual["siri_ride_id"].drop_duplicates().to_numpy()
    if len(ride_ids) > max_rides:
        idx = [round(i) for i in _linspace(0, len(ride_ids) - 1, max_rides)]
        ride_ids = ride_ids[idx]

    series = []
    for rid in ride_ids:
        ride = actual[actual["siri_ride_id"] == rid].sort_values("stop_sequence")
        series.append(Series(
            name=f"ride_{rid}",
            points=[Point(x=float(r.elapsed_min), y=float(r.stop_sequence))
                    for r in ride.itertuples() if pd.notna(r.elapsed_min)],
        ))
    series.append(Series(
        name="Planned",
        emphasis=True,
        points=[Point(x=float(r.elapsed_min), y=float(r.stop_sequence))
                for r in planned.itertuples()],
    ))

    n_weak = sum(y_tick_weak)
    notes = [
        "Each faint line is one sampled ride; the bold dashed line is the schedule. "
        "Steep = moving, flat = stuck, and the width of the fan is the route's "
        "unreliability.",
        _CREDIT,
    ]
    if n_weak:
        weak_names = [name for name, w in zip(y_tick_labels, y_tick_weak) if w][:5]
        more = f" (+{n_weak - 5} more)" if n_weak > 5 else ""
        notes.insert(1, f"Dimmed, italic stop labels ({n_weak} of them) are stops the GPS "
                        f"rarely resolved, incl. {', '.join(weak_names)}{more} — trajectories "
                        "through them are interpolation more than measurement.")

    notes = [*_match_notes(line, alts), *notes]
    res = AnalysisResult(
        kind="chart", chart_type="trajectories", series=series,
        title="Where the bus loses time",
        subtitle=f"{line.label} · {subtitle}",
        x_label="elapsed minutes", y_label=None,
        y_tick_labels=y_tick_labels, y_tick_weak=y_tick_weak,
        notes=notes,
    ).ensure_table()
    res.image_png = _static_png(
        ("marey", line.line_ref, subtitle),
        lambda: plot_marey(*elapsed_profiles(stop_events), line.label, subtitle,
                           mode="light", coverage=coverage, stops_on_x=False),
    )
    return res


def _linspace(start: float, stop: float, num: int) -> list[float]:
    if num <= 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]


@analysis(
    name="bus-hourly-heatmap",
    title="Which segments break down at rush hour",
    description="Segment × departure hour, coloured by the actual/planned duration "
                "ratio — red ran long, blue ran quick, neutral is on schedule. Hover "
                "any cell for its ratio and ride count.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_heatmap(req: AnalysisRequest):
    try:
        line, _stop_events, ride_segments, subtitle, alts = _fetch(req)
    except NoMatch as exc:
        return _no_match_card(exc)
    matrix = segment_hour_matrix(ride_segments, DEFAULT_MIN_SAMPLES)
    # matrix.ratio is indexed by (segment_index, from_name, to_name); the segment
    # pair is what a reader actually recognises, so label rows with that.
    labels = [f"{from_name} ← {to_name}" for _, from_name, to_name in matrix.ratio.index]
    notes = [
        *_match_notes(line, alts),
        "1.00 means exactly on schedule; above that the segment ran longer than "
        "the timetable allows. Hatched cells are measured but rest on fewer than "
        f"{DEFAULT_MIN_SAMPLES} rides; empty cells had no usable ride at all.",
        _CREDIT,
    ]
    res = heatmap(
        matrix.ratio,
        matrix.count,
        row_labels=labels,
        col_labels=[f"{int(h):02d}" for h in matrix.ratio.columns],
        min_count=DEFAULT_MIN_SAMPLES,
        center=1.0,
        title="Which segments break down at rush hour",
        subtitle=f"{line.label} · {subtitle}",
        row_axis_label="segment",
        col_axis_label="departure hour",
        value_label="actual / planned",
        notes=notes,
    )
    res.image_png = _static_png(
        ("heatmap", line.line_ref, subtitle),
        lambda: plot_segment_hour_heatmap(
            segment_hour_matrix(ride_segments), line.label, subtitle,
            min_samples=DEFAULT_MIN_SAMPLES, mode="light", stops_on_x=False),
    )
    return res
