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

A record-integrity metric: what share of the national schedule is even **capable**
of being measured, given the feed's own gaps.

It is the composite of the defects filed separately in this milestone — the
unpopulated aggregate (#1770), the broken stored linkage (#1775), duplicate rides
(#1776), doubled planned counts (#1781) and the operators with no feed (#1780).

## Why it belongs in the product

Every other number in דאטאבוס is conditional on this one. A 94% execution rate
means something quite different if 5% of the schedule is unmeasurable and the
denominator is inflated on 22 days of the year.

Publishing measurability **alongside** performance is the difference between a
dashboard that can be quoted and one that cannot.

## Suggested shape

A single per-month figure with a breakdown by cause, on `/data-research`, plus a
small badge wherever a performance number is shown. Pairs naturally with the
coverage scorecard in #1802 and with #24.

Method: [`source-material/busanalysis/metrics/record_integrity.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/busanalysis/metrics/record_integrity.md)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — lihay7.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`docs/busanalysis.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/docs/busanalysis.md)
