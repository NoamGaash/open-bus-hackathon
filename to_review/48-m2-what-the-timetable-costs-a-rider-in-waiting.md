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

Median **extra** waiting time beyond what the published timetable promises,
nationally, per month. Reported: **4.2 minutes**, with **11.8% of line-months
running 10+ minutes over promise**.

## Why it matters

It reframes reliability from the operator's point of view to the rider's. "94% of
departures ran" is an operator statistic; "you wait four minutes longer than the
timetable says" is what a passenger experiences, and it is the number that would
change behaviour if published per line.

The proposed remedy is unusual and worth stating: **an honest every-20 beats a
broken every-10.** The metric rewards publishing a timetable the service can
actually keep.

## Important limitation

The record holds no observed departure time, so this is a **waiting** measure
derived scheduled-against-scheduled — it is *not* a punctuality measure, and it
must never be presented as one. See #1778 for why first-ping is not a departure
time.

Closely related: #37 computes actual-vs-planned wait from the bunching dataset by a
different route. **If both are built, they should be reconciled** — two different
"what riders actually wait" numbers in one product would be worse than either alone.

Method: [`source-material/busanalysis/metrics/departure_fidelity.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/busanalysis/metrics/departure_fidelity.md)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — lihay7.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`docs/busanalysis.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/docs/busanalysis.md)
