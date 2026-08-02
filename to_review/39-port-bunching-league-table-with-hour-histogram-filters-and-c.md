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

The navigational layer of the bunching dashboard: **602 line-directions with at
least 30 pairs**, ranked, filterable by city / operator / line, with a
pairs-by-hour histogram driving a time filter.

![Pairs by hour, with city, operator and line filters](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/bunch-hour-and-filters.png)

*Pairs by hour, with city, operator and line filters*

Columns: planned gap · effective gap · pairs · bunched % · cause split as a stacked
bar · planned wait · actual wait · late-start caused · route ridden bunched.

## Why it matters

The cause split renders **inline per row**, so a reader scanning the table sees
immediately that two lines with the same 26% bunching rate have completely
different causes. That is the design idea worth copying, more than the table
itself.

## Suggested next step

CSV export, and a permalink that encodes the active filters so a finding can be
cited.

**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined to the GTFS timetable.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
