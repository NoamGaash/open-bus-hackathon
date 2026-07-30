"""Worked example: planned vs actual service, by day.

This file exists to be copied. It hits the real Stride API, handles the empty
case, returns two different result kinds, and is deliberately short — if your
analysis is much longer than this, consider moving the exploration into
``workspace/<you>/`` and keeping only the final computation here.
"""

from __future__ import annotations

import pandas as pd

from openbus_hack import AnalysisRequest, analysis, line_chart, metrics, stride


@analysis(
    name="service-by-operator",
    title="Planned vs actual rides",
    description=(
        "Daily count of rides planned (GTFS) against how many were actually "
        "observed (SIRI), for the selected operator(s). The gap is unrun service."
    ),
    author="example",
    tags=["service", "reliability", "operators"],
    # This one aggregates across whatever operators are selected, so a line
    # filter would be misleading.
    inputs=["operators", "dates"],
    draft=False,
)
def run(req: AnalysisRequest):
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

    daily = (
        agg.groupby("gtfs_route_date", as_index=False)[planned_col]
        .sum()
        .rename(columns={planned_col: "Planned", "gtfs_route_date": "day"})
    )
    daily["day"] = pd.to_datetime(daily["day"]).dt.date.astype(str)

    if actual_col is not None:
        daily["Actual"] = (
            agg.groupby("gtfs_route_date")[actual_col].sum().to_numpy()
        )
        actual_total, planned_total = float(agg[actual_col].sum()), float(agg[planned_col].sum())
        if planned_total:
            notes.append(
                f"Overall {actual_total / planned_total:.1%} of planned rides were observed."
            )
        long = daily.melt(id_vars="day", value_vars=["Planned", "Actual"],
                          var_name="series", value_name="rides")
    else:
        notes.append("No actual-rides column returned by /gtfs_rides_agg — showing planned only.")
        long = daily.rename(columns={"Planned": "rides"}).assign(series="Planned")

    long = long.sort_values("day")

    return line_chart(
        long,
        x="day",
        y="rides",
        series="series",
        title="Planned vs actual rides per day",
        subtitle=f"{req.date_from} → {req.date_to}",
        x_label="day",
        y_label="rides",
        notes=notes,
    )


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Tolerate small API column renames instead of hard-failing mid-demo."""
    for c in candidates:
        if c in df.columns:
            return c
    return None
