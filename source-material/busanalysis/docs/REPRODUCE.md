# Reproducing this

Every command below is marked **[verified]** (run on this machine, with its real output and
timing) or **[unrun]** (needs database credentials and hours — documented, not executed).
Nothing here is idealised: if it says verified, it ran.

Environment used for the verified runs: **Python 3.13.5, Windows 11**.

## Prerequisites

```bash
python -m venv .venv
. .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Two environment variables are needed for anything that imports the package:

```bash
export PYTHONPATH=src         # the repo has no packaging metadata; src goes on the path
export PYTHONUTF8=1           # REQUIRED: Hebrew locality names crash on Windows cp1252 without it
```

```powershell
$env:PYTHONPATH='src'
$env:PYTHONUTF8='1'
```

`PYTHONUTF8=1` is not optional on Windows. Without it, any command that prints a Hebrew locality
name dies with `UnicodeEncodeError: 'charmap' codec can't encode character`.

---

## The 60-second path — no credentials, no warehouse

This is what a fresh clone can do immediately, and it is where to start.

**1. Look at the results.** Open either file directly from the filesystem — no server needed:

- `report/dashboard/brief.html` — one screen, four findings (0.3 MB)
- `report/dashboard/index.html` — the full six-tab dashboard (11.6 MB)

Both are committed and self-contained. The only thing in either page that reaches the network is
the interactive map's basemap tiles, on the Map tab of the full dashboard; everything else,
including every chart, is embedded.

**2. Run the test suite. [verified]**

```bash
python -m pytest -q
```

```
395 passed, 6 warnings in 49.83s
```

Wall clock including startup: **52 s**. The tests are the pipeline's real specification — they
cover the matcher's identities, the metric arithmetic, and the page generators' refusal to render
malformed input.

**3. Rebuild both pages from the committed data. [verified]**

```bash
python -m busanalysis.viz.brief
python -m busanalysis.viz.dashboard
```

```
wrote report\dashboard\brief.html (0.3 MB)                              # 1 s
wrote report\dashboard\index.html (11.6 MB) -- 1306/1307 days, 117.2M rides, 17/17 panels   # 2 s
```

This works on a bare clone because the inputs both generators need are committed:
`report/metrics/**` (the aggregates), `report/figures/**` (the PNGs), and the single 90 KB
`data/warehouse/marts/operator_month.parquet`.

Two honest caveats about step 3 on a fresh clone:

- The dashboard's build-progress tiles read `data/warehouse/matched/manifest.json`, which is not
  committed. Without it those tiles render a "processing" card. Every finding, figure and number
  is unaffected.
- **Re-rendering the figures is a different matter** and does *not* work from a bare clone:
  `busanalysis.viz.charts` requires `--marts data/warehouse/marts`, and `route_day.parquet`
  (87 MB) is not committed. The committed PNGs already carry those figures; regenerating them
  needs the full rebuild below.

---

## The full rebuild, stage by stage

Stages 1–2 need read-only stride credentials (copy `.env.example` → `.env`) and roughly 7 GB of
local disk. **Neither was re-run for this document** — the mirror and the census already exist on
the authoring machine, and re-pulling them costs hours of shared-infrastructure time for no new
information. Timings below for those two stages come from the project's own session notes and are
labelled as such.

### Stage 1 — mirror the source tables [unrun]

```bash
python -m busanalysis.pipeline.mirror
```

Real usage line:

```
usage: mirror.py [-h] [--root ROOT]
                 [--table {gtfs_route,gtfs_ride,siri_route,siri_ride}]
                 [--max-chunks MAX_CHUNKS] [--chunk-width CHUNK_WIDTH]
                 [--force]
```

Reads four slim ride-level tables from stride over a read-only, timeout-capped session.
Writes `data/warehouse/mirror/` — **245M rows, ~4.5 GB**.
Needs credentials. Estimated from session notes: a few hours, network-bound.

### Stage 2 — match each service day [unrun]

```bash
python -m busanalysis.pipeline.stage1_days      # per-day extract + match
python -m busanalysis.pipeline.backfill         # re-run specific days
```

Reads the mirror; writes `data/warehouse/matched/` — 1,306 day partitions plus `manifest.json`,
**~2.7 GB**. No credentials (the mirror is local). Estimated from session notes: hours for the
full census; a single day is cheap.

This stage applies the four corrections described in
[ARCHITECTURE.md](ARCHITECTURE.md#four-corrections-the-matcher-must-apply-or-the-answer-is-wrong).
Skipping them changes the national answer from 5.2% to 7.4%.

### Stage 3 — marts [unrun]

```bash
python -m busanalysis.pipeline.marts rebuild
```

```
usage: marts.py [-h] [--matched-root MATCHED_ROOT] [--marts-root MARTS_ROOT]
                {rebuild}
```

Reads matched partitions; writes `data/warehouse/marts/route_day.parquet` (8.4M rows, 87 MB) and
`operator_month.parquet` (90 KB, committed).

### Stage 4 — metrics [unrun without the marts]

```bash
python -m busanalysis.metrics.gap_series          --marts data/warehouse/marts --out report/metrics/gap_series
python -m busanalysis.metrics.enforcement_gap     --marts data/warehouse/marts --out report/metrics/enforcement_gap
python -m busanalysis.metrics.departure_fidelity  --marts data/warehouse/marts --out report/metrics/departure_fidelity
python -m busanalysis.metrics.record_integrity    --marts data/warehouse/marts --out report/metrics/record_integrity
python -m busanalysis.metrics.city_profiles       --marts data/warehouse/marts --out report/metrics/city_profiles
```

Check each module's `--help` for its exact flags before running — they differ slightly (the city
profiles stage also needs `--geo data/warehouse/geo`). Outputs are the committed
`report/metrics/**` parquets plus a `summary.md` per metric.

### Stage 5 — figures [unrun without the marts]

```bash
python -m busanalysis.viz.charts         --gap-series report/metrics/gap_series --marts data/warehouse/marts --out report/figures
python -m busanalysis.viz.heatmap        --gap-series report/metrics/gap_series --out report/figures
python -m busanalysis.viz.findings_charts --audit data/warehouse/audit --gap-series report/metrics/gap_series --out report/figures/findings
python -m busanalysis.viz.city_map       --geo data/warehouse/geo --marts data/warehouse/marts --out report/figures
```

### Stage 6 — the pages [verified, see the 60-second path]

---

## Verifying a rebuild is correct

Three independent checks, in increasing strength:

**1. The test suite.** 395 tests. A rebuild that breaks an identity fails here rather than
producing a plausible number.

**2. The frozen-number guard — this is the important one.** The published figures are transcribed
into the page generators from
[`../assistant/verification/headline_stats.md`](../assistant/verification/headline_stats.md), and
`viz/dashboard.py` recomputes the headline live from the marts on every build. If the live value
drifts from the frozen value beyond a small tolerance, the page prints a **visible reconciliation
warning** telling the reader to treat the frozen sentence as stale.

That means you do not have to trust the numbers on the page: if the data and the claims ever
disagree, the page says so about itself. A clean build with no warning is evidence they agree.

**3. Identity guards inside the matcher.** `planned = matched_t + gap_t` is checked at every
tolerance; a violation raises instead of continuing.

---

## Troubleshooting

**`UnicodeEncodeError: 'charmap' codec can't encode character`** — you are on Windows without
`PYTHONUTF8=1`. Hebrew locality names cannot be printed under cp1252. Set the variable; this is
the single most common failure.

**`ModuleNotFoundError: No module named 'busanalysis'`** — `PYTHONPATH=src` is not set. The repo
intentionally has no packaging metadata.

**`FileNotFoundError: credentials file .../.env not found`** — a stage-1/2 command needs
credentials. Copy `.env.example` to `.env`. Everything from stage 4 onward runs without them.

**A "Processing" card where you expected a chart** — the generator found no input file at that
path. On a fresh clone this is expected for the build-progress tiles only (see above). If it
appears anywhere else, an input is genuinely missing; the card names the file it wanted.

**The dashboard shows a reconciliation warning** — the live computation no longer matches the
frozen headline. Do not quote the page. Either the marts changed (re-freeze the statistics and
update `headline_stats.md`) or a correction regressed.

**`busanalysis.viz.charts` fails on a fresh clone** — expected: it needs `route_day.parquet`,
which is not committed. Use the committed PNGs, or do the full rebuild.

**Stale figures after a rebuild** — a browser will serve a cached copy of an 11 MB local file
quite happily. Hard-refresh (Ctrl+Shift+R). And if you left a `--watch` loop running from an
earlier session, it will keep overwriting the page you just rebuilt; check for stray
`busanalysis.viz.dashboard --watch` processes first. Both of these cost real debugging time
during development.
