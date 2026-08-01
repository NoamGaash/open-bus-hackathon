# Algorithms — what each hackathon solution actually does

One file per solution. Each documents the **author**, the **algorithm**, the
**reasoning** behind the design choices, the **findings** (each with a stated
confidence level), and **criticism** — where the output should not be trusted,
and what would have to change for it to be.

These are working notes for two audiences: whoever picks a POC up for
consolidation upstream, and whoever has to defend a number in the
presentation. Neither is served by a document that only says what worked.

## Index

| Solution | Author | Cards | What it answers |
|---|---|---|---|
| [bus-arrival-reliability.md](bus-arrival-reliability.md) | noamf2001 | 3 | Where is the timetable optimistic? Where does the bus lose time? Which segments break at rush hour? |
| [schedule-adherence.md](schedule-adherence.md) | yuvalko1 | 3 | How much does the same departure vary day to day, geographically and per day? |
| [siri-coverage.md](siri-coverage.md) | yuvalko1 | 1 | What share of planned stops actually got a real-time GPS ping, by hour? |
| [gps-trace-map.md](gps-trace-map.md) | yuvalko1 | 1 | What does one real ride's raw GPS trail look like? |
| [poisson-arrival-regularity.md](poisson-arrival-regularity.md) | yuvalko1 / Yuval | 1 | Does headway spacing decay into a random Poisson process downstream? **Currently broken.** |
| [days-with-no-cancellations.md](days-with-no-cancellations.md) | orion | 1 (+CLI) | What fraction of the last 15 days did a line run with zero cancellations? |
| [service-violations.md](service-violations.md) | team | 2 | Ghost rides, early departures, late departures — the three fineable failure modes. |
| [bus-bunching.md](bus-bunching.md) | team | 1 | How evenly spaced were consecutive buses against the line's own scheduled spacing? |
| [route-divergence.md](route-divergence.md) | team | 2 | Which buses strayed from the planned route, and where? |
| [busline-usage-anomaly.md](busline-usage-anomaly.md) | team | 1 | Which lines carry unusually many/few riders for their peer group and hour? |
| [service-by-operator.md](service-by-operator.md) | example | 1 | Planned vs actual rides per day — the worked example. |

Related, not a hackathon solution: [`docs/busanalysis.md`](../docs/busanalysis.md)
summarises `lihay7/BusAnalysis`, an independent national reconstruction on the
same data whose five upstream defect reports overlap heavily with what these
cards hit.

## Upstream issues

[upstream-issues.md](upstream-issues.md) collects every defect these solutions
ran into, deduplicated and written as paste-ready issue drafts, with the repo
each one belongs in. That is the prep for filing against
[hasadna/open-bus-map-search](https://github.com/hasadna/open-bus-map-search)
and its sibling repos.

## Card status

Every registered analysis was run once with a default `AnalysisRequest` on
2026-08-01. **16 of 17 cards render; 1 errors.**

| Result | Cards |
|---|---|
| ✅ renders | `bus-segment-reliability`, `bus-marey-diagram`, `bus-hourly-heatmap`, `bus-bunching`, `busline-usage-anomaly`, `days-with-no-cancellations`, `service-by-operator`, `gps-trace-map`, `route-divergence`, `route-divergence-map`, `schedule-adherence-average`, `schedule-adherence-map`, `schedule-adherence-by-day`, `service-violations`, `service-violations-by-day`, `siri-coverage` |
| ❌ errors | `poisson-arrival-regularity` — `AttributeError: 'LineSpec' object has no attribute 'short_name'`. One-line fix, see [poisson-arrival-regularity.md](poisson-arrival-regularity.md#status) |

Note that `./dev check` only verifies that modules **import**, so it does not
catch a card that imports cleanly and raises at runtime. A smoke test that runs
every registered analysis once and asserts `kind != "error"` would have caught
this one.

Rendering is not the same as being right — `service-by-operator` renders a
confident chart showing ~0% of buses ran, which is a broken upstream column and
not a fact about Israel. See [service-by-operator.md](service-by-operator.md).

## Confidence levels

Every finding below carries one of these. They describe **how much the finding
would survive scrutiny**, not how large the effect is.

| Level | Means |
|---|---|
| **High** | Directly observed in the data, on a population large enough that sampling isn't the explanation, and the mechanism is understood. Would survive being quoted in public. |
| **Medium** | Observed and reproducible, but on one line / a few days / one operator, or resting on a proxy whose error is understood but not bounded. Directionally trustworthy; the exact number is not. |
| **Low** | Observed once, or on a sample too small to separate from noise, or resting on a proxy that could be an artifact. Worth investigating, not worth quoting. |
| **Not a finding** | An artifact of the data pipeline that was mistaken for a finding at some point during the hackathon, and is recorded here so nobody rediscovers it as real. |

A structural rule that applies to nearly everything here: **these are claims
about the record, not about the road.** A ride SIRI never saw is
indistinguishable from a ride that never ran. Where a card counts "missing"
rides, the finding is about what the tracking feed contains.

## Shared method, shared caveats

Most cards converge on the same skeleton, for the same reasons — worth reading
once rather than in every file:

- **Line resolution.** A "line" (`route_short_name` like `480`) is *not* one
  thing. It is many `line_ref`s — one per direction × route alternative ×
  operator — and the set changes over time (line 480 was 2 refs in Nov 2025 and
  8 in Jul 2026). Cards resolve `route_short_name → line_ref` through
  `/gtfs_routes/list` **for the window being analysed**, and most take the first
  match, which is a real simplification.
- **SIRI lag.** Ingestion runs ~3 days behind live. Every card clamps its window
  back by `LAG_DAYS = 3`; without it, a perfectly healthy line returns zero
  pings and reads as a total service collapse.
- **Weekend exclusion.** Israeli bus service is thin by design on Fri/Sat, so
  headway- and reliability-based cards drop `weekday() in (4, 5)`.
- **Duplicate pings.** Overlapping SIRI snapshots repeat the same physical
  observation — measured at ~10% of rows. Every card that touches raw pings
  dedups on `(siri_ride__id, recorded_at_time, lat, lon)`.
- **First-ping-as-departure.** No card observes a real "doors closed" moment.
  Actual departure is inferred from GPS, and the naive version of that inference
  is wrong in a specific, measured way — see
  [service-violations.md](service-violations.md), which is where the artifact
  was found and corrected.
- **Cost caps.** These run as live dashboard cards, not batch jobs. Where an
  original notebook scanned 90 days, the port scans 2–21 and says so in its
  notes. Lower confidence is the price, and it is disclosed on the card rather
  than hidden.
