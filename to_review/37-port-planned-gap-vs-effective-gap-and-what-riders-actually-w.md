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

Two rider-facing measures from the bunching dashboard that the current metrics
miss entirely.

**Effective gap** — when two buses arrive nose-to-tail they are one arrival from a
passenger's point of view. Counting them as two makes the service look twice as
frequent as it is.

**Actual wait vs planned wait** — the honest cost of that. Examples from the
ranked table:

| Line | Planned gap | Effective gap | Planned wait | **Actual wait** |
|---|---|---|---|---|
| 4 (דן) | 7 min | 9 min | 3.5 min | **7.9 min** |
| 18 | 10 min | 12 min | 4.8 min | **9.0 min** |
| 142 | 13 min | 15 min | 6.5 min | **11.5 min** |

![Planned vs effective gap and planned vs actual wait, per line](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/bunch-ranked-table.png)

*Planned vs effective gap and planned vs actual wait, per line*

## Why it matters

**Riders on line 4 wait more than twice as long as the timetable implies** — 7.9
minutes against 3.5. That gap is invisible in any punctuality metric, because the
buses may all be individually "on time". It is the number a passenger would
recognise as their own experience.

## Suggested next step

Publish actual-wait alongside planned-wait everywhere frequency is shown, and
consider it as a headline service metric in its own right.

**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined to the GTFS timetable.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
