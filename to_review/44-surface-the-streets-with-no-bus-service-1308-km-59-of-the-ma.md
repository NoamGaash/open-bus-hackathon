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

The speed dashboard reports **1,308 km of mapped street with no bus service at
all — 59% of the network** in Tel Aviv and the inner ring. It is a toggle on the
map ("show unserved streets") rather than a headline.

## Why it deserves its own view

Every other metric in דאטאבוס measures **service that exists**: was it late, did it
run, did it bunch. This measures the opposite, and it is the one a resident of an
underserved neighbourhood would actually care about.

It also has an equity dimension the current metrics cannot see. A neighbourhood
with no bus scores no cancellations and perfect punctuality — it is indistinguishable
from a well-served one in every reliability statistic.

## Caveats

59% of *street kilometres* is not 59% of people — buses reasonably follow arterials,
and a residential cul-de-sac with no bus is not a failure. The useful version of
this metric is **walking distance to the nearest served street**, weighted by
population, not raw kilometres.

## Suggested next step

Join to population or dwelling counts to turn street coverage into people coverage,
then compare across cities. Related: the UrbanAccess accessibility work in #50,
which is the proper tool for this and was never ported.

**60,359,656 street readings from 11,559,010 ping pairs**, 10 weekdays (May–June 2026), 97.3% match rate. Source: SIRI telemetry joined to OpenStreetMap geometry.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
