# Segment reliability: where the timetable is optimistic

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

For one line, the median measured travel time of each stop-to-stop segment against the planned duration, with the ride-to-ride interquartile spread as a whisker. Where a bar overshoots its marker, the schedule is optimistic about that stretch.

![Segment reliability: where the timetable is optimistic](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/bus-segment-reliability.png)

*Segment reliability: where the timetable is optimistic — screenshot of the hackathon dashboard card.*

## How it works

1. Resolve `route_short_name` → `line_ref` + `operator_ref` via `/gtfs_routes/list`.
2. Pull planned times, stop coordinates and Hebrew stop names from `/route_timetable/list`.
3. Pull GPS from `/siri_vehicle_locations/list`.
4. **Derive arrival times** — the API serves none, so an arrival is the moment of
   the vehicle's closest approach to a stop's coordinates, interpolated between
   the two bracketing pings (±30 s).
5. Aggregate per segment: median, p25, p75, planned duration, and a `confidence`
   verdict (`implausible value` / `few samples` / `patchy coverage` /
   `coarse GPS timing` / `loose stop match`).

## Where it could go in דאטאבוס

`/line-profile` — it is a per-line diagnostic and that page already owns line identity. `/gaps_patterns` is the alternative if it should sit next to the other pattern views.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Derived arrivals are ±30 s, so consecutive city stops under a minute apart are mostly noise on a single ride — the aggregate is the point. The first segment is systematically least trustworthy because buses idle at the terminal. Fetch cost is ~1–2 minutes per line, so this needs caching or pre-aggregation to be interactive.

## Suggested next steps

Roll the per-segment ratio up into a **per-operator punctuality metric** (see the scale-up issue) so operators can be compared, not just lines. A per-corridor view would also identify infrastructure bottlenecks shared across lines.

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
