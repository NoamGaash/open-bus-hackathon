"""Chart 1 — actual vs planned travel time for each segment of a route."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from ..transform import CONFIDENCE_OK, quality_summary
from .hebrew import segment_label
from .theme import add_titles, horizontal_value_label, styled


def plot_segment_times(
    aggregated: pd.DataFrame,
    line_label: str,
    subtitle: str | None = None,
    mode: str = 'light',
    show_counts: bool = True,
    stops_on_x: bool = False,
) -> plt.Figure:
    """Median measured duration per segment as bars, with the planned duration overlaid.

    Takes the output of :func:`bus_times.transform.aggregate_segments`. Where the bar overshoots the
    schedule marker, the timetable is optimistic about that stretch of road.

    Three deliberate choices:

    * **Horizontal bars.** Stop names run 20-40 characters and a route has dozens of segments;
      rotated 45° they become the largest thing on the canvas and still read badly. On the y axis they
      sit flat and legible, and the route reads top-to-bottom like the other two charts.
    * **Median with an interquartile range**, not mean ± standard deviation. Arrival times are derived
      from GPS, so an occasional ride is minutes out; one such ride moves a mean enough to squash
      every other segment into the bottom of the axis.
    * **Confidence is drawn, not filtered.** Segments whose numbers are shaky — too few rides, patchy
      coverage, coarse GPS timing, a loose stop match, or an implausible result — are hatched and
      labelled with the reason instead of being dropped. A segment quietly missing from the chart is
      indistinguishable from a segment that does not exist.

    ``show_counts`` writes the ride count beside each bar, so no bar's weight of evidence is ever a
    mystery.

    ``stops_on_x`` puts the segments along the x axis with duration rising up the y axis, the
    conventional bar-chart layout. It costs label legibility — Hebrew stop names have to be rotated
    45° and take up a large share of the canvas — which is why the default is the other way round.
    """
    median_min = aggregated['actual_median_s'] / 60
    planned_min = aggregated['planned_duration_s'] / 60
    # asymmetric whiskers: distance from the median out to each quartile
    lower = (median_min - aggregated['actual_p25_s'] / 60).clip(lower=0)
    upper = (aggregated['actual_p75_s'] / 60 - median_min).clip(lower=0)
    y = np.arange(len(aggregated))
    # Rotated 45° along the bottom, a full-length pair label collides with its neighbours once a route
    # runs to a few dozen segments, so names are trimmed harder in that orientation.
    max_chars = 14 if stops_on_x else 22
    labels = [segment_label(r.from_name, r.to_name, max_chars=max_chars)
              for r in aggregated.itertuples()]
    reliable = aggregated['is_reliable'].to_numpy()

    with styled(mode) as colors:
        if stops_on_x:
            fig, ax = plt.subplots(figsize=(max(10.0, 0.52 * len(aggregated) + 3.0), 8.0))
        else:
            fig, ax = plt.subplots(figsize=(12.0, max(4.5, 0.36 * len(aggregated) + 2.0)))
        ax.grid(False)
        ax.grid(axis='y' if stops_on_x else 'x')
        ax.set_axisbelow(True)

        # Colours are set explicitly rather than left to the property cycle: matplotlib advances
        # separate cycles for patches and lines, so a bar+line pair drifts out of step.
        if stops_on_x:
            bars = ax.bar(y, median_min, width=0.66,
                          yerr=[lower, upper], ecolor=colors.ink_muted, capsize=2.5,
                          error_kw={'linewidth': 1},
                          color=colors.actual, linewidth=0, zorder=2)
        else:
            bars = ax.barh(y, median_min, height=0.66,
                           xerr=[lower, upper], ecolor=colors.ink_muted, capsize=2.5,
                           error_kw={'linewidth': 1},
                           color=colors.actual, linewidth=0, zorder=2)
        # Hatching is a second, colour-independent channel, so the caveat survives greyscale printing
        # and colour-vision deficiency.
        for bar, is_reliable in zip(bars, reliable):
            if not is_reliable:
                bar.set_hatch('///')
                bar.set_alpha(0.45)
                bar.set_edgecolor(colors.surface)
                bar.set_linewidth(0)

        marker_x, marker_y = (y, planned_min) if stops_on_x else (planned_min, y)
        ax.plot(marker_x, marker_y, color=colors.planned, linewidth=0, marker='D', markersize=7,
                # A surface-coloured ring keeps the marker legible where it sits on a bar.
                markeredgecolor=colors.surface, markeredgewidth=1.5, zorder=3,
                label='לפי לוח הזמנים')

        if show_counts:
            _annotate_evidence(ax, aggregated, y, median_min, upper, colors, stops_on_x)

        if stops_on_x:
            ax.set_xticks(y)
            ax.set_xticklabels(labels, rotation=45, ha='right', rotation_mode='anchor')
            ticks = ax.get_xticklabels()
            ax.set_xlim(-0.7, len(aggregated) - 0.3)
            ax.tick_params(axis='x', length=0)
            ax.set_ylim(bottom=0)
            horizontal_value_label(ax, 'משך נסיעה, דקות', colors)
        else:
            ax.set_yticks(y)
            ax.set_yticklabels(labels)
            ticks = ax.get_yticklabels()
            ax.invert_yaxis()  # first segment at the top, so the route reads downwards
            ax.set_ylim(len(aggregated) - 0.5, -0.5)
            ax.tick_params(axis='y', length=0)
            ax.set_xlim(left=0)
            ax.set_xlabel('משך נסיעה, דקות')

        # Flagged segments get a muted label too, so the axis itself shows where to be careful.
        for tick, is_reliable in zip(ticks, reliable):
            tick.set_color(colors.ink_secondary if is_reliable else colors.ink_muted)

        handles = [
            # Brackets are safe: matplotlib runs the real bidi algorithm, which mirrors them.
            Patch(facecolor=colors.actual, label='בפועל (חציון ורבעון 25–75)'),
            Patch(facecolor=colors.actual, alpha=0.45, hatch='///', edgecolor=colors.surface,
                  label='מדידה לא מבוססת — ראו הערה'),
            *ax.get_legend_handles_labels()[0],
        ]
        # With bars growing upward the headroom above them is the clear space; with bars growing
        # rightward it is the bottom corner.
        ax.legend(handles=handles, loc='upper right' if stops_on_x else 'lower right',
                  handletextpad=0.6).set_zorder(4)

        add_titles(fig, f'זמני נסיעה בין תחנות — {line_label}', subtitle, colors,
                   footnote=quality_summary(aggregated), footnote_at_top=stops_on_x)
        fig.tight_layout(rect=(0, 0, 1, 0.90 if stops_on_x else 0.94))

    return fig


def _annotate_evidence(ax, aggregated, y, median_min, upper, colors,
                       stops_on_x: bool = False) -> None:
    """Write the ride count past the end of each bar, and the reason on every flagged segment.

    With stops on the x axis there is only bar-width room, so the reason is dropped and just the count
    is stacked vertically above the bar; the hatching and the footnote still carry the caveat.
    """
    tip = median_min + upper
    offset = 0.02 * max(tip.max(), 1.0)
    for i, row in enumerate(aggregated.itertuples()):
        note = f'n={row.sample_count}'
        color = colors.ink_secondary if row.is_reliable else colors.ink_muted
        if stops_on_x:
            ax.annotate(note, xy=(y[i], tip.iat[i] + offset), va='bottom', ha='center',
                        fontsize=7, rotation=90, color=color)
        else:
            if row.confidence != CONFIDENCE_OK:
                note += f' · {row.confidence}'
            ax.annotate(note, xy=(tip.iat[i] + offset, y[i]), va='center', ha='left',
                        fontsize=7.5, color=color)

    # Leave room past the bar tips for the annotations.
    if stops_on_x:
        ax.set_ylim(top=tip.max() * 1.22)
    else:
        ax.set_xlim(right=tip.max() * 1.42)
