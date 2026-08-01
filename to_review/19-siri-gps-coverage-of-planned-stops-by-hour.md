# SIRI GPS coverage of planned stops, by hour

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

For one line and direction, what fraction of planned GTFS stops actually got a matching real-time GPS ping, broken down by hour of day. **This is a data-quality measure wearing a service-quality costume** — it measures the feed, not the buses, and every other planned-vs-actual view depends on the answer.

![SIRI GPS coverage of planned stops, by hour](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/siri-coverage.png)

*SIRI GPS coverage of planned stops, by hour — screenshot of the hackathon dashboard card.*

## How it works

1. Resolve one line + direction; sample up to 3 days.
2. Per day, fetch the planned timetable and the actual GPS pings.
3. Per planned ride, match pings to stops: **nearest stop by distance AND within
   20 minutes** of that stop's planned elapsed time. Without the time gate, routes
   that loop back near their own path match a later ping to an early stop.
4. Aggregate by the ride's scheduled hour: `Σ covered / Σ planned`.

## Where it could go in דאטאבוס

`/data-research` — it is a meta-view about data completeness rather than about service, and that page is already the home for that kind of question.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

**The nearest-stop match has no distance ceiling** — a ping 4 km from every stop still "covers" the least-far one if it falls inside the time window, so coverage here is an upper bound. Capped at 3 days against the source pipeline's ~20. Hours with under 3 rides are flagged low-confidence.

## Suggested next steps

Add a distance ceiling (the sibling analysis uses 150 m / 300 m thresholds), then build a **per-operator and per-region coverage scorecard** — this is the single most valuable scale-up here, because it tells every other metric where it can and cannot be trusted.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by yuvalko1.
· Method, evidence and caveats: [`algorithms/siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
· Original work: https://github.com/yuvalko1/talpiot-hackathon-public-transportation *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
