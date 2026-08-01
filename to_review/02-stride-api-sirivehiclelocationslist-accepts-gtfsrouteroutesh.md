# `stride-api:` `/siri_vehicle_locations/list` accepts `gtfs_route__route_short_name` and silently ignores it

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

Passing `gtfs_route__route_short_name` to `/siri_vehicle_locations/list` does not
filter. It does not error, does not warn, and does not return an empty set — it
returns **every ping in the time window, from every line in the country**, which
the caller then treats as belonging to their line.

## Evidence

*Re-verified against the live Stride API on 2026-08-01 immediately before filing; the reproduction below is the exact check that was run.*

```python
base = {"recorded_at_time_from": "2026-07-28T08:00+03:00",
        "recorded_at_time_to":   "2026-07-28T09:00+03:00", "limit": 400}
unfiltered = stride.get("/siri_vehicle_locations/list", base)
filtered   = stride.get("/siri_vehicle_locations/list",
                        {**base, "gtfs_route__route_short_name": "23"})
```

| Query | rows | distinct `siri_route__line_ref` |
|---|---|---|
| unfiltered | 400 | **202** |
| with `gtfs_route__route_short_name=23` | 400 | **202** |

Byte-identical result sets. The parameter has no effect.

## Why it matters

How it was originally caught: an off-route analysis reported buses **50 km from
their route on 97.7% of pings**. The buses were fine — the pings belonged to other
lines. That was only obvious because the number was absurd. Anything computing a
rate, a median or a coverage percentage gets a **plausible wrong answer** with no
indication anything went wrong. Two hackathon participants hit this independently.

The working filter is `siri_routes__line_ref` (a `line_ref`, not a
`route_short_name`), which requires resolving through `/gtfs_routes/list` first.

## Requested

Either apply the filter, or reject the parameter with a 4xx. Silently ignoring a
filter is the worst of the three options.

Possibly the same class of bug as hasadna/open-bus-stride-api#23 (closed), where
`/siri_rides/list` did not join on `line_ref`/`operator_ref`.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/route-divergence.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/route-divergence.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
