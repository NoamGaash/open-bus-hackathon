# Aggregate segment reliability into a per-operator punctuality metric

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What

The segment-reliability analysis produces a median actual/planned duration ratio per stop-to-stop segment for one line. Roll that up: per line → per operator → per region, so operators can be compared on how realistic their timetables are.

## Why it matters

Every reliability view in the hackathon is single-line. A regulator, a journalist or a rider choosing between operators needs a **comparable** number. This is the step that turns a demo into a metric.

## Sketch

Weight segments by ride volume so a rarely-run segment does not dominate. Report the sample size and the confidence mix alongside the headline, since some segments rest on very few rides. Exclude operators outside the SIRI feed entirely rather than scoring them badly.

## Depends on

Derived arrival times, which currently cost ~1–2 minutes per line to compute — see the pre-aggregation issue in this milestone.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
