# Live re-verification, 2026-08-01 (before filing)

| Defect | Result | Evidence |
|---|---|---|
| A `total_actual_rides` = 0 | CONFIRMED | group_by, 4 dates: planned 121420/122088/53260/27327, actual 0/0/0/0 |
| B `route_short_name` ignored | CONFIRMED | 400 rows / 202 line_refs identical filtered vs unfiltered |
| E `actual_start_time` is a flag | CONFIRMED | 676 rows with both: 676 identical, 0 differing |
| E2 unplanned rides (planned null) | CONFIRMED, rate lower | 1.4% (write-up said 3-6%) |
| G1 route_timetable >1 day | CONFIRMED | 1-day OK; 3-day -> 500 |
| G3 row cap 15k/20k | CONFIRMED | 15000 OK; 20000 -> 500 |
| G4 silent default page size | CONFIRMED, varies | agg/list 1000, gtfs_routes 100, agencies 36 |
| H naive datetime | CONFIRMED | 500 Internal Server Error |

## Corrections to the hackathon write-ups (do NOT quote the old numbers)

1. orion's planned totals (3,498 / 3,510 / 3,227 / 3,927) were computed from
   `/gtfs_rides_agg/list` WITHOUT an explicit limit, so they are truncated
   samples of the default 1000-row page, not network totals. Real network
   planned totals via group_by are ~27k-122k. The actual=0 conclusion is
   unaffected and holds at every page size and via group_by.
2. The default page size is 1000 for /gtfs_rides_agg/list and 100 for
   /gtfs_routes/list - it varies per endpoint. The source repo's "~100 rows"
   was right for one endpoint, not universally.
3. Unplanned-ride rate measured at 1.4% on line 480 (write-up said 3-6% on
   line 2259). Both may be true per-line; quote as "1-6%, line-dependent".

---

# Phase 2 reconciliation, 2026-08-02

Read `lihay7/BusAnalysis` handoff issues over `gh api` (we have access) and compared
against the public rendering in `frontend/public/editorial.html`.

## F9 — #1780 needs a SUBSTANTIVE correction

The handoff doc **contradicts itself**. Its prose says "three operators are never
present and two more are under 1% covered"; its own evidence table shows:

| operator | scheduled rides | share absent |
|---|---|---|
| Cable Express | 2.11M | 100% |
| Kfir | 0.37M | 100% |
| Carmelit | 0.18M | 100% |
| Dan Netivim | 0.05M | 100% |
| Metro Kav Taxis | 0.02M | 82% (shared-taxi mode) |

So: **four at 100%, a fifth at 82%** — the editorial's framing is the accurate one.
I filed the prose version. Also missed:
- The set is **derived, not hardcoded**: pooled matched share < 50% over the window
  selects operator refs 20, 21, 33, 39, 91.
- Naive national gap **7.36% vs 5.19% corrected** — ~2.2pp of the difference.
- Includes an **East Jerusalem cluster**, so the gap is not evenly distributed.

## F8 — #1781 was CORRECT; both counts are real, they measure different things

"50 days exceed 1.5×, 36 exceed 1.8×" is the ratio-threshold count (accurate).
The editorial's "22 service days" is the count where the stale-release mechanism was
confirmed. Worth citing both. Additional evidence not filed:
- Every major operator sits at ~2.0× on affected days — not operator-specific.
- The actual-ride count stays flat through every doubled day, which **rules out
  "SIRI coverage halved"** as the alternative explanation.
- Refuted alternatives, so nobody repeats the work: route_alternative duplication
  (zero duplicate route rows per date), genuinely-new-trips, operator concentration.

## F8 also answers an open question in #1779

I filed #1779 (null `start_time` on `/gtfs_rides/list`) saying "only per-query counts
were recorded, never a network-wide rate". F8 has it: **first seen 2023-01-04, present
on 134 of 1,307 days.** Longstanding, not a recent regression.

## F6 — #1776 figures were right; additions worth making

3.93% / 2.56% / 66× / quadrupled all confirmed. Missed:
- The trend is ~1.4% (2023) → ~5.9% (2026).
- The shares are **lower bounds** — the grouping key is conservative.
- Because the skew is 66×, the error **does not cancel out in a league table**.

## F7 — #1775 figures were right; additions worth making

Missed: **49.21% of all `siri_ride` rows** have the field null overall, and four
independent signs it is a job outage rather than fleet behaviour — perfect synchrony
across ~39 operators, only 2.6× per-operator spread in the populated era, nulls
flipping day-quantised during a 2026-06 backfill, and `duration_minutes` following the
identical curve.

## Verdict on the "unverifiable" caveat

Wrong in all four. The findings are published in this repo at
`frontend/public/editorial.html` (public, tracked). Replace the caveat with a pointer
to that page and inline the specific numbers so each issue stands alone.
