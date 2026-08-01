# `stride-api:` `siri_rides__schedualed_start_time_*` is misspelled

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

The filter parameters on `/siri_vehicle_locations/list` are spelled
**`schedualed`**:

```
siri_rides__schedualed_start_time_from
siri_rides__schedualed_start_time_to
```

Every consumer carries a `# sic` comment next to it — there are four separate
occurrences in the hackathon repo alone:

```python
"siri_rides__schedualed_start_time_from": day_from,  # sic — API's own spelling
```

## Requested

Accept `scheduled_start_time_from` / `_to` as an alias, keep the old spelling
working, and mark it deprecated in the docs. Cheap, and it stops the typo
propagating into every downstream codebase.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/service-violations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/service-violations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
