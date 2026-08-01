# Rank operators by days-without-cancellations (the unbuilt "method 3")

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

The days-without-cancellations work specified three methods: score one line, score every line of an operator, and **compare operators against each other**. The third was specified and never built.

## Why it matters

It is the comparison a regulator would actually want, and the one the first two methods exist to enable. Per-line scores are diagnostic; per-operator ranking is accountability.

## Sketch

Careful with the denominator: lines with no planned rides must be excluded rather than scored, and operators with no SIRI feed must be excluded rather than ranked last. The original code already returns `None` rather than `0.0` for "unknown" precisely so this averaging step cannot go wrong — preserve that distinction.

## Depends on

A feed-health sanity floor, so a degraded ingestion day does not read as mass cancellation for whichever operator happened to be affected.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
