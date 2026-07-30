"""The shared contract between each team member's analysis and the dashboard.

Everyone writes the same shape of function::

    @analysis(name="my-thing", title="My Thing", author="you")
    def run(req: AnalysisRequest) -> AnalysisResult:
        ...

You get an :class:`AnalysisRequest` (which lines / which operators / what dates)
and you return *something renderable*. You almost never build an
:class:`AnalysisResult` by hand — use the helpers at the bottom of this module
(:func:`metrics`, :func:`line_chart`, :func:`bar_chart`, :func:`table`,
:func:`image`), or just return a matplotlib figure or a DataFrame and let the
registry coerce it.
"""

from __future__ import annotations

import base64
import io
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "AnalysisRequest",
    "AnalysisResult",
    "Heatmap",
    "HeatmapCell",
    "Metric",
    "Point",
    "Series",
    "Table",
    "metrics",
    "line_chart",
    "bar_chart",
    "heatmap",
    "table",
    "image",
    "error",
]

# ── Input ────────────────────────────────────────────────────────────────────

ChartType = Literal["line", "bar", "stacked_bar", "area", "scatter", "trajectories"]
ResultKind = Literal["metrics", "chart", "table", "image", "heatmap", "geo", "error"]


class AnalysisRequest(BaseModel):
    """What the dashboard asks an analysis to look at.

    Every field is optional with a sane default, so an analysis can be run with
    ``AnalysisRequest()`` in a notebook and still do something useful.
    """

    lines: list[str] = Field(
        default_factory=list,
        description="GTFS route_short_name values, e.g. ['480', '1']. Empty = caller didn't filter by line.",
    )
    operators: list[str] = Field(
        default_factory=list,
        description="Agency names as they appear in GTFS, e.g. ['אגד', 'דן']. Empty = all operators.",
    )
    date_from: date = Field(default_factory=lambda: date.today() - timedelta(days=8))
    date_to: date = Field(default_factory=lambda: date.today() - timedelta(days=1))
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form knobs specific to one analysis. Declare them in @analysis(options=...).",
    )

    # ── convenience for analysis authors ──
    @property
    def line(self) -> str | None:
        """First requested line, for analyses that only handle one."""
        return self.lines[0] if self.lines else None

    @property
    def operator(self) -> str | None:
        """First requested operator, for analyses that only handle one."""
        return self.operators[0] if self.operators else None

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1

    def dates(self) -> list[date]:
        return [self.date_from + timedelta(days=i) for i in range(self.days)]

    def opt(self, key: str, default: Any = None) -> Any:
        return self.options.get(key, default)


# ── Output ───────────────────────────────────────────────────────────────────


class Metric(BaseModel):
    """A single headline number for a stat tile."""

    label: str
    value: float | int | str
    unit: str | None = None
    # Optional change-vs-baseline. Positive is not automatically "good" —
    # say so explicitly, because for delays up is bad.
    delta: float | None = None
    delta_is_good: bool | None = None
    help: str | None = None


class Point(BaseModel):
    x: str | float
    y: float | None = None


class Series(BaseModel):
    """One line / one bar-group / one stack segment. Named, because the
    dashboard always shows a legend for >= 2 series."""

    name: str
    points: list[Point] = Field(default_factory=list)
    # kind="chart", chart_type="trajectories" only: an emphasized series (e.g. a
    # single "Planned" reference line among many individual-ride trajectories)
    # is drawn bold and legended; the rest share one muted, unlegended color —
    # a legend entry per ride would be noise, not information.
    emphasis: bool = False


class Table(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class HeatmapCell(BaseModel):
    """One cell of a heatmap grid.

    ``count`` is the sample size behind ``value``. It is separate from the value
    on purpose: a cell resting on one observation and a cell resting on fifty must
    not look equally authoritative, and a cell with *no* data must not look like a
    cell that measured zero. The renderer draws those three states differently.
    """

    row: int
    col: int
    value: float | None = None
    count: int | None = None
    # Set when the cell is measured but under-sampled — drawn hatched, not hidden.
    weak: bool = False


class Heatmap(BaseModel):
    """A labelled grid of values — segment × hour, stop × day, and so on.

    Sparse by design: only cells that have something to say are listed, so a large
    mostly-empty grid stays a small payload. Anything absent renders as "no data",
    which is a distinct appearance from a measured zero.
    """

    row_labels: list[str] = Field(default_factory=list)
    col_labels: list[str] = Field(default_factory=list)
    cells: list[HeatmapCell] = Field(default_factory=list)
    row_axis_label: str | None = None
    col_axis_label: str | None = None
    # Diverging scales need to know where "neutral" sits — e.g. 1.0 for an
    # actual/planned ratio. Left None for a plain sequential (low→high) scale.
    center: float | None = None
    value_label: str | None = None
    value_suffix: str | None = None


class AnalysisResult(BaseModel):
    """Whatever your analysis produced, in a form the dashboard can render.

    One flat model rather than a union, so the frontend has a single shape to
    narrow on ``kind`` and every renderer can fall back to ``table``.
    """

    kind: ResultKind = "metrics"
    title: str | None = None
    subtitle: str | None = None

    # kind="metrics"
    metrics: list[Metric] = Field(default_factory=list)

    # kind="chart"
    chart_type: ChartType = "line"
    series: list[Series] = Field(default_factory=list)
    x_label: str | None = None
    y_label: str | None = None
    # Set when x is a date/ordered category so the frontend doesn't re-sort it.
    x_is_temporal: bool = False
    # Bars run left-to-right with categories on the y axis instead of the x —
    # for bar/stacked_bar only. Needed when category labels are long (route
    # names, stop pairs): rotated x labels collide, flat y labels don't.
    horizontal: bool = False
    # chart_type="trajectories" only: ordered labels for integer y ticks
    # 0..N-1 (e.g. stop names), since y there is a stop *position*, not a
    # plain number.
    y_tick_labels: list[str] | None = None

    # kind="table", and the mandatory relief view for every chart
    # (light-mode palette has sub-3:1 slots, so a table view is required).
    table: Table | None = None

    # kind="image" — base64 PNG, for matplotlib/seaborn/folium output
    image_png: str | None = None
    image_alt: str | None = None

    # kind="heatmap" — raw grid, rendered client-side (interactive, small payload)
    heatmap: Heatmap | None = None

    # kind="geo" — a GeoJSON FeatureCollection
    geojson: dict[str, Any] | None = None

    # Free-text caveats shown under the chart. Use these! "only 3 days of SIRI
    # data available" belongs here, not in a print().
    notes: list[str] = Field(default_factory=list)

    # Populated by the registry on failure.
    error_message: str | None = None
    error_traceback: str | None = None

    def ensure_table(self) -> AnalysisResult:
        """Derive a table view from series if the author didn't supply one.

        Called by the registry so every chart satisfies the relief rule for free.
        """
        if self.table is not None or not self.series:
            return self
        xs: list[str | float] = []
        seen: set[str | float] = set()
        for s in self.series:
            for p in s.points:
                if p.x not in seen:
                    seen.add(p.x)
                    xs.append(p.x)
        by_series = {s.name: {p.x: p.y for p in s.points} for s in self.series}
        self.table = Table(
            columns=[self.x_label or "x", *by_series.keys()],
            rows=[[x, *(by_series[n].get(x) for n in by_series)] for x in xs],
        )
        return self


# ── Helpers: the API analysis authors actually touch ─────────────────────────


def metrics(*items: Metric | tuple[str, Any] | dict[str, Any], title: str | None = None,
            subtitle: str | None = None, notes: list[str] | None = None) -> AnalysisResult:
    """Headline numbers. Accepts Metric objects, ``("label", value)`` tuples, or dicts.

    >>> metrics(("Total rides", 1234), ("On-time %", 87.5))
    """
    out: list[Metric] = []
    for it in items:
        if isinstance(it, Metric):
            out.append(it)
        elif isinstance(it, tuple):
            out.append(Metric(label=str(it[0]), value=it[1]))
        else:
            out.append(Metric(**it))
    return AnalysisResult(kind="metrics", metrics=out, title=title, subtitle=subtitle,
                          notes=notes or [])


def _series_from(data: Any, x: str | None, y: str | None, series: str | None) -> list[Series]:
    """Build Series from a DataFrame, a dict of {name: {x: y}}, or a list of Series."""
    if isinstance(data, list) and (not data or isinstance(data[0], Series)):
        return list(data)
    if isinstance(data, dict):
        return [
            Series(name=str(k), points=[Point(x=xx, y=yy) for xx, yy in v.items()])
            for k, v in data.items()
        ]
    # Assume DataFrame-like
    df = data
    if x is None or y is None:
        raise ValueError("line_chart/bar_chart need x= and y= column names for a DataFrame")
    if series:
        return [
            Series(
                name=str(name),
                points=[Point(x=_jsonable_x(r[x]), y=_nan_to_none(r[y])) for _, r in grp.iterrows()],
            )
            for name, grp in df.groupby(series, sort=False)
        ]
    return [
        Series(
            name=str(y),
            points=[Point(x=_jsonable_x(r[x]), y=_nan_to_none(r[y])) for _, r in df.iterrows()],
        )
    ]


def _jsonable_x(v: Any) -> str | float:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()[:19]
    return str(v)


def _nan_to_none(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check without importing math


def line_chart(data: Any, x: str | None = None, y: str | None = None, series: str | None = None,
               *, title: str | None = None, subtitle: str | None = None,
               x_label: str | None = None, y_label: str | None = None,
               temporal: bool = True, notes: list[str] | None = None) -> AnalysisResult:
    """A line chart from a DataFrame (``x=``/``y=``, optional ``series=`` to split)."""
    return AnalysisResult(
        kind="chart", chart_type="line", series=_series_from(data, x, y, series),
        title=title, subtitle=subtitle, x_label=x_label or x, y_label=y_label or y,
        x_is_temporal=temporal, notes=notes or [],
    ).ensure_table()


def bar_chart(data: Any, x: str | None = None, y: str | None = None, series: str | None = None,
              *, stacked: bool = False, horizontal: bool = False, title: str | None = None,
              subtitle: str | None = None, x_label: str | None = None, y_label: str | None = None,
              notes: list[str] | None = None) -> AnalysisResult:
    """A bar chart. ``stacked=True`` for parts-of-a-whole, ``horizontal=True`` when
    category labels are long enough that rotated x-axis text would collide."""
    return AnalysisResult(
        kind="chart", chart_type="stacked_bar" if stacked else "bar",
        series=_series_from(data, x, y, series), horizontal=horizontal,
        title=title, subtitle=subtitle, x_label=x_label or x, y_label=y_label or y,
        x_is_temporal=False, notes=notes or [],
    ).ensure_table()


def heatmap(values: Any, counts: Any = None, *, row_labels: list[str] | None = None,
            col_labels: list[str] | None = None, min_count: int | None = None,
            center: float | None = None, title: str | None = None,
            subtitle: str | None = None, row_axis_label: str | None = None,
            col_axis_label: str | None = None, value_label: str | None = None,
            value_suffix: str | None = None,
            notes: list[str] | None = None) -> AnalysisResult:
    """A grid of values rendered client-side, from a DataFrame (rows × columns).

    ``values`` is a DataFrame whose index is the rows and columns the columns;
    ``counts`` is an optional same-shaped frame of sample sizes. Cells below
    ``min_count`` are flagged ``weak`` and drawn hatched rather than dropped —
    a silently missing cell is indistinguishable from one that has no data.

    Pass ``center`` (e.g. ``1.0`` for an actual/planned ratio) to get a diverging
    scale around that neutral point instead of a plain low→high one.

    >>> heatmap(ratio_df, count_df, min_count=3, center=1.0)
    """
    rows = [str(r) for r in (row_labels if row_labels is not None else values.index)]
    cols = [str(c) for c in (col_labels if col_labels is not None else values.columns)]

    cells: list[HeatmapCell] = []
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = _nan_to_none(values.iat[i, j])
            n = None if counts is None else _nan_to_none(counts.iat[i, j])
            # Absent cells are simply omitted — the renderer shows "no data",
            # which must not look like a measured zero.
            if v is None and not n:
                continue
            count = None if n is None else int(n)
            cells.append(HeatmapCell(
                row=i, col=j, value=v, count=count,
                weak=bool(min_count is not None and count is not None and count < min_count),
            ))

    # The relief view is mandatory (light-mode palette has sub-3:1 slots), so
    # derive it here rather than asking every author to remember.
    grid: dict[tuple[int, int], float | None] = {(c.row, c.col): c.value for c in cells}
    return AnalysisResult(
        kind="heatmap", title=title, subtitle=subtitle, notes=notes or [],
        heatmap=Heatmap(
            row_labels=rows, col_labels=cols, cells=cells,
            row_axis_label=row_axis_label, col_axis_label=col_axis_label,
            center=center, value_label=value_label, value_suffix=value_suffix,
        ),
        table=Table(
            columns=[row_axis_label or "", *cols],
            rows=[[rows[i], *(grid.get((i, j)) for j in range(len(cols)))]
                  for i in range(len(rows))],
        ),
    )


def table(df: Any, *, title: str | None = None, subtitle: str | None = None,
          max_rows: int = 500, notes: list[str] | None = None) -> AnalysisResult:
    """A plain table from a DataFrame. Truncated to ``max_rows`` for transport."""
    notes = list(notes or [])
    total = len(df)
    view = df.head(max_rows)
    if total > max_rows:
        notes.append(f"Showing first {max_rows:,} of {total:,} rows.")
    return AnalysisResult(
        kind="table", title=title, subtitle=subtitle, notes=notes,
        table=Table(
            columns=[str(c) for c in view.columns],
            rows=[[_cell(v) for v in row] for row in view.itertuples(index=False)],
        ),
    )


def _cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, str, bool)):
        return v
    if isinstance(v, float):
        return None if v != v else v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def image(fig: Any = None, *, title: str | None = None, subtitle: str | None = None,
          alt: str | None = None, dpi: int = 144,
          notes: list[str] | None = None) -> AnalysisResult:
    """Render a matplotlib figure to an inline PNG.

    Pass a Figure, or nothing to grab the current pyplot figure.
    """
    import matplotlib.pyplot as plt

    if fig is None:
        fig = plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return AnalysisResult(
        kind="image", title=title, subtitle=subtitle, notes=notes or [],
        image_png=base64.b64encode(buf.getvalue()).decode("ascii"),
        image_alt=alt or title or "chart",
    )


def error(message: str, traceback_text: str | None = None) -> AnalysisResult:
    """A failed analysis. The dashboard shows this as a card, not a blank page."""
    return AnalysisResult(kind="error", title="Analysis failed",
                          error_message=message, error_traceback=traceback_text)
