"""Phase 2 issue bodies — the hackathon work the first pass missed.

Covers the three standalone dashboards, the never-ported notebooks, the reusable
infrastructure, and the public-appeal update. Reuses the banner/credit/indent
helpers from gen_issues.py so both batches read identically.

    uv run python scripts/gen_issues_phase2.py to_review
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from textwrap import dedent

sys.path.insert(0, str(Path(__file__).parent))
from gen_issues import ALGO, BANNER, HACK, body, ind  # noqa: E402

DASH = f"https://raw.githubusercontent.com/hasadna/open-bus-hackathon-26/main/algorithms/img/dashboards"
SRC = f"{HACK}/blob/main/source-material"

BUNCH_PAGE = f"{HACK}/blob/main/frontend/public/bunching-reasons.html"
SPEED_PAGE = f"{HACK}/blob/main/frontend/public/tlv-bus-speed.html"
EDIT_PAGE = f"{HACK}/blob/main/frontend/public/editorial.html"

OPEN_IT = (
    "The page is **self-contained** — download it and open it in a browser, or run "
    "`./dev` in the hackathon repo and visit the path directly. No server, no build, "
    "no credentials."
)

ISSUES: list[dict] = []


def add(n, title, labels, md):
    ISSUES.append({"n": n, "title": title, "labels": labels, "body": md, "group": 4})


def shot(name, caption):
    return f"![{caption}]({DASH}/{name}.png)\n\n*{caption}*"


def credit(who, doc, extra=""):
    return dedent(f"""\
        ---

        **Credit & provenance**
        Found during the hasadna Open Bus hackathon, July 2026 — {who}.
        · Source material, republished with the participants' permission: [`source-material/`]({SRC}/README.md)
        · Per-solution write-ups: [`{doc}`]({HACK}/blob/main/{doc if doc.startswith('docs/') else 'algorithms/' + doc})
        {extra}""")


# ══ Bunching dashboard ══════════════════════════════════════════════════════

BUNCH_SCALE = (
    "**709 line-directions · 138,716 rides · 127,754 consecutive pairs**, over 5 "
    "term-time weekdays (2026-05-13 → 06-14). Source: SIRI vehicle telemetry joined "
    "to the GTFS timetable."
)

add(35, 'Surface the "Where the buses bunch" dashboard', ["enhancement", "frontend", "good first issue"],
    body(BANNER, dedent(f"""\
    ## What

    The hackathon produced a full bunching dashboard that works today and is not
    reachable from דאטאבוס. Link or embed it as a first step, while the individual
    charts get ported natively (#36–#40).

    {ind(shot("bunch-header-kpis", "Headline and KPI tiles"))}

    {BUNCH_SCALE}

    Headline numbers: **9.9% of consecutive pairs ran bunched** (12,674 nose-to-tail),
    **13% were already bunched leaving the terminal**, **50% of the route is ridden
    bunched** on average, worst line 4 (דן) at 32%.

    ## Where

    `/gaps_patterns` is the natural home, or a link from the dashboard page.

    ## Caveats to carry across

    It is a **fixed 5-day sample**, not a live view — the page states its own window,
    and any link should too. The "grow the sample" button needs the original
    hackathon server and will fail politely if the page is served standalone.

    {OPEN_IT}

    File: [`frontend/public/bunching-reasons.html`]({BUNCH_PAGE})
    """), credit("the hackathon team", "bus-bunching.md")))

add(36, "Port: why buses bunch — attribute every event to a cause", ["enhancement", "backend", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What

    The single most valuable thing in the bunching dashboard, and nothing comparable
    exists in דאטאבוס: **every bunching event attributed to a cause.**

    {ind(shot("bunch-why-decomposition", "Share of all bunching events by cause"))}

    | Cause | Share | Meaning |
    |---|---|---|
    | **Late departure** | 13% | Already bunched leaving the terminal — the leader left late, the follower left early, or the timetable left no gap |
    | **First 20% of route** | 10% | Left with a healthy gap, collapsed within the first fifth |
    | **En route** | 73% | Collapsed after the 20% mark — classic traffic-and-dwell feedback |
    | **Origin outside area** | rest | Entered the observed area already bunched; onset not visible |

    ## Why it matters

    It separates problems with **different owners**. 13% born at the terminal is a
    dispatch and timetabling problem the operator can fix this week. 73% en route is a
    road-priority and dwell-time problem that needs infrastructure. Publishing a single
    "bunching rate" hides that split and points everyone at the wrong lever.

    ## Suggested next step

    Per-operator and per-corridor breakdowns of the same split. An operator whose
    bunching is mostly terminal-born is failing at something entirely different from
    one whose bunching is mostly en route.

    {BUNCH_SCALE}
    """), credit("the hackathon team", "bus-bunching.md")))

add(37, "Port: planned gap vs effective gap, and what riders actually wait", ["enhancement", "backend", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    Two rider-facing measures from the bunching dashboard that the current metrics
    miss entirely.

    **Effective gap** — when two buses arrive nose-to-tail they are one arrival from a
    passenger's point of view. Counting them as two makes the service look twice as
    frequent as it is.

    **Actual wait vs planned wait** — the honest cost of that. Examples from the
    ranked table:

    | Line | Planned gap | Effective gap | Planned wait | **Actual wait** |
    |---|---|---|---|---|
    | 4 (דן) | 7 min | 9 min | 3.5 min | **7.9 min** |
    | 18 | 10 min | 12 min | 4.8 min | **9.0 min** |
    | 142 | 13 min | 15 min | 6.5 min | **11.5 min** |

    {ind(shot("bunch-ranked-table", "Planned vs effective gap and planned vs actual wait, per line"))}

    ## Why it matters

    **Riders on line 4 wait more than twice as long as the timetable implies** — 7.9
    minutes against 3.5. That gap is invisible in any punctuality metric, because the
    buses may all be individually "on time". It is the number a passenger would
    recognise as their own experience.

    ## Suggested next step

    Publish actual-wait alongside planned-wait everywhere frequency is shown, and
    consider it as a headline service metric in its own right.

    {BUNCH_SCALE}
    """), credit("the hackathon team", "bus-bunching.md")))

add(38, "Port: per-line Marey diagram over the full bunching dataset", ["enhancement", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    Clicking a line in the bunching dashboard draws its **Marey diagram** — every ride
    as a path down the route, so bunching is visible as converging lines.

    ## Relationship to #1783

    #1783 proposes a Marey diagram from the live-card analysis, which samples **up to
    60 rides** over a ≤10-day window. This one is drawn from **138,716 rides**. Same
    visual grammar, very different evidential weight — worth building once, with the
    data source configurable.

    ## Why it matters

    A Marey diagram is the only chart where bunching is *self-evident* rather than
    inferred: two trajectories converging and then travelling together is the
    phenomenon itself, not a statistic about it.

    ## Suggested next step

    Overlay the cause attribution from #36 — colour each convergence by whether it was
    terminal-born or en-route — so the diagram explains itself.

    {BUNCH_SCALE}
    """), credit("the hackathon team", "bus-bunching.md")))

add(39, "Port: bunching league table with hour histogram, filters and CSV export", ["enhancement", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    The navigational layer of the bunching dashboard: **602 line-directions with at
    least 30 pairs**, ranked, filterable by city / operator / line, with a
    pairs-by-hour histogram driving a time filter.

    {ind(shot("bunch-hour-and-filters", "Pairs by hour, with city, operator and line filters"))}

    Columns: planned gap · effective gap · pairs · bunched % · cause split as a stacked
    bar · planned wait · actual wait · late-start caused · route ridden bunched.

    ## Why it matters

    The cause split renders **inline per row**, so a reader scanning the table sees
    immediately that two lines with the same 26% bunching rate have completely
    different causes. That is the design idea worth copying, more than the table
    itself.

    ## Suggested next step

    CSV export, and a permalink that encodes the active filters so a finding can be
    cited.

    {BUNCH_SCALE}
    """), credit("the hackathon team", "bus-bunching.md")))

add(40, 'Adopt the "grow the sample" incremental-loading pattern', ["enhancement", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    The bunching dashboard opens on a 5-day sample and offers **"add N random
    weekdays"**, which probes the archive for healthy days and loads them in the
    background. The page stays fully usable while they land, and a progress panel
    reports coverage — *"2,880 / 2,880 five-min slices · 100.0%"*.

    ## Why it matters

    It is a direct answer to the cost problem behind half the tickets in this
    milestone. Several analyses take 1–2 minutes per line because they derive data the
    API does not serve. The usual options are a slow page or a small sample; this is a
    third — **start small, stay interactive, deepen in the background, and show the
    reader exactly how much evidence is currently behind the chart.**

    ## Why it is honest as well as fast

    The progress panel doubles as a confidence indicator. A reader looking at a chart
    built from 20% of the intended sample can see that, which is strictly better than
    a chart that looks identical whether it rests on one day or thirty.

    ## Suggested next step

    Apply it first to the cards that currently cap their windows for cost reasons —
    segment reliability (#1782), schedule adherence (#1785) and bunching (#1790).
    """), credit("the hackathon team", "bus-bunching.md")))

# ══ Speed dashboard ═════════════════════════════════════════════════════════

SPEED_SCALE = (
    "**60,359,656 street readings from 11,559,010 ping pairs**, 10 weekdays "
    "(May–June 2026), 97.3% match rate. Source: SIRI telemetry joined to "
    "OpenStreetMap geometry."
)

add(41, 'Surface the "Where the buses crawl" street-speed dashboard', ["enhancement", "frontend", "good first issue"],
    body(BANNER, dedent(f"""\
    ## What

    Door-to-door bus speed on **every street** of Tel Aviv and the inner ring, by hour
    of day, measured from GPS. It works today and is not reachable from דאטאבוס.

    {ind(shot("speed-header-kpis", "Network speed, bus-minutes lost, worst corridor, streets with no bus"))}

    {SPEED_SCALE}

    Headline numbers at 16:00: network bus speed **18.8 km/h**; **33,660 bus-minutes
    lost per hour** against each street's own free-flow speed; worst single corridor
    Geha W-bound at **787 min/hr**; slowest busy street Sderot David Ben Gurion at
    **4.7 km/h**; and **1,308 km of street with no bus at all**.

    ## Where

    `/velocity-heatmap` is the closest existing page, or a link from the map page.

    ## Note

    This also answers **#1231** — the ask to embed a notebook about vehicle velocities
    into the public appeal. This is that research, at national-data scale and already
    interactive.

    {OPEN_IT}

    File: [`frontend/public/tlv-bus-speed.html`]({SPEED_PAGE})
    """), credit("the hackathon team", "upstream-issues.md")))

add(42, "Port: street-level bus speed map with six colour modes", ["enhancement", "frontend", "backend"],
    body(BANNER, dedent(f"""\
    ## What

    A street-level choropleth of measured bus speed, switchable between six views:
    **speed · lost minutes · vs free-flow · vs speed limit · buses/hr · coverage**.

    {ind(shot("speed-map", "Median bus speed per street, Tel Aviv and the inner ring"))}

    Filters: hour of day, city, operator, single line, hide motorways, only streets
    with ≥20 buses/hr, show unserved streets, and a street search.

    {ind(shot("speed-controls", "Colour mode and filter controls"))}

    ## Why six modes rather than one

    They answer different questions and disagree usefully. A street can be slow in
    absolute terms but at its own free-flow speed (nothing to fix), or fast in absolute
    terms but far below its limit (something to fix). "vs free-flow" is what isolates
    *congestion* from *street design*.

    {SPEED_SCALE}

    ## Suggested next step

    Extend beyond Tel Aviv. The method is city-agnostic — it needs GTFS, SIRI and OSM
    geometry, all of which exist nationally.
    """), credit("the hackathon team", "upstream-issues.md")))

add(43, "Port: bus-minutes-lost corridor ranking — where a bus lane pays off", ["enhancement", "backend", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What

    **725 corridors ranked by bus-minutes lost per hour** — the total delay borne by
    all buses on that street, against the street's own free-flow speed.

    {ind(shot("speed-corridors", "Corridors ranked by bus-minutes lost per hour"))}

    Worst corridor: **Geha W-bound — 787 bus-minutes lost per hour**, running at 25.7
    km/h against 62.6 free-flow (a 59% slowdown), carrying 59 buses/hr across 234
    lines over 10.61 km.

    ## Why this is the most policy-ready output of the hackathon

    It converts a diffuse complaint into a **ranked, costed list of streets**. "Buses
    are slow" is not actionable; "this corridor costs 787 bus-minutes every hour, and
    here are the next 724 in order" is a capital-works priority list.

    It is also a direct answer to the first open question on the דאטאבוס public-appeal
    page — *"איפה נדרשים נתיבי תעדוף לתחבורה ציבורית (נת״צים)?"* — see #55.

    ## Suggested next step

    Weight by passengers rather than buses, if ridership can be joined. A corridor with
    59 nearly-empty buses and one with 59 full ones are not the same investment case.

    {SPEED_SCALE}
    """), credit("the hackathon team", "upstream-issues.md")))

add(44, "Surface the streets with no bus service (1,308 km, 59% of the mapped network)", ["enhancement", "data research"],
    body(BANNER, dedent(f"""\
    ## What

    The speed dashboard reports **1,308 km of mapped street with no bus service at
    all — 59% of the network** in Tel Aviv and the inner ring. It is a toggle on the
    map ("show unserved streets") rather than a headline.

    ## Why it deserves its own view

    Every other metric in דאטאבוס measures **service that exists**: was it late, did it
    run, did it bunch. This measures the opposite, and it is the one a resident of an
    underserved neighbourhood would actually care about.

    It also has an equity dimension the current metrics cannot see. A neighbourhood
    with no bus scores no cancellations and perfect punctuality — it is indistinguishable
    from a well-served one in every reliability statistic.

    ## Caveats

    59% of *street kilometres* is not 59% of people — buses reasonably follow arterials,
    and a residential cul-de-sac with no bus is not a failure. The useful version of
    this metric is **walking distance to the nearest served street**, weighted by
    population, not raw kilometres.

    ## Suggested next step

    Join to population or dwelling counts to turn street coverage into people coverage,
    then compare across cities. Related: the UrbanAccess accessibility work in #50,
    which is the proper tool for this and was never ported.

    {SPEED_SCALE}
    """), credit("the hackathon team", "upstream-issues.md")))

add(45, "Document the door-to-door speed method (ping pairs → street segments)", ["documentation", "data research"],
    body(BANNER, dedent(f"""\
    ## What

    Write up how street-level bus speed is derived, so the numbers in #42, #43 and #44
    can be checked and the method reused for other cities.

    ## The method in outline

    Consecutive SIRI pings from the same vehicle form a **ping pair**. Each pair is
    map-matched to OpenStreetMap street geometry, giving a distance and an elapsed time
    and therefore a speed reading attributable to a specific street and five-minute
    slice. Aggregated: 60,359,656 readings from 11,559,010 pairs over 10 weekdays, at a
    **97.3% match rate**.

    "Bus-minutes lost" is then the difference between observed traversal time and
    free-flow traversal time, summed over every bus using that street in the hour.

    ## What needs documenting properly

    - How free-flow speed per street is established, and how it is separated from the
      posted limit.
    - The map-matching rule, and what the 2.7% unmatched consists of.
    - The minimum sample per street-hour before a cell is drawn.
    - How motorway ramps and very short segments are handled — both distort speed
      badly.

    ## Why bother

    Every figure in #43 is a policy argument. Policy arguments get contested, and an
    undocumented method loses that argument regardless of whether it was right.
    """), credit("the hackathon team", "upstream-issues.md")))

# ══ Editorial ═══════════════════════════════════════════════════════════════

add(46, 'Surface the "what the open data shows" editorial page', ["enhancement", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    A long-form data-journalism page built entirely from the open data, written for a
    general reader rather than an analyst.

    {ind(shot("editorial-header", "Editorial page header"))}

    It covers the headline non-execution finding, the five upstream data defects
    (F1/F6/F7/F8/F9 — filed here as #1775, #1776, #1780, #1781), three service metrics
    that do not exist elsewhere (#47, #48, #49), the periphery finding, and
    operator-by-operator series.

    ## Why it is worth surfacing

    דאטאבוס is excellent at *"here is the data, explore it"* and has nothing that says
    *"here is what the data means"*. This is that, and it is written to be quotable —
    every figure names its time window and its population.

    ## Caveats

    A fixed snapshot, not a live view, and it should be dated wherever it is linked.
    Some numbers state findings differently from the underlying write-ups — the
    reconciliation is in [`to_review/00-VERIFICATION.md`]({HACK}/blob/main/to_review/00-VERIFICATION.md).

    {OPEN_IT}

    File: [`frontend/public/editorial.html`]({EDIT_PAGE})
    """), credit("lihay7", "docs/busanalysis.md")))

add(47, "M1 — the enforcement reality gap, as a live metric", ["enhancement", "backend", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What

    Compare the non-execution rate reconstructed from open data against the figure the
    ministry's own electronic control publishes for the same period, at the same
    tolerance.

    Reported: **5.0% reconstructed against 1.5% published** for 2024-H1, both at ±30
    min.

    ## Why it matters

    If the reconstruction is right, unseen failure is unpriced failure — service that
    did not run is not being counted, and the enforcement basis is already electronic,
    so the data to count it exists. That is a live policy question, not an academic one.

    ## Why it needs care before publication

    A 3.3× discrepancy against an official statistic is a strong claim, and the most
    likely explanations are **definitional rather than substantive** — different
    tolerance windows, different operator populations, different treatment of the
    operators that have no feed at all (#1780), or the duplicate-ride inflation in
    #1776. Each of those must be excluded before the gap can be attributed to
    under-reporting.

    ## Suggested next step

    Reproduce the comparison at several tolerance windows and with the F6/F8/F9
    corrections applied and not applied, so the sensitivity of the gap is visible
    rather than asserted.

    Method: [`source-material/busanalysis/metrics/enforcement_gap.md`]({SRC}/busanalysis/metrics/enforcement_gap.md)
    """), credit("lihay7", "docs/busanalysis.md")))

add(48, "M2 — what the timetable costs a rider in waiting", ["enhancement", "backend", "bus-expert-needed"],
    body(BANNER, dedent(f"""\
    ## What

    Median **extra** waiting time beyond what the published timetable promises,
    nationally, per month. Reported: **4.2 minutes**, with **11.8% of line-months
    running 10+ minutes over promise**.

    ## Why it matters

    It reframes reliability from the operator's point of view to the rider's. "94% of
    departures ran" is an operator statistic; "you wait four minutes longer than the
    timetable says" is what a passenger experiences, and it is the number that would
    change behaviour if published per line.

    The proposed remedy is unusual and worth stating: **an honest every-20 beats a
    broken every-10.** The metric rewards publishing a timetable the service can
    actually keep.

    ## Important limitation

    The record holds no observed departure time, so this is a **waiting** measure
    derived scheduled-against-scheduled — it is *not* a punctuality measure, and it
    must never be presented as one. See #1778 for why first-ping is not a departure
    time.

    Closely related: #37 computes actual-vs-planned wait from the bunching dataset by a
    different route. **If both are built, they should be reconciled** — two different
    "what riders actually wait" numbers in one product would be worse than either alone.

    Method: [`source-material/busanalysis/metrics/departure_fidelity.md`]({SRC}/busanalysis/metrics/departure_fidelity.md)
    """), credit("lihay7", "docs/busanalysis.md")))

add(49, "M3 — can the ministry measure its own network at all?", ["enhancement", "data research"],
    body(BANNER, dedent(f"""\
    ## What

    A record-integrity metric: what share of the national schedule is even **capable**
    of being measured, given the feed's own gaps.

    It is the composite of the defects filed separately in this milestone — the
    unpopulated aggregate (#1770), the broken stored linkage (#1775), duplicate rides
    (#1776), doubled planned counts (#1781) and the operators with no feed (#1780).

    ## Why it belongs in the product

    Every other number in דאטאבוס is conditional on this one. A 94% execution rate
    means something quite different if 5% of the schedule is unmeasurable and the
    denominator is inflated on 22 days of the year.

    Publishing measurability **alongside** performance is the difference between a
    dashboard that can be quoted and one that cannot.

    ## Suggested shape

    A single per-month figure with a breakdown by cause, on `/data-research`, plus a
    small badge wherever a performance number is shown. Pairs naturally with the
    coverage scorecard in #1802 and with #24.

    Method: [`source-material/busanalysis/metrics/record_integrity.md`]({SRC}/busanalysis/metrics/record_integrity.md)
    """), credit("lihay7", "docs/busanalysis.md")))

# ══ Unported source material ════════════════════════════════════════════════

add(50, "Accessibility analysis (UrbanAccess) — researched, never ported", ["enhancement", "backend", "data research"],
    body(BANNER, dedent(f"""\
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

    Notebook: [`source-material/talpiot/notebooks/siri accessibility analysis using UrbanAccess.ipynb`]({SRC}/talpiot/notebooks/)
    """), credit("yuvalko1", "siri-coverage.md")))

add(51, "Unported notebooks: per-line arrivals, route-rides loader, routes-between-points", ["data research", "help needed"],
    body(BANNER, dedent(f"""\
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

    Notebooks: [`source-material/talpiot/notebooks/`]({SRC}/talpiot/notebooks/)
    """), credit("yuvalko1", "siri-coverage.md")))

# ══ Infrastructure ══════════════════════════════════════════════════════════

add(52, "Adopt the colourblind-safe series palette (validated, light and dark)", ["enhancement", "CSS", "frontend"],
    body(BANNER, dedent(f"""\
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

    Source: [`openbus_hack/theme.py`]({HACK}/blob/main/openbus_hack/theme.py) and
    [`frontend/src/theme.css`]({HACK}/blob/main/frontend/src/theme.css)
    """), credit("the hackathon team", "README.md")))

add(53, "Chart contract: a table fallback, and every chart marks its own weak spots", ["enhancement", "frontend", "semantic html"],
    body(BANNER, dedent(f"""\
    ## What

    Two conventions the hackathon dashboard enforced at the framework level rather than
    leaving to each chart author.

    **1. Every chart carries a table.** `ensure_table()` derives one automatically from
    the chart's own series if the author did not supply it, so there is no chart
    without a text equivalent — for screen readers, for colour-blind readers, and for
    anyone who wants the actual number.

    **2. Every chart marks where it is weak**, rather than looking uniformly confident:

    | Cue | Meaning |
    |---|---|
    | Hatched or pale bar/cell | The number is there but shaky; a note names why |
    | `n=…` beside every mark | The sample behind it, always visible, never inferred |
    | Dimmed italic axis label | That stop/segment was rarely resolved — interpolation more than measurement |
    | Blank vs hatched cell | **No data** and **thin data** look different, deliberately |

    ## Why the second rule is the important one

    An under-sampled segment silently missing from a chart is indistinguishable from a
    segment that does not exist — the most misleading failure available. The rule is
    **flag, never drop.**

    This matters especially here because so much of the underlying data is patchy in
    ways the reader cannot see: derived arrival times at ±30 s, operators with no feed,
    days with doubled schedules.

    Source: [`openbus_hack/contract.py`]({HACK}/blob/main/openbus_hack/contract.py)
    """), credit("the hackathon team", "bus-arrival-reliability.md")))

add(54, "Source-material appendix: show the raw notebook beside the finished chart", ["enhancement", "non-code"],
    body(BANNER, dedent(f"""\
    ## What

    The hackathon dashboard has an appendix that fetches each contributor's **original
    notebook or script** and renders it beside the finished card, with a line saying
    what it was built into — or **why it was not**.

    Example entries:

    > `explore_gtfs_siri_coverage.py` → *"ported near-verbatim (nearest-stop +
    > time-tolerance matching), scoped down from a system-wide batch scan to one live
    > line"*
    >
    > `siri accessibility analysis using UrbanAccess.ipynb` → *"Not ported — urbanaccess
    > pulls ~10 heavy deps and its own notebook warns the network build is slow; that is
    > a batch job, not a live card"*

    ## Why it is worth copying

    It makes the **distance between research and product** visible. A reader can see
    that a card is a scoped-down version of a broader analysis, and reviewers can check
    the port against the original without cloning anything.

    The "not ported, and here is why" entries turned out to be the most valuable ones —
    they are how #50 and #51 in this milestone were found at all. Without them, that
    work would simply have disappeared.

    ## Suggested shape

    Lighter than the original: a per-chart "methods and source" link pointing at the
    notebook or script it came from, plus an explicit list of research that was
    considered and not built.

    Source: [`openbus_hack/source_material.py`]({HACK}/blob/main/openbus_hack/source_material.py),
    [`frontend/src/SourceMaterial.tsx`]({HACK}/blob/main/frontend/src/SourceMaterial.tsx)
    """), credit("the hackathon team", "README.md")))

# ══ Public appeal ═══════════════════════════════════════════════════════════

add(55, "Update the קול קורא page — all four open questions now have answers", ["enhancement", "non-code", "frontend"],
    body(BANNER, dedent(f"""\
    ## What

    The [public-appeal page](https://open-bus-map-search.hasadna.org.il/public-appeal)
    asks the public for help with four research questions. **The hackathon answered all
    four.** The page should say so, point at the answers, and ask the next question
    instead.

    ## Question by question

    ### 1. איפה נדרשים נתיבי תעדוף לתחבורה ציבורית (נת״צים)?
    *Where are bus priority lanes needed?*

    **Answered — with a ranked, costed list.** 725 corridors ranked by bus-minutes lost
    per hour; worst is Geha W-bound at **787 min/hr**, running 25.7 km/h against 62.6
    free-flow. Built from 60.3M street readings. → **#43**, dashboard in **#41**

    ### 2. חישוב שעת היציאה מתחנת המוצא, ושעת ההגעה לתחנות השונות במסלול
    *Computing departure from the origin stop and arrival at stops along the route*

    **Answered, including the trap.** The API serves no actual arrival times, so they
    are derived by interpolating the vehicle's closest approach to each stop (±30 s).
    Critically: the obvious approach — take the first GPS ping as departure — **is
    wrong**. The feed reports a vehicle ~30 or ~5 minutes before its scheduled start
    while it is still parked, which makes ~90% of rides look early. → **#1778**, method
    in **#1782**

    ### 3. איך לשייך קווי אוטובוס לאזורים גיאוגרפיים?
    *How to associate bus lines with geographic areas?*

    **Answered — no join required.** The ministry's own `cluster_nm` ("אשכול") ships in
    the per-line ticketing dataset and is a real geographic/service grouping. An earlier
    attempt to derive a distance-to-city-centre score failed because the resource it
    read has no line column at all. → **#1797**

    ### 4. התקבצות אוטובוסים
    *Bus bunching*

    **Answered at scale, with causes attributed.** 127,754 consecutive pairs across 709
    line-directions; 9.9% ran bunched; every event attributed to late departure (13%),
    first fifth of the route (10%) or en route (73%). → **#36**, dashboard in **#35**,
    rider cost in **#37**

    ## Also closes #1231

    #1231 asks to embed a notebook about vehicle velocities into this page. The speed
    dashboard (**#41**) *is* that research, at national-data scale and already
    interactive — a better fit than a Colab link.

    ## Suggested next questions to ask the public

    The hackathon surfaced questions it could not answer, which are better appeals than
    the four now closed:

    - **Which operators are contractually exempt from AVL reporting?** Four operators
      never appear in the tracking feed (#1780). From outside it is impossible to tell
      whether that is an exemption or a compliance failure — and it changes the national
      non-execution rate by ~2.2 points.
    - **What are the actual regulatory tolerances** for early and late departure?
      #1793 had to invent thresholds because the fine schedule was not available.
    - **How should unserved areas be measured?** 59% of mapped street-km in Tel Aviv has
      no bus (#44), but street-km is the wrong unit — population-weighted access is the
      right one, and nobody has built it (#50).

    ## Note on provenance

    Every linked answer is AI-drafted from hackathon materials and carries
    `needs-validation`. The public-appeal page should not present them as settled — the
    honest framing is *"the hackathon produced candidate answers; help us check them"*,
    which is also a better invitation.

    Related: #768 (page touch-ups).
    """), credit("the hackathon team", "README.md")))


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "to_review")
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest-phase2.json"
    manifest = []
    for it in ISSUES:
        slug = "".join(c if c.isalnum() or c in "- " else "" for c in it["title"].lower())
        slug = "-".join(slug.split())[:60].strip("-")
        fn = out / f"{it['n']:02d}-{slug}.md"
        fn.write_text(it["body"], encoding="utf-8")
        manifest.append({"n": it["n"], "title": it["title"], "labels": it["labels"],
                         "group": it["group"], "file": str(fn)})
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"wrote {len(manifest)} phase-2 issue bodies to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
