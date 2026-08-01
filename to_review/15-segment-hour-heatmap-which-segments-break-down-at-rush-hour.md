# Segment × hour heatmap: which segments break down at rush hour

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

A segment × departure-hour matrix coloured by the actual/planned duration ratio. 1.00 is exactly on schedule; above that the segment ran longer than the timetable allows. It localises congestion in both space and time simultaneously.

![Segment × hour heatmap: which segments break down at rush hour](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/bus-hourly-heatmap.png)

*Segment × hour heatmap: which segments break down at rush hour — screenshot of the hackathon dashboard card.*

## How it works

1. Same shared fetch.
2. `segment_hour_matrix(ride_segments, min_samples)` → aligned ratio and count matrices.
3. Colour diverging around a centre of 1.0.
4. **Three distinct cell appearances**, deliberately: solid = enough rides,
   hatched = measured but under `min_samples`, blank = no usable ride at all.
   "One ride" and "no data" must not look alike.

## Where it could go in דאטאבוס

`/gaps_patterns` — it is a pattern view by construction, and that page already frames time-of-day analysis.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Cells on low-frequency lines rest on very few rides; hatching flags this but the ≤10-day fetch window is what puts them there. Ratios outside 0.25–4.0 are treated as artifacts rather than traffic.

## Suggested next steps

Aggregate across all lines sharing a corridor to find **infrastructure** bottlenecks rather than line-specific ones — a junction that slows six lines at 08:00 is a road problem, not a scheduling problem.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by noamf2001.
· Method, evidence and caveats: [`algorithms/bus-arrival-reliability.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-arrival-reliability.md)
· Original work: https://github.com/noamf2001/PublicTransportHackathon *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
