# Route divergence map: where buses leave the route

> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What it answers

The line's planned stops against every GPS ping beyond the off-route threshold, coloured by how far out. A recurring detour shows up as a **cluster** rather than a number — scattered single points are usually GPS error, but a tight cluster in one place is a diversion the whole line takes.

![Route divergence map: where buses leave the route](https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/route-divergence-map.png)

*Route divergence map: where buses leave the route — screenshot of the hackathon dashboard card.*

## How it works

1. Same fetch and haversine distance calculation as the bar-chart card.
2. Keep pings beyond the threshold (default 500 m).
3. Colour by severity relative to the worst observed stray.
4. Sample down to 600 markers **evenly** rather than taking the worst N, so the map
   still shows *where* strays happen instead of only the single worst cluster.

## Where it could go in דאטאבוס

`/single-line-map` for the per-line view, or `/map` if it should be a network-wide layer.

*A suggestion, not a decision — page ownership is the maintainers'.*

## Known limitations

Same nearest-stop caveat as the bar chart. The current legend labels the mid-severity bucket with a fixed multiple of the threshold while the code splits at the midpoint to the worst observed stray — a small inconsistency worth fixing in any port.

## Suggested next steps

Overlay divergence clusters from **all** lines to find shared problem locations — a junction that six lines detour around is a road-network finding, not a per-line one.

## Status

The research is done and the numbers exist — a working implementation runs in the
hackathon repo against the live Stride API. What is missing is a production-shaped
version in this app.

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — analysis by the hackathon team.
· Method, evidence and caveats: [`algorithms/route-divergence.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/route-divergence.md)
· Original work: https://github.com/hasadna/open-bus-hackathon-26
· Issue drafts and the full defect list: [`algorithms/upstream-issues.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/upstream-issues.md)
