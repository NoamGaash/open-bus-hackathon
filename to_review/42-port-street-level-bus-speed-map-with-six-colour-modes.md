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

A street-level choropleth of measured bus speed, switchable between six views:
**speed · lost minutes · vs free-flow · vs speed limit · buses/hr · coverage**.

![Median bus speed per street, Tel Aviv and the inner ring](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/speed-map.png)

*Median bus speed per street, Tel Aviv and the inner ring*

Filters: hour of day, city, operator, single line, hide motorways, only streets
with ≥20 buses/hr, show unserved streets, and a street search.

![Colour mode and filter controls](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/speed-controls.png)

*Colour mode and filter controls*

## Why six modes rather than one

They answer different questions and disagree usefully. A street can be slow in
absolute terms but at its own free-flow speed (nothing to fix), or fast in absolute
terms but far below its limit (something to fix). "vs free-flow" is what isolates
*congestion* from *street design*.

**60,359,656 street readings from 11,559,010 ping pairs**, 10 weekdays (May–June 2026), 97.3% match rate. Source: SIRI telemetry joined to OpenStreetMap geometry.

## Suggested next step

Extend beyond Tel Aviv. The method is city-agnostic — it needs GTFS, SIRI and OSM
geometry, all of which exist nationally.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
