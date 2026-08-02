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

**725 corridors ranked by bus-minutes lost per hour** — the total delay borne by
all buses on that street, against the street's own free-flow speed.

![Corridors ranked by bus-minutes lost per hour](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/speed-corridors.png)

*Corridors ranked by bus-minutes lost per hour*

Worst corridor: **Geha W-bound — 787 bus-minutes lost per hour**, running at 25.7
km/h against 62.6 free-flow (a 59% slowdown), carrying 59 buses/hr across 234
lines over 10.61 km.

## Why this is the most policy-ready output of the hackathon

It converts a diffuse complaint into a **ranked, costed list of streets**. "Buses
are slow" is not actionable; "this corridor costs 787 bus-minutes every hour, and
here are the next 724 in order" is a capital-works priority list.

It is also a direct answer to the first open question on the דאטאבוס public-appeal
page — *"איפה נדרשים נתיבי תעדוף לתחבורה ציבורית (נת״צים)?"* — see #55.

## Suggested next step

Weight by passengers rather than buses, if ridership can be joined. A corridor with
59 nearly-empty buses and one with 59 full ones are not the same investment case.

**60,359,656 street readings from 11,559,010 ping pairs**, 10 weekdays (May–June 2026), 97.3% match rate. Source: SIRI telemetry joined to OpenStreetMap geometry.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
