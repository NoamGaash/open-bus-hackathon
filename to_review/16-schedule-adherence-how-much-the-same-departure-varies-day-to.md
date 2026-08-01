# Schedule adherence: how much the same departure varies day to day

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

Take one departure — same line, same time of day — and watch it across many days. Each faint line is one day; the bold dashed line is the GTFS plan and the bold solid line is the cross-day average. The width of the fan is how unreliable that specific departure is.

![Schedule adherence: how much the same departure varies day to day](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/schedule-adherence-average.png)

*Schedule adherence: how much the same departure varies day to day — screenshot of the hackathon dashboard card.*

## How it works

1. Anchor on a real departure time, then scan back day by day (default 21).
2. **Canonical stop signature filter** — a day counts only if its stop sequence
   matches the reference day's exactly. One `line_ref` serves several stop
   patterns, and averaging across them silently blends different journeys.
3. Match pings to stops by nearest stop, **gated to ±20 min** of that stop's
   planned elapsed time (distance alone mis-assigns on routes that loop back).
4. Two guards on the average: a stop must be measured on at least half the matched
   days, and the result is clamped monotonic — a bus cannot reach a later stop
   earlier, so residual dips are mis-assignment, not a reversing bus.

## Where it could go in דאטאבוס

`/line-profile` — it is inherently a single-line, single-departure view.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Skipped days are reported by category (`no_plan` / `route_mismatch` / `no_actual`) so "different journey" stays distinct from "missing data". The source notebook required 20 matched days before averaging; the live card usually has fewer. Distances are currently Euclidean in raw lon/lat degrees, which understates east-west distance by ~15% at Israel's latitude — worth switching to haversine.

## Suggested next steps

Turn the fan width into a **single per-departure reliability number**, then rank a line's departures by it. "Your 07:40 is reliable, your 08:10 is a lottery" is directly actionable for both riders and schedulers.

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
