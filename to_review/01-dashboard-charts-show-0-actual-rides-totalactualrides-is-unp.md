# Dashboard charts show ~0% actual rides — `total_actual_rides` is unpopulated upstream

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## Symptom

`totalActualRides` is consumed in five places, all fed by `useGroupBy` →
`/gtfs_rides_agg/group_by` (`src/api/groupByService.ts`):

- `src/pages/dashboard/AllLineschart/AllLinesChart.tsx`
- `src/pages/dashboard/WorstLinesChart/WorstLinesChart.tsx`
- `src/pages/dashboard/ArrivalByTimeChart/DayTimeChart.tsx`
- `src/pages/operator/OperatorGaps.tsx`
- `src/pages/DataResearch/DataResearch.tsx`

That column is **0 for every row, network-wide**. The rendered result is not an
empty state — it is a confident chart showing that essentially no bus in Israel ran.

Here is the same defect reproduced on the hackathon dashboard, which uses the
same endpoint. Note the flat `Actual` series and the caption *"Overall 0.0% of
planned rides were observed"*:

![Planned vs actual rides — Actual is flat at zero](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/service-by-operator.png)

*Planned vs actual rides — Actual is flat at zero — screenshot of the hackathon dashboard card.*

## Evidence

*Re-verified against the live Stride API on 2026-08-01 immediately before filing; the reproduction below is the exact check that was run.*

```python
from openbus_hack import stride
for d in ["2026-07-01", "2026-06-15", "2026-04-01", "2025-11-01"]:
    rows = stride.get("/gtfs_rides_agg/group_by",
                      {"date_from": d, "date_to": d,
                       "group_by": "operator_ref,gtfs_route_date"})
    print(d, sum(r["total_planned_rides"] or 0 for r in rows),
             sum(r["total_actual_rides"] or 0 for r in rows))
```

| Date | Σ `total_planned_rides` | Σ `total_actual_rides` |
|---|---|---|
| 2026-07-01 | 121,420 | **0** |
| 2026-06-15 | 122,088 | **0** |
| 2026-04-01 | 53,260 | **0** |
| 2025-11-01 | 27,327 | **0** |

**This is not ingestion lag.** Control: line 2259 on 2026-07-29 reports
`total_actual_rides = 0` in the aggregate, while `/rides_execution/list` for the
same line and date returns real `actual_start_time` values and zero
cancellations. Actuals exist at ride level; they are not being rolled into the
aggregate.

`num_planned_rides` is populated and cross-checks well against the ride-level
endpoint, so the aggregate remains usable **as a planned-ride denominator**.

## Upstream

Root cause belongs to the API/ETL — hasadna/open-bus-stride-api#49 reports the
same thing for a single date (2025-09-17); the evidence above extends it to nine
months, network-wide, with a control. This issue tracks the **frontend symptom**.

Closely related: #24 (better indication of partial data in the UI) — that is the
general ask; this is one concrete, currently-live instance of it.

## Suggested interim mitigation

Until the upstream column is fixed, detect
`totalActualRides === 0 && totalPlannedRides > 0` across a whole response and show
a data-quality banner instead of plotting a zero series.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/service-by-operator.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-by-operator.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
