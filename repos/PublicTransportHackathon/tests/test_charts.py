"""Smoke tests that every chart renders from realistic synthetic data.

These do not check that a chart *looks* right — that needs eyes on the PNG — but they do catch the
mistakes that otherwise only surface at the end of a several-minute API run: a missing column, a
label built from the wrong field, an empty-axis crash.
"""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use('Agg')

from bus_times.transform import (  # noqa: E402  - must follow the Agg backend selection
    aggregate_segments,
    build_ride_segments,
    elapsed_profiles,
    segment_hour_matrix,
    stop_coverage,
)
from bus_times.viz import plot_marey, plot_segment_hour_heatmap, plot_segment_times  # noqa: E402

STOPS = ['ביטוח לאומי', 'גשר המיתרים', 'שדרות שז״ר', 'עמק המצלבה', 'האומן/ברעם']


@pytest.fixture
def stop_events():
    """Twelve rides spread over three hours, running progressively later than scheduled."""
    rng = np.random.default_rng(0)
    frames = []
    for ride_id, hour in enumerate([7, 7, 7, 7, 8, 8, 8, 8, 13, 13, 13, 13], start=1):
        base = pd.Timestamp(f'2026-07-20 {hour:02d}:00', tz='UTC')
        slowdown = 1.8 if hour == 8 else 1.0
        planned_offsets = np.array([0, 60, 180, 300, 420], dtype=float)
        actual_offsets = np.cumsum(np.concatenate(
            [[0.0], np.diff(planned_offsets) * slowdown + rng.normal(0, 8, 4)]))
        frames.append(pd.DataFrame({
            'siri_ride_id': ride_id,
            'ride_date': base.date(),
            'scheduled_start_time': base,
            'departure_hour': hour,
            'stop_sequence': range(len(STOPS)),
            'stop_name': STOPS,
            'city': 'ירושלים',
            'planned_time': [base + pd.Timedelta(seconds=s) for s in planned_offsets],
            'actual_time': [base + pd.Timedelta(seconds=s) for s in actual_offsets],
            'match_distance_m': 40.0,
            'resolution_s': 30.0,
        }))
    return pd.concat(frames, ignore_index=True)


def test_segment_bars_render(stop_events):
    agg = aggregate_segments(build_ride_segments(stop_events), min_samples=3)

    fig = plot_segment_times(agg, 'קו 15 ירושלים', subtitle='2026-07-20')

    ax = fig.axes[0]
    # Horizontal bars: one labelled tick per segment on the y axis, route reading downwards.
    assert len(ax.get_yticklabels()) == len(agg)
    assert ax.get_ylim()[0] > ax.get_ylim()[1]
    assert ax.get_legend() is not None
    matplotlib.pyplot.close(fig)


def test_marey_renders(stop_events):
    actual, planned = elapsed_profiles(stop_events)

    fig = plot_marey(actual, planned, 'קו 15 ירושלים')

    ax = fig.axes[0]
    assert [t.get_text() for t in ax.get_yticklabels()] != []
    # First stop at the top: the y axis runs downwards.
    assert ax.get_ylim()[0] > ax.get_ylim()[1]
    matplotlib.pyplot.close(fig)


def test_marey_caps_the_number_of_trajectories(stop_events):
    actual, planned = elapsed_profiles(stop_events)

    fig = plot_marey(actual, planned, 'קו 15', max_rides=3)

    # Three ride trajectories plus the planned reference.
    assert len(fig.axes[0].lines) == 4
    matplotlib.pyplot.close(fig)


def test_heatmap_renders_with_hour_columns(stop_events):
    matrix = segment_hour_matrix(build_ride_segments(stop_events))

    fig = plot_segment_hour_heatmap(matrix, 'קו 15 ירושלים', min_samples=3)

    ax = fig.axes[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == ['07', '08', '13']
    assert len(ax.get_yticklabels()) == len(matrix.ratio)
    matplotlib.pyplot.close(fig)


def test_heatmap_hatches_cells_backed_by_too_few_rides(stop_events):
    matrix = segment_hour_matrix(build_ride_segments(stop_events))

    # Every cell rests on 4 rides, so a threshold of 5 must hatch all of them and a threshold of 2
    # none — the hatch overlay is what tells a thin cell from a solid one.
    hatched = plot_segment_hour_heatmap(matrix, 'קו 15', min_samples=5)
    solid = plot_segment_hour_heatmap(matrix, 'קו 15', min_samples=2)

    assert _hatched_patches(hatched) == matrix.count.to_numpy().size
    assert _hatched_patches(solid) == 0
    matplotlib.pyplot.close(hatched)
    matplotlib.pyplot.close(solid)


def _hatched_patches(fig) -> int:
    return sum(1 for patch in fig.axes[0].patches if patch.get_hatch())


def test_segment_bars_hatch_and_label_unreliable_segments(stop_events):
    """A flagged segment must stay visible and say why, rather than vanish from the chart."""
    thin = stop_events[stop_events['siri_ride_id'] <= 2]  # only two rides
    agg = aggregate_segments(build_ride_segments(thin), min_samples=5)
    assert not agg['is_reliable'].any()

    fig = plot_segment_times(agg, 'קו 15')

    ax = fig.axes[0]
    assert len(ax.patches) == len(agg)
    assert all(patch.get_hatch() for patch in ax.patches)
    notes = [child.get_text() for child in ax.texts]
    assert any('n=2' in note and 'few samples' in note for note in notes)
    matplotlib.pyplot.close(fig)


def test_marey_survives_duplicate_stop_names_at_one_position(stop_events):
    """Regression: real routes reuse a position for different stops, which broke coverage indexing."""
    events = stop_events.copy()
    events.loc[events['siri_ride_id'] > 6, 'stop_name'] = events.loc[
        events['siri_ride_id'] > 6, 'stop_name'].where(
        events['stop_sequence'] != 3, 'תחנה חלופית')

    fig = plot_marey(*elapsed_profiles(events), 'קו 15', coverage=stop_coverage(events))

    assert fig.axes[0].get_yticklabels()
    matplotlib.pyplot.close(fig)


def test_marey_marks_stops_with_patchy_coverage(stop_events):
    events = stop_events.copy()
    # Wipe one stop's arrivals on most rides, leaving it poorly covered.
    poor = (events['stop_name'] == STOPS[2]) & (events['siri_ride_id'] > 2)
    events.loc[poor, 'actual_time'] = pd.NaT
    coverage = stop_coverage(events)

    fig = plot_marey(*elapsed_profiles(events), 'קו 15', coverage=coverage)

    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert any('17%' in label for label in labels)  # 2 of 12 rides matched
    italic = [t for t in fig.axes[0].get_yticklabels() if t.get_style() == 'italic']
    assert len(italic) == 1
    matplotlib.pyplot.close(fig)


def test_segment_bars_can_put_stops_on_the_x_axis(stop_events):
    agg = aggregate_segments(build_ride_segments(stop_events), min_samples=3)

    fig = plot_segment_times(agg, 'קו 15', stops_on_x=True)

    ax = fig.axes[0]
    assert len(ax.get_xticklabels()) == len(agg)
    # Duration now rises up the y axis, and the stop labels are angled to fit.
    assert ax.get_ylim()[1] > ax.get_ylim()[0]
    assert ax.get_xticklabels()[0].get_rotation() == pytest.approx(45.0)
    matplotlib.pyplot.close(fig)


def test_marey_can_put_stops_on_the_x_axis(stop_events):
    actual, planned = elapsed_profiles(stop_events)

    fig = plot_marey(actual, planned, 'קו 15', stops_on_x=True)

    ax = fig.axes[0]
    assert len(ax.get_xticklabels()) == planned['stop_sequence'].nunique()
    # Elapsed time increases upward rather than the route running downward.
    assert ax.get_ylim()[1] > ax.get_ylim()[0]
    matplotlib.pyplot.close(fig)


def test_heatmap_transposes_when_stops_go_on_the_x_axis(stop_events):
    matrix = segment_hour_matrix(build_ride_segments(stop_events))

    default = plot_segment_hour_heatmap(matrix, 'קו 15', min_samples=3)
    swapped = plot_segment_hour_heatmap(matrix, 'קו 15', min_samples=3, stops_on_x=True)

    # Hours and segments trade places.
    assert [t.get_text() for t in default.axes[0].get_xticklabels()] == ['07', '08', '13']
    assert [t.get_text() for t in swapped.axes[0].get_yticklabels()] == ['07', '08', '13']
    assert len(swapped.axes[0].get_xticklabels()) == len(matrix.ratio)
    matplotlib.pyplot.close(default)
    matplotlib.pyplot.close(swapped)


def test_stops_on_x_keeps_the_uncertainty_hatching(stop_events):
    """The caveat cues must survive the transpose, not just the default layout."""
    thin = stop_events[stop_events['siri_ride_id'] <= 2]
    agg = aggregate_segments(build_ride_segments(thin), min_samples=5)
    matrix = segment_hour_matrix(build_ride_segments(stop_events))

    bars = plot_segment_times(agg, 'קו 15', stops_on_x=True)
    heat = plot_segment_hour_heatmap(matrix, 'קו 15', min_samples=5, stops_on_x=True)

    assert all(patch.get_hatch() for patch in bars.axes[0].patches)
    assert _hatched_patches(heat) == matrix.count.to_numpy().size
    matplotlib.pyplot.close(bars)
    matplotlib.pyplot.close(heat)


def test_charts_render_in_dark_mode(stop_events):
    agg = aggregate_segments(build_ride_segments(stop_events), min_samples=3)

    fig = plot_segment_times(agg, 'קו 15', mode='dark')

    assert fig.get_facecolor() != (1.0, 1.0, 1.0, 1.0)
    matplotlib.pyplot.close(fig)
