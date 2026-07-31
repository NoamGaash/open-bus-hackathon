# open-bus-hackathon

Shared infra for the hasadna **Open Bus** hackathon. Everyone writes one function;
they all show up on one dashboard for the final presentation.

POCs proven here get consolidated upstream into
[open-bus-map-search](https://github.com/hasadna/open-bus-map-search),
[open-bus-stride-api](https://github.com/hasadna/open-bus-stride-api), and
[open-bus-pipelines](https://github.com/hasadna/open-bus-pipelines).

---

## Getting started

**You need Docker + VS Code.** Everything else is inside the container — don't
install Python or Node on your machine.

1. Install [Docker](https://docs.docker.com/engine/install/) and the VS Code
   [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Clone and open this repo in VS Code.
3. Click **Reopen in Container** when prompted (or `F1` → *Dev Containers: Reopen in Container*).
4. Wait for the one-time setup, then in the container terminal:

```bash
./dev
```

That's it. Three things start:

| | URL | What |
|---|---|---|
| **Dashboard** | http://localhost:5173 | ← the thing you look at |
| API | http://localhost:8000/docs | runs your analysis, feeds the dashboard |
| JupyterLab | http://localhost:8888 | notebooks, no token needed |

> **No Docker?** Open the repo in a
> [GitHub Codespace](https://codespaces.new/NoamGaash/open-bus-hackathon) instead —
> same container, nothing to install.

### Claude Code is in the container

Run `claude` in any container terminal. It sees the same Python env, the same data
client, and the same running services you do — so "why is my analysis returning an
empty frame?" is a question it can actually investigate.

First run asks you to sign in. That login is stored in a Docker volume scoped to
this repo, so **you only do it once** — it survives container rebuilds.

---

## Add your analysis

```bash
./dev new delay-by-hour
```

That scaffolds `analyses/delay_by_hour.py`. Fill in the TODO and your card appears
on the dashboard — no wiring, no imports to register anywhere.

The whole contract:

```python
from openbus_hack import AnalysisRequest, analysis, line_chart, stride

@analysis(
    name="delay-by-hour",
    title="Delay by hour of day",
    description="Median delay per hour, to find the worst part of the day.",
    author="your-name",
)
def run(req: AnalysisRequest):
    df = stride.siri_rides(
        lines=req.lines,
        operators=req.operators,
        date_from=req.date_from,
        date_to=req.date_to,
    )
    hourly = df.groupby(df["scheduled_start_time"].dt.hour).size().reset_index(name="rides")
    return line_chart(hourly, x="scheduled_start_time", y="rides")
```

### What you get in `req`

| | |
|---|---|
| `req.lines` | `["480", "1"]` — line short-names (may be empty) |
| `req.operators` | `["אגד"]` — agency names (may be empty) |
| `req.date_from` / `req.date_to` | `date` objects |
| `req.line` / `req.operator` | first one, for single-value analyses |
| `req.days` | number of days in the window |
| `req.opt("top_n", 5)` | your own declared options |

### What you can return

| Return this | Renders as |
|---|---|
| `metrics(("Total rides", 1234), ("On-time", 87.5))` | stat tiles |
| `line_chart(df, x="day", y="rides", series="operator")` | line chart |
| `bar_chart(df, x="hour", y="count", stacked=True)` | bar chart |
| `table(df)` | scrollable table |
| a matplotlib figure | inline PNG |
| a DataFrame | table |

Add caveats with `notes=["only 3 days of SIRI data"]` — they render under the chart.

Set `draft=True` while you're still hacking; the card gets a **DRAFT** badge so
nobody demos a work-in-progress by accident.

---

## Getting the data

```python
from openbus_hack import stride

stride.agencies()                       # operator_ref ↔ agency_name
stride.routes(lines=["480"])            # GTFS routes
stride.siri_rides(lines=["480"])        # actual observed rides
stride.gtfs_rides_agg(d1, d2, group_by="operator_ref,gtfs_route_date")   # fast aggregates
stride.siri_vehicle_locations(t1, t2)   # raw GPS pings — pass a tight window
```

All return DataFrames, all paged for you, all cached on disk — so re-running a
cell fifty times hits the cache, not the community's shared API.
`stride.clear_cache()` to reset.

Full API: https://open-bus-stride-api.hasadna.org.il/docs

> `gtfs_rides_agg`'s `group_by` only accepts `gtfs_route_date`, `gtfs_route_hour`,
> `operator_ref`, `day_of_week`, `line_ref`. Anything else returns a 500.
> Direct link to that endpoint's docs:
> https://open-bus-stride-api.hasadna.org.il/docs#/aggregations/group_by__gtfs_rides_agg_group_by_get

### Skipping the client: direct Postgres access

The Stride API is backed by a Postgres read replica, reachable directly if you'd
rather write SQL than page through REST:

```
host = open-bus-stride-db.hasadna.org.il
port = 5432
user = talpihack26
```

(Password shared separately — ask in Slack if you don't have it.) Prefer
`openbus_hack.stride` for anything the REST API already covers — it's cached on
disk and won't hammer the shared DB.

### More resources

| | |
|---|---|
| Stride API source | https://github.com/hasadna/open-bus-stride-api |
| Stride DB schema / data model | https://github.com/hasadna/open-bus-stride-db/blob/main/DATA_MODEL.md |
| Stride Python client + notebook guide | https://github.com/hasadna/open-bus-stride-client/blob/main/README.md#using-the-interactive-jupyter-notebooks |
| Open Bus map search (consumes this data today) | https://github.com/hasadna/open-bus-map-search |
| Geo layer for roads / PT infrastructure | https://geo.mot.gov.il/ |
| Line info lookup (e.g. line 86001) | https://markav.net/line/86001/ |
| Hasadna Slack (#opendata / open-bus channels) | https://join.slack.com/t/hasadna/shared_invite/zt-458cp0v0n-GSnHzAq6F5aHeK43O4YeeA |

---

## Your scratch space

`workspace/<your-name>/` is created for you on first run:

```
workspace/noam/
  notebooks/   drafts, exploration, dead ends
  data/        intermediate results worth keeping   (data/raw/ is gitignored)
  out/         exported charts
  NOTES.md     running log
```

Be messy in there. Only `analyses/*.py` reaches the dashboard.

## Commit everything

This repo ignores almost nothing on purpose — **commit your drafts, notebooks and
intermediate results.** A half-finished notebook in git beats a perfect one on
your laptop.

```bash
./dev save "explored delay distribution for 480"
```

Stages everything, commits, pushes. `nbdime` is configured, so notebook diffs are
actually readable.

---

## Commands

```
./dev              start everything
./dev dash         dashboard only
./dev api          API only
./dev lab          JupyterLab only
./dev new <name>   scaffold a new analysis
./dev list         list registered analyses
./dev check        verify nothing is broken  ← run before the demo
./dev save "msg"   commit + push everything
```

## Layout

```
.devcontainer/     the dev environment
openbus_hack/      shared library
  contract.py      AnalysisRequest / AnalysisResult + return helpers
  registry.py      the @analysis decorator and auto-discovery
  stride.py        Open Bus API client
  theme.py         shared matplotlib styling
  server.py        FastAPI bridge to the dashboard
analyses/          ← one file per person; this is the deliverable
frontend/          the dashboard (React + Vite)
notebooks/         shared notebooks
workspace/         per-person scratch space
```

One broken analysis can't break the demo: import failures and exceptions render
as an error card, and everything else keeps working.

## Tests / CI

The dashboard has a Playwright end-to-end suite in `frontend/e2e/`. It never
talks to the real API — `/api/**` is intercepted with `page.route()` and
served from hand-written fixtures under `frontend/e2e/fixtures/` (shaped to
match `openbus_hack/contract.py`), because the real analyses call a public
transit API and can take 60-90s per call. That means the suite only needs the
Vite dev server, not the Python backend.

```
cd frontend
npx playwright install --with-deps chromium   # first time only
npm run test:e2e
```

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:
a `python` job that `uv sync`s and runs `./dev check` (plus a non-blocking
`ruff check`), and a `frontend` job that type-checks with `tsc` and runs the
Playwright suite, uploading the HTML report as an artifact.

## Desired quality checks for the hackathon

https://docs.google.com/spreadsheets/d/1uFikn1oFehRSQzr4VxS09NjVna7_gvvluq2YKs1pl5Y/edit?gid=0#gid=0
