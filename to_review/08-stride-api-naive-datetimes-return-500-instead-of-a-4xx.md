# `stride-api:` naive datetimes return 500 instead of a 4xx

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

Passing a datetime without a timezone to a time-range filter returns a 500.

*Re-verified against the live Stride API on 2026-08-01 immediately before filing; the reproduction below is the exact check that was run.*

```python
stride.get("/siri_vehicle_locations/list", {
    "recorded_at_time_from": "2026-07-28T08:00:00",   # no tzinfo
    "recorded_at_time_to":   "2026-07-28T09:00:00",
})
# -> httpx.HTTPStatusError: Server error '500 Internal Server Error'
```

The server-side message is `tzinfo is required`.

## Why it should be a 4xx

This is client input error, not a server fault. A 422 naming the offending field
would be self-explanatory; a 500 is indistinguishable from the API being broken,
which is how it reads to a newcomer.

Every analysis in the hackathon repo carries a `_day_bounds()` helper written
specifically to avoid this:

```python
def _day_bounds(day):
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=ZoneInfo("Asia/Jerusalem"))
    end   = dt.datetime.combine(day, dt.time(23, 59), tzinfo=ZoneInfo("Asia/Jerusalem"))
    return start.isoformat(), end.isoformat()
```

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
