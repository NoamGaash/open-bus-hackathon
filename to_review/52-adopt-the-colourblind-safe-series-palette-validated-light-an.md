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

The hackathon dashboard uses a series palette **validated for adjacent-pair
separation under the common colour-vision deficiencies**, defined once and shared
between the Python and TypeScript sides.

Rules that come with it, and matter more than the hex values:

- Slots are assigned in **fixed order** and never reordered — a series keeps its
  colour between renders, so two charts of the same data are comparable.
- Past 8 series, the overflow folds into **"Other"** rather than cycling — a
  recycled colour is worse than an honest bucket.
- Separate light and dark ramps, because a palette that passes in one fails in the
  other.
- **Status colours are a different scale** from series colours, so "critical red"
  never collides with "series 3 red".

## Why it matters

A chart whose colours are indistinguishable to ~8% of male readers is not
accessible, and the failure is invisible to everyone else — nobody files a bug,
the chart is just quietly useless to some readers.

## Note

The hackathon's own palette has known sub-3:1 slots in light mode. Its response was
the table-fallback rule in **#53**, not a claim that the palette alone is
sufficient. Worth adopting the two together.

Source: [`openbus_hack/theme.py`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/openbus_hack/theme.py) and
[`frontend/src/theme.css`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/frontend/src/theme.css)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`README.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/README.md)
