# `stride-db:` null `start_time` on a minority of `/gtfs_rides/list` rows

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What happens

A real minority of `/gtfs_rides/list` rows come back with `start_time` (and
`end_time`) null. This looks like a GTFS source gap rather than a SIRI matching
problem.

## Why it matters

A ride with no scheduled time cannot be timed **or** ghost-checked. Left in a
planned-vs-actual join it falls through as a spurious unmatched "cancellation",
inflating any non-execution rate computed from it.

The hackathon code drops them up front and reports the count, rather than letting
them become phantom cancellations:

```python
planned = planned.dropna(subset=["start_time"])
```

## What is not known

Only per-query counts were recorded, never a network-wide rate. **Worth
quantifying** — if it is a fraction of a percent it is a footnote; if it is
several percent it materially affects every cancellation statistic.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/service-violations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-violations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
