# Upstream issues — prep for hasadna

Every defect the hackathon solutions hit, deduplicated, routed to a repo, and
written paste-ready. Sources are the per-solution docs in this folder plus
[`docs/busanalysis.md`](../docs/busanalysis.md).

**Nothing here has been filed yet.** This is the prep.

## Read this before filing

**Most of these are not `open-bus-map-search` bugs.** That repo is the React
frontend; the defects are in the API, the DB and the ETL. But it is the most
active repo, it has `data research` and `bus-expert-needed` labels, and — crucially
— it is a *consumer* of the broken fields, so several of these have a real
frontend-visible symptom that belongs there.

The split used below:

| Repo | Gets |
|---|---|
| [open-bus-map-search](https://github.com/hasadna/open-bus-map-search) | Symptoms visible in the UI, and requests to surface data caveats to users |
| [open-bus-stride-api](https://github.com/hasadna/open-bus-stride-api) | Endpoint behaviour: ignored filters, error codes, undocumented limits, field semantics |
| [open-bus-stride-db](https://github.com/hasadna/open-bus-stride-db) | Data content: null columns, duplicate rows, coverage holes |
| [open-bus-pipelines](https://github.com/hasadna/open-bus-pipelines) | ETL jobs that stopped or import wrongly |

Useful labels on map-search: `data research`, `bus-expert-needed`, `backend`,
`timezone/midnight`, `clarification needed`.

## Duplicate check (done 2026-08-01)

Searched all four repos. What already exists:

| Existing | State | Our relationship to it |
|---|---|---|
| [stride-api#49](https://github.com/hasadna/open-bus-stride-api/issues/49) — "API returns total_actual_rides: 0 for all operators on 2025-09-17 !" | **open**, 0 comments, filed 2025-09-18 | **Same defect as our A.** One date; we have 9 months, network-wide, plus a control. **Comment, do not open a new issue.** |
| [stride-api#23](https://github.com/hasadna/open-bus-stride-api/issues/23) — "stride.get doesn't filter on line_ref and operator_ref" | **closed** | Same *family* as our B (a filter accepted and not applied) on `/siri_rides/list`. Ours is `/siri_vehicle_locations/list` and `gtfs_route__route_short_name`. Reference it; it suggests a recurring class of bug. |
| [stride-api#54](https://github.com/hasadna/open-bus-stride-api/issues/54) — "`rides_execution/list` uses UTC midnight for date filtering instead of Israel midnight" | **closed** | Explains orion's "the API's service-date filter is fuzzy at the window edges". **Verify whether the fix shipped** before filing anything on it — our client-side re-filter may now be unnecessary. |
| [stride-api#43](https://github.com/hasadna/open-bus-stride-api/issues/43) — "Missing data" | open, 3 comments | Possibly a broad umbrella for several of these. Read before filing. |
| [map-search#1149](https://github.com/hasadna/open-bus-map-search/issues/1149) | open | `rides_execution/list` returns empty without certain parameters. Adjacent to our E. |
| [map-search#19](https://github.com/hasadna/open-bus-map-search/issues/19) — "Improve rides reliability metric by adding 'actual start time' ETL" | open | Directly relevant to our E and G. |
| [map-search#175](https://github.com/hasadna/open-bus-map-search/issues/175) — "Research \| explain weird patterns in the data" | open | Several findings here are candidate answers. |
| hasadna issue #390 — `scheduled_start_time` drift | referenced by BusAnalysis F6 | Root cause of our D. Locate it before filing D. |

No existing issue found for: the ignored `route_short_name` filter on
`siri_vehicle_locations`, the SIRI reporting-lead-time artifact, duplicate ping
rows, the >15k row cap, or the `schedualed` misspelling.

---

# Priority 1 — data is wrong and someone is already drawing charts from it

## A. `total_actual_rides` is 0 for every row, network-wide

**Action: comment on [stride-api#49](https://github.com/hasadna/open-bus-stride-api/issues/49), don't open a new issue.**
**Then open the map-search issue below**, because this one has a live UI symptom.

Evidence to add to #49:

> Confirming this is not specific to 2025-09-17. Two independent hackathon
> analyses measured it across `/gtfs_rides_agg/list` **and** `/group_by`, on
> every date sampled from 2025-11 to 2026-07, network-wide:
>
> | Date | Σ planned | Σ actual |
> |---|---|---|
> | 2026-07-01 | 3,498 | **0** |
> | 2026-06-15 | 3,510 | **0** |
> | 2026-04-01 | 3,227 | **0** |
> | 2025-11-01 | 3,927 | **0** |
>
> **It is not ingestion lag.** Control: line 2259 on 2026-07-29 reports
> `total_actual_rides=0` in the aggregate, while `/rides_execution/list` for the
> same line and date returns real `actual_start_time` values and zero
> cancellations. Actuals exist at ride level and are not being rolled into the
> aggregate.
>
> `num_planned_rides` is populated normally and cross-checks well against the
> ride-level endpoint (aggregate 123 vs 126 planned for that line/date), so the
> aggregate is usable as a planned-ride denominator — the actual column alone is
> the problem.
>
> Sources: [orion's method study](…), [service_violations.py](…).

### A2 — map-search issue (new)

**Repo:** `open-bus-map-search` · **Labels:** `bug`, `data research`, `bus-expert-needed`

> **Title:** Dashboard charts show ~0% actual rides because `total_actual_rides` is unpopulated upstream
>
> `totalActualRides` is consumed in five places:
>
> - `src/pages/dashboard/AllLineschart/AllLinesChart.tsx`
> - `src/pages/dashboard/WorstLinesChart/WorstLinesChart.tsx`
> - `src/pages/dashboard/ArrivalByTimeChart/DayTimeChart.tsx`
> - `src/pages/operator/OperatorGaps.tsx`
> - `src/pages/DataResearch/DataResearch.tsx`
>
> all fed by `useGroupBy` → `/gtfs_rides_agg/group_by` (`src/api/groupByService.ts`).
>
> That column is 0 for every row network-wide (upstream:
> hasadna/open-bus-stride-api#49). The rendered result is not "no data" — it is a
> confident chart showing that essentially no bus in Israel ran.
>
> Until the upstream column is fixed, the frontend should detect
> `totalActualRides === 0 && totalPlannedRides > 0` across a whole response and
> show a data-quality banner rather than plotting it.
>
> Reproduced independently by two hackathon analyses; see the evidence table in
> hasadna/open-bus-stride-api#49.

**Why this is the highest-priority item:** it is the only defect here with a
confirmed, currently-live, user-facing wrong answer in hasadna's own product.

## B. `/siri_vehicle_locations/list` silently ignores `gtfs_route__route_short_name`

**Repo:** `open-bus-stride-api` · **Labels:** `bug`
**Source:** [route-divergence.md](route-divergence.md) finding 1, [gps-trace-map.md](gps-trace-map.md) finding 1

> **Title:** `/siri_vehicle_locations/list` accepts `gtfs_route__route_short_name` and ignores it, returning the entire country's pings
>
> Passing `gtfs_route__route_short_name` to `/siri_vehicle_locations/list` does
> not filter. It does not error, does not warn, and does not return an empty set
> — it returns **every** ping in the time window, from every line in the country.
> The caller then treats them as belonging to their line.
>
> This is how we caught it: an off-route analysis reported buses **50 km from
> their route on 97.7% of pings**. The buses were fine; the pings belonged to
> other lines.
>
> The symptom is only obvious because that particular analysis produces an
> absurd number. Anything computing a rate, a median or a coverage percentage
> gets a plausible, wrong answer with no indication anything went wrong.
>
> Two separate hackathon participants hit this independently. The working filter
> is `siri_routes__line_ref` (a `line_ref`, not a `route_short_name`), which
> requires resolving through `/gtfs_routes/list` first.
>
> **Requested:** either apply the filter, or reject the parameter with a 4xx.
> Silently ignoring a filter is the worst of the three options.
>
> Possibly the same class of bug as #23 (closed), which was `/siri_rides/list`
> not joining on `line_ref`/`operator_ref`.

## C. SIRI→GTFS stored linkage columns are unpopulated

**Repo:** `open-bus-pipelines` (job) + `open-bus-stride-db` (symptom)
**Labels:** `bug` · **Source:** [service-violations.md](service-violations.md) finding 3, BusAnalysis **F1** + **F7**

> **Title:** The SIRI→GTFS ride-matching job has written no matches since 2024-10; `first_vehicle_location_id` null for 18 months
>
> Two related symptoms, both observed independently by two projects:
>
> **1. The ride link.** `siri_ride.gtfs_ride_id` and its three siblings
> (`route_gtfs_ride_id`, `scheduled_time_gtfs_ride_id`, `journey_gtfs_ride_id`)
> all stop being populated together. Healthy through 2024-08, degrading 2024-09,
> effectively zero 2024-10 → 2026-07. The raw feed never stopped: ~2.9–3.1M
> `siri_ride` rows/month are still created.
>
> **2. The enrichment.** `siri_ride.first_vehicle_location_id` is null for
> **100.00%** of rides for 18 consecutive months (2024-12 → 2026-05, 49.4M
> rides); `duration_minutes` tracks it to within 0.006/month. Overall 49.21% of
> all `siri_ride` rows have it null.
>
> A hackathon analysis independently found these columns "inconsistently NULL —
> present for some days, absent for others, for identical, genuinely-tracked
> rides", and had to derive planned-vs-actual from raw GPS pings instead.
>
> **The interpretation risk on (2) is worth calling out separately:**
> `first_vehicle_location_id` looks like it means "this vehicle never reported
> its position", and it is easy to build a per-operator transmission metric on
> it. It does not mean that — **it encodes whether the enrichment job has
> processed that day**. It is a processing-state flag, not a property of the bus.
>
> Detail and day-by-day scans: BusAnalysis `handoff/issues/F1-stored-linkage.md`
> and `F7-enrichment-flag.md` (private repo; ask @lihay7 to share).

## D. Duplicate rides and duplicate location rows

**Repo:** `open-bus-stride-db` · **Labels:** `bug`, `data research`
**Source:** BusAnalysis **F6**, [days-with-no-cancellations.md](days-with-no-cancellations.md) finding 5, repo-wide ~10% duplicate ping rate

> **Title:** 2.6% of `siri_ride` rows are duplicate journeys; overlapping snapshots also repeat ~10% of location rows
>
> **Ride level.** Over a full census (2022-12-30 → 2026-08-01, 116,335,248
> rows): 3.93% of rides sit in a duplicated `(siri_route_id, journey_ref,
> service day)` group, 2.56% of all rows are surplus duplicates, 66× skewed
> across operators, and the rate has roughly quadrupled from 2023 to 2026.
> Downstream of the `scheduled_start_time` drift bug (hasadna #390): when a
> journey's scheduled start drifts, a **new** row is written instead of the
> existing one being updated.
>
> **The same shape appears in GTFS.** 2026-07-26 on one line returned 259
> `/rides_execution/list` rows for 127 distinct `planned_start_time`s (some ×4)
> under 255 distinct `gtfs_ride_id`s — one physical departure emitted under
> several ride ids. Any naive count of planned rides double-counts, and a
> duplicated row with a null actual becomes a phantom cancellation.
>
> **Location level.** Overlapping SIRI snapshots repeat the same physical
> observation — same `siri_ride__id`, same `recorded_at_time`, same lat/lon —
> at roughly 10% of rows. Harmless for `min()`/`max()` aggregations, **not**
> harmless for anything weighted or counted: one hackathon analysis computes a
> distance-weighted average position, where a duplicated ping carries its weight
> twice.
>
> Every analysis in our hackathon repo now dedups on
> `(siri_ride__id, recorded_at_time, lat, lon)` as a matter of course. That is a
> workaround every consumer is independently reinventing.

## E. `/rides_execution/list`'s `actual_start_time` is a flag, not a time

**Repo:** `open-bus-stride-api` · **Labels:** `documentation`, `data research`
**Source:** [days-with-no-cancellations.md](days-with-no-cancellations.md) finding 2

> **Title:** `rides_execution.actual_start_time` always equals `planned_start_time` — document it as a boolean, or populate it
>
> For **all 1,726** non-null rows sampled, `actual_start_time ==
> planned_start_time` to the second.
>
> The field is genuinely useful as-is: null means the ride did not run, which is
> the cleanest cancellation signal in the API, and we built a working
> days-without-cancellations score on it. But the name promises an observed
> departure time, and it is not one. The endpoint can never be used for delay or
> punctuality work.
>
> **Requested:** either populate it from SIRI, or rename/document it as
> `did_run`-style boolean so nobody builds a punctuality metric on it. Related:
> hasadna/open-bus-map-search#19.

---

# Priority 2 — correctness traps that produce plausible wrong answers

## F. SIRI reports a vehicle against its next ride while it is still parked

**Repo:** `open-bus-map-search` (`data research`) and/or `open-bus-stride-db` (documentation)
**Source:** [service-violations.md](service-violations.md) finding 1 — **the most reusable result the hackathon produced**

> **Title:** "First SIRI ping" is not departure time — the feed reports a vehicle ~30 or ~5 min before its scheduled start, while stationary
>
> On a sampled line, **~80% of rides' raw first pings** landed at almost exactly
> **−30 or −5 minutes** before scheduled departure, with
> `distance_from_journey_start == 0` and `velocity == 0` — the vehicle parked at
> the origin stop, boarding.
>
> Taking that first ping as "actual departure" made **~90% of matched rides look
> early**. That is not early running; it is the operator feed's reporting lead
> time.
>
> Two sharp clusters at fixed offsets rather than a smooth distribution is what
> identifies it as a feed convention.
>
> **The fix that worked:** use the first ping where the vehicle has actually
> started moving — `distance_from_journey_start > 0 || velocity > 0` — and fall
> back to the raw first ping only when the vehicle was never observed moving
> (and flag those rides as unreliable).
>
> Filing this as documentation/research rather than a bug: the feed is behaving
> as operators report it. But any consumer computing departure punctuality from
> first-ping is currently measuring the wrong thing, and there is nothing in the
> docs that says so.

## G. Undocumented endpoint constraints

**Repo:** `open-bus-stride-api` · **Labels:** `documentation`
**Source:** [siri-coverage.md](siri-coverage.md) findings 1–3, [bus-bunching.md](bus-bunching.md) finding 2

> **Title:** Document (or make discoverable) four hard endpoint constraints that are currently found by trial and error
>
> Every hackathon participant rediscovered these independently. None is in the
> OpenAPI docs.
>
> 1. **`/route_timetable/list` rejects any date range over a single day**, and
>    times out server-side when unfiltered regardless of range.
> 2. **`/siri_vehicle_locations/list` accepts only one `line_ref` per request**,
>    while `/route_timetable/list`'s `line_refs` *does* accept a comma-separated
>    batch. The asymmetry is surprising and undocumented.
> 3. **There is a row cap between 15,000 and 20,000.** `limit=15000` succeeds;
>    `limit=20000` returns an immediate **500**. A 400 with a stated maximum, or
>    a documented cap, would save everyone the bisection.
> 4. **`stride.iterate()`'s `limit=` kwarg is client-side only** — the server
>    silently defaults to ~100 rows unless `limit` is *also* passed inside the
>    request params. This one is the most dangerous: it is a silent truncation,
>    not an error, so an analysis that doesn't know gets a plausible answer
>    computed from the first 100 rows.
>
> Happy to open a PR against the docs if that's the preferred route.

## H. Naive datetimes return 500 instead of 422

**Repo:** `open-bus-stride-api` · **Labels:** `bug`, `good first issue`

> **Title:** Passing a naive datetime to time-range filters returns 500 ("tzinfo is required") instead of a 4xx
>
> `/siri_vehicle_locations/list` and `/route_timetable/list` 500 with
> "tzinfo is required" when a time filter is given without a timezone. This is a
> client input error and should be a 422 with the field named. It is currently
> indistinguishable from a server fault, and every analysis in our repo carries
> a `_day_bounds()` helper written specifically to avoid it.

## I. Parameter name misspelled: `schedualed_start_time`

**Repo:** `open-bus-stride-api` · **Labels:** `good first issue`

> **Title:** `siri_rides__schedualed_start_time_from/to` is misspelled ("schedualed")
>
> Every consumer carries a `# sic` comment next to it. Suggest accepting
> `scheduled_start_time_from/to` as an alias, keeping the old spelling working,
> and marking it deprecated in the docs. Cheap, and it stops propagating the
> typo into every downstream codebase.

---

# Priority 3 — data content and coverage

## J. Null `start_time` on a minority of `/gtfs_rides/list` rows

**Repo:** `open-bus-stride-db` · **Labels:** `data research`

> A real minority of `/gtfs_rides/list` rows return with `start_time` (and
> `end_time`) null. A ride with no scheduled time cannot be timed or
> ghost-checked; left in a planned-vs-actual join it falls through as a spurious
> unmatched "cancellation". Looks like a GTFS source gap rather than a SIRI
> matching problem. Worth quantifying network-wide — we only have per-query
> counts.

## K. Five operators never appear in the tracking feed

**Repo:** `open-bus-stride-db` + `open-bus-map-search` · **Source:** BusAnalysis **F9**, corroborated by [siri-coverage.md](siri-coverage.md) finding 7

> Three operators are **never** present in SIRI across 2023-01 → 2026-07, and two
> more are under 1% covered. Together: **2.74M scheduled rides, ~2.3% of national
> planned volume**.
>
> Their buses may be running perfectly. Nothing reports them, so nothing about
> them can be measured — and counting them as cancellations is most of how a
> national non-execution figure goes from 5.2% to 7.4%.
>
> **For map-search:** these operators should be visibly marked as unmeasured
> rather than appearing in reliability rankings with a terrible score.

## L. GTFS import retains the previous release, doubling planned counts

**Repo:** `open-bus-pipelines` · **Source:** BusAnalysis **F8**

> On affected dates `gtfs_ride` holds two near-complete daily schedules under a
> single `gtfs_route.date` — same trip, same route row, same `start_time`, with
> `journey_ref` suffixes stamping both the current and previous release. 85% of
> days are clean; **50 days exceed 1.5× the expected planned count and 36 exceed
> 1.8×**, scattered across 2023-02 → 2026-07 with no era pattern.
>
> Planned-ride denominators are ~2× too high on those dates.

---

# Suggested filing order

1. **A + A2** — live wrong answer in hasadna's own UI. A is a comment on an
   existing issue, A2 is new. Do these first.
2. **B** — silent wrong results, trivially reproducible, two independent hits.
3. **G, H, I** — cheap documentation/DX wins that build credibility before the
   heavier data issues.
4. **C, D** — the big ETL ones. Both need BusAnalysis's census numbers, which
   means asking @lihay7 to share or re-derive them; **do not cite a private repo's
   figures publicly without asking first.**
5. **E, F** — semantics and interpretation; frame as research, not bug reports.
6. **J, K, L** — quantify further before filing.

## Before filing anything

- [ ] Confirm with the original authors (noamf2001, yuvalko1, orion, @lihay7) that
      they're happy to be credited, and how.
- [ ] Get @lihay7's permission before quoting BusAnalysis figures — the repo is
      private.
- [ ] Re-verify each finding against the live API on filing day. Several date
      windows here are hackathon-specific, and [stride-api#54](https://github.com/hasadna/open-bus-stride-api/issues/54)
      shows fixes do ship.
- [ ] Read [stride-api#43](https://github.com/hasadna/open-bus-stride-api/issues/43)
      ("Missing data") and [map-search#175](https://github.com/hasadna/open-bus-map-search/issues/175)
      ("explain weird patterns in the data") — some of these may belong as comments
      there rather than as new issues.
- [ ] Replace the `(…)` source placeholders in draft A with real permalinks once
      this repo is public at its new home
      ([hasadna/open-bus-hackathon-26](https://github.com/hasadna/open-bus-hackathon-26)).
