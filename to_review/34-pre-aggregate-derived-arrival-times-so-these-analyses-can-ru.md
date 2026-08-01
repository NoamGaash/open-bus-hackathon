# Pre-aggregate derived arrival times so these analyses can run interactively

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

The Stride API serves no actual stop arrival times, so every analysis derives them from raw GPS by interpolating the vehicle's closest approach to each stop (±30 s). That derivation costs ~1–2 minutes per line and is repeated by every consumer independently.

## Why it matters

It is the single shared bottleneck under most of this milestone. Computing it once in the ETL and storing it would make segment reliability, Marey diagrams, headway-decay CV and bunching all cheap enough to be interactive — and would give every consumer the *same* numbers instead of each reinventing the interpolation.

## Sketch

Store per (ride, stop): derived arrival time, match distance, and the gap between the bracketing pings. Those last two are what let consumers judge whether to trust a value — the existing work uses 150 m for a loose match and 300 m to drop a stop entirely, plus a 2-minute ping gap as a coarse-timing warning. Handle the known artifacts explicitly: terminal dwell (the origin resolves to departure, not closest approach) and coincident junction stops (needs a forward-constrained monotonic search).

## Depends on

Nothing — this is foundational, and arguably should be built before the other scale-ups rather than after.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
