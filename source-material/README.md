# Source material from participants' own repositories

Supporting evidence for the hackathon issues filed in
[hasadna/open-bus-map-search milestone #10](https://github.com/hasadna/open-bus-map-search/milestone/10).

Several participants worked in their own repositories, some of them private. The
issues cite figures from that work, so a reader with no access to those repos
could not check anything. This folder closes that gap: everything an upstream
ticket references is here, in the open.

## Permission

> *"I have permission from all participants to publicly publish and use any
> product of the hackathon in any way that I find suitable for our project."*
> — Noam Gaash, hackathon organiser, 2026-08-02

Recorded here so the provenance of republished material is auditable rather than
assumed. `BusAnalysis` is additionally MIT-licensed (`busanalysis/LICENSE`), which
permits redistribution with attribution independently of the above.

**If you are a participant and want something removed or amended, open an issue on
this repo and it will be done.**

## What is here

### `busanalysis/` — lihay7

From [`lihay7/BusAnalysis`](https://github.com/lihay7/BusAnalysis) *(private)*, an
independent national reconstruction of Israel's planned-vs-actual bus record:
1,306 service days, 117.2M schedule links. MIT licensed.

| Path | What it is | Cited by |
|---|---|---|
| `handoff/issues/F1…F9.md` | The five upstream defect write-ups, authored explicitly "for the maintainer" | #1775, #1776, #1779, #1780, #1781 |
| `handoff/QUESTIONS_FOR_HASADNA.md` | Open questions for the stride maintainers | — |
| `docs/ARCHITECTURE.md`, `DATA.md`, `REPRODUCE.md` | How the pipeline works and how to re-derive its numbers | all of the above |
| `figures/f6…f9_*.png` | The evidence figure behind each defect | one per defect issue |
| `figures/tolerance_curve.png`, `density_bands.png` | The two headline findings | — |
| `metrics/*.md` | Per-metric summaries — departure fidelity, enforcement gap, gap series, record integrity, city profiles | the M1/M2/M3 tickets |

Deliberately **not** copied: `src/`, `tests/`, `assistant/`, `plans/`, the 11 MB
dashboard, the interactive HTML bundles and the parquet aggregates. None is needed
to verify a ticket.

> ⚠️ The F-write-ups and the public
> [`frontend/public/editorial.html`](../frontend/public/editorial.html) state some
> figures differently, and **F9's prose contradicts its own evidence table**. The
> reconciliation is in [`to_review/00-VERIFICATION.md`](../to_review/00-VERIFICATION.md).
> Prefer the table over the prose.

### `talpiot/` — yuvalko1

From [`yuvalko1/talpiot-hackathon-public-transportation`](https://github.com/yuvalko1/talpiot-hackathon-public-transportation)
*(private)*. The notebooks and the system-wide coverage script that several
analyses were ported from.

| Path | Ported into |
|---|---|
| `scripts/explore_gtfs_siri_coverage.py` | `analyses/siri_coverage.py` — nearest-stop + time-tolerance matching, near-verbatim |
| `notebooks/compare_gtfs_siri_average.ipynb` | `analyses/schedule_adherence_average.py` — all three cards |
| `notebooks/load siri vehicle locations…ipynb` | `analyses/gps_trace_map.py` |
| `notebooks/compare gtfs planned vs siri actual.ipynb` | covered by the schedule-adherence stringline |
| `notebooks/siri accessibility analysis using UrbanAccess.ipynb` | **never ported** — pulls ~10 heavy deps and needs a batch home |
| `notebooks/getting all arrivals…ipynb`, `Load route rides…ipynb`, `algorithm for getting data…ipynb` | **never ported** — loaders and an unfinished trip-planning sketch |

### noamf2001

Already vendored in full at [`repos/PublicTransportHackathon/`](../repos/PublicTransportHackathon/)
— the `bus_times` package behind the segment-reliability, Marey and rush-hour
heatmap cards, including its 65-test suite. Nothing further needed.

## See also

- [`algorithms/`](../algorithms/) — one document per solution: algorithm, reasoning,
  confidence-graded findings, criticism
- [`algorithms/upstream-issues.md`](../algorithms/upstream-issues.md) — the defect
  drafts and their routing
- [`to_review/`](../to_review/) — the filed issue bodies, and the verification log
