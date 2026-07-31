"""Chart 3 — segment × departure hour, coloured by how far reality drifts from the schedule."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch

from ..transform import HourMatrix
from .hebrew import segment_label
from .theme import add_titles, horizontal_value_label, ratio_colormap, styled


def plot_segment_hour_heatmap(
    matrix: HourMatrix,
    line_label: str,
    subtitle: str | None = None,
    min_samples: int = 3,
    mode: str = 'light',
    annotate_counts: bool = True,
    stops_on_x: bool = False,
) -> plt.Figure:
    """Median actual/planned duration ratio per segment and departure hour.

    Takes the output of :func:`bus_times.transform.segment_hour_matrix`. Red means the segment took
    longer than scheduled, blue means it ran quicker, and the neutral centre is exactly on schedule. A
    ratio is used rather than a duration so a 30-second hop and a five-minute run share one scale.

    **Three states, three appearances** — because a heatmap's worst habit is making a cell built on one
    ride look exactly as authoritative as one built on fifty:

    * solid — at least ``min_samples`` rides
    * hatched — measured, but on fewer than ``min_samples`` rides
    * blank — no ride produced a usable value at all

    With ``annotate_counts`` and a grid small enough to fit them, each cell also carries its ride
    count.

    ``stops_on_x`` transposes the grid so segments run left to right and departure hours down the y
    axis, reading like a timetable with the earliest hour at the top.
    """
    values = matrix.ratio.to_numpy(dtype=float)
    counts = matrix.count.to_numpy(dtype=int)
    # Rotated 45° along the bottom, full-length pair labels collide once a route runs to a few dozen
    # segments, so names are trimmed harder in that orientation.
    labels = [segment_label(from_name, to_name, max_chars=14 if stops_on_x else 22)
              for _, from_name, to_name in matrix.ratio.index]
    hours = list(matrix.ratio.columns)
    if stops_on_x:
        values = values.T
        counts = counts.T

    # Symmetric limits keep the neutral colour pinned to 1.0, so equal drift in either direction gets
    # equal visual weight. The range comes from a high percentile rather than the maximum: one freak
    # ride would otherwise stretch the scale until every real difference washed out.
    deviation = np.abs(values - 1.0)
    spread = float(np.nanpercentile(deviation, 95)) if np.isfinite(deviation).any() else 0.5
    spread = float(np.clip(spread, 0.15, 1.0))
    norm = TwoSlopeNorm(vmin=1 - spread, vcenter=1.0, vmax=1 + spread)

    thin = (counts > 0) & (counts < min_samples)

    hour_labels = [f'{h:02d}' for h in hours]

    with styled(mode) as colors:
        if stops_on_x:
            fig, ax = plt.subplots(figsize=(max(9.0, 0.52 * len(labels) + 4.0),
                                            max(5.0, 0.42 * len(hours) + 4.0)))
        else:
            fig, ax = plt.subplots(figsize=(max(8.0, 0.66 * len(hours) + 6.0),
                                            max(5.0, 0.38 * len(labels) + 2.4)))
        ax.grid(False)

        n_cols, n_rows = values.shape[1], values.shape[0]
        cmap = ratio_colormap(mode).with_extremes(bad=colors.surface)
        mesh = ax.pcolormesh(np.arange(n_cols + 1), np.arange(n_rows + 1),
                             np.ma.masked_invalid(values),
                             cmap=cmap, norm=norm,
                             # A hairline in the surface colour separates the cells, so adjacent
                             # values never bleed into one another.
                             edgecolors=colors.surface, linewidth=1.5)

        _hatch_thin_cells(ax, thin, colors)
        if annotate_counts and n_cols * n_rows <= 420:
            _annotate_counts(ax, counts, values, norm, cmap, colors)

        col_labels, row_labels = ((labels, hour_labels) if stops_on_x
                                  else (hour_labels, labels))
        ax.set_xticks(np.arange(n_cols) + 0.5)
        ax.set_yticks(np.arange(n_rows) + 0.5)
        if stops_on_x:
            ax.set_xticklabels(col_labels, rotation=45, ha='right', rotation_mode='anchor')
            horizontal_value_label(ax, 'שעת יציאה', colors)
        else:
            ax.set_xticklabels(col_labels)
            ax.set_xlabel('שעת יציאה')
        ax.set_yticklabels(row_labels)
        # Downwards: route order in the default layout, earliest hour first when transposed - both
        # read top to bottom.
        ax.invert_yaxis()
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # extend='both' puts arrowheads on the bar, so it is visible that the percentile-based range
        # clips rather than pretending the extremes are the true limits.
        bar = fig.colorbar(mesh, ax=ax, pad=0.02, aspect=28, extend='both', extendfrac=0.015,
                           ticks=[1 - spread, 1.0, 1 + spread])
        bar.ax.set_yticklabels([f'{1 - spread:.2f}', '1.00', f'{1 + spread:.2f}'])
        # Horizontal, above the bar, rather than matplotlib's default sideways label: rotated Hebrew
        # is genuinely hard to read.
        bar.ax.set_title('יחס בפועל / מתוכנן', color=colors.ink_secondary, fontsize=9,
                         pad=8, loc='left')
        bar.ax.tick_params(labelsize=8, length=0, colors=colors.ink_muted)
        bar.outline.set_visible(False)

        # Anchored to the figure, not the axes: an axes-relative offset that clears the x label on a
        # short chart collides with it on a tall one.
        fig.legend(
            handles=[
                Patch(facecolor=colors.grid, hatch='///', edgecolor=colors.ink_muted,
                      label=f'פחות מ־{min_samples} נסיעות — ממוצע על מדגם קטן'),
                Patch(facecolor=colors.surface, edgecolor=colors.baseline,
                      label='אין נתונים כלל'),
            ],
            # Transposed, the bottom belongs to the rotated segment labels, so the key moves up top.
            loc='upper left' if stops_on_x else 'lower left',
            bbox_to_anchor=(0.01, 0.90) if stops_on_x else (0.01, 0.0),
            ncol=2, handletextpad=0.6, fontsize=8.5,
        )

        add_titles(fig, f'עומס לפי שעה וקטע — {line_label}', subtitle, colors)
        fig.tight_layout(rect=(0, 0, 1, 0.88) if stops_on_x else (0, 0.045, 1, 0.95))

    return fig


def _hatch_thin_cells(ax, thin: np.ndarray, colors) -> None:
    """Overlay hatching where a cell rests on fewer rides than the threshold."""
    for row, col in zip(*np.nonzero(thin)):
        ax.add_patch(plt.Rectangle(
            (col, row), 1, 1, fill=False, hatch='///',
            edgecolor=colors.ink_muted, linewidth=0, zorder=3))


def _annotate_counts(ax, counts, values, norm, cmap, colors) -> None:
    """Print each cell's ride count, in whichever ink stays legible on that cell's colour."""
    for row in range(counts.shape[0]):
        for col in range(counts.shape[1]):
            if counts[row, col] == 0:
                continue
            value = values[row, col]
            # Dark cells at either end of the diverging scale need light text.
            extreme = np.isfinite(value) and not 0.22 < norm(value) < 0.78
            ax.annotate(str(counts[row, col]), xy=(col + 0.5, row + 0.5),
                        ha='center', va='center', fontsize=6.5, zorder=4,
                        color='#ffffff' if extreme else colors.ink_secondary)
