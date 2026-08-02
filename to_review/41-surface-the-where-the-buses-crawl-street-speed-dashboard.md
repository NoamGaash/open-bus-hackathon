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

Door-to-door bus speed on **every street** of Tel Aviv and the inner ring, by hour
of day, measured from GPS. It works today and is not reachable from דאטאבוס.

![Network speed, bus-minutes lost, worst corridor, streets with no bus](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards/speed-header-kpis.png)

*Network speed, bus-minutes lost, worst corridor, streets with no bus*

**60,359,656 street readings from 11,559,010 ping pairs**, 10 weekdays (May–June 2026), 97.3% match rate. Source: SIRI telemetry joined to OpenStreetMap geometry.

Headline numbers at 16:00: network bus speed **18.8 km/h**; **33,660 bus-minutes
lost per hour** against each street's own free-flow speed; worst single corridor
Geha W-bound at **787 min/hr**; slowest busy street Sderot David Ben Gurion at
**4.7 km/h**; and **1,308 km of street with no bus at all**.

## Where

`/velocity-heatmap` is the closest existing page, or a link from the map page.

## Note

This also answers **#1231** — the ask to embed a notebook about vehicle velocities
into the public appeal. This is that research, at national-data scale and already
interactive.

The page is **self-contained** — download it and open it in a browser, or run `./dev` in the hackathon repo and visit the path directly. No server, no build, no credentials.

File: [`frontend/public/tlv-bus-speed.html`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/frontend/public/tlv-bus-speed.html)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
