# Per-region SIRI coverage scorecard

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

Run the stop-level coverage analysis across all lines and publish coverage per operator, per region and per hour — a standing measure of how complete the real-time feed actually is.

## Why it matters

**This is the highest-leverage scale-up of the set.** Every other metric in דאטאבוס is a statement about the tracking record rather than about the road, and its trustworthiness depends entirely on coverage. Publishing coverage alongside the metrics is what lets a reader know when a number means something.

## Sketch

Add a distance ceiling to the nearest-stop match first — without one, coverage is an upper bound. The original full-network scan was estimated at 1–2 hours, so this is a scheduled batch job, not a live query. A two-stage screen (cheap ride-volume pass, then expensive per-stop matching) already exists in the source work.

## Depends on

Nothing blocking — but it pairs naturally with surfacing operators that have no feed at all.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
