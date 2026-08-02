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

A long-form data-journalism page built entirely from the open data, written for a
general reader rather than an analyst.

![Editorial page header](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/editorial-header.png)

*Editorial page header*

It covers the headline non-execution finding, the five upstream data defects
(F1/F6/F7/F8/F9 — filed here as #1775, #1776, #1780, #1781), three service metrics
that do not exist elsewhere (#47, #48, #49), the periphery finding, and
operator-by-operator series.

## Why it is worth surfacing

דאטאבוס is excellent at *"here is the data, explore it"* and has nothing that says
*"here is what the data means"*. This is that, and it is written to be quotable —
every figure names its time window and its population.

## Caveats

A fixed snapshot, not a live view, and it should be dated wherever it is linked.
Some numbers state findings differently from the underlying write-ups — the
reconciliation is in [`to_review/00-VERIFICATION.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/to_review/00-VERIFICATION.md).

The page is **self-contained** — download it and open it in a browser, or run `./dev` in the hackathon repo and visit the path directly. No server, no build, no credentials.

File: [`frontend/public/editorial.html`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/frontend/public/editorial.html)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — lihay7.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`docs/busanalysis.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/docs/busanalysis.md)
