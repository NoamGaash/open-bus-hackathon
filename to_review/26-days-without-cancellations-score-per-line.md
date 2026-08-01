# Days-without-cancellations score per line

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What it answers

What fraction of the last 15 service days did this line run with **zero** cancellations? Deliberately harsh — a day with ≥1 cancellation scores 0, a fully operated day scores 1. It asks "did this line have a clean day", which is closer to how a passenger experiences a line than a 99.4% completion rate is.

![Days-without-cancellations score per line](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/days-with-no-cancellations.png)

*Days-without-cancellations score per line — screenshot of the hackathon dashboard card.*

## How it works

1. 15-day window ending **yesterday** (today's actuals are still landing, so a live
   day looks like a wall of cancellations).
2. Resolve the line to its `(line_ref, operator_ref)` pairs **for that window** —
   line 480 was 2 refs in Nov 2025 and 8 in Jul 2026, so a cached mapping silently
   under-counts.
3. Page `/rides_execution/list` per variant; a null `actual_start_time` is a
   cancellation.
4. Drop rows with no `planned_start_time` (unplanned rides — the mirror image of a
   cancellation).
5. Key on the departure itself and let **any** observed actual mark it operated, so
   a duplicated row with a null actual cannot invent a phantom cancellation.
6. Bucket by Israel service date using real `ZoneInfo`, never a fixed UTC+3 —
   Israel is UTC+2 in winter and a fixed offset spills a 16th day into the window.

## Where it could go in דאטאבוס

`/line-profile` — a per-line reliability headline.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

**A feed outage is indistinguishable from a bad day.** The method flags lines with zero actuals across the whole window as unscoreable, but cannot catch a line whose feed was 30% degraded, which reads as a genuinely bad score. A sanity floor was designed and not built. Partial rides count as fully operated — a bus that started and died mid-route has an `actual_start_time`. The binary daily metric also takes only 16 distinct values over 15 days, so lines cluster heavily.

## Suggested next steps

Add the feed-health sanity floor, then offer a **volume-weighted execution rate** alongside the binary score — the binary version disproportionately penalises high-frequency lines, where losing one of 100 daily runs is near-certain.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by Broundal.
· Method, evidence and caveats: [`algorithms/days-with-no-cancellations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/days-with-no-cancellations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26/tree/main/orion
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
