# Ghost rides, early and late departures per line

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

Every planned ride in a line's schedule, classified as a ghost (no GPS ever matched), an early departure, a late departure, or on-time — the three failure modes the Ministry of Transport can fine for.

![Ghost rides, early and late departures per line](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/service-violations.png)

*Ghost rides, early and late departures per line — screenshot of the hackathon dashboard card.*

## How it works

1. Planned rides from `/gtfs_rides/list` for the whole window in one paged call.
2. Drop rows with a null `start_time` — they cannot be timed or ghost-checked.
3. GPS from `/siri_vehicle_locations/list`, deduplicated.
4. **Departure proxy** = first ping where the vehicle is actually moving
   (`distance_from_journey_start > 0` or `velocity > 0`), *not* the raw first ping.
5. Join plan to actual on exact scheduled-time equality; unmatched = ghost.
6. Classify against user-editable early/late thresholds.

## Where it could go in דאטאבוס

`/gaps` — that page already owns the missing-service question.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

**The thresholds are illustrative, not regulatory.** 1 min early / 5 min late reflect commonly cited practice, not the ministry's actual fine schedule, which was not available. The card is honest about this in its notes, but the framing invites over-reading — sourcing the real tolerances is the highest-value follow-up. **Ghost rides are the weakest category**: a bus that ran untracked is indistinguishable from one that was cancelled, so these are candidates for investigation, not confirmed non-arrivals. Scope is one line.

## Suggested next steps

Source the real regulatory tolerances, then compute a violation rate **per operator per month** — the enforcement basis is already electronic, so this is the analysis with the most direct policy consequence of anything in the hackathon.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/service-violations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-violations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
