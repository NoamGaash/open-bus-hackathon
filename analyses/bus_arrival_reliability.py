"""Planned-vs-actual bus arrival analysis, adapted from noamf2001's ``bus_times``
package (github.com/noamf2001/PublicTransportHackathon, `analyze-per-subsequent-stops`
branch, pulled in as a dependency in pyproject.toml).

The Stride API doesn't serve actual arrival times — they're derived here from GPS
pings interpolated against each stop, accurate to about ±30s. Because of that, every
chart marks its own weak spots (hatching, ride counts, coverage %) instead of looking
uniformly confident. See the upstream README for the full method and its limits.

All three charts share one fetch (`_load`, memoized): resolving a line and pulling its
timetable + sampled GPS pings costs 1-2 minutes, and the dashboard's global filter bar
means all three cards usually run with identical parameters.
"""

from __future__ import annotations

import datetime
from functools import lru_cache

from bus_times import (
    aggregate_segments,
    elapsed_profiles,
    load_line_data,
    plot_marey,
    plot_segment_hour_heatmap,
    plot_segment_times,
    quality_summary,
    resolve_line,
    segment_hour_matrix,
    stop_coverage,
)
from bus_times.config import DEFAULT_LAG_DAYS, DEFAULT_MIN_SAMPLES

from openbus_hack import AnalysisRequest, OptionSpec, analysis, image

_INPUTS = ["lines", "operators", "dates"]
_OPTIONS = [
    OptionSpec(
        key="name_contains",
        label="City / route contains",
        type="text",
        default="תל אביב",
        help="A line number alone is often ambiguous (multiple cities run the same "
             "number) — this narrows it via route_long_name, e.g. a city name.",
    ),
    OptionSpec(
        key="direction",
        label="Direction",
        type="select",
        default="1",
        choices=["1", "2"],
    ),
]

_CREDIT = "Analysis by noamf2001 (github.com/noamf2001/PublicTransportHackathon)."


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


@lru_cache(maxsize=8)
def _load(line_short_name: str, operator: str, name_contains: str, direction: str,
          date_from: datetime.date, date_to: datetime.date):
    line = resolve_line(
        line_short_name, date_from, date_to,
        agency_name=operator or None,
        name_contains=name_contains or None,
        direction=direction or None,
    )
    stop_events, ride_segments = load_line_data(line, date_from, date_to, verbose=False)
    rides = stop_events["siri_ride_id"].nunique()
    days = stop_events["ride_date"].nunique()
    subtitle = (f"{date_from.isoformat()}..{date_to.isoformat()} · {rides} rides over "
                f"{days} days · arrival times derived from GPS, ±30s")
    return line, stop_events, ride_segments, subtitle


def _fetch(req: AnalysisRequest):
    date_from, date_to = _window(req)
    return _load(
        line_short_name=req.line or "23",
        operator=req.operator or "דן",
        name_contains=str(req.opt("name_contains", "תל אביב") or ""),
        direction=str(req.opt("direction", "1") or ""),
        date_from=date_from,
        date_to=date_to,
    )


@analysis(
    name="bus-segment-reliability",
    title="Where the timetable is optimistic",
    description="Median measured travel time per stop-to-stop segment, against the "
                "planned duration. Where the bar overshoots the marker, the schedule "
                "is optimistic about that stretch.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_segments(req: AnalysisRequest):
    line, _stop_events, ride_segments, subtitle = _fetch(req)
    aggregated = aggregate_segments(ride_segments, DEFAULT_MIN_SAMPLES)
    fig = plot_segment_times(aggregated, line.label, subtitle)
    return image(
        fig,
        title="Where the timetable is optimistic",
        alt=f"Segment travel times for {line.label}",
        notes=[
            quality_summary(aggregated),
            "Hatched bars are shaky, not wrong — too few rides, patchy coverage, or "
            "coarse GPS timing. The number beside each bar is the ride count behind it.",
            _CREDIT,
        ],
    )


@analysis(
    name="bus-marey-diagram",
    title="Where the bus loses time",
    description="A time-space diagram: one trajectory per sampled ride against the "
                "schedule. Steep = moving, flat = stuck, and the width of the fan is "
                "the route's unreliability.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_marey(req: AnalysisRequest):
    line, stop_events, _ride_segments, subtitle = _fetch(req)
    coverage = stop_coverage(stop_events)
    fig = plot_marey(*elapsed_profiles(stop_events), line.label, subtitle, coverage=coverage)
    return image(
        fig,
        title="Where the bus loses time",
        alt=f"Marey diagram for {line.label}",
        notes=[
            "Dimmed, italic stop labels marked with a % are stops the GPS rarely "
            "resolved — trajectories through them are interpolation more than "
            "measurement.",
            _CREDIT,
        ],
    )


@analysis(
    name="bus-hourly-heatmap",
    title="Which segments break down at rush hour",
    description="Segment × departure hour, coloured by the actual/planned duration "
                "ratio — red ran long, blue ran quick, neutral is on schedule.",
    author="noamf2001",
    tags=["reliability", "punctuality", "gps"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_heatmap(req: AnalysisRequest):
    line, _stop_events, ride_segments, subtitle = _fetch(req)
    matrix = segment_hour_matrix(ride_segments, DEFAULT_MIN_SAMPLES)
    fig = plot_segment_hour_heatmap(matrix, line.label, subtitle, min_samples=DEFAULT_MIN_SAMPLES)
    return image(
        fig,
        title="Which segments break down at rush hour",
        alt=f"Segment/hour heatmap for {line.label}",
        notes=[
            "The number in each cell is its ride count: solid means enough rides, "
            "hatched means too few, blank means no data at all — those three are "
            "deliberately drawn differently.",
            _CREDIT,
        ],
    )
