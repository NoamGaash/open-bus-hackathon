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

Clicking a line in the bunching dashboard draws its **Marey diagram** — every ride
as a path down the route, so bunching is visible as converging lines.

## Relationship to #1783

#1783 proposes a Marey diagram from the live-card analysis, which samples **up to
60 rides** over a ≤10-day window. This one is drawn from **138,716 rides**. Same
visual grammar, very different evidential weight — worth building once, with the
data source configurable.

## Why it matters

A Marey diagram is the only chart where bunching is *self-evident* rather than
inferred: two trajectories converging and then travelling together is the
phenomenon itself, not a statistic about it.

## Suggested next step

Overlay the cause attribution from #36 — colour each convergence by whether it was
terminal-born or en-route — so the diagram explains itself.

**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined to the GTFS timetable.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
