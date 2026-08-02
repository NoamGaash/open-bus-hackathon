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

Compare the non-execution rate reconstructed from open data against the figure the
ministry's own electronic control publishes for the same period, at the same
tolerance.

Reported: **5.0% reconstructed against 1.5% published** for 2024-H1, both at ±30
min.

## Why it matters

If the reconstruction is right, unseen failure is unpriced failure — service that
did not run is not being counted, and the enforcement basis is already electronic,
so the data to count it exists. That is a live policy question, not an academic one.

## Why it needs care before publication

A 3.3× discrepancy against an official statistic is a strong claim, and the most
likely explanations are **definitional rather than substantive** — different
tolerance windows, different operator populations, different treatment of the
operators that have no feed at all (#1780), or the duplicate-ride inflation in
#1776. Each of those must be excluded before the gap can be attributed to
under-reporting.

## Suggested next step

Reproduce the comparison at several tolerance windows and with the F6/F8/F9
corrections applied and not applied, so the sensitivity of the gap is visible
rather than asserted.

Method: [`source-material/busanalysis/metrics/enforcement_gap.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/busanalysis/metrics/enforcement_gap.md)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — lihay7.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`docs/busanalysis.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/docs/busanalysis.md)
