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

The single most valuable thing in the bunching dashboard, and nothing comparable
exists in דאטאבוס: **every bunching event attributed to a cause.**

![Share of all bunching events by cause](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/bunch-why-decomposition.png)

*Share of all bunching events by cause*

| Cause | Share | Meaning |
|---|---|---|
| **Late departure** | 13% | Already bunched leaving the terminal — the leader left late, the follower left early, or the timetable left no gap |
| **First 20% of route** | 10% | Left with a healthy gap, collapsed within the first fifth |
| **En route** | 73% | Collapsed after the 20% mark — classic traffic-and-dwell feedback |
| **Origin outside area** | rest | Entered the observed area already bunched; onset not visible |

## Why it matters

It separates problems with **different owners**. 13% born at the terminal is a
dispatch and timetabling problem the operator can fix this week. 73% en route is a
road-priority and dwell-time problem that needs infrastructure. Publishing a single
"bunching rate" hides that split and points everyone at the wrong lever.

## Suggested next step

Per-operator and per-corridor breakdowns of the same split. An operator whose
bunching is mostly terminal-born is failing at something entirely different from
one whose bunching is mostly en route.

**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined to the GTFS timetable.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
