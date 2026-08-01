# Route divergence: rides that strayed from the planned route

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

For each sampled ride, how far it got from the nearest stop on its own line. A ride that spends time far from every planned stop either detoured, was diverted, or is mis-assigned to this route. Both the worst point and the typical (median) point are shown, because one bad fix is a GPS glitch while a whole ride out there is a real detour.

![Route divergence: rides that strayed from the planned route](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/route-divergence.png)

*Route divergence: rides that strayed from the planned route — screenshot of the hackathon dashboard card.*

## How it works

1. Resolve the line; take a 4-hour weekday morning window.
2. Planned stop coordinates from `/route_timetable/list`, deduplicated to distinct
   locations.
3. GPS pings from `/siri_vehicle_locations/list`, deduplicated.
4. **Haversine** great-circle distance from every ping to every stop; take the row
   minimum. (Euclidean degrees would understate east-west distance by ~15% at
   Israel's latitude.)
5. Per ride: worst, median, ping count. Rides with fewer than 5 pings are dropped.

## Where it could go in דאטאבוס

`/single-line-map`, as a diagnostic beside the route view.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Distance is to the nearest *stop*, not to the road the route follows, so a long stop-free stretch of an otherwise correct route reads as divergence — the threshold is a user option for exactly this reason. Express and intercity segments need a much higher threshold, which then blinds it to urban detours. **Measuring perpendicular distance to the GTFS shape polyline would fix this properly** and is the main thing standing between this and production.

## Suggested next steps

Switch to GTFS shape geometry, then detect *recurring* divergences across days — a cluster that repeats is a permanent diversion the GTFS should be updated to reflect, which is directly actionable feedback to the operator.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/route-divergence.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/route-divergence.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
