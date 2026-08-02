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

The bunching dashboard opens on a 5-day sample and offers **"add N random
weekdays"**, which probes the archive for healthy days and loads them in the
background. The page stays fully usable while they land, and a progress panel
reports coverage — *"2,880 / 2,880 five-min slices · 100.0%"*.

## Why it matters

It is a direct answer to the cost problem behind half the tickets in this
milestone. Several analyses take 1–2 minutes per line because they derive data the
API does not serve. The usual options are a slow page or a small sample; this is a
third — **start small, stay interactive, deepen in the background, and show the
reader exactly how much evidence is currently behind the chart.**

## Why it is honest as well as fast

The progress panel doubles as a confidence indicator. A reader looking at a chart
built from 20% of the intended sample can see that, which is strictly better than
a chart that looks identical whether it rests on one day or thirty.

## Suggested next step

Apply it first to the cards that currently cap their windows for cost reasons —
segment reliability (#1782), schedule adherence (#1785) and bunching (#1790).

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`bus-bunching.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/bus-bunching.md)
