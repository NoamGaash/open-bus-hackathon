# BusAnalysis — related work on the same data

[`lihay7/BusAnalysis`](https://github.com/lihay7/BusAnalysis) is an independent
reconstruction of Israel's planned-vs-actual bus record, built on the same
hasadna `stride` data this hackathon uses. It is worth knowing about here for
two reasons: it answers "did the scheduled bus run?" at national scale, and it
found five defects in the upstream data that affect anyone querying the same
tables — including our analyses.

**Access:** the repo is **private** (a plain `curl` or unauthenticated fetch
404s — that is permission, not a missing repo). Licence is MIT, but it is not
our code: anything ported across needs `lihay7`'s sign-off first. Read it with
an authenticated `gh`:

```bash
gh repo view lihay7/BusAnalysis
gh api repos/lihay7/BusAnalysis/git/trees/main?recursive=1 --jq '.tree[].path'
```

Scope: 1,306 service days (2023-01 → 2026-07), 117.2M schedule links, ~7 GB
local warehouse rebuilt from GTFS + SIRI. Created and pushed 2026-07-31.
Languages are Python (~1 MB of source) and HTML (the committed dashboards).

---

## The four findings

| # | Finding | Fix direction |
|---|---|---|
| 1 | **5.2%** of scheduled departures never appear in the national tracking record (±5 min, 116.4M rides, tracked operators). Widening to ±60 min only moves it to 4.9% — so these are cancellations, not delays. | Publish the rate per line and per month **with its window stated**. |
| 2 | **~1.7×** — the sparsest lines (under 8 departures/day) lose **7.8%** of departures against **4.6–4.8%** on mid-frequency lines, after the control that kills the naive version of the claim. | Protect thin lines first: one missing bus on a two-a-day line is the whole service that day. |
| 3 | **5.0% vs 1.5%** — reconstructed non-execution for 2024-H1 against the figure the ministry's own electronic control published for the same period, both at ±30 min. | Compute the violation rate from the open record; the enforcement basis is already electronic. |
| 4 | **4.2 minutes** median *extra* waiting beyond what the published timetable promises, nationally, every month. 11.8% of line-months run 10+ minutes over promise. | Publish a timetable the service can keep — an honest every-20 beats a broken every-10. |

Each number is reproducible from committed aggregates in `report/metrics/`
(parquet, ~9 MB) without rebuilding the warehouse.

---

## Five upstream data defects — relevant to our analyses

Written up as paste-ready issues in `handoff/issues/`. These describe the
`stride` database we query through [stride.py](../openbus_hack/stride.py), so
they constrain what our own cards can honestly claim.

| ID | Defect | Why it matters to us |
|---|---|---|
| **F1** | The SIRI→GTFS ride-matching job has written **zero matches since October 2024**. All four match columns (`gtfs_ride_id`, `route_gtfs_ride_id`, `scheduled_time_gtfs_ride_id`, `journey_gtfs_ride_id`) fail together; the raw feed is healthy (~2.9–3.1M `siri_ride` rows/month). | Any analysis joining actual→planned via the stored link gets nothing for the last ~21 months. You have to match yourself. |
| **F6** | **2.6%** of `siri_ride` rows are surplus duplicate journeys (3.93% sit in a duplicated group); rate has ~quadrupled since 2023 and is 66× skewed across operators. Downstream of the `scheduled_start_time` drift bug (hasadna #390). | Raw counts of tracking rows overstate real service. Affects anything counting rides rather than deduplicating journeys. |
| **F7** | `first_vehicle_location_id` is **100% null for 18 consecutive months** (2024-12 → 2026-05, 49.4M rides); `duration_minutes` tracks it. | It is a **processing-state flag, not a property of the bus** — it encodes whether stride's enrichment job ran, not whether a vehicle transmitted. Easy to misread as a per-operator transmission metric. Don't. |
| **F8** | The GTFS import sometimes keeps the previous release alongside the current one under a single `gtfs_route.date`, **doubling planned counts** on affected dates. 50 days exceed 1.5×, 36 exceed 1.8×, scattered with no era pattern. | Planned-ride denominators are ~2× too high on those dates. |
| **F9** | **Five operators never reach the tracking feed** — three absent entirely across 3.5 years, two under 1% covered. 2.74M scheduled rides, ~2.3% of national planned volume. | They are unmeasurable, not failing. Counting them as cancellations is most of how 5.2% becomes 7.4%. |

Fixing all five moves the national figure from **7.4% → 5.2%** (and to 42% on
the worst days), which is the case for treating them as defects rather than
noise.

---

## How to read numbers off this data honestly

Four rules the project holds itself to. They apply to our cards too:

1. **Every rate names its time window.** There is no tolerance-free answer to
   "did the bus run?" A figure without a window can't be compared to one that
   has it.
2. **These are claims about the tracking record, not about the road.** A ride
   the feed never saw counts as missing. No independent national bound exists
   on the feed's own completeness — so the phrasing is "never appears in the
   record", never "the bus didn't run".
3. **Time differences here are scheduled-against-scheduled, not punctuality.**
   The record holds no observed departure time. Their M2 is a *waiting*
   measure; actual lateness needs stop-level data.
4. **Five operators have no tracking feed at all** — excluded from every
   performance rate and reported as a finding in their own right (F9).

---

## How it relates to this repo

Same data, opposite architecture:

| | this repo | BusAnalysis |
|---|---|---|
| Data access | live paginating API client with a disk cache | ~7 GB local mirror (4 slim tables, 245M rows), not committed |
| Unit of work | one `@analysis` function per person → card | a batch pipeline: mirror → per-day matcher → marts → metrics → figures |
| Matching | not attempted; we lean on what the API returns | own greedy 1:1 matcher, 6 time windows, in `src/busanalysis/matching/greedy.py` |
| Output | live React dashboard over FastAPI | committed self-contained HTML (`report/dashboard/index.html`, 11.6 MB; `brief.html`, one screen) |
| Registry | `openbus_hack/registry.py` discovers `analyses/*` | has its own `src/busanalysis/registry.py` for the same job |

Layout of theirs, briefly:

```
src/busanalysis/
  pipeline/    mirror, extract_day, marts, backfill
  matching/    greedy 1:1 matcher + validation
  quality/     filters
  metrics/     departure_fidelity, enforcement_gap, gap_series,
               record_integrity, city_profiles
  viz/         charts, dashboard, brief, city_map, heatmap
tests/         substantial — test_extract_day.py alone is 42 KB
report/        dashboards, figures, committed parquet aggregates
handoff/       the five defect issues + QUESTIONS_FOR_HASADNA.md
assistant/     research record: findings ledger, verification memos,
               DECISIONS.md, ATTEMPTS_AND_FAILURES.md (the dead ends)
plans/         the plans each phase was executed from
```

## Directions worth taking from it

- **Port finding #2 as an analysis card.** "Sparse lines lose disproportionately
  more service" maps cleanly onto `@analysis` + `bar_chart` over
  `gtfs_rides_agg`, and it is the finding that most needs a live, per-line view
  rather than a static national figure.
- **Cross-check.** They built from an offline mirror, we query the API live. If
  our numbers diverge from their 5.2%, the divergence itself is informative —
  most likely F6/F8 territory.
- **Carry the defect list upstream.** The five `handoff/issues/` write-ups are
  directly relevant to the consolidation this hackathon feeds into
  (`open-bus-stride-api`, `open-bus-pipelines`). F1 in particular claims the
  national "rides that didn't run" statistic has had no computable basis since
  October 2024.
