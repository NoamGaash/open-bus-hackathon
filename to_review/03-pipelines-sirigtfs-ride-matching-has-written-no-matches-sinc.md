# `pipelines:` SIRI→GTFS ride-matching has written no matches since 2024-10

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

Two related symptoms, observed independently by two hackathon projects.

**1. The ride link.** `siri_ride.gtfs_ride_id` and its three siblings
(`route_gtfs_ride_id`, `scheduled_time_gtfs_ride_id`, `journey_gtfs_ride_id`) stop
being populated together. Reported as healthy through 2024-08, degrading 2024-09,
effectively zero 2024-10 → 2026-07. The raw feed never stopped — roughly 2.9–3.1M
`siri_ride` rows per month are still created.

**2. The enrichment.** `siri_ride.first_vehicle_location_id` reported null for
100% of rides across 18 consecutive months (2024-12 → 2026-05, ~49.4M rides), with
`duration_minutes` tracking the same pattern.

A hackathon analysis independently found these columns *"inconsistently NULL —
present for some days, absent for others, for identical, genuinely-tracked
rides"*, and had to derive planned-vs-actual from raw GPS pings instead.

## Interpretation risk worth flagging separately

`first_vehicle_location_id` **looks** like it means "this vehicle never reported
its position", and it is easy to build a per-operator transmission metric on it.
It does not mean that — it encodes **whether the enrichment job has processed that
day**. It is a processing-state flag, not a property of the bus.

## Confidence

The 18-month and 21-month figures come from a separate hackathon project
(BusAnalysis by lihay7) whose repository is currently private, so **the census
numbers cannot be independently checked from this issue alone.** What *was*
reproduced in the shared hackathon repo is the qualitative finding: these columns
are unreliable enough that every planned-vs-actual analysis had to bypass them.

Treat the precise dates and percentages as **needing confirmation against the
database** before anyone acts on them.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by lihay7.
· Method, evidence and caveats: [`algorithms/service-violations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-violations.md)
· Original work: https://github.com/lihay7/BusAnalysis *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
