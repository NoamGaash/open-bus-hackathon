# Planned route vs. GPS-measured route, on a map

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

The planned route dashed at its timetable coordinates, against the *measured* route solid — where each stop sits at a distance-weighted average of the real GPS pings that matched it, sized by how many did. Both coloured by minutes since departure, so a colour mismatch at the same place is the bus running late there.

![Planned route vs. GPS-measured route, on a map](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/schedule-adherence-map.png)

*Planned route vs. GPS-measured route, on a map — screenshot of the hackathon dashboard card.*

## How it works

1. Same multi-day fetch and stop-signature filter as the stringline card.
2. Pool every matched ping per stop across all matched days.
3. Average positions weighted by `1 / (distance + ε)`, so pings that passed
   closest to a stop dominate its position.
4. Render planned and measured as two GeoJSON layers on Leaflet.

## Where it could go in דאטאבוס

`/single-line-map` — that page already owns the planned-route-on-a-map view; this adds the measured counterpart.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

The measured route can bow away from the planned one, but the weighted average rests on nearest-stop matching, which does mis-assign — a bow could be a real detour or an assignment artifact, and this card cannot distinguish them. Duplicate pings bias the weighting and must be dropped first.

## Suggested next steps

Compare measured stop positions against GTFS coordinates systematically to build a **stop-location quality report** — persistent offsets are likely stale GTFS entries or relocated bays worth reporting to the ministry.

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
