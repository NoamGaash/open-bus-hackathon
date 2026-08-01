# `pipelines:` GTFS import appears to retain the previous release, doubling planned counts on some dates

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

On affected dates `gtfs_ride` reportedly holds **two near-complete daily schedules
under a single `gtfs_route.date`** — the same trip, the same route row, the same
`start_time`, with `journey_ref` suffixes stamping both the current release and
the previous one. The import retained the old release instead of replacing it.

On clean days the two release stamps are complementary halves of one schedule. On
broken days each stamp is a full day, so the date carries roughly twice the real
schedule.

## Reported scale

- 85% of days are clean (planned/actual ratio within [0.9, 1.1])
- **50 days exceed 1.5×**, and **36 exceed 1.8×**
- Scattered across 2023-02 → 2026-07 with no era pattern

## Why it matters

Planned-ride denominators are ~2× too high on those dates. Any execution rate,
cancellation rate or coverage percentage computed for an affected date is
correspondingly halved.

## Confidence

These figures come from a hackathon project (BusAnalysis by lihay7) whose
repository is currently private, and this specific defect was **not** independently
reproduced in the shared hackathon repo. **Treat as a lead to investigate rather
than a confirmed finding** — a per-date planned-count histogram against
`gtfs_route.date` would confirm or kill it quickly.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by lihay7.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/lihay7/BusAnalysis *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
