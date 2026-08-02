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

Write up how street-level bus speed is derived, so the numbers in #42, #43 and #44
can be checked and the method reused for other cities.

## The method in outline

Consecutive SIRI pings from the same vehicle form a **ping pair**. Each pair is
map-matched to OpenStreetMap street geometry, giving a distance and an elapsed time
and therefore a speed reading attributable to a specific street and five-minute
slice. Aggregated: 60,359,656 readings from 11,559,010 pairs over 10 weekdays, at a
**97.3% match rate**.

"Bus-minutes lost" is then the difference between observed traversal time and
free-flow traversal time, summed over every bus using that street in the hour.

## What needs documenting properly

- How free-flow speed per street is established, and how it is separated from the
  posted limit.
- The map-matching rule, and what the 2.7% unmatched consists of.
- The minimum sample per street-hour before a cell is drawn.
- How motorway ramps and very short segments are handled — both distort speed
  badly.

## Why bother

Every figure in #43 is a policy argument. Policy arguments get contested, and an
undocumented method loses that argument regardless of whether it was right.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
