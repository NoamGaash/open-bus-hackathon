# Aggregate bunching CV into a per-line and per-region regularity score

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

The bunching analysis computes a coefficient of variation for one line over a couple of days. Compute it continuously across all high-frequency lines and publish a regularity score per line, per corridor and per region.

## Why it matters

Headway regularity is the standard international metric for frequent transit and Israel currently publishes nothing equivalent. It is also the metric that best matches passenger experience on lines where nobody consults a timetable.

## Sketch

Only apply it to lines above a frequency threshold — CV is meaningless on a line running twice a day. Bucket against each hour's own scheduled headway rather than a single pooled median. Measure at several points along the route, not just the origin.

## Depends on

Fixing the first-ping departure proxy (see the first-ping issue in this milestone), otherwise a bimodal reporting lead fabricates variance.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
