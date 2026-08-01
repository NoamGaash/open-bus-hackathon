# Bus bunching: headway regularity against scheduled spacing

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

The classic frequent-service failure: a delayed bus picks up extra passengers at every stop, falls further behind, and the bus behind closes the gap — until two arrive nose-to-tail followed by a long empty gap. **The signal is not lateness, it is unevenness.** A line reliably 6 minutes late is fine to wait for; a 10-minute headway that is really 2-then-18 is not.

![Bus bunching: headway regularity against scheduled spacing](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/bus-bunching.png)

*Bus bunching: headway regularity against scheduled spacing — screenshot of the hackathon dashboard card.*

## How it works

1. Resolve one line + operator; sample weekdays only (Fri/Sat service is thin by
   design and reads as false bunching).
2. Reduce each ride to its scheduled time and its first GPS ping.
3. Take consecutive gaps within each day for both scheduled and actual.
4. Target headway = median of scheduled gaps. Classify each actual gap:
   **bunched** < 0.25×, **gapped** > 1.75×, normal in between.
5. Report the coefficient of variation; above ~0.5 is the usual bunching sign.

## Where it could go in דאטאבוס

`/gaps_patterns` — bunching is a pattern about service regularity and belongs with the other frequency views.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Uses the **raw first ping** as the departure proxy, which the sibling analysis showed is a feed artifact (see the first-ping issue in this milestone). A constant reporting lead cancels out of a *difference*, but a bimodal one (−30 or −5 min) fabricates swings large enough to move rides between buckets — worth fixing before productionising. The single pooled target headway also flags normal off-peak service as "gapped"; bucketing against each hour's own scheduled headway would fix that. Headways are measured at the origin, where bunching has not developed yet.

## Suggested next steps

Measure headway CV **per stop along the route** rather than only at the origin — that is where bunching actually appears. Then aggregate into a per-line and per-region regularity score so high-frequency corridors can be ranked.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
