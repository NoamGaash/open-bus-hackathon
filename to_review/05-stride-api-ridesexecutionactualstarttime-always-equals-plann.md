# `stride-api:` `rides_execution.actual_start_time` always equals `planned_start_time`

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

`actual_start_time` never carries an observed departure time. Where both fields
are present, it is byte-identical to `planned_start_time`.

## Evidence

*Re-verified against the live Stride API on 2026-08-01 immediately before filing; the reproduction below is the exact check that was run.*

Line 480, all resolved `line_ref` variants, 2026-07-15 → 2026-07-29:

| | count |
|---|---|
| rows with **both** planned and actual | 676 |
| `actual_start_time == planned_start_time` | **676** |
| `actual_start_time != planned_start_time` | **0** |
| cancelled (`actual_start_time` null) | 4 |
| unplanned (`planned_start_time` null) | 10 (1.4% of rows) |

## Why this still matters

The field is genuinely useful as-is — null means the ride did not run, which is
the cleanest cancellation signal in the API, and a working
days-without-cancellations score was built on exactly that. But the **name
promises an observed departure time and it is not one**, so the endpoint can never
be used for delay or punctuality work.

## Requested

Either populate it from SIRI, or rename/document it as a `did_run`-style boolean
so nobody builds a punctuality metric on it.

Related: #19 (improve rides reliability metric by adding "actual start time" ETL)
— that issue is arguably the fix for this one.

## Note on a possibly-related closed issue

hasadna/open-bus-stride-api#54 (`rides_execution/list` used UTC midnight instead of
Israel midnight) is closed. The hackathon code still carries a client-side
re-filter working around fuzzy service-date boundaries; if #54's fix shipped, that
workaround may now be unnecessary. Worth confirming.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by Broundal.
· Method, evidence and caveats: [`algorithms/days-with-no-cancellations.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/days-with-no-cancellations.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26/tree/main/orion
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
