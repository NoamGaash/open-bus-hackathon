# Poisson headway decay: CV along the route against the CV=1 benchmark

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

Does bus spacing decay into a *random* process as buses travel downstream? Buses leave the terminal on a schedule, so headways start near-deterministic; traffic and boarding progressively randomise them. A memoryless (exponential) interarrival distribution has **CV = 1** — so as CV approaches 1, the timetable has stopped meaning anything for a waiting passenger.

![Poisson headway decay: CV along the route against the CV=1 benchmark](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/poisson-arrival-regularity.png)

*Poisson headway decay: CV along the route against the CV=1 benchmark — screenshot of the hackathon dashboard card.*

## How it works

1. Reuse the derived per-stop arrival times from the segment analysis.
2. Group by `stop_sequence`; **within each service date**, sort arrivals and take
   consecutive gaps (so no overnight gap enters the sample).
3. Where a stop has ≥3 gaps, compute `CV = std(ddof=1) / mean`.
4. Plot CV against stop index with a reference line at CV = 1.

## Where it could go in דאטאבוס

`/data-research`, or `/gaps_patterns` if it should sit with the other reliability views.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

**The screenshot above does not show the clean monotonic rise the theory predicts** — on this line CV starts near 0.87 and oscillates around 1.0 rather than climbing steadily. That is an honest result and should not be smoothed over. Arrivals are GPS-derived at ±30 s, and that measurement noise inflates CV *toward* the benchmark, which is the direction that would create a false positive; the measurement-error floor should be subtracted or at least stated. A CV from 3 observations is nearly meaningless and is currently drawn with the same weight as one from 300.

## Suggested next steps

Establish the measurement-error floor first, then compare CV curves **across lines** — a line whose CV is already at 1.0 by stop 5 has a different problem from one that reaches it at stop 40, and the intervention differs accordingly.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by yuvalko1.
· Method, evidence and caveats: [`algorithms/poisson-arrival-regularity.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/poisson-arrival-regularity.md)
· Original work: https://github.com/yuvalko1/talpiot-hackathon-public-transportation *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
