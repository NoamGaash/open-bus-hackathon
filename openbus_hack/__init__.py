"""openbus_hack — shared infra for the Open Bus hackathon.

Everything an analysis author needs is re-exported here, so one import line does it:

    from openbus_hack import analysis, AnalysisRequest, stride, line_chart, metrics
"""

from __future__ import annotations

from . import stride
from .contract import (
    AnalysisRequest,
    AnalysisResult,
    Heatmap,
    HeatmapCell,
    Metric,
    Point,
    Series,
    Table,
    bar_chart,
    error,
    geo,
    heatmap,
    image,
    line_chart,
    metrics,
    table,
)
from .registry import AnalysisSpec, OptionSpec, analysis, discover, get, registry, run
from .theme import use_openbus_style

__all__ = [
    # authoring
    "analysis",
    "AnalysisRequest",
    "AnalysisResult",
    "OptionSpec",
    # result helpers
    "metrics",
    "line_chart",
    "bar_chart",
    "heatmap",
    "geo",
    "table",
    "image",
    "error",
    "Metric",
    "Series",
    "Point",
    "Table",
    "Heatmap",
    "HeatmapCell",
    # data access
    "stride",
    # registry internals (mostly for the server + notebooks)
    "AnalysisSpec",
    "discover",
    "registry",
    "get",
    "run",
    # charts
    "use_openbus_style",
]

__version__ = "0.1.0"
