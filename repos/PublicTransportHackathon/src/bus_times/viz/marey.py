"""Chart 2 — a Marey time-space diagram of every sampled ride."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .hebrew import shorten
from .theme import add_titles, horizontal_value_label, styled


def plot_marey(
    actual: pd.DataFrame,
    planned: pd.DataFrame,
    line_label: str,
    subtitle: str | None = None,
    max_rides: int = 60,
    mode: str = 'light',
    coverage: pd.DataFrame | None = None,
    min_coverage: float = 0.5,
    stops_on_x: bool = False,
) -> plt.Figure:
    """Stop sequence against elapsed time, one trajectory per ride over the planned reference.

    Takes the output of :func:`bus_times.transform.elapsed_profiles`. Reading it: a steep line is a
    bus making good progress, a flat stretch is one stuck in traffic, and the width of the fan is the
    line's unreliability. Because the x axis is time *elapsed since departure* rather than clock
    time, rides from different hours and days can be compared directly.

    ``max_rides`` caps the number of trajectories — past roughly 60 the fan turns into a solid block
    and stops being readable. The sample is evenly spaced through the rides rather than the first N,
    so the whole date and hour range stays represented.

    Pass ``coverage`` (from :func:`bus_times.transform.stop_coverage`) to mark stops the GPS rarely
    resolves: their axis labels are dimmed and suffixed with the match rate. Those stops are where a
    trajectory's shape is guesswork rather than measurement, and nothing else on the chart would
    reveal it — a line is drawn through every stop regardless of how well it was measured.

    ``stops_on_x`` swaps the axes: stops run left to right and elapsed time rises up the y axis, so a
    delay reads as a line climbing rather than drifting right. Traditional Marey diagrams put distance
    on the vertical axis, which is the default here, but the transposed form suits a long route on a
    wide page.
    """
    ride_ids = actual['siri_ride_id'].drop_duplicates().to_numpy()
    if len(ride_ids) > max_rides:
        ride_ids = ride_ids[np.linspace(0, len(ride_ids) - 1, max_rides).round().astype(int)]
    shown = actual[actual['siri_ride_id'].isin(ride_ids)]

    stops = planned.sort_values('stop_sequence')
    sequences = stops['stop_sequence'].to_numpy()
    rates = _coverage_by_sequence(coverage, stops)
    stop_labels = [_stop_tick_label(name, rates.get(seq), min_coverage)
                   for seq, name in zip(stops['stop_sequence'], stops['stop_name'])]

    with styled(mode) as colors:
        if stops_on_x:
            fig, ax = plt.subplots(figsize=(max(10.0, 0.5 * len(stops) + 3.0), 8.5))
        else:
            fig, ax = plt.subplots(figsize=(10.5, max(6.0, 0.32 * len(stops))))
        ax.grid(False)
        # Rules on the stop axis: they carry the eye from each stop name to the trajectories.
        ax.grid(axis='x' if stops_on_x else 'y')
        ax.set_axisbelow(True)

        def orient(along_route, elapsed):
            return (along_route, elapsed) if stops_on_x else (elapsed, along_route)

        # Alpha low enough that overlapping trajectories build up density: where the line is dark,
        # many rides did the same thing, and a lone pale line is one bad day.
        alpha = float(np.clip(6.0 / max(len(ride_ids), 1), 0.10, 0.55))
        for i, (_, ride) in enumerate(shown.groupby('siri_ride_id', sort=False)):
            ride = ride.sort_values('stop_sequence')
            xs, ys = orient(ride['stop_sequence'], ride['elapsed_min'])
            ax.plot(xs, ys, color=colors.actual, linewidth=1.1, alpha=alpha,
                    solid_capstyle='round', zorder=2,
                    label='נסיעות בפועל' if i == 0 else None)

        xs, ys = orient(stops['stop_sequence'], stops['elapsed_min'])
        ax.plot(xs, ys, color=colors.planned, linewidth=2.4, linestyle='--', dashes=(5, 3),
                zorder=3, label='לפי לוח הזמנים')

        if stops_on_x:
            ax.set_xticks(sequences)
            ax.set_xticklabels(stop_labels, rotation=45, ha='right', rotation_mode='anchor')
            ticks = ax.get_xticklabels()
            ax.set_xlim(sequences.min() - 0.5, sequences.max() + 0.5)
            ax.tick_params(axis='x', length=0)
            horizontal_value_label(ax, 'דקות מתחילת הנסיעה', colors)
            ax.set_ylim(bottom=0)
        else:
            ax.set_yticks(sequences)
            ax.set_yticklabels(stop_labels)
            ticks = ax.get_yticklabels()
            # First stop at the top, so the route reads downwards. Bound by the actual sequence
            # numbers rather than the row count, which need not be the same.
            ax.set_ylim(sequences.max() + 0.5, sequences.min() - 0.5)
            ax.tick_params(axis='y', length=0)
            ax.set_xlabel('דקות מתחילת הנסיעה')
            ax.set_xlim(left=0)

        for tick, seq in zip(ticks, stops['stop_sequence']):
            rate = rates.get(seq)
            if rate is not None and rate < min_coverage:
                tick.set_color(colors.ink_muted)
                tick.set_style('italic')

        note = f'{len(ride_ids)} נסיעות מוצגות'
        weak = sum(1 for rate in rates.values() if rate < min_coverage)
        if weak == 1:
            note += ' · תחנה אחת בכיסוי חלקי, מסומנת באפור'
        elif weak:
            note += f' · {weak} תחנות בכיסוי חלקי, מסומנות באפור'
        add_titles(fig, f'התקדמות לאורך המסלול — {line_label}', subtitle, colors,
                   footnote=note, footnote_at_top=stops_on_x)
        # Default layout: trajectories run top-left to bottom-right, leaving the upper right clear.
        # Transposed: they climb left to right, so the upper left is the empty corner.
        legend = ax.legend(loc='upper left' if stops_on_x else 'upper right', handletextpad=0.6)
        for line in legend.get_lines():
            line.set_alpha(1.0)  # full-strength swatches; the transparency is a density device
            line.set_linewidth(2.4)
        fig.tight_layout(rect=(0, 0, 1, 0.90 if stops_on_x else 0.94))

    return fig


def _coverage_by_sequence(coverage: pd.DataFrame | None, stops: pd.DataFrame) -> dict[int, float]:
    """Match rate per stop_sequence, or an empty mapping when coverage was not supplied."""
    if coverage is None or coverage.empty:
        return {}
    return (coverage.set_index('stop_sequence')['coverage']
            .reindex(stops['stop_sequence'])
            .dropna()
            .to_dict())


def _stop_tick_label(name: str, rate: float | None, min_coverage: float) -> str:
    """Stop name, carrying its GPS match rate only when that rate is a problem.

    Annotating every stop would put a column of mostly-100% labels beside the axis, which is noise
    that competes with the trajectories. Only the stops worth doubting are called out.
    """
    if rate is None or rate >= min_coverage:
        return shorten(name)
    # Logical order: matplotlib's bidi pass puts the percentage on the correct visual side and keeps
    # its digits left-to-right.
    return f'{rate:.0%} {shorten(name)}'
