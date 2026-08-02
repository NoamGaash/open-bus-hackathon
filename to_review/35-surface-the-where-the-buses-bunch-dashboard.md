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

The hackathon produced a full bunching dashboard that works today and is not
reachable from דאטאבוס. Link or embed it as a first step, while the individual
charts get ported natively (#36–#40).

![Headline and KPI tiles](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/bunch-header-kpis.png)

*Headline and KPI tiles*

**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined to the GTFS timetable.

Headline numbers: **9.9% of consecutive pairs ran bunched** (12,674 nose-to-tail),
**13% were already bunched leaving the terminal**, **50% of the route is ridden
bunched** on average, worst line 4 (דן) at 32%.

## Where

`/gaps_patterns` is the natural home, or a link from the dashboard page.

## Caveats to carry across

It is a **fixed 5-day sample**, not a live view — the page states its own window,
and any link should too. The "grow the sample" button needs the original
hackathon server and will fail politely if the page is served standalone.

The page is **self-contained** — download it and open it in a browser, or run `./dev` in the hackathon repo and visit the path directly. No server, no build, no credentials.

File: [`frontend/public/bunching-reasons.html`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/frontend/public/bunching-reasons.html)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
