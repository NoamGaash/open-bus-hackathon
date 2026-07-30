"""Which bus lines carry unusually many/few passengers for their peer group, by hour.

Ported from a teammate's ``busline_usage_anomaly.ipynb`` (vendored at the repo
root, so the original sits in git next to this port).

The idea worth keeping: raw passenger counts can't be compared across lines — a
dense-city line and a suburban one carry wildly different volumes for reasons
that have nothing to do with how well either is running. So lines are compared
only against *peers*, and only within the same hour of day, as a z-score. A low
score then means "carries fewer riders than comparable lines at the same time of
day", not merely "is a small line".

Two deliberate changes from the notebook, both because the original couldn't
work as written:

1. **Peer grouping.** The notebook derived a "metro score" (exponential decay
   from the nearest of Tel Aviv / Jerusalem / Haifa) from station coordinates.
   But it read that from data.gov.il resource 3ad014c3 (station passengers),
   which has **no line column at all** — its ``get_station_passengers(office_line_id)``
   silently ignores its argument and refetches the same global station table for
   every line, so every line ended up scored off identical rows. Rather than
   reproduce that, this uses the ministry's own ``cluster_nm`` ("אשכול") —
   a real geographic/service grouping shipped in the same per-line dataset,
   which is what the metro score was proxying for anyway, and needs no join.

2. **Hours.** The notebook mapped 7 coarse Hebrew time bands to an hour. The
   per-line resource used here carries a true ``hour_a`` (0-23), so no mapping
   is needed and the resolution is better.

Data source is data.gov.il's ticketing/validation open data — a different source
from the Stride SIRI/GTFS data every other card here uses.
"""

from __future__ import annotations

import httpx
import pandas as pd

from openbus_hack import AnalysisRequest, OptionSpec, analysis, bar_chart, metrics
from openbus_hack.diskcache import cached

_CREDIT = "Ported from a teammate's busline_usage_anomaly.ipynb (vendored at the repo root)."

DATA_GOV_URL = "https://data.gov.il/api/3/action/datastore_search"
# Per-line, per-direction, per-hour boardings, with operator + cluster names.
LINE_HOURLY_RESOURCE = "ef42a264-9da2-41ad-9120-822064fb5433"

DAY_COLS = [f"D{i}" for i in range(1, 32)]
# Rail rows share this dataset but aren't bus lines and dwarf them in volume;
# the ministry marks them with a sentinel line id.
SENTINEL_LINE_ID = -1
UNDEFINED_CLUSTER = "לא מוגדר"


def _line_hourly(sample_rows: int) -> pd.DataFrame:
    """One row per (line, direction, hour) with its cluster and mean daily riders."""

    def compute() -> pd.DataFrame:
        rows: list[dict] = []
        offset, page = 0, 5000
        while offset < sample_rows:
            r = httpx.get(
                DATA_GOV_URL,
                params={"resource_id": LINE_HOURLY_RESOURCE,
                        "limit": min(page, sample_rows - offset), "offset": offset},
                timeout=60.0,
            )
            r.raise_for_status()
            batch = r.json().get("result", {}).get("records", [])
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < page:
                break
            offset += page

        df = pd.DataFrame(rows)
        if df.empty or "OfficeLineId" not in df.columns:
            return pd.DataFrame()

        present_days = [c for c in DAY_COLS if c in df.columns]
        if not present_days:
            return pd.DataFrame()
        # Each row is one month; the D1..D31 columns are that month's daily
        # counts, with nulls for days the line didn't run (or the month is short).
        df["riders"] = df[present_days].apply(pd.to_numeric, errors="coerce").mean(axis=1)

        df["hour"] = pd.to_numeric(df.get("hour_a"), errors="coerce")
        df["line"] = df["OfficeLineId"].astype(str)
        df["cluster"] = df.get("cluster_nm", pd.Series(dtype=str)).fillna(UNDEFINED_CLUSTER)
        df["operator"] = df.get("operator_nm", pd.Series(dtype=str)).fillna("?")

        df = df[(df["OfficeLineId"] != SENTINEL_LINE_ID) & (df["cluster"] != UNDEFINED_CLUSTER)]
        df = df.dropna(subset=["riders", "hour"])
        if df.empty:
            return pd.DataFrame()
        df["hour"] = df["hour"].astype(int)

        # Collapse direction/month duplicates into one figure per line-hour.
        return (df.groupby(["line", "operator", "cluster", "hour"], as_index=False)["riders"]
                .mean())

    return cached("data_gov_line_hourly", ("v2", sample_rows), compute)


def _z_scores(df: pd.DataFrame) -> pd.DataFrame:
    """z-score each (line, hour) against its cluster peers in the same hour."""
    peers = (df.groupby(["cluster", "hour"])["riders"]
             .agg(peer_mean="mean", peer_std="std", peer_count="count")
             .reset_index())
    out = df.merge(peers, on=["cluster", "hour"], how="left")
    # A peer group of one has no spread; the epsilon keeps the division finite
    # and lands its z at ~0, which is the honest reading for "nothing to compare".
    out["peer_std"] = out["peer_std"].fillna(0.0).replace(0, 1e-5)
    out["z"] = ((out["riders"] - out["peer_mean"]) / out["peer_std"]).round(2)
    return out


@analysis(
    name="busline-usage-anomaly",
    title="Over- and under-used lines vs. their peers",
    description="Average daily boardings per line and hour, scored against other "
                "lines in the same ministry cluster at the same hour. A negative "
                "score means fewer riders than comparable lines — not simply a "
                "small line.",
    author="team (busline_usage_anomaly.ipynb)",
    tags=["ridership", "anomaly", "data.gov.il", "interactive"],
    # Ticketing data keys on the ministry's own line ids, which don't line up
    # with the SIRI/GTFS line + operator + date pickers in the global filter bar.
    inputs=[],
    options=[
        OptionSpec(
            key="sample_rows",
            label="Ticketing rows to sample",
            type="number",
            default=15000,
            help="data.gov.il pages this dataset 5000 rows at a time; more rows "
                 "means more lines compared, but a slower first run.",
        ),
        OptionSpec(
            key="min_peers",
            label="Minimum peer-group size",
            type="number",
            default=3,
            help="Line-hours whose cluster has fewer lines than this are dropped — "
                 "a z-score against one other line is noise.",
        ),
        OptionSpec(
            key="top_n",
            label="Lines to show",
            type="number",
            default=14,
            help="The most extreme line-hours by absolute z-score.",
        ),
    ],
)
def run(req: AnalysisRequest):
    sample_rows = int(req.opt("sample_rows", 15000) or 15000)
    min_peers = int(req.opt("min_peers", 3) or 3)
    top_n = int(req.opt("top_n", 14) or 14)

    base = _line_hourly(sample_rows)
    if base.empty:
        return metrics(
            ("No data", 0),
            notes=["data.gov.il returned no usable rows — the resource id or its "
                   "column names may have changed.", _CREDIT],
        )

    scored = _z_scores(base)
    usable = scored[scored["peer_count"] >= min_peers]
    if usable.empty:
        return metrics(
            ("Lines sampled", int(scored["line"].nunique())),
            notes=[f"No cluster reached {min_peers} lines in the sampled rows — "
                   "lower the minimum peer-group size or sample more rows.", _CREDIT],
        )

    # One row per line: its single most extreme hour.
    extreme = (usable.reindex(usable["z"].abs().sort_values(ascending=False).index)
               .drop_duplicates(subset=["line"])
               .head(top_n)
               .sort_values("z"))
    extreme["label"] = [f"{r.line} · {r.hour:02d}:00 · {r.operator}" for r in extreme.itertuples()]

    n_under = int((usable["z"] <= -1.5).sum())
    n_over = int((usable["z"] >= 1.5).sum())
    return bar_chart(
        extreme, x="label", y="z", horizontal=True,
        title="Over- and under-used lines vs. their peers",
        subtitle=(f"{usable['line'].nunique()} lines across "
                  f"{usable['cluster'].nunique()} ministry clusters · "
                  f"{len(base):,} line-hours sampled"),
        x_label="line · hour · operator", y_label="z-score vs cluster peers",
        notes=[
            "Each bar is one line's most extreme hour. Negative = fewer boardings "
            "than other lines in the same ministry cluster at that hour; positive "
            "= more.",
            f"Across every line-hour scored: {n_under} under-performing (z ≤ -1.5) "
            f"and {n_over} over-performing (z ≥ +1.5).",
            f"Clusters with fewer than {min_peers} lines are dropped — a z-score "
            "against one other line is noise, not a signal.",
            "Counts are data.gov.il ticketing validations, so they undercount "
            "anyone not validating; and this is a sample of the dataset, not the "
            "whole country.",
            "Peer groups are the ministry's own clusters, replacing the notebook's "
            "distance-to-city-centre score — see this module's docstring for why.",
            _CREDIT,
        ],
    )
