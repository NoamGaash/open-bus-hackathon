"""Days without cancellations quality score dashboard card.

Integrates the "orion" group materials from orion/days_with_no_cancellations.py.
"""

from __future__ import annotations

import base64
import datetime
import pandas as pd

from openbus_hack import (
    AnalysisRequest,
    AnalysisResult,
    Table,
    analysis,
    bar_chart,
    metrics,
)
from orion.days_with_no_cancellations import (
    daily_report,
    operator_line_scores,
    plot_operator_scores,
)


@analysis(
    name="days-with-no-cancellations",
    title="Days with zero cancellations",
    description="Quality score based on how many days all buses operated as expected (zero cancellations). "
                "A day with >=1 cancellation counts as 0, a day with full operations is 1.",
    author="orion",
    tags=["reliability", "cancellations", "data.gov.il"],
    inputs=["lines", "operators", "dates"],
)
def run(req: AnalysisRequest):
    days_back = 15  # Core metric looks at last 15 days
    # Default window end date (retaining LAG_DAYS to be consistent with data freshness)
    end_date = min(req.date_to, datetime.date.today() - datetime.timedelta(days=1))

    # ── Method 1: Single Line ────────────────────────────────────────────────
    if req.line:
        operators = req.operators if req.operators else None
        df = daily_report(req.line, days=days_back, end=end_date, operators=operators)
        if df.empty:
            return metrics(
                ("No data", 0),
                notes=[
                    f"No planned rides for line {req.line} in the last {days_back} days.",
                    "Ensure you have selected the correct operator or clear filters.",
                ]
            )

        # Reshape to long format for bar_chart (Operated vs Cancelled)
        df["date_str"] = df["date"].astype(str)
        df["Operated"] = df["planned"] - df["cancelled"]
        df_long = df.melt(
            id_vars="date_str",
            value_vars=["Operated", "cancelled"],
            var_name="Status",
            value_name="rides",
        )

        good_days = int(df["good"].sum())
        total_days = len(df)
        score = good_days / total_days if total_days > 0 else 0.0

        return bar_chart(
            df_long,
            x="date_str",
            y="rides",
            series="Status",
            stacked=True,
            title=f"Line {req.line} — Daily cancellations and runs",
            subtitle=f"Score: {score:.2f} ({good_days}/{total_days} clean days in the last {days_back} days)",
            notes=[
                "A 'clean day' is one with absolutely zero cancellations.",
                "Data source is the Ministry's rides execution endpoint (/rides_execution/list), "
                "where scheduled departures with no matching GPS arrival record represent cancellations.",
            ],
        )

    # ── Method 2: Operator Overview ──────────────────────────────────────────
    else:
        operator = req.operator or "סופרבוס"  # Fallback to Superbus
        scores = operator_line_scores(
            operator, days=days_back, end=end_date, max_lines=15, progress=False
        )
        if scores.empty:
            return metrics(
                ("No data", 0),
                notes=[f"No lines with planned rides found for operator {operator}."]
            )

        # Generate horizontal bar chart using the custom matplotlib plotter
        fig_path = plot_operator_scores(scores, operator, days=days_back)

        # Read the written file directly as bytes to avoid re-rendering
        png_bytes = fig_path.read_bytes()
        b64_str = base64.b64encode(png_bytes).decode("ascii")

        # Expose precise numbers as the relief table
        t = Table(
            columns=["line", "score", "good_days", "days_scored", "planned", "cancelled"],
            rows=[
                [
                    row.line,
                    f"{row.score:.2f}",
                    int(row.good_days),
                    int(row.days_scored),
                    int(row.planned),
                    int(row.cancelled),
                ]
                for row in scores.itertuples()
            ],
        )

        return AnalysisResult(
            kind="image",
            title=f"{operator} — Days without cancellations",
            subtitle=f"Scores for worst performing lines, last {days_back} days",
            image_png=b64_str,
            image_alt=f"{operator} cancellation scores",
            table=t,
            notes=[
                "Each bar represents the fraction of days (out of last 15) with zero cancellations.",
                "Hatched bars ('///') indicate lines with zero actual GPS reports, which represent data gaps rather than actual 100% cancellations.",
                "Toggle 'Table view' at the top-right of the card to see exact planned, operated, and cancelled counts for each line.",
                f"Data retrieved live from /rides_execution/list.",
            ],
        )
