> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What

Two conventions the hackathon dashboard enforced at the framework level rather than
leaving to each chart author.

**1. Every chart carries a table.** `ensure_table()` derives one automatically from
the chart's own series if the author did not supply it, so there is no chart
without a text equivalent — for screen readers, for colour-blind readers, and for
anyone who wants the actual number.

**2. Every chart marks where it is weak**, rather than looking uniformly confident:

| Cue | Meaning |
|---|---|
| Hatched or pale bar/cell | The number is there but shaky; a note names why |
| `n=…` beside every mark | The sample behind it, always visible, never inferred |
| Dimmed italic axis label | That stop/segment was rarely resolved — interpolation more than measurement |
| Blank vs hatched cell | **No data** and **thin data** look different, deliberately |

## Why the second rule is the important one

An under-sampled segment silently missing from a chart is indistinguishable from a
segment that does not exist — the most misleading failure available. The rule is
**flag, never drop.**

This matters especially here because so much of the underlying data is patchy in
ways the reader cannot see: derived arrival times at ±30 s, operators with no feed,
days with doubled schedules.

Source: [`openbus_hack/contract.py`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/openbus_hack/contract.py)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-arrival-reliability.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-arrival-reliability.md)
