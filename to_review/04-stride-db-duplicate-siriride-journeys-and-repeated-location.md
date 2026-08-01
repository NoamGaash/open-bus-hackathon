# `stride-db:` duplicate `siri_ride` journeys and repeated location rows

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What happens

**Ride level.** The same physical journey is stored more than once. Reported at
3.93% of rides sitting in a duplicated `(siri_route_id, journey_ref, service day)`
group and 2.56% of all rows being surplus duplicates, over a full census of
~116.3M rows — 66× skewed across operators, and roughly quadrupling from 2023 to
2026. Attributed to `scheduled_start_time` drift: when a journey's scheduled start
drifts, a **new** row is written rather than the existing one updated.

**The same shape appears in GTFS.** On 2026-07-26 one line returned 259
`/rides_execution/list` rows for 127 distinct `planned_start_time`s (some ×4)
under 255 distinct `gtfs_ride_id`s — one physical departure emitted under several
ride ids. Any naive count of planned rides double-counts, and a duplicated row
with a null actual becomes a phantom cancellation.

**Location level.** Overlapping SIRI snapshots repeat the same physical
observation — same `siri_ride__id`, same `recorded_at_time`, same lat/lon — at
roughly 10% of rows. Harmless for `min()`/`max()` aggregations; **not** harmless
for anything weighted or counted. One hackathon analysis computes a
distance-weighted average position, where a duplicated ping carries its weight
twice and drags the result.

## Evidence of the workaround spreading

Every analysis in the hackathon repo now dedups on
`(siri_ride__id, recorded_at_time, lat, lon)` as a matter of course:

```python
pings = pings.drop_duplicates(
    subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])
```

That is a workaround every consumer is independently reinventing, which is the
strongest argument for fixing it at the source.

## Confidence

The ride-level census figures come from a hackathon project (BusAnalysis by
lihay7) whose repository is currently private — **treat them as needing
confirmation.** The GTFS duplicate-departure observation and the ~10% duplicate
ping rate were reproduced in the shared hackathon repo.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by lihay7.
· Method, evidence and caveats: [`algorithms/days-with-no-cancellations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/days-with-no-cancellations.md)
· Original work: https://github.com/lihay7/BusAnalysis *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
