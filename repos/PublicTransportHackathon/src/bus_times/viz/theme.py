"""Shared look for every chart: one palette, one rcParams set, both light and dark.

Colours come from the validated reference palette (categorical slot 1 blue for measured/actual and
slot 2 orange for the schedule, diverging blue↔red for the ratio heatmap). Both modes pass the
palette validator's six checks against their own surface.
"""

from contextlib import contextmanager
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from .hebrew import resolve_hebrew_font


@dataclass(frozen=True)
class Palette:
    surface: str
    ink_primary: str
    ink_secondary: str
    ink_muted: str
    grid: str
    baseline: str
    actual: str      # categorical slot 1 - what the buses really did
    planned: str     # categorical slot 2 - what the timetable promised
    diverging: tuple[str, ...]  # fast -> on schedule -> slow


LIGHT = Palette(
    surface='#fcfcfb',
    ink_primary='#0b0b0b',
    ink_secondary='#52514e',
    ink_muted='#898781',
    grid='#e1e0d9',
    baseline='#c3c2b7',
    actual='#2a78d6',
    planned='#eb6834',
    diverging=('#184f95', '#2a78d6', '#f0efec', '#e34948', '#8f2020'),
)

DARK = Palette(
    surface='#1a1a19',
    ink_primary='#ffffff',
    ink_secondary='#c3c2b7',
    ink_muted='#898781',
    grid='#2c2c2a',
    baseline='#383835',
    actual='#3987e5',
    planned='#d95926',
    diverging=('#184f95', '#3987e5', '#383835', '#e66767', '#8f2020'),
)


def palette(mode: str = 'light') -> Palette:
    if mode not in ('light', 'dark'):
        raise ValueError(f"mode must be 'light' or 'dark', got {mode!r}")
    return LIGHT if mode == 'light' else DARK


def ratio_colormap(mode: str = 'light') -> LinearSegmentedColormap:
    """Diverging map for actual/planned duration ratios, neutral at the midpoint.

    Diverging rather than sequential because 1.0 is a real midpoint — exactly on schedule — and the
    two directions mean opposite things. The neutral grey centre keeps "as scheduled" from reading as
    a value.
    """
    return LinearSegmentedColormap.from_list(f'ratio_{mode}', palette(mode).diverging)


def rc_params(mode: str = 'light') -> dict[str, object]:
    """Recessive chrome, Hebrew-capable font, no top/right spines, horizontal grid only."""
    colors = palette(mode)
    return {
        'font.family': 'sans-serif',
        'font.sans-serif': [resolve_hebrew_font(), 'DejaVu Sans'],
        # Hebrew fonts often lack U+2212; the ASCII hyphen always renders.
        'axes.unicode_minus': False,
        'figure.facecolor': colors.surface,
        'figure.dpi': 150,
        # No savefig.* settings here on purpose: saving happens after the style context has exited,
        # so they would be inert. Use save_figure() instead.
        'axes.facecolor': colors.surface,
        'axes.edgecolor': colors.baseline,
        'axes.labelcolor': colors.ink_secondary,
        'axes.labelsize': 10,
        'axes.titlecolor': colors.ink_secondary,
        'axes.titlesize': 10,
        'axes.titleweight': 'normal',
        'axes.grid': True,
        # Value-axis gridlines only. Charts that want the other axis turn it on explicitly, so a
        # stray perpendicular grid can never leak in from here.
        'axes.grid.axis': 'y',
        'axes.axisbelow': True,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.color': colors.grid,
        'grid.linewidth': 1,
        'xtick.color': colors.ink_muted,
        'ytick.color': colors.ink_muted,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.frameon': False,
        'legend.fontsize': 9,
        'legend.labelcolor': colors.ink_secondary,
    }


@contextmanager
def styled(mode: str = 'light'):
    """Apply the chart style for the duration of a plotting block."""
    with plt.style.context(rc_params(mode)):
        yield palette(mode)


def horizontal_value_label(ax, text: str, colors: Palette) -> None:
    """Put a y-axis label flat above the axis instead of rotated up its side.

    Matplotlib rotates y labels 90° by default, which makes Hebrew genuinely hard to read.
    """
    ax.set_ylabel(text, rotation=0, ha='left', va='bottom', color=colors.ink_secondary)
    ax.yaxis.set_label_coords(0.0, 1.01)


def add_titles(fig, title: str, subtitle: str | None, colors: Palette,
               footnote: str | None = None, footnote_at_top: bool = False) -> None:
    """Left-aligned headline above a smaller subtitle, the layout every chart here uses.

    All three are placed against the *figure* rather than the axes. Long Hebrew tick labels push the
    axes far to the right, and an axes-anchored title follows it there and runs off the canvas.

    ``footnote`` carries data-quality caveats — how many rides, how many stops are thinly covered.
    It sits at the bottom because it qualifies the whole chart rather than any one mark. Set
    ``footnote_at_top`` when the chart has rotated tick labels along the bottom, which reach the
    canvas edge and would otherwise be written over.
    """
    fig.suptitle(title, color=colors.ink_primary, fontsize=13, fontweight='bold',
                 x=0.01, y=0.99, ha='left', va='top')
    subtitle_y = 0.955
    if subtitle:
        fig.text(0.01, subtitle_y, subtitle, color=colors.ink_muted, fontsize=9.5,
                 ha='left', va='top')
    if footnote:
        if footnote_at_top:
            fig.text(0.01, subtitle_y - (0.028 if subtitle else 0.0), footnote,
                     color=colors.ink_muted, fontsize=8.5, ha='left', va='top')
        else:
            fig.text(0.01, 0.005, footnote, color=colors.ink_muted, fontsize=8.5,
                     ha='left', va='bottom')


def save_figure(fig, path, dpi: int = 150) -> None:
    """Write a figure to disk without clipping its labels.

    ``bbox_inches='tight'`` has to be passed here rather than set in the style: by the time a caller
    saves, the style context has exited and any ``savefig.*`` rcParam is long out of scope. Without
    it, the long Hebrew stop names that sit outside the axes get cut off at the canvas edge.

    ``pad_inches`` matters too — a tight bbox is the content's exact bounding box, so the longest stop
    name ends up flush against the edge of the image with nothing to breathe.
    """
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.28,
                facecolor=fig.get_facecolor())
