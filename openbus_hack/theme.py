"""One chart theme, shared by everyone, so the presentation looks like one product.

The palette here is the *same* set of hexes the React dashboard uses (see
``frontend/src/theme.css``). It's a validated categorical palette: assign slots
in order, never cycle past 8 — fold the tail into "Other" instead.

    from openbus_hack import use_openbus_style
    use_openbus_style()          # then plot normally

If you return structured data (``line_chart(...)``) instead of a PNG, you get
this styling automatically from the frontend and don't need this module at all.
"""

from __future__ import annotations

from typing import Literal

__all__ = ["SERIES_LIGHT", "SERIES_DARK", "STATUS", "use_openbus_style", "series_color"]

# Categorical slots, in fixed assignment order. Validated for CVD separation on
# adjacent pairs in both modes — do not reorder.
SERIES_LIGHT = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]
SERIES_DARK = [
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
]

# Reserved — never reuse these as a series color.
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

_CHROME = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e",
        "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7",
        "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835",
    },
}


def series_color(i: int, mode: Literal["light", "dark"] = "light") -> str:
    """Color for series index ``i`` (0-based). Past slot 8 you should be folding
    into an "Other" bucket rather than asking for a 9th hue — this clamps."""
    palette = SERIES_LIGHT if mode == "light" else SERIES_DARK
    return palette[min(i, len(palette) - 1)]


def use_openbus_style(mode: Literal["light", "dark"] = "light") -> None:
    """Apply the shared matplotlib style in-place.

    Thin marks, recessive grid, no top/right spines, horizontal-only gridlines.
    """
    import matplotlib as mpl
    from cycler import cycler

    c = _CHROME[mode]
    palette = SERIES_LIGHT if mode == "light" else SERIES_DARK

    mpl.rcParams.update({
        "figure.facecolor": c["surface"],
        "axes.facecolor": c["surface"],
        "savefig.facecolor": c["surface"],
        "figure.figsize": (8, 4.5),
        "figure.dpi": 110,
        "font.family": ["DejaVu Sans"],  # has Hebrew glyphs; agency names are Hebrew
        "font.size": 11,
        "axes.prop_cycle": cycler(color=palette),
        "axes.edgecolor": c["axis"],
        "axes.labelcolor": c["ink2"],
        "axes.titlecolor": c["ink"],
        "axes.titlesize": 13,
        "axes.titleweight": "600",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": c["grid"],
        "grid.linewidth": 0.8,
        "xtick.color": c["muted"],
        "ytick.color": c["muted"],
        "xtick.labelcolor": c["ink2"],
        "ytick.labelcolor": c["ink2"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "lines.linewidth": 2.0,
        "lines.markersize": 5,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": c["ink2"],
    })
