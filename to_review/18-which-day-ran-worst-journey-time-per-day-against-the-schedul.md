# Which day ran worst — journey time per day against the schedule

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

Total journey time for each matched day against the schedule. The stringline shows *where* time is lost; this shows *which days* lost it, so a single bad day is not hidden inside a multi-day average.

![Which day ran worst — journey time per day against the schedule](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/schedule-adherence-by-day.png)

*Which day ran worst — journey time per day against the schedule — screenshot of the hackathon dashboard card.*

## How it works

1. Same fetch as the other two schedule-adherence cards.
2. Per day, take the elapsed time at the **last stop its GPS actually resolved** —
   not the route's last stop.
3. Compare against the plan **truncated to that same stop**, so a day whose GPS
   died halfway is not scored as an impossibly quick trip.

## Where it could go in דאטאבוס

`/line-profile`, alongside the stringline.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Only as good as the day-matching upstream of it; days running a different stop pattern are excluded entirely rather than shown as outliers.

## Suggested next steps

Join against weather, holidays and known roadworks to explain *why* a day was bad. A per-day series across a whole operator would also expose systemic bad days (strikes, fleet shortages) versus line-specific ones.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by yuvalko1.
· Method, evidence and caveats: [`algorithms/schedule-adherence.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/schedule-adherence.md)
· Original work: https://github.com/yuvalko1/talpiot-hackathon-public-transportation *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
