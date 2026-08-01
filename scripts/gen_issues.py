"""Generate the hackathon issue bodies for hasadna/open-bus-map-search.

Writes one markdown file per issue to the scratchpad, plus a manifest.json the
filing step reads. Nothing here touches GitHub — review the output first.

    uv run python scripts/gen_issues.py <outdir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from string import Template
from textwrap import dedent

HACK = "https://github.com/hasadna/open-bus-hackathon-26"
RAW = "https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img"
ALGO = f"{HACK}/blob/main/algorithms"

BANNER = dedent("""\
    > ### ⚠️ AI-generated draft — needs human validation
    >
    > This issue was **written by an AI agent** from materials produced during the
    > hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
    > under hackathon conditions, and **has not been peer-reviewed**. Figures,
    > endpoint behaviour and conclusions all need independent verification before
    > anyone acts on them or quotes them publicly.
    >
    > **Please validate before implementing. Corrections very welcome.**
    """)

VERIFIED = (
    "*Re-verified against the live Stride API on 2026-08-01 immediately before "
    "filing; the reproduction below is the exact check that was run.*"
)

# handle -> (display, source repo url, private?)
PEOPLE = {
    "noamf2001": ("noamf2001", "https://github.com/noamf2001/PublicTransportHackathon", True),
    "yuvalko1": ("yuvalko1", "https://github.com/yuvalko1/talpiot-hackathon-public-transportation", True),
    "Broundal": ("Broundal", HACK + "/tree/main/orion", False),
    "lihay7": ("lihay7", "https://github.com/lihay7/BusAnalysis", True),
    "team": ("the hackathon team", HACK, False),
}


def credit(handle: str, doc: str) -> str:
    display, repo, private = PEOPLE[handle]
    who = f"analysis by {display}" if handle != "team" else "analysis by the hackathon team"
    priv = " *(private repo — ask the owner for access)*" if private else ""
    return dedent(f"""\
        ---

        **Credit & provenance**
        Found during the hasadna Open Bus hackathon, July 2026 — {who}.
        · Method, evidence and caveats: [`algorithms/{doc}`]({ALGO}/{doc})
        · Original work: {repo}{priv}
        · Issue drafts and the full defect list: [`algorithms/upstream-issues.md`]({ALGO}/upstream-issues.md)
        """)


def body(*parts: str) -> str:
    """Join sections. Each part is dedented independently, so a multi-line value
    spliced into one part can never flatten another part's indentation."""
    out = []
    for p in parts:
        if p and p.strip():
            out.append(dedent(p).strip())
    return "\n\n".join(out) + "\n"


def shot(card: str, caption: str) -> str:
    return f"![{caption}]({RAW}/{card}.png)\n\n*{caption} — screenshot of the hackathon dashboard card.*"


def ind(text: str, pad: str = "    ") -> str:
    """Indent a multi-line value to match the surrounding dedent block.

    dedent() strips the longest common leading whitespace, so splicing a
    flush-left multi-line string into an indented template collapses the
    common prefix to "" and dedent silently becomes a no-op.
    """
    lines = text.strip().splitlines()
    # The template already supplies the first line's indent via its own literal
    # prefix, so indenting it again leaves it 4 spaces proud after dedent().
    return "\n".join(
        [lines[0]] + [pad + ln if ln.strip() else ln for ln in lines[1:]]
    )


ISSUES: list[dict] = []


def add(num, title, labels, md, group):
    ISSUES.append({"n": num, "title": title, "labels": labels, "body": md, "group": group})


# ── Group 1: defects ─────────────────────────────────────────────────────────

add(1, "Dashboard charts show ~0% actual rides — `total_actual_rides` is unpopulated upstream",
    ["bug", "data research", "frontend", "backend"],
    body(BANNER, dedent(f"""\
    ## Symptom

    `totalActualRides` is consumed in five places, all fed by `useGroupBy` →
    `/gtfs_rides_agg/group_by` (`src/api/groupByService.ts`):

    - `src/pages/dashboard/AllLineschart/AllLinesChart.tsx`
    - `src/pages/dashboard/WorstLinesChart/WorstLinesChart.tsx`
    - `src/pages/dashboard/ArrivalByTimeChart/DayTimeChart.tsx`
    - `src/pages/operator/OperatorGaps.tsx`
    - `src/pages/DataResearch/DataResearch.tsx`

    That column is **0 for every row, network-wide**. The rendered result is not an
    empty state — it is a confident chart showing that essentially no bus in Israel ran.

    Here is the same defect reproduced on the hackathon dashboard, which uses the
    same endpoint. Note the flat `Actual` series and the caption *"Overall 0.0% of
    planned rides were observed"*:

    {ind(shot("service-by-operator", "Planned vs actual rides — Actual is flat at zero"))}

    ## Evidence

    {VERIFIED}

    ```python
    from openbus_hack import stride
    for d in ["2026-07-01", "2026-06-15", "2026-04-01", "2025-11-01"]:
        rows = stride.get("/gtfs_rides_agg/group_by",
                          {{"date_from": d, "date_to": d,
                           "group_by": "operator_ref,gtfs_route_date"}})
        print(d, sum(r["total_planned_rides"] or 0 for r in rows),
                 sum(r["total_actual_rides"] or 0 for r in rows))
    ```

    | Date | Σ `total_planned_rides` | Σ `total_actual_rides` |
    |---|---|---|
    | 2026-07-01 | 121,420 | **0** |
    | 2026-06-15 | 122,088 | **0** |
    | 2026-04-01 | 53,260 | **0** |
    | 2025-11-01 | 27,327 | **0** |

    **This is not ingestion lag.** Control: line 2259 on 2026-07-29 reports
    `total_actual_rides = 0` in the aggregate, while `/rides_execution/list` for the
    same line and date returns real `actual_start_time` values and zero
    cancellations. Actuals exist at ride level; they are not being rolled into the
    aggregate.

    `num_planned_rides` is populated and cross-checks well against the ride-level
    endpoint, so the aggregate remains usable **as a planned-ride denominator**.

    ## Upstream

    Root cause belongs to the API/ETL — hasadna/open-bus-stride-api#49 reports the
    same thing for a single date (2025-09-17); the evidence above extends it to nine
    months, network-wide, with a control. This issue tracks the **frontend symptom**.

    Closely related: #24 (better indication of partial data in the UI) — that is the
    general ask; this is one concrete, currently-live instance of it.

    ## Suggested interim mitigation

    Until the upstream column is fixed, detect
    `totalActualRides === 0 && totalPlannedRides > 0` across a whole response and show
    a data-quality banner instead of plotting a zero series.
    """), credit("team", "service-by-operator.md")), 1)

add(2, "`stride-api:` `/siri_vehicle_locations/list` accepts `gtfs_route__route_short_name` and silently ignores it",
    ["bug", "backend"],
    body(BANNER, dedent(f"""\
    ## What happens

    Passing `gtfs_route__route_short_name` to `/siri_vehicle_locations/list` does not
    filter. It does not error, does not warn, and does not return an empty set — it
    returns **every ping in the time window, from every line in the country**, which
    the caller then treats as belonging to their line.

    ## Evidence

    {VERIFIED}

    ```python
    base = {{"recorded_at_time_from": "2026-07-28T08:00+03:00",
            "recorded_at_time_to":   "2026-07-28T09:00+03:00", "limit": 400}}
    unfiltered = stride.get("/siri_vehicle_locations/list", base)
    filtered   = stride.get("/siri_vehicle_locations/list",
                            {{**base, "gtfs_route__route_short_name": "23"}})
    ```

    | Query | rows | distinct `siri_route__line_ref` |
    |---|---|---|
    | unfiltered | 400 | **202** |
    | with `gtfs_route__route_short_name=23` | 400 | **202** |

    Byte-identical result sets. The parameter has no effect.

    ## Why it matters

    How it was originally caught: an off-route analysis reported buses **50 km from
    their route on 97.7% of pings**. The buses were fine — the pings belonged to other
    lines. That was only obvious because the number was absurd. Anything computing a
    rate, a median or a coverage percentage gets a **plausible wrong answer** with no
    indication anything went wrong. Two hackathon participants hit this independently.

    The working filter is `siri_routes__line_ref` (a `line_ref`, not a
    `route_short_name`), which requires resolving through `/gtfs_routes/list` first.

    ## Requested

    Either apply the filter, or reject the parameter with a 4xx. Silently ignoring a
    filter is the worst of the three options.

    Possibly the same class of bug as hasadna/open-bus-stride-api#23 (closed), where
    `/siri_rides/list` did not join on `line_ref`/`operator_ref`.
    """), credit("team", "route-divergence.md")), 1)

add(3, "`pipelines:` SIRI→GTFS ride-matching has written no matches since 2024-10",
    ["bug", "backend", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What happens

    Two related symptoms, observed independently by two hackathon projects.

    **1. The ride link.** `siri_ride.gtfs_ride_id` and its three siblings
    (`route_gtfs_ride_id`, `scheduled_time_gtfs_ride_id`, `journey_gtfs_ride_id`) stop
    being populated together. Reported as healthy through 2024-08, degrading 2024-09,
    effectively zero 2024-10 → 2026-07. The raw feed never stopped — roughly 2.9–3.1M
    `siri_ride` rows per month are still created.

    **2. The enrichment.** `siri_ride.first_vehicle_location_id` reported null for
    100% of rides across 18 consecutive months (2024-12 → 2026-05, ~49.4M rides), with
    `duration_minutes` tracking the same pattern.

    A hackathon analysis independently found these columns *"inconsistently NULL —
    present for some days, absent for others, for identical, genuinely-tracked
    rides"*, and had to derive planned-vs-actual from raw GPS pings instead.

    ## Interpretation risk worth flagging separately

    `first_vehicle_location_id` **looks** like it means "this vehicle never reported
    its position", and it is easy to build a per-operator transmission metric on it.
    It does not mean that — it encodes **whether the enrichment job has processed that
    day**. It is a processing-state flag, not a property of the bus.

    ## Confidence

    The 18-month and 21-month figures come from a separate hackathon project
    (BusAnalysis by lihay7) whose repository is currently private, so **the census
    numbers cannot be independently checked from this issue alone.** What *was*
    reproduced in the shared hackathon repo is the qualitative finding: these columns
    are unreliable enough that every planned-vs-actual analysis had to bypass them.

    Treat the precise dates and percentages as **needing confirmation against the
    database** before anyone acts on them.
    """), credit("lihay7", "service-violations.md")), 1)

add(4, "`stride-db:` duplicate `siri_ride` journeys and repeated location rows",
    ["bug", "data research"],
    body(BANNER, dedent(f"""\
    ## What happens

    **Ride level.** The same physical journey is stored more than once. Reported at
    3.93% of rides sitting in a duplicated `(siri_route_id, journey_ref, service day)`
    group and 2.56% of all rows being surplus duplicates, over a full census of
    ~116.3M rows — 66× skewed across operators, and roughly quadrupling from 2023 to
    2026. Attributed to `scheduled_start_time` drift: when a journey's scheduled start
    drifts, a **new** row is written rather than the existing one updated.

    **The same shape appears in GTFS.** On 2026-07-26 one line returned 259
    `/rides_execution/list` rows for 127 distinct `planned_start_time`s (some ×4)
    under 255 distinct `gtfs_ride_id`s — one physical departure emitted under several
    ride ids. Any naive count of planned rides double-counts, and a duplicated row
    with a null actual becomes a phantom cancellation.

    **Location level.** Overlapping SIRI snapshots repeat the same physical
    observation — same `siri_ride__id`, same `recorded_at_time`, same lat/lon — at
    roughly 10% of rows. Harmless for `min()`/`max()` aggregations; **not** harmless
    for anything weighted or counted. One hackathon analysis computes a
    distance-weighted average position, where a duplicated ping carries its weight
    twice and drags the result.

    ## Evidence of the workaround spreading

    Every analysis in the hackathon repo now dedups on
    `(siri_ride__id, recorded_at_time, lat, lon)` as a matter of course:

    ```python
    pings = pings.drop_duplicates(
        subset=["siri_ride__id", "recorded_at_time", "lat", "lon"])
    ```

    That is a workaround every consumer is independently reinventing, which is the
    strongest argument for fixing it at the source.

    ## Confidence

    The ride-level census figures come from a hackathon project (BusAnalysis by
    lihay7) whose repository is currently private — **treat them as needing
    confirmation.** The GTFS duplicate-departure observation and the ~10% duplicate
    ping rate were reproduced in the shared hackathon repo.
    """), credit("lihay7", "days-with-no-cancellations.md")), 1)

add(5, "`stride-api:` `rides_execution.actual_start_time` always equals `planned_start_time`",
    ["documentation", "data research"],
    body(BANNER, dedent(f"""\
    ## What happens

    `actual_start_time` never carries an observed departure time. Where both fields
    are present, it is byte-identical to `planned_start_time`.

    ## Evidence

    {VERIFIED}

    Line 480, all resolved `line_ref` variants, 2026-07-15 → 2026-07-29:

    | | count |
    |---|---|
    | rows with **both** planned and actual | 676 |
    | `actual_start_time == planned_start_time` | **676** |
    | `actual_start_time != planned_start_time` | **0** |
    | cancelled (`actual_start_time` null) | 4 |
    | unplanned (`planned_start_time` null) | 10 (1.4% of rows) |

    ## Why this still matters

    The field is genuinely useful as-is — null means the ride did not run, which is
    the cleanest cancellation signal in the API, and a working
    days-without-cancellations score was built on exactly that. But the **name
    promises an observed departure time and it is not one**, so the endpoint can never
    be used for delay or punctuality work.

    ## Requested

    Either populate it from SIRI, or rename/document it as a `did_run`-style boolean
    so nobody builds a punctuality metric on it.

    Related: #19 (improve rides reliability metric by adding "actual start time" ETL)
    — that issue is arguably the fix for this one.

    ## Note on a possibly-related closed issue

    hasadna/open-bus-stride-api#54 (`rides_execution/list` used UTC midnight instead of
    Israel midnight) is closed. The hackathon code still carries a client-side
    re-filter working around fuzzy service-date boundaries; if #54's fix shipped, that
    workaround may now be unnecessary. Worth confirming.
    """), credit("Broundal", "days-with-no-cancellations.md")), 1)

add(6, '"First SIRI ping" is not departure time — the feed reports a vehicle while it is still parked',
    ["data research", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## The finding

    On a sampled line, **~80% of rides' raw first pings** landed at almost exactly
    **−30 or −5 minutes** before scheduled departure, with
    `distance_from_journey_start == 0` and `velocity == 0` — the vehicle parked at the
    origin stop, boarding.

    Taking that first ping as "actual departure" made **~90% of matched rides look
    early**. That is not early running; it is the operator feed's reporting lead time.

    Two sharp clusters at fixed offsets, rather than a smooth distribution, is what
    identifies this as a feed convention rather than a real phenomenon.

    ## The fix that worked

    Use the first ping where the vehicle has actually started moving:

    ```python
    dist = pd.to_numeric(pings["distance_from_journey_start"], errors="coerce").fillna(0)
    vel  = pd.to_numeric(pings["velocity"], errors="coerce").fillna(0)
    moving = pings[(dist > 0) | (vel > 0)]
    departure = moving.groupby("siri_ride__id")["recorded_at_time"].min()
    ```

    Fall back to the raw first ping only when the vehicle was never observed moving,
    and flag those rides as unreliable.

    ## Why file this here

    Filing as research/documentation rather than a bug — the feed is behaving as
    operators report it. But **any consumer computing departure punctuality from
    first-ping is currently measuring the wrong thing**, and nothing in the docs says
    so. This is the most reusable single result from the hackathon.

    Worth checking whether any דאטאבוס metric derives a departure time this way.
    """), credit("team", "service-violations.md")), 1)

add(7, "`stride-api:` document four undocumented endpoint constraints",
    ["documentation", "backend"],
    body(BANNER, dedent(f"""\
    Every hackathon participant rediscovered these by trial and error. None appears
    in the OpenAPI docs. {VERIFIED}

    ### 1. `/route_timetable/list` rejects any date range over a single day

    ```
    1-day range  -> 200 OK
    3-day range  -> 500 Internal Server Error
    ```

    It also times out server-side when unfiltered, regardless of range.

    ### 2. `/siri_vehicle_locations/list` accepts only one `line_ref` per request

    while `/route_timetable/list`'s `line_refs` **does** accept a comma-separated
    batch. The asymmetry is surprising and undocumented.

    ### 3. There is a row cap between 15,000 and 20,000

    ```
    limit=15000 -> 200 OK, 15000 rows
    limit=20000 -> 500 Internal Server Error
    ```

    A 400 naming the maximum, or a documented cap, would save everyone the bisection.

    ### 4. The default page size is silent, and varies per endpoint

    Omitting `limit` does not return everything and does not warn:

    | Endpoint | rows returned with no `limit` |
    |---|---|
    | `/gtfs_rides_agg/list` | **1,000** |
    | `/gtfs_routes/list` | **100** |
    | `/gtfs_agencies/list` | 36 (appears complete) |

    **This is the most dangerous of the four** because it fails quietly: an analysis
    that does not know gets a plausible answer computed from a truncated page. It
    already bit this hackathon — a planned-ride total quoted in our own write-up
    turned out to be a truncated 1,000-row sample rather than a network figure.

    Note `stride.iterate()`'s `limit=` kwarg is client-side only; the server default
    applies unless `limit` is *also* passed inside the request params.

    ## Requested

    Document all four. Happy to open a PR against the docs if that is the preferred
    route.
    """), credit("yuvalko1", "siri-coverage.md")), 1)

add(8, "`stride-api:` naive datetimes return 500 instead of a 4xx",
    ["bug", "good first issue", "backend"],
    body(BANNER, dedent(f"""\
    ## What happens

    Passing a datetime without a timezone to a time-range filter returns a 500.

    {VERIFIED}

    ```python
    stride.get("/siri_vehicle_locations/list", {{
        "recorded_at_time_from": "2026-07-28T08:00:00",   # no tzinfo
        "recorded_at_time_to":   "2026-07-28T09:00:00",
    }})
    # -> httpx.HTTPStatusError: Server error '500 Internal Server Error'
    ```

    The server-side message is `tzinfo is required`.

    ## Why it should be a 4xx

    This is client input error, not a server fault. A 422 naming the offending field
    would be self-explanatory; a 500 is indistinguishable from the API being broken,
    which is how it reads to a newcomer.

    Every analysis in the hackathon repo carries a `_day_bounds()` helper written
    specifically to avoid this:

    ```python
    def _day_bounds(day):
        start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=ZoneInfo("Asia/Jerusalem"))
        end   = dt.datetime.combine(day, dt.time(23, 59), tzinfo=ZoneInfo("Asia/Jerusalem"))
        return start.isoformat(), end.isoformat()
    ```
    """), credit("team", "siri-coverage.md")), 1)

add(9, "`stride-api:` `siri_rides__schedualed_start_time_*` is misspelled",
    ["good first issue", "backend"],
    body(BANNER, dedent(f"""\
    ## What happens

    The filter parameters on `/siri_vehicle_locations/list` are spelled
    **`schedualed`**:

    ```
    siri_rides__schedualed_start_time_from
    siri_rides__schedualed_start_time_to
    ```

    Every consumer carries a `# sic` comment next to it — there are four separate
    occurrences in the hackathon repo alone:

    ```python
    "siri_rides__schedualed_start_time_from": day_from,  # sic — API's own spelling
    ```

    ## Requested

    Accept `scheduled_start_time_from` / `_to` as an alias, keep the old spelling
    working, and mark it deprecated in the docs. Cheap, and it stops the typo
    propagating into every downstream codebase.
    """), credit("team", "service-violations.md")), 1)

add(10, "`stride-db:` null `start_time` on a minority of `/gtfs_rides/list` rows",
    ["data research"],
    body(BANNER, dedent(f"""\
    ## What happens

    A real minority of `/gtfs_rides/list` rows come back with `start_time` (and
    `end_time`) null. This looks like a GTFS source gap rather than a SIRI matching
    problem.

    ## Why it matters

    A ride with no scheduled time cannot be timed **or** ghost-checked. Left in a
    planned-vs-actual join it falls through as a spurious unmatched "cancellation",
    inflating any non-execution rate computed from it.

    The hackathon code drops them up front and reports the count, rather than letting
    them become phantom cancellations:

    ```python
    planned = planned.dropna(subset=["start_time"])
    ```

    ## What is not known

    Only per-query counts were recorded, never a network-wide rate. **Worth
    quantifying** — if it is a fraction of a percent it is a footnote; if it is
    several percent it materially affects every cancellation statistic.
    """), credit("team", "service-violations.md")), 1)

add(11, "`stride-db:` some operators never appear in the SIRI feed at all",
    ["data research", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What happens

    Reported: three operators are **never** present in SIRI across 2023-01 → 2026-07,
    and two more are under 1% covered. Together ~2.74M scheduled rides, about **2.3%
    of national planned volume**.

    Independently, a hackathon coverage analysis hit lines with zero SIRI coverage and
    had to special-case them, since 0% coverage reads as total service collapse when
    it actually means the line is not in the real-time feed.

    ## Why it matters

    Their buses may be running perfectly. Nothing reports them, so nothing about them
    can be measured — and counting them as cancellations is reportedly most of how a
    national non-execution figure moves from 5.2% to 7.4%.

    **For דאטאבוס specifically:** these operators should be visibly marked as
    *unmeasured* rather than appearing in reliability rankings with a terrible score.
    An operator with no feed currently looks identical to an operator that cancelled
    everything.

    ## Confidence

    The five-operator census comes from a hackathon project (BusAnalysis by lihay7)
    whose repository is currently private — **the operator list and the 2.3% figure
    need confirmation against the database.** The general phenomenon (lines with
    literally zero SIRI coverage) was reproduced in the shared hackathon repo.
    """), credit("lihay7", "siri-coverage.md")), 1)

add(12, "`pipelines:` GTFS import appears to retain the previous release, doubling planned counts on some dates",
    ["bug", "backend"],
    body(BANNER, dedent(f"""\
    ## What happens

    On affected dates `gtfs_ride` reportedly holds **two near-complete daily schedules
    under a single `gtfs_route.date`** — the same trip, the same route row, the same
    `start_time`, with `journey_ref` suffixes stamping both the current release and
    the previous one. The import retained the old release instead of replacing it.

    On clean days the two release stamps are complementary halves of one schedule. On
    broken days each stamp is a full day, so the date carries roughly twice the real
    schedule.

    ## Reported scale

    - 85% of days are clean (planned/actual ratio within [0.9, 1.1])
    - **50 days exceed 1.5×**, and **36 exceed 1.8×**
    - Scattered across 2023-02 → 2026-07 with no era pattern

    ## Why it matters

    Planned-ride denominators are ~2× too high on those dates. Any execution rate,
    cancellation rate or coverage percentage computed for an affected date is
    correspondingly halved.

    ## Confidence

    These figures come from a hackathon project (BusAnalysis by lihay7) whose
    repository is currently private, and this specific defect was **not** independently
    reproduced in the shared hackathon repo. **Treat as a lead to investigate rather
    than a confirmed finding** — a per-date planned-count histogram against
    `gtfs_route.date` would confirm or kill it quickly.
    """), credit("lihay7", "upstream-issues.md")), 1)


# ── Group 2: POC visualizations ──────────────────────────────────────────────

def poc(num, title, card, handle, doc, what, algo, placement, limits, nxt, labels):
    add(num, title, labels, body(BANNER, dedent(f"""\
    ## What it answers

    {ind(what)}

    {ind(shot(card, title))}

    ## How it works

    {ind(algo)}

    ## Where it could go in דאטאבוס

    {ind(placement)}

    *A suggestion, not a decision — page ownership is the maintainers'.*

    ## Known limitations

    {ind(limits)}

    ## Suggested next steps

    {ind(nxt)}

    ## Status

    The research is done and the numbers exist — a working implementation runs in the
    hackathon repo against the live Stride API. What is missing is a production-shaped
    version in this app.
    """), credit(handle, doc)), 2)


poc(13, "Segment reliability: where the timetable is optimistic", "bus-segment-reliability",
    "noamf2001", "bus-arrival-reliability.md",
    "For one line, the median measured travel time of each stop-to-stop segment "
    "against the planned duration, with the ride-to-ride interquartile spread as a "
    "whisker. Where a bar overshoots its marker, the schedule is optimistic about "
    "that stretch.",
    dedent("""\
    1. Resolve `route_short_name` → `line_ref` + `operator_ref` via `/gtfs_routes/list`.
    2. Pull planned times, stop coordinates and Hebrew stop names from `/route_timetable/list`.
    3. Pull GPS from `/siri_vehicle_locations/list`.
    4. **Derive arrival times** — the API serves none, so an arrival is the moment of
       the vehicle's closest approach to a stop's coordinates, interpolated between
       the two bracketing pings (±30 s).
    5. Aggregate per segment: median, p25, p75, planned duration, and a `confidence`
       verdict (`implausible value` / `few samples` / `patchy coverage` /
       `coarse GPS timing` / `loose stop match`).
    """),
    "`/line-profile` — it is a per-line diagnostic and that page already owns line "
    "identity. `/gaps_patterns` is the alternative if it should sit next to the other "
    "pattern views.",
    "Derived arrivals are ±30 s, so consecutive city stops under a minute apart are "
    "mostly noise on a single ride — the aggregate is the point. The first segment is "
    "systematically least trustworthy because buses idle at the terminal. Fetch cost "
    "is ~1–2 minutes per line, so this needs caching or pre-aggregation to be "
    "interactive.",
    "Roll the per-segment ratio up into a **per-operator punctuality metric** (see the "
    "scale-up issue) so operators can be compared, not just lines. A per-corridor view "
    "would also identify infrastructure bottlenecks shared across lines.",
    ["enhancement", "frontend"])

poc(14, "Marey time-space diagram for one line", "bus-marey-diagram",
    "noamf2001", "bus-arrival-reliability.md",
    "One trajectory per sampled ride, plotted against the schedule. Steep = moving, "
    "flat = stuck, and the width of the fan is the route's unreliability. It makes "
    "*where* a line loses time legible at a glance in a way no bar chart does.",
    dedent("""\
    1. Same shared fetch as the segment-reliability card.
    2. `elapsed_profiles(stop_events)` → per-ride (elapsed minutes, stop sequence) traces.
    3. `stop_coverage(stop_events)` → the share of rides where GPS resolved each stop.
    4. Draw up to 60 ride trajectories (past that the fan becomes a solid block) plus
       the planned profile, bold.
    5. Stops the GPS rarely resolved get **dimmed, italic axis labels** — trajectories
       through them are interpolation more than measurement.
    """),
    "`/single-line-map` as a companion view — the map answers *where the bus is*, this "
    "answers *when it got there*, and they read well side by side.",
    "Capped at 60 rides for legibility. Stop labels are long in Hebrew, which drove the "
    "stops-on-y-axis default. Same ±30 s derived-arrival limit as the segment card.",
    "Add a date-range comparator — the same line's fan before and after a timetable "
    "change is the clearest possible evidence that a retiming worked or did not.",
    ["enhancement", "frontend"])

poc(15, "Segment × hour heatmap: which segments break down at rush hour", "bus-hourly-heatmap",
    "noamf2001", "bus-arrival-reliability.md",
    "A segment × departure-hour matrix coloured by the actual/planned duration ratio. "
    "1.00 is exactly on schedule; above that the segment ran longer than the timetable "
    "allows. It localises congestion in both space and time simultaneously.",
    dedent("""\
    1. Same shared fetch.
    2. `segment_hour_matrix(ride_segments, min_samples)` → aligned ratio and count matrices.
    3. Colour diverging around a centre of 1.0.
    4. **Three distinct cell appearances**, deliberately: solid = enough rides,
       hatched = measured but under `min_samples`, blank = no usable ride at all.
       "One ride" and "no data" must not look alike.
    """),
    "`/gaps_patterns` — it is a pattern view by construction, and that page already "
    "frames time-of-day analysis.",
    "Cells on low-frequency lines rest on very few rides; hatching flags this but the "
    "≤10-day fetch window is what puts them there. Ratios outside 0.25–4.0 are treated "
    "as artifacts rather than traffic.",
    "Aggregate across all lines sharing a corridor to find **infrastructure** "
    "bottlenecks rather than line-specific ones — a junction that slows six lines at "
    "08:00 is a road problem, not a scheduling problem.",
    ["enhancement", "frontend"])

poc(16, "Schedule adherence: how much the same departure varies day to day", "schedule-adherence-average",
    "yuvalko1", "schedule-adherence.md",
    "Take one departure — same line, same time of day — and watch it across many days. "
    "Each faint line is one day; the bold dashed line is the GTFS plan and the bold "
    "solid line is the cross-day average. The width of the fan is how unreliable that "
    "specific departure is.",
    dedent("""\
    1. Anchor on a real departure time, then scan back day by day (default 21).
    2. **Canonical stop signature filter** — a day counts only if its stop sequence
       matches the reference day's exactly. One `line_ref` serves several stop
       patterns, and averaging across them silently blends different journeys.
    3. Match pings to stops by nearest stop, **gated to ±20 min** of that stop's
       planned elapsed time (distance alone mis-assigns on routes that loop back).
    4. Two guards on the average: a stop must be measured on at least half the matched
       days, and the result is clamped monotonic — a bus cannot reach a later stop
       earlier, so residual dips are mis-assignment, not a reversing bus.
    """),
    "`/line-profile` — it is inherently a single-line, single-departure view.",
    "Skipped days are reported by category (`no_plan` / `route_mismatch` / "
    "`no_actual`) so \"different journey\" stays distinct from \"missing data\". The "
    "source notebook required 20 matched days before averaging; the live card usually "
    "has fewer. Distances are currently Euclidean in raw lon/lat degrees, which "
    "understates east-west distance by ~15% at Israel's latitude — worth switching to "
    "haversine.",
    "Turn the fan width into a **single per-departure reliability number**, then rank "
    "a line's departures by it. \"Your 07:40 is reliable, your 08:10 is a lottery\" is "
    "directly actionable for both riders and schedulers.",
    ["enhancement", "frontend"])

poc(17, "Planned route vs. GPS-measured route, on a map", "schedule-adherence-map",
    "yuvalko1", "schedule-adherence.md",
    "The planned route dashed at its timetable coordinates, against the *measured* "
    "route solid — where each stop sits at a distance-weighted average of the real GPS "
    "pings that matched it, sized by how many did. Both coloured by minutes since "
    "departure, so a colour mismatch at the same place is the bus running late there.",
    dedent("""\
    1. Same multi-day fetch and stop-signature filter as the stringline card.
    2. Pool every matched ping per stop across all matched days.
    3. Average positions weighted by `1 / (distance + ε)`, so pings that passed
       closest to a stop dominate its position.
    4. Render planned and measured as two GeoJSON layers on Leaflet.
    """),
    "`/single-line-map` — that page already owns the planned-route-on-a-map view; this "
    "adds the measured counterpart.",
    "The measured route can bow away from the planned one, but the weighted average "
    "rests on nearest-stop matching, which does mis-assign — a bow could be a real "
    "detour or an assignment artifact, and this card cannot distinguish them. "
    "Duplicate pings bias the weighting and must be dropped first.",
    "Compare measured stop positions against GTFS coordinates systematically to build "
    "a **stop-location quality report** — persistent offsets are likely stale GTFS "
    "entries or relocated bays worth reporting to the ministry.",
    ["enhancement", "frontend"])

poc(18, "Which day ran worst — journey time per day against the schedule", "schedule-adherence-by-day",
    "yuvalko1", "schedule-adherence.md",
    "Total journey time for each matched day against the schedule. The stringline "
    "shows *where* time is lost; this shows *which days* lost it, so a single bad day "
    "is not hidden inside a multi-day average.",
    dedent("""\
    1. Same fetch as the other two schedule-adherence cards.
    2. Per day, take the elapsed time at the **last stop its GPS actually resolved** —
       not the route's last stop.
    3. Compare against the plan **truncated to that same stop**, so a day whose GPS
       died halfway is not scored as an impossibly quick trip.
    """),
    "`/line-profile`, alongside the stringline.",
    "Only as good as the day-matching upstream of it; days running a different stop "
    "pattern are excluded entirely rather than shown as outliers.",
    "Join against weather, holidays and known roadworks to explain *why* a day was "
    "bad. A per-day series across a whole operator would also expose systemic bad days "
    "(strikes, fleet shortages) versus line-specific ones.",
    ["enhancement", "frontend"])

poc(19, "SIRI GPS coverage of planned stops, by hour", "siri-coverage",
    "yuvalko1", "siri-coverage.md",
    "For one line and direction, what fraction of planned GTFS stops actually got a "
    "matching real-time GPS ping, broken down by hour of day. **This is a data-quality "
    "measure wearing a service-quality costume** — it measures the feed, not the buses, "
    "and every other planned-vs-actual view depends on the answer.",
    dedent("""\
    1. Resolve one line + direction; sample up to 3 days.
    2. Per day, fetch the planned timetable and the actual GPS pings.
    3. Per planned ride, match pings to stops: **nearest stop by distance AND within
       20 minutes** of that stop's planned elapsed time. Without the time gate, routes
       that loop back near their own path match a later ping to an early stop.
    4. Aggregate by the ride's scheduled hour: `Σ covered / Σ planned`.
    """),
    "`/data-research` — it is a meta-view about data completeness rather than about "
    "service, and that page is already the home for that kind of question.",
    "**The nearest-stop match has no distance ceiling** — a ping 4 km from every stop "
    "still \"covers\" the least-far one if it falls inside the time window, so coverage "
    "here is an upper bound. Capped at 3 days against the source pipeline's ~20. Hours "
    "with under 3 rides are flagged low-confidence.",
    "Add a distance ceiling (the sibling analysis uses 150 m / 300 m thresholds), then "
    "build a **per-operator and per-region coverage scorecard** — this is the single "
    "most valuable scale-up here, because it tells every other metric where it can and "
    "cannot be trusted.",
    ["enhancement", "frontend", "data research"])

poc(20, "Poisson headway decay: CV along the route against the CV=1 benchmark", "poisson-arrival-regularity",
    "yuvalko1", "poisson-arrival-regularity.md",
    "Does bus spacing decay into a *random* process as buses travel downstream? Buses "
    "leave the terminal on a schedule, so headways start near-deterministic; traffic "
    "and boarding progressively randomise them. A memoryless (exponential) "
    "interarrival distribution has **CV = 1** — so as CV approaches 1, the timetable "
    "has stopped meaning anything for a waiting passenger.",
    dedent("""\
    1. Reuse the derived per-stop arrival times from the segment analysis.
    2. Group by `stop_sequence`; **within each service date**, sort arrivals and take
       consecutive gaps (so no overnight gap enters the sample).
    3. Where a stop has ≥3 gaps, compute `CV = std(ddof=1) / mean`.
    4. Plot CV against stop index with a reference line at CV = 1.
    """),
    "`/data-research`, or `/gaps_patterns` if it should sit with the other reliability "
    "views.",
    "**The screenshot above does not show the clean monotonic rise the theory "
    "predicts** — on this line CV starts near 0.87 and oscillates around 1.0 rather "
    "than climbing steadily. That is an honest result and should not be smoothed over. "
    "Arrivals are GPS-derived at ±30 s, and that measurement noise inflates CV *toward* "
    "the benchmark, which is the direction that would create a false positive; the "
    "measurement-error floor should be subtracted or at least stated. A CV from 3 "
    "observations is nearly meaningless and is currently drawn with the same weight as "
    "one from 300.",
    "Establish the measurement-error floor first, then compare CV curves **across "
    "lines** — a line whose CV is already at 1.0 by stop 5 has a different problem from "
    "one that reaches it at stop 40, and the intervention differs accordingly.",
    ["enhancement", "frontend"])

poc(21, "Bus bunching: headway regularity against scheduled spacing", "bus-bunching",
    "team", "bus-bunching.md",
    "The classic frequent-service failure: a delayed bus picks up extra passengers at "
    "every stop, falls further behind, and the bus behind closes the gap — until two "
    "arrive nose-to-tail followed by a long empty gap. **The signal is not lateness, "
    "it is unevenness.** A line reliably 6 minutes late is fine to wait for; a "
    "10-minute headway that is really 2-then-18 is not.",
    dedent("""\
    1. Resolve one line + operator; sample weekdays only (Fri/Sat service is thin by
       design and reads as false bunching).
    2. Reduce each ride to its scheduled time and its first GPS ping.
    3. Take consecutive gaps within each day for both scheduled and actual.
    4. Target headway = median of scheduled gaps. Classify each actual gap:
       **bunched** < 0.25×, **gapped** > 1.75×, normal in between.
    5. Report the coefficient of variation; above ~0.5 is the usual bunching sign.
    """),
    "`/gaps_patterns` — bunching is a pattern about service regularity and belongs "
    "with the other frequency views.",
    "Uses the **raw first ping** as the departure proxy, which the sibling analysis "
    "showed is a feed artifact (see the first-ping issue in this milestone). A "
    "constant reporting lead cancels out of a *difference*, but a bimodal one (−30 or "
    "−5 min) fabricates swings large enough to move rides between buckets — worth "
    "fixing before productionising. The single pooled target headway also flags normal "
    "off-peak service as \"gapped\"; bucketing against each hour's own scheduled "
    "headway would fix that. Headways are measured at the origin, where bunching has "
    "not developed yet.",
    "Measure headway CV **per stop along the route** rather than only at the origin — "
    "that is where bunching actually appears. Then aggregate into a per-line and "
    "per-region regularity score so high-frequency corridors can be ranked.",
    ["enhancement", "frontend"])

poc(22, "Route divergence: rides that strayed from the planned route", "route-divergence",
    "team", "route-divergence.md",
    "For each sampled ride, how far it got from the nearest stop on its own line. A "
    "ride that spends time far from every planned stop either detoured, was diverted, "
    "or is mis-assigned to this route. Both the worst point and the typical (median) "
    "point are shown, because one bad fix is a GPS glitch while a whole ride out there "
    "is a real detour.",
    dedent("""\
    1. Resolve the line; take a 4-hour weekday morning window.
    2. Planned stop coordinates from `/route_timetable/list`, deduplicated to distinct
       locations.
    3. GPS pings from `/siri_vehicle_locations/list`, deduplicated.
    4. **Haversine** great-circle distance from every ping to every stop; take the row
       minimum. (Euclidean degrees would understate east-west distance by ~15% at
       Israel's latitude.)
    5. Per ride: worst, median, ping count. Rides with fewer than 5 pings are dropped.
    """),
    "`/single-line-map`, as a diagnostic beside the route view.",
    "Distance is to the nearest *stop*, not to the road the route follows, so a long "
    "stop-free stretch of an otherwise correct route reads as divergence — the "
    "threshold is a user option for exactly this reason. Express and intercity "
    "segments need a much higher threshold, which then blinds it to urban detours. "
    "**Measuring perpendicular distance to the GTFS shape polyline would fix this "
    "properly** and is the main thing standing between this and production.",
    "Switch to GTFS shape geometry, then detect *recurring* divergences across days — "
    "a cluster that repeats is a permanent diversion the GTFS should be updated to "
    "reflect, which is directly actionable feedback to the operator.",
    ["enhancement", "frontend", "backend"])

poc(23, "Route divergence map: where buses leave the route", "route-divergence-map",
    "team", "route-divergence.md",
    "The line's planned stops against every GPS ping beyond the off-route threshold, "
    "coloured by how far out. A recurring detour shows up as a **cluster** rather than "
    "a number — scattered single points are usually GPS error, but a tight cluster in "
    "one place is a diversion the whole line takes.",
    dedent("""\
    1. Same fetch and haversine distance calculation as the bar-chart card.
    2. Keep pings beyond the threshold (default 500 m).
    3. Colour by severity relative to the worst observed stray.
    4. Sample down to 600 markers **evenly** rather than taking the worst N, so the map
       still shows *where* strays happen instead of only the single worst cluster.
    """),
    "`/single-line-map` for the per-line view, or `/map` if it should be a "
    "network-wide layer.",
    "Same nearest-stop caveat as the bar chart. The current legend labels the "
    "mid-severity bucket with a fixed multiple of the threshold while the code splits "
    "at the midpoint to the worst observed stray — a small inconsistency worth fixing "
    "in any port.",
    "Overlay divergence clusters from **all** lines to find shared problem locations — "
    "a junction that six lines detour around is a road-network finding, not a "
    "per-line one.",
    ["enhancement", "frontend"])

poc(24, "Ghost rides, early and late departures per line", "service-violations",
    "team", "service-violations.md",
    "Every planned ride in a line's schedule, classified as a ghost (no GPS ever "
    "matched), an early departure, a late departure, or on-time — the three failure "
    "modes the Ministry of Transport can fine for.",
    dedent("""\
    1. Planned rides from `/gtfs_rides/list` for the whole window in one paged call.
    2. Drop rows with a null `start_time` — they cannot be timed or ghost-checked.
    3. GPS from `/siri_vehicle_locations/list`, deduplicated.
    4. **Departure proxy** = first ping where the vehicle is actually moving
       (`distance_from_journey_start > 0` or `velocity > 0`), *not* the raw first ping.
    5. Join plan to actual on exact scheduled-time equality; unmatched = ghost.
    6. Classify against user-editable early/late thresholds.
    """),
    "`/gaps` — that page already owns the missing-service question.",
    "**The thresholds are illustrative, not regulatory.** 1 min early / 5 min late "
    "reflect commonly cited practice, not the ministry's actual fine schedule, which "
    "was not available. The card is honest about this in its notes, but the framing "
    "invites over-reading — sourcing the real tolerances is the highest-value "
    "follow-up. **Ghost rides are the weakest category**: a bus that ran untracked is "
    "indistinguishable from one that was cancelled, so these are candidates for "
    "investigation, not confirmed non-arrivals. Scope is one line.",
    "Source the real regulatory tolerances, then compute a violation rate **per "
    "operator per month** — the enforcement basis is already electronic, so this is the "
    "analysis with the most direct policy consequence of anything in the hackathon.",
    ["enhancement", "bus-expert-needed", "frontend"])

poc(25, "Which days had the worst service failures", "service-violations-by-day",
    "team", "service-violations.md",
    "The same ghost / early / late / on-time breakdown, split by day, so a spike on "
    "one bad day is not hidden inside a window average.",
    dedent("""\
    Identical method and thresholds to the per-line card, grouped by service date and
    drawn as a stacked bar per day, with every date in the window present even when a
    category is empty.
    """),
    "`/gaps`, directly beside the per-line breakdown.",
    "Inherits every caveat of the per-line card — the same invented thresholds and the "
    "same ghost-vs-untracked ambiguity. A day where SIRI ingestion was degraded looks "
    "identical to a day of mass cancellations, which matters more here than in the "
    "aggregate view because a single day has no averaging to soften it.",
    "Add a **feed-health floor**: cross-check each day against network-wide SIRI volume "
    "and grey out days where ingestion was clearly degraded, rather than reporting them "
    "as service failures.",
    ["enhancement", "frontend"])

poc(26, "Days-without-cancellations score per line", "days-with-no-cancellations",
    "Broundal", "days-with-no-cancellations.md",
    "What fraction of the last 15 service days did this line run with **zero** "
    "cancellations? Deliberately harsh — a day with ≥1 cancellation scores 0, a fully "
    "operated day scores 1. It asks \"did this line have a clean day\", which is closer "
    "to how a passenger experiences a line than a 99.4% completion rate is.",
    dedent("""\
    1. 15-day window ending **yesterday** (today's actuals are still landing, so a live
       day looks like a wall of cancellations).
    2. Resolve the line to its `(line_ref, operator_ref)` pairs **for that window** —
       line 480 was 2 refs in Nov 2025 and 8 in Jul 2026, so a cached mapping silently
       under-counts.
    3. Page `/rides_execution/list` per variant; a null `actual_start_time` is a
       cancellation.
    4. Drop rows with no `planned_start_time` (unplanned rides — the mirror image of a
       cancellation).
    5. Key on the departure itself and let **any** observed actual mark it operated, so
       a duplicated row with a null actual cannot invent a phantom cancellation.
    6. Bucket by Israel service date using real `ZoneInfo`, never a fixed UTC+3 —
       Israel is UTC+2 in winter and a fixed offset spills a 16th day into the window.
    """),
    "`/line-profile` — a per-line reliability headline.",
    "**A feed outage is indistinguishable from a bad day.** The method flags lines with "
    "zero actuals across the whole window as unscoreable, but cannot catch a line whose "
    "feed was 30% degraded, which reads as a genuinely bad score. A sanity floor was "
    "designed and not built. Partial rides count as fully operated — a bus that started "
    "and died mid-route has an `actual_start_time`. The binary daily metric also takes "
    "only 16 distinct values over 15 days, so lines cluster heavily.",
    "Add the feed-health sanity floor, then offer a **volume-weighted execution rate** "
    "alongside the binary score — the binary version disproportionately penalises "
    "high-frequency lines, where losing one of 100 daily runs is near-certain.",
    ["enhancement", "frontend"])

add(27, "Days-without-cancellations score per operator",
    ["enhancement", "frontend"],
    body(BANNER, dedent(f"""\
    ## What it answers

    The same zero-cancellations score, computed for every line of one operator and
    ranked worst-first — so a company's weak lines are visible at a glance.

    {ind(shot("days-with-no-cancellations", "Days without cancellations, per line, for one operator"))}

    ## How it works

    Resolves every `line_ref` of the operator from `/gtfs_routes/list`, then runs the
    per-line scoring for each. Lines whose entire window reports zero actuals are drawn
    **grey and hatched at 1.0** rather than scored 0.00 — that is an ingestion gap, not
    a company that cancelled every bus it ever scheduled, and it must not be readable
    as a score.

    ## Where it could go in דאטאבוס

    `/operator` — it is an operator-level summary and that page already exists for
    exactly this kind of view.

    *A suggestion, not a decision — page ownership is the maintainers'.*

    ## Known limitations

    **Cost is the real constraint.** One paged request per `line_ref`: ~80 for a small
    company, **~1,240 for אגד**. The hackathon card caps at 15 lines and sorts by name
    length before truncating, which is an arbitrary selection presented as an operator
    overview — a production version needs either pre-aggregation or a proper sampling
    strategy.

    Inherits the feed-outage ambiguity from the per-line version.

    ## Suggested next steps

    Build the **cross-operator comparison** — the original author specified this as
    "method 3" and it was never built. Ranking operators against each other is the
    comparison a regulator would actually want, and it is the natural endpoint of this
    work.
    """), credit("Broundal", "days-with-no-cancellations.md")), 2)

poc(28, "Ridership anomaly: lines carrying unusually few riders for their peer group", "busline-usage-anomaly",
    "team", "busline-usage-anomaly.md",
    "Which lines carry unusually many or few passengers **for their peer group, at that "
    "hour**? Raw counts cannot be compared across lines — a dense-city line and a "
    "suburban one differ for reasons unrelated to how well either runs. Scoring against "
    "peers means a low score reads as \"carries fewer riders than comparable lines at "
    "the same time of day\", not merely \"is a small line\".",
    dedent("""\
    1. Page data.gov.il's hourly ticketing datastore (**not** Stride — this is the only
       analysis on a different source).
    2. Each row is one line × direction × hour × month with `D1..D31` daily counts;
       take the mean, skipping nulls.
    3. Drop the rail sentinel and undefined clusters; collapse direction and month.
    4. Group by the ministry's own `cluster_nm` ("אשכול") and hour, then z-score each
       line-hour against its peers.
    5. Drop peer groups below a minimum size — a z-score against one other line is noise.
    """),
    "`/data-research` — it is a different data source with different identifiers and "
    "does not fit the line/operator pickers.",
    "**Ticketing identifiers do not map to GTFS/SIRI** `line_ref` or `route_short_name`, "
    "so this card sits in a silo and the global filters do not affect it — bridging that "
    "id mapping is the main blocker. The current \"sample\" takes the first N rows in "
    "dataset order, which is not random sampling. Z-scores also assume roughly normal "
    "peer distributions, while ridership is strongly right-skewed. Validation counts "
    "undercount anyone not validating.",
    "Build the **ticketing-id ↔ GTFS line_ref mapping** first — that single piece of "
    "plumbing would let ridership be joined to reliability, which is the genuinely "
    "novel question: *are the least reliable lines also the ones losing riders?*",
    ["enhancement", "data research", "backend"])

poc(29, "One bus, actual GPS trace, coloured by elapsed time", "gps-trace-map",
    "yuvalko1", "gps-trace-map.md",
    "A single real ride's raw GPS trail on a map, coloured by elapsed time. It makes no "
    "analytical claim — its job is **ground truth for the eye**. Every other card turns "
    "pings into statistics; this shows what the pings actually look like, including the "
    "reporting interval, the dropouts, and the clustering when a bus sits still.",
    dedent("""\
    1. Resolve the line to a `line_ref` **before** fetching (the `route_short_name`
       filter is silently ignored by this endpoint — see the separate bug in this
       milestone).
    2. Fetch a 4-hour weekday morning window; deduplicate pings.
    3. Pick the ride with the most pings.
    4. Draw one coloured segment per consecutive pair, plus a point per ping with its
       timestamp, along a viridis gradient.
    """),
    "`/vehicle` — that page is already about a single vehicle's journey.",
    "One ride, one morning, **chosen for being the best-tracked** — which for a card "
    "about feed quality shows the feed at its best. Nothing generalises from it. The "
    "colour gradient is normalised per ride, so two loads are not comparable.",
    "Offer the **median or worst-tracked** ride as well as the best — that is far more "
    "informative about what the data usually looks like, and costs nothing to add.",
    ["enhancement", "frontend", "good first issue"])


# ── Group 3: scale-up follow-ups ─────────────────────────────────────────────

def scale(num, title, labels, what, why, how, dep):
    add(num, title, labels, body(BANNER, dedent(f"""\
    ## What

    {ind(what)}

    ## Why it matters

    {ind(why)}

    ## Sketch

    {ind(how)}

    ## Depends on

    {ind(dep)}
    """), credit("team", "upstream-issues.md")), 3)


scale(30, "Aggregate segment reliability into a per-operator punctuality metric",
      ["enhancement", "backend", "data research"],
      "The segment-reliability analysis produces a median actual/planned duration ratio "
      "per stop-to-stop segment for one line. Roll that up: per line → per operator → "
      "per region, so operators can be compared on how realistic their timetables are.",
      "Every reliability view in the hackathon is single-line. A regulator, a journalist "
      "or a rider choosing between operators needs a **comparable** number. This is the "
      "step that turns a demo into a metric.",
      "Weight segments by ride volume so a rarely-run segment does not dominate. Report "
      "the sample size and the confidence mix alongside the headline, since some "
      "segments rest on very few rides. Exclude operators outside the SIRI feed entirely "
      "rather than scoring them badly.",
      "Derived arrival times, which currently cost ~1–2 minutes per line to compute — "
      "see the pre-aggregation issue in this milestone.")

scale(31, "Aggregate bunching CV into a per-line and per-region regularity score",
      ["enhancement", "backend", "data research"],
      "The bunching analysis computes a coefficient of variation for one line over a "
      "couple of days. Compute it continuously across all high-frequency lines and "
      "publish a regularity score per line, per corridor and per region.",
      "Headway regularity is the standard international metric for frequent transit and "
      "Israel currently publishes nothing equivalent. It is also the metric that best "
      "matches passenger experience on lines where nobody consults a timetable.",
      "Only apply it to lines above a frequency threshold — CV is meaningless on a line "
      "running twice a day. Bucket against each hour's own scheduled headway rather than "
      "a single pooled median. Measure at several points along the route, not just the "
      "origin.",
      "Fixing the first-ping departure proxy (see the first-ping issue in this "
      "milestone), otherwise a bimodal reporting lead fabricates variance.")

scale(32, "Rank operators by days-without-cancellations (the unbuilt \"method 3\")",
      ["enhancement", "backend"],
      "The days-without-cancellations work specified three methods: score one line, "
      "score every line of an operator, and **compare operators against each other**. "
      "The third was specified and never built.",
      "It is the comparison a regulator would actually want, and the one the first two "
      "methods exist to enable. Per-line scores are diagnostic; per-operator ranking is "
      "accountability.",
      "Careful with the denominator: lines with no planned rides must be excluded rather "
      "than scored, and operators with no SIRI feed must be excluded rather than ranked "
      "last. The original code already returns `None` rather than `0.0` for \"unknown\" "
      "precisely so this averaging step cannot go wrong — preserve that distinction.",
      "A feed-health sanity floor, so a degraded ingestion day does not read as mass "
      "cancellation for whichever operator happened to be affected.")

scale(33, "Per-region SIRI coverage scorecard",
      ["enhancement", "backend", "data research"],
      "Run the stop-level coverage analysis across all lines and publish coverage per "
      "operator, per region and per hour — a standing measure of how complete the "
      "real-time feed actually is.",
      "**This is the highest-leverage scale-up of the set.** Every other metric in "
      "דאטאבוס is a statement about the tracking record rather than about the road, and "
      "its trustworthiness depends entirely on coverage. Publishing coverage alongside "
      "the metrics is what lets a reader know when a number means something.",
      "Add a distance ceiling to the nearest-stop match first — without one, coverage is "
      "an upper bound. The original full-network scan was estimated at 1–2 hours, so this "
      "is a scheduled batch job, not a live query. A two-stage screen (cheap ride-volume "
      "pass, then expensive per-stop matching) already exists in the source work.",
      "Nothing blocking — but it pairs naturally with surfacing operators that have no "
      "feed at all.")

scale(34, "Pre-aggregate derived arrival times so these analyses can run interactively",
      ["enhancement", "backend", "bus-expert-needed"],
      "The Stride API serves no actual stop arrival times, so every analysis derives them "
      "from raw GPS by interpolating the vehicle's closest approach to each stop "
      "(±30 s). That derivation costs ~1–2 minutes per line and is repeated by every "
      "consumer independently.",
      "It is the single shared bottleneck under most of this milestone. Computing it once "
      "in the ETL and storing it would make segment reliability, Marey diagrams, "
      "headway-decay CV and bunching all cheap enough to be interactive — and would give "
      "every consumer the *same* numbers instead of each reinventing the interpolation.",
      "Store per (ride, stop): derived arrival time, match distance, and the gap between "
      "the bracketing pings. Those last two are what let consumers judge whether to trust "
      "a value — the existing work uses 150 m for a loose match and 300 m to drop a stop "
      "entirely, plus a 2-minute ping gap as a coarse-timing warning. Handle the known "
      "artifacts explicitly: terminal dwell (the origin resolves to departure, not "
      "closest approach) and coincident junction stops (needs a forward-constrained "
      "monotonic search).",
      "Nothing — this is foundational, and arguably should be built before the other "
      "scale-ups rather than after.")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "issues")
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for it in ISSUES:
        slug = "".join(c if c.isalnum() or c in "- " else "" for c in it["title"].lower())
        slug = "-".join(slug.split())[:60].strip("-")
        fn = out / f"{it['n']:02d}-{slug}.md"
        fn.write_text(f"# {it['title']}\n\n{it['body']}", encoding="utf-8")
        manifest.append({"n": it["n"], "title": it["title"], "labels": it["labels"],
                         "group": it["group"], "file": str(fn)})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"wrote {len(manifest)} issue bodies to {out}")
    for g in (1, 2, 3):
        print(f"  group {g}: {sum(1 for m in manifest if m['group'] == g)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
