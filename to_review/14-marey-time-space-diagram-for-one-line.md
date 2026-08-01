# Marey time-space diagram for one line

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

One trajectory per sampled ride, plotted against the schedule. Steep = moving, flat = stuck, and the width of the fan is the route's unreliability. It makes *where* a line loses time legible at a glance in a way no bar chart does.

![Marey time-space diagram for one line](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/bus-marey-diagram.png)

*Marey time-space diagram for one line — screenshot of the hackathon dashboard card.*

## How it works

1. Same shared fetch as the segment-reliability card.
2. `elapsed_profiles(stop_events)` → per-ride (elapsed minutes, stop sequence) traces.
3. `stop_coverage(stop_events)` → the share of rides where GPS resolved each stop.
4. Draw up to 60 ride trajectories (past that the fan becomes a solid block) plus
   the planned profile, bold.
5. Stops the GPS rarely resolved get **dimmed, italic axis labels** — trajectories
   through them are interpolation more than measurement.

## Where it could go in דאטאבוס

`/single-line-map` as a companion view — the map answers *where the bus is*, this answers *when it got there*, and they read well side by side.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Capped at 60 rides for legibility. Stop labels are long in Hebrew, which drove the stops-on-y-axis default. Same ±30 s derived-arrival limit as the segment card.

## Suggested next steps

Add a date-range comparator — the same line's fan before and after a timetable change is the clearest possible evidence that a retiming worked or did not.

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
