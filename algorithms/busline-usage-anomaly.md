# Bus line usage anomaly — over- and under-used lines vs. their peers

**Author:** team — ported from `busline_usage_anomaly.ipynb`, vendored at [busline_usage_anomaly.ipynb](../busline_usage_anomaly.ipynb) in the repo root
**Code:** [analyses/busline_usage_anomaly.py](../analyses/busline_usage_anomaly.py)
**Card:** `busline-usage-anomaly`
**Data:** **data.gov.il** ticketing/validation open data — resource `ef42a264-9da2-41ad-9120-822064fb5433`. The only card here not built on Stride SIRI/GTFS.

## What it answers

Which bus lines carry unusually many or few passengers **for their peer group, at
that hour of day**?

The idea worth keeping: raw passenger counts cannot be compared across lines. A
dense-city line and a suburban one carry wildly different volumes for reasons that
have nothing to do with how well either is running. So lines are compared only
against *peers*, and only within the same hour. A low score then means "carries
fewer riders than comparable lines at the same time of day" — **not** merely "is a
small line".

## Algorithm

1. **Fetch** `sample_rows` (default 15,000) from the data.gov.il datastore API,
   paged 5,000 at a time.
2. **Riders per row** — each row is one line × direction × hour × **month**, with
   `D1..D31` daily counts. `riders = mean(D1..D31)`, nulls skipped (days the line
   did not run, or a short month).
3. **Clean** — drop the rail sentinel `OfficeLineId == -1` (rail rows share the
   dataset and dwarf buses in volume) and drop `cluster_nm == "לא מוגדר"`.
4. **Collapse** direction and month duplicates: `groupby(line, operator, cluster,
   hour).riders.mean()`.
5. **Peer z-score** — group by `(cluster, hour)`, compute `peer_mean`, `peer_std`,
   `peer_count`, then `z = (riders - peer_mean) / peer_std`.
6. **Filter** to `peer_count >= min_peers` (default 3).
7. **Report** each line's single most extreme hour by `|z|`, top 14, sorted by z.

## Reasoning

Two deliberate departures from the notebook, **both because the original could not
work as written** — this is the most substantive porting critique in the repo:

**1. Peer grouping was rebuilt.** The notebook derived a "metro score" (exponential
decay from the nearest of Tel Aviv / Jerusalem / Haifa) from station coordinates —
but read it from data.gov.il resource `3ad014c3` (station passengers), **which has
no line column at all**. Its `get_station_passengers(office_line_id)` silently
ignored its argument and refetched the same global station table for every line, so
**every line ended up scored off identical rows**. The port uses the ministry's own
`cluster_nm` ("אשכול") — a real geographic/service grouping shipped in the same
per-line dataset, which is what the metro score was proxying for anyway, and needs
no join.

**2. Hours were simplified.** The notebook mapped 7 coarse Hebrew time bands to an
hour. The per-line resource carries a true `hour_a` (0–23), so no mapping is needed
and the resolution is better.

**Why `inputs=[]`.** Ticketing data keys on the ministry's own line ids, which do not
line up with the SIRI/GTFS line + operator + date pickers in the global filter bar.
Rather than accept filters it would silently ignore, the card declares it takes none.
Given [route-divergence's finding 1](route-divergence.md) — a filter accepted and
ignored producing a plausible wrong answer — this is exactly the right instinct.

**Why `peer_std` gets an epsilon.** A peer group of one has no spread; replacing 0
with `1e-5` keeps the division finite and lands its z at ~0, the honest reading for
"nothing to compare".

## Findings

### 1. data.gov.il resource `3ad014c3` has no line column, and the notebook's per-line metro score was therefore meaningless — **confidence: High**

`get_station_passengers(office_line_id)` ignored its argument and refetched the same
global table for every line. Every line was scored off identical rows, so the
resulting "metro score" varied not at all between lines. A schema fact plus a code
path, both checkable; it is why the peer grouping was replaced rather than ported.

**This is a finding about an analysis, not about buses** — recorded here because the
whole point of these documents is that dead ends should not be rediscovered.

### 2. `cluster_nm` is a usable ministry-defined peer grouping — **confidence: High**

Shipped in the same per-line dataset, requires no join, and is the ministry's own
geographic/service grouping. Directly observed in the data.

### 3. The per-line resource carries a true `hour_a` (0–23) — **confidence: High**

Better resolution than the 7 Hebrew time bands the notebook mapped from. Schema fact.

### 4. Ticketing counts undercount anyone not validating — **confidence: High**

Stated in the card's notes. Structural to validation data everywhere, not specific to
Israel; the size of the undercount is unknown and unmeasured here.

### 5. Which specific lines are over- or under-used vs. peers — **confidence: Low**

The card's actual output. Three compounding reasons:

- It is a **sample** (15,000 rows by default) of a much larger dataset, and the
  sample is whatever the datastore returns first — **not random**. Which lines even
  appear is an artifact of dataset ordering.
- Peer groups need only 3 members by default. A z-score against 2 other lines has
  almost no distributional meaning.
- `riders` is a mean over a month's daily counts, so a line that ran 4 days scores
  the same way as one that ran 30.

The *method* is sound; the numbers it currently produces are not quotable.

### 6. Counts of under- and over-performing line-hours (`z ≤ -1.5`, `z ≥ +1.5`) — **confidence: Low**

Reported in the notes. With peer groups as small as 3, |z| ≥ 1.5 is not a rare event
under any null hypothesis, and no multiple-comparison correction is applied across
thousands of line-hours.

## Criticism

**"Sample the first 15,000 rows" is not sampling.** `offset` walks from 0 in dataset
order, so the card analyses whichever lines the resource happens to list first.
Everything downstream — which clusters have enough peers, which lines appear as
extremes — inherits that ordering. A random sample, or full pagination with a longer
cache TTL, would fix this and is the single highest-value change to the card.

**Z-scores assume roughly normal peer distributions.** Ridership within a cluster is
strongly right-skewed (a few trunk lines, many feeders), so z overstates how unusual
the top end is and compresses the bottom. A rank-based or log-transformed score would
suit the distribution better. The card's own framing — "not merely a small line" — is
what makes this matter: skew is precisely the effect the z-score was meant to remove.

**Peer groups mix operators and route types.** `cluster_nm` is geographic. Within one
cluster, an express line and a local circulator are peers, and one of them will
always look anomalous. The notes do not mention this.

**The `min_peers = 3` default is far too low** for the statistic being computed, and
the option's own help text ("a z-score against one other line is noise") suggests the
author knew where the line was and drew it one step too permissively. With
`peer_count = 3`, `peer_std` is estimated from three points.

**Direction and month are averaged away** at step 4. A line that is packed inbound at
08:00 and empty outbound at 08:00 shows as average. That is a real signal — arguably
*the* signal for identifying under-served corridors — and it is discarded before
scoring.

**No date scoping at all.** The dataset spans multiple months; the card pools them
with no window and no indication of which months are in play. Two runs with different
`sample_rows` cover different time periods and are not comparable.
