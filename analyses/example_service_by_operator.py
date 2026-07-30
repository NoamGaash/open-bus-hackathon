"""Worked example: planned vs actual service, by operator and by day.

This file exists to be copied. It hits the real Stride API, handles the empty
case, returns two different result kinds, and is deliberately short — if your
analysis is much longer than this, consider moving the exploration into
``workspace/<you>/`` and keeping only the final computation here.
"""

from __future__ import annotations

import pandas as pd

from openbus_hack import AnalysisRequest, OptionSpec, analysis, line_chart, metrics, stride


@analysis(
    name="service-by-operator",
    title="Planned vs actual rides",
    description=(
        "Daily count of rides each operator planned (GTFS) against how many were "
        "actually observed (SIRI). The gap is unrun service."
    ),
    author="example",
    tags=["service", "reliability", "operators"],
    # This one aggregates at operator level, so a line filter would be misleading.
    inputs=["operators", "dates"],
    options=[
        OptionSpec(
            key="top_n",
            label="Show top N operators",
            type="number",
            default=5,
            help="By total planned rides. The rest are folded into 'Other'.",
        )
    ],
    draft=False,
)
def run(req: AnalysisRequest):
    top_n = int(req.opt("top_n", 5) or 5)

    # gtfs_rides_agg is pre-aggregated server-side — much kinder than paging
    # every individual ride.
    agg = stride.gtfs_rides_agg(
        req.date_from, req.date_to, group_by="operator_ref,gtfs_route_date"
    )
    if agg.empty:
        return metrics(
            ("No data", 0),
            notes=[f"No aggregated rides between {req.date_from} and {req.date_to}."],
        )

    # Attach human-readable operator names.
    names = stride.agencies(req.date_from, req.date_to)
    if not names.empty:
        agg = agg.merge(
            names[["operator_ref", "agency_name"]], on="operator_ref", how="left"
        )
    agg["agency_name"] = agg.get("agency_name", pd.Series(dtype=str)).fillna(
        agg["operator_ref"].astype(str)
    )

    if req.operators:
        agg = agg[agg["agency_name"].isin(req.operators)]
        if agg.empty:
            return metrics(
                ("No data", 0),
                notes=[f"No rides for {', '.join(req.operators)} in that window."],
            )

    planned_col = _first_col(agg, ["total_planned_rides", "planned_rides", "num_planned_rides"])
    actual_col = _first_col(agg, ["total_actual_rides", "actual_rides", "num_actual_rides"])
    if planned_col is None:
        # The aggregate endpoint changed shape — show the raw frame rather than crash.
        from openbus_hack import table

        return table(agg, notes=["Unexpected columns from /gtfs_rides_agg/group_by."])

    notes: list[str] = []

    # Fold the long tail into "Other" — never generate a 9th series color.
    totals = agg.groupby("agency_name")[planned_col].sum().sort_values(ascending=False)
    keep = set(totals.head(top_n).index)
    if len(totals) > top_n:
        notes.append(f"{len(totals) - top_n} smaller operators folded into “Other”.")
    agg["series"] = agg["agency_name"].where(agg["agency_name"].isin(keep), "Other")

    daily = (
        agg.groupby(["gtfs_route_date", "series"], as_index=False)[planned_col]
        .sum()
        .rename(columns={planned_col: "planned", "gtfs_route_date": "day"})
    )
    daily["day"] = pd.to_datetime(daily["day"]).dt.date.astype(str)
    daily = daily.sort_values("day")

    if actual_col is not None:
        actual_total = float(agg[actual_col].sum())
        planned_total = float(agg[planned_col].sum())
        if planned_total:
            notes.append(
                f"Overall {actual_total / planned_total:.1%} of planned rides were observed."
            )

    return line_chart(
        daily,
        x="day",
        y="planned",
        series="series",
        title="Planned rides per day",
        subtitle=f"{req.date_from} → {req.date_to}",
        x_label="day",
        y_label="planned rides",
        notes=notes,
    )


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Tolerate small API column renames instead of hard-failing mid-demo."""
    for c in candidates:
        if c in df.columns:
            return c
    return None
