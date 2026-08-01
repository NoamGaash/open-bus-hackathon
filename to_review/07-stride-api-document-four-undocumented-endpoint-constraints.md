# `stride-api:` document four undocumented endpoint constraints

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

Every hackathon participant rediscovered these by trial and error. None appears
in the OpenAPI docs. *Re-verified against the live Stride API on 2026-08-01 immediately before filing; the reproduction below is the exact check that was run.*

### 1. `/route_timetable/list` rejects any date range over a single day

```
1-day range  -> 200 OK
3-day range  -> 500 Internal Server Error
```

It also times out server-side when unfiltered, regardless of range.

### 2. `/siri_vehicle_locations/list` accepts only one `line_ref` per request

while `/route_timetable/list`'s `line_refs` **does** accept a comma-separated
batch. The asymmetry is surprising and undocumented.

### 3. There is a row cap between 15,000 and 20,000

```
limit=15000 -> 200 OK, 15000 rows
limit=20000 -> 500 Internal Server Error
```

A 400 naming the maximum, or a documented cap, would save everyone the bisection.

### 4. The default page size is silent, and varies per endpoint

Omitting `limit` does not return everything and does not warn:

| Endpoint | rows returned with no `limit` |
|---|---|
| `/gtfs_rides_agg/list` | **1,000** |
| `/gtfs_routes/list` | **100** |
| `/gtfs_agencies/list` | 36 (appears complete) |

**This is the most dangerous of the four** because it fails quietly: an analysis
that does not know gets a plausible answer computed from a truncated page. It
already bit this hackathon — a planned-ride total quoted in our own write-up
turned out to be a truncated 1,000-row sample rather than a network figure.

Note `stride.iterate()`'s `limit=` kwarg is client-side only; the server default
applies unless `limit` is *also* passed inside the request params.

## Requested

Document all four. Happy to open a PR against the docs if that is the preferred
route.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by yuvalko1.
· Method, evidence and caveats: [`algorithms/siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
· Original work: https://github.com/yuvalko1/talpiot-hackathon-public-transportation *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
