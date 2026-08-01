# "First SIRI ping" is not departure time — the feed reports a vehicle while it is still parked

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## The finding

On a sampled line, **~80% of rides' raw first pings** landed at almost exactly
**−30 or −5 minutes** before scheduled departure, with
`distance_from_journey_start == 0` and `velocity == 0` — the vehicle parked at the
origin stop, boarding.

Taking that first ping as "actual departure" made **~90% of matched rides look
early**. That is not early running; it is the operator feed's reporting lead time.

Two sharp clusters at fixed offsets, rather than a smooth distribution, is what
identifies this as a feed convention rather than a real phenomenon.

## The fix that worked

Use the first ping where the vehicle has actually started moving:

```python
dist = pd.to_numeric(pings["distance_from_journey_start"], errors="coerce").fillna(0)
vel  = pd.to_numeric(pings["velocity"], errors="coerce").fillna(0)
moving = pings[(dist > 0) | (vel > 0)]
departure = moving.groupby("siri_ride__id")["recorded_at_time"].min()
```

Fall back to the raw first ping only when the vehicle was never observed moving,
and flag those rides as unreliable.

## Why file this here

Filing as research/documentation rather than a bug — the feed is behaving as
operators report it. But **any consumer computing departure punctuality from
first-ping is currently measuring the wrong thing**, and nothing in the docs says
so. This is the most reusable single result from the hackathon.

Worth checking whether any דאטאבוס metric derives a departure time this way.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/service-violations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-violations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
