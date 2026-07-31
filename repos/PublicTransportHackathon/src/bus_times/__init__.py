"""Planned vs. real-time bus arrival analysis, built on the Stride open-data API.

Typical use::

    from bus_times import resolve_line, load_line_data, aggregate_segments, plot_segment_times

    line = resolve_line(15, date_from, date_to, agency_name='אגד', name_contains='ירושלים',
                        direction=1)
    stop_events, ride_segments = load_line_data(line, date_from, date_to)
    fig = plot_segment_times(aggregate_segments(ride_segments, min_samples=3), line.label)

The API exposes no actual arrival times, so they are derived from raw GPS pings; see
``docs/superpowers/specs/2026-07-30-bus-arrival-analysis-design.md`` for the method and its
accuracy limits.
"""

from .fetch import (
    fetch_pings,
    fetch_planned_timetable,
    fetch_rides,
    load_line_data,
    sample_rides,
    weekdays_between,
)
from .lines import LineSpec, find_lines, resolve_line
from .transform import (
    aggregate_segments,
    build_ride_segments,
    build_stop_events,
    dominant_stop_pattern,
    elapsed_profiles,
    estimate_arrival_seconds,
    quality_summary,
    segment_hour_matrix,
    stop_coverage,
)
from .viz import plot_marey, plot_segment_hour_heatmap, plot_segment_times, save_figure

__all__ = [
    'LineSpec',
    'aggregate_segments',
    'build_ride_segments',
    'build_stop_events',
    'dominant_stop_pattern',
    'elapsed_profiles',
    'estimate_arrival_seconds',
    'fetch_pings',
    'fetch_planned_timetable',
    'fetch_rides',
    'find_lines',
    'load_line_data',
    'plot_marey',
    'plot_segment_hour_heatmap',
    'plot_segment_times',
    'quality_summary',
    'resolve_line',
    'sample_rides',
    'save_figure',
    'segment_hour_matrix',
    'stop_coverage',
    'weekdays_between',
]
