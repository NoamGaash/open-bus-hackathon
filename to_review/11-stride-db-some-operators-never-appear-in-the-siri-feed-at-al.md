# `stride-db:` some operators never appear in the SIRI feed at all

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

Reported: three operators are **never** present in SIRI across 2023-01 → 2026-07,
and two more are under 1% covered. Together ~2.74M scheduled rides, about **2.3%
of national planned volume**.

Independently, a hackathon coverage analysis hit lines with zero SIRI coverage and
had to special-case them, since 0% coverage reads as total service collapse when
it actually means the line is not in the real-time feed.

## Why it matters

Their buses may be running perfectly. Nothing reports them, so nothing about them
can be measured — and counting them as cancellations is reportedly most of how a
national non-execution figure moves from 5.2% to 7.4%.

**For דאטאבוס specifically:** these operators should be visibly marked as
*unmeasured* rather than appearing in reliability rankings with a terrible score.
An operator with no feed currently looks identical to an operator that cancelled
everything.

## Confidence

The five-operator census comes from a hackathon project (BusAnalysis by lihay7)
whose repository is currently private — **the operator list and the 2.3% figure
need confirmation against the database.** The general phenomenon (lines with
literally zero SIRI coverage) was reproduced in the shared hackathon repo.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by lihay7.
· Method, evidence and caveats: [`algorithms/siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
· Original work: https://github.com/lihay7/BusAnalysis *(private repo — ask the owner for access)*
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
