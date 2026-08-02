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

Three hackathon notebooks that were never turned into anything, recorded so the
work is findable rather than lost.

| Notebook | What it does | State |
|---|---|---|
| `getting all arrivals to all stops of a given line in a given day.ipynb` | Pulls every arrival at every stop of one line for one day | Working loader; no chart |
| `Load route rides to dataframe.ipynb` | Route rides into a tidy DataFrame | Working loader; no chart |
| `algorithm for getting data to calculate routes between points.ipynb` | Sketch toward trip planning between two points | **Unfinished** |

## Why file this

The first two are **useful query recipes** against endpoints whose behaviour is not
obvious — see #1772 for four constraints that are undocumented. They would save the
next person the rediscovery, and are candidates for the API docs or a cookbook.

The third is genuinely unfinished and is filed only so nobody starts it from
scratch believing no one tried.

## Suggested next step

Extract the two working loaders as documented examples. Low effort, low risk,
good first issue for someone learning the API.

Notebooks: [`source-material/talpiot/notebooks/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/talpiot/notebooks/)

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — yuvalko1.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`siri-coverage.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/siri-coverage.md)
