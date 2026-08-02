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

The hackathon dashboard has an appendix that fetches each contributor's **original
notebook or script** and renders it beside the finished card, with a line saying
what it was built into — or **why it was not**.

Example entries:

> `explore_gtfs_siri_coverage.py` → *"ported near-verbatim (nearest-stop +
> time-tolerance matching), scoped down from a system-wide batch scan to one live
> line"*
>
> `siri accessibility analysis using UrbanAccess.ipynb` → *"Not ported — urbanaccess
> pulls ~10 heavy deps and its own notebook warns the network build is slow; that is
> a batch job, not a live card"*

## Why it is worth copying

It makes the **distance between research and product** visible. A reader can see
that a card is a scoped-down version of a broader analysis, and reviewers can check
the port against the original without cloning anything.

The "not ported, and here is why" entries turned out to be the most valuable ones —
they are how #50 and #51 in this milestone were found at all. Without them, that
work would simply have disappeared.

## Suggested shape

Lighter than the original: a per-chart "methods and source" link pointing at the
notebook or script it came from, plus an explicit list of research that was
considered and not built.

Source: [`openbus_hack/source_material.py`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/openbus_hack/source_material.py),
[`frontend/src/SourceMaterial.tsx`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/frontend/src/SourceMaterial.tsx)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`README.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/README.md)
