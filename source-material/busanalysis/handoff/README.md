# For the maintainer receiving this

You are getting an external analysis built entirely on hasadna's open data, plus five defect
reports about the data itself. This page is the 5-minute orientation; nothing else in the repo
needs to be read first.

## What to do, in order

**1. Look at the results (30 seconds, no setup).**
Open `../report/dashboard/brief.html` — one screen, four findings.
If you want depth, `../report/dashboard/index.html` is the full six-tab version with every caveat.
Both are committed and self-contained; double-click, no server.

**2. Read the five defect reports (15 minutes).**
These are the part that is *for you*. Each is a complete issue body, ready to paste into your
tracker, with reproduction, evidence, and a suggested fix:

| Issue | What it is | Why it is first or last |
|---|---|---|
| [F1](issues/F1-stored-linkage.md) | the SIRI→GTFS matching job has written **zero** matches since Oct 2024 (~61.5M rides) | **start here** — it is the largest, and the data is intact, so a backfill fixes it |
| [F8](issues/F8-stale-gtfs-release.md) | the GTFS import keeps the previous release, doubling planned counts on 50 days | affects your own dashboards' planned counts today |
| [F6](issues/F6-duplicate-rides.md) | 2.6% of `siri_ride` rows are duplicate journeys, 4× worse since 2023 | downstream of the known drift bug (#390) |
| [F7](issues/F7-enrichment-flag.md) | an enrichment job stopped for 18 months; the field is widely mis-readable as "vehicle went dark" | cheapest fix: document the field's meaning |
| [F9](issues/F9-coverage-holes.md) | five operators never appear in the feed — 2.3% of the national schedule | may be contractual rather than a bug; we cannot tell from outside |

**3. Answer what you can of [QUESTIONS_FOR_HASADNA.md](QUESTIONS_FOR_HASADNA.md).**
Eight questions where one sentence from inside hasadna would remove a caveat we currently have to
publish. Question 1 (was a matching migration started in 2024-09?) would change F1's diagnosis;
question 2 (does the published rate credit war exemptions?) is the single largest unresolved
attribution in the whole analysis.

**4. Only if you want to run it:** [`../docs/REPRODUCE.md`](../docs/REPRODUCE.md) marks every
command as verified or unrun. The 60-second path needs no credentials.

## What this analysis actually claims

Four service findings, each with a fix that requires no new buses:

1. **5.2%** of scheduled departures never appear in the tracking record (±5 min, 116.4M rides,
   1,306 days). Widening to ±60 min moves it to 4.9% — these are cancellations, not delays.
2. **~1.7×**: the sparsest lines lose 7.8% of departures vs 4.6–4.8% on mid-frequency lines,
   after the density control.
3. **5.0% vs 1.5%**: our reconstructed non-execution rate for 2024-H1 against the ministry's own
   published figure, same period, same ±30 min basis.
4. **4.2 minutes** median extra waiting beyond the published timetable's promise.

## What it does *not* claim — please hold us to these

- **Every number is about the tracking record, not the road.** A ride the feed never saw counts as
  missing. There is no independent national bound on the feed's own completeness, so we never say
  "the bus didn't run".
- **Nothing here is a punctuality measure.** The record holds no observed departure times; the time
  differences available are scheduled-against-scheduled. Metric M2 is a *waiting* measure.
- **No operator is ranked as bad.** Route density, network composition and coverage holes move
  these numbers mechanically, and the data defects above move them more than any operator does.
- **The 1.7× periphery figure is national and pooled.** It inverts in some cities (Be'er Sheva
  reads 0.77×). It must not be quoted per city.
- **Friday/Saturday rates are unverified** and deliberately unpublished — the short-service-day
  envelope could inflate them mechanically.

## Two things we would ask

**On the defect reports:** they are written as contributions, not complaints. The data is a
volunteer-built public good, and every finding in this project exists *because* stride exists. If
any report is wrong, we would rather be told than have it sit in a tracker.

**On the workarounds:** for each defect we describe what we did instead. Those workarounds are load-
bearing for our published numbers — if you judge one to be unsound, our figures inherit that
problem, and we would want to know.

## Provenance and licence

MIT ([`../LICENSE`](../LICENSE)). Built on stride and the MoT's published GTFS and SIRI feeds.
Prior art this positions against — `open-bus-map-search`, markav.net, Transit Analyst Israel — is
catalogued in [`../data/registry/prior_art.md`](../data/registry/prior_art.md).

Nothing in this package has been sent anywhere. No issue has been filed, no data published upstream.
