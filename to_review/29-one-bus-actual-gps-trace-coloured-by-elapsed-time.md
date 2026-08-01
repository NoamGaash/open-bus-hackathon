# One bus, actual GPS trace, coloured by elapsed time

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

A single real ride's raw GPS trail on a map, coloured by elapsed time. It makes no analytical claim — its job is **ground truth for the eye**. Every other card turns pings into statistics; this shows what the pings actually look like, including the reporting interval, the dropouts, and the clustering when a bus sits still.

![One bus, actual GPS trace, coloured by elapsed time](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/gps-trace-map.png)

*One bus, actual GPS trace, coloured by elapsed time — screenshot of the hackathon dashboard card.*

## How it works

1. Resolve the line to a `line_ref` **before** fetching (the `route_short_name`
   filter is silently ignored by this endpoint — see the separate bug in this
   milestone).
2. Fetch a 4-hour weekday morning window; deduplicate pings.
3. Pick the ride with the most pings.
4. Draw one coloured segment per consecutive pair, plus a point per ping with its
   timestamp, along a viridis gradient.

## Where it could go in דאטאבוס

`/vehicle` — that page is already about a single vehicle's journey.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

One ride, one morning, **chosen for being the best-tracked** — which for a card about feed quality shows the feed at its best. Nothing generalises from it. The colour gradient is normalised per ride, so two loads are not comparable.

## Suggested next steps

Offer the **median or worst-tracked** ride as well as the best — that is far more informative about what the data usually looks like, and costs nothing to add.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by yuvalko1.
· Method, evidence and caveats: [`algorithms/gps-trace-map.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/gps-trace-map.md)
· Original work: https://github.com/yuvalko1/talpiot-hackathon-public-transportation *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
