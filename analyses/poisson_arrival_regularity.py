"""Poisson arrival regularity: evolution of interarrival headway variation along the route.

Adapted from Yuval's open_bus_poisson_analysis_all_in_one.ipynb notebook.
"""

from __future__ import annotations

import base64
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from openbus_hack import (
    AnalysisRequest,
    AnalysisResult,
    Point,
    Series,
    Table,
    analysis,
    image,
    metrics,
)
from analyses.bus_arrival_reliability import (
    NoMatch,
    _INPUTS,
    _OPTIONS,
    _load,
    _match_notes,
    _no_match_card,
)

_CREDIT = "Ported from Yuval's exploratory Poisson arrival notebook."


@analysis(
    name="poisson-arrival-regularity",
    title="Poisson arrival: headway regularity decay",
    description="Tests how bus interarrival spacing (headway) degenerates into a random "
                "Poisson process as buses travel downstream. CV is the Coefficient of "
                "Variation of gaps (Exponential benchmark: CV = 1). When CV approaches 1, "
                "spacing is fully random and schedule adherence is lost.",
    author="yuvalko1",
    tags=["reliability", "punctuality", "gps", "interactive"],
    inputs=_INPUTS,
    options=_OPTIONS,
)
def run_poisson(req: AnalysisRequest):
    try:
        # Reuse the robust, cached fetch logic from bus_arrival_reliability
        resolved_data, alts = _load(
            req.line or "23",
            req.operator or "",
            str(req.opt("name_contains", "תל אביב")),
            str(req.opt("direction", "1")),
            req.date_from,
            req.date_to,
        )
    except NoMatch as exc:
        return _no_match_card(exc)

    if resolved_data is None:
        return _no_match_card(NoMatch(req.line or "23", req.operator, alts))

    line, stop_events, _ride_segments, subtitle = resolved_data

    # Calculate stop-wise interarrival gap CV
    # stop_events has: siri_ride_id, stop_sequence, stop_name, actual_time, ride_date
    stop_events = stop_events.dropna(subset=["actual_time", "stop_sequence"])

    stop_results = []

    for seq, grp in stop_events.groupby("stop_sequence"):
        stop_name = grp["stop_name"].iloc[0]

        # Calculate gaps within the same day
        gaps = []
        for _date, day_grp in grp.groupby("ride_date"):
            # Sort chronologically to get consecutive arrivals
            arrivals = day_grp["actual_time"].sort_values()
            if len(arrivals) >= 2:
                # Gaps in minutes
                day_gaps = arrivals.diff().dropna().dt.total_seconds() / 60
                gaps.extend(day_gaps.tolist())

        if len(gaps) >= 3:  # Need at least 3 gaps for meaningful CV
            mean_gap = np.mean(gaps)
            std_gap = np.std(gaps, ddof=1)
            cv = std_gap / mean_gap if mean_gap > 0 else 0.0
            stop_results.append(
                {
                    "stop_index": int(seq) + 1,
                    "stop_name": stop_name,
                    "n_gaps": len(gaps),
                    "mean_gap": float(mean_gap),
                    "cv": float(cv),
                }
            )

    if not stop_results:
        return metrics(
            ("No data", 0),
            notes=[
                "Not enough consecutive rides were observed to calculate interarrival headways.",
                "Try picking a higher-frequency line or widening the date range.",
                _CREDIT,
            ],
        )

    df = pd.DataFrame(stop_results).sort_values("stop_index")

    # 1. Structured data for React view (Table)
    t = Table(
        columns=["stop_index", "stop_name", "observed_gaps", "mean_gap_min", "headway_cv"],
        rows=[
            [
                row.stop_index,
                row.stop_name,
                row.n_gaps,
                round(row.mean_gap, 1),
                round(row.cv, 2),
            ]
            for row in df.itertuples()
        ],
    )

    # Render React line chart points
    points = [Point(x=float(r.stop_index), y=float(r.cv)) for r in df.itertuples()]
    # Add a horizontal benchmark line series at CV=1.0
    benchmark_points = [Point(x=float(r.stop_index), y=1.0) for r in df.itertuples()]

    series = [
        Series(name=f"Line {line.short_name} CV", points=points),
        Series(name="Exponential Benchmark (CV=1)", points=benchmark_points),
    ]

    notes = [
        *_match_notes(line, alts),
        "The Coefficient of Variation (CV = std/mean) measures headway regularity.",
        "CV ~ 0 means buses are perfectly spaced (origin terminal). CV ~ 1.0 means "
        "interarrival times are completely random (Poisson process, headway decay downstream).",
        "Toggle 'Static draft' in the footer to see Yuval's gorgeous matplotlib-styled plot, "
        "or 'Table' for raw numbers.",
        _CREDIT,
    ]

    res = AnalysisResult(
        kind="chart",
        chart_type="line",  # Recharts line chart
        series=series,
        title="Poisson arrival: headway regularity decay",
        subtitle=f"{line.label} · {subtitle}",
        x_label="Stop index along route (origin = 1)",
        y_label="Coefficient of variation (CV)",
        table=t,
        notes=notes,
    )

    # 2. Matplotlib render for 'static draft' view
    try:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(
            df["stop_index"],
            df["cv"],
            marker="o",
            color="#2a78d6",
            linewidth=2.0,
            label=f"Line {line.short_name}",
        )
        ax.axhline(
            1.0,
            color="#d03b3b",
            linestyle="--",
            linewidth=1.2,
            label="Exponential Benchmark (CV=1)",
        )
        ax.set_xlabel("Stop index along route (origin = 1)")
        ax.set_ylabel("Coefficient of variation (CV)")
        ax.set_title("Evolution of bus-interarrival variability along the route")
        ax.grid(alpha=0.25)
        ax.legend(loc="best")

        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", dpi=144, bbox_inches="tight", facecolor=fig.get_facecolor()
        )
        plt.close(fig)
        res.image_png = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        notes.append(f"Matplotlib render failed: {exc}")
        res.notes = notes

    return res
