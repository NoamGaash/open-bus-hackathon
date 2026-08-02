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

A hackathon notebook builds a transit accessibility analysis with
[UrbanAccess](https://github.com/UDST/urbanaccess), combining the GTFS network with
the street network to answer *where can you actually get to, and how fast*.

**It was deliberately not ported**, and the reason is recorded: urbanaccess pulls
~10 heavy dependencies (pandana, osmnet, scipy, scikit-learn) and its own notebook
warns the network build is slow. That is a batch job, not a live dashboard card.

## Why it should not be dropped

Accessibility is the question underneath most of the others. #44 finds 1,308 km of
street with no bus; accessibility analysis is the proper tool for turning that into
*how many people can reach a hospital within 45 minutes*, which is what actually
matters.

Nothing else in this milestone answers a spatial-equity question.

## Suggested shape

A scheduled batch job writing pre-computed accessibility surfaces, served as static
tiles or a small API — the same architecture #1803 proposes for derived arrival
times. Not a live query.

Notebook: [`source-material/talpiot/notebooks/siri accessibility analysis using UrbanAccess.ipynb`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/talpiot/notebooks/)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — yuvalko1.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
