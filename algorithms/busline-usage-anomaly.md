# Bus Line Ridership Anomaly — "Over- and under-used lines vs. their peers"

**Author:** team (`author="team (busline_usage_anomaly.ipynb)"` in the registry)
**Code:** [analyses/busline_usage_anomaly.py](../analyses/busline_usage_anomaly.py) and original notebook [busline_usage_anomaly.ipynb](../busline_usage_anomaly.ipynb)
**Cards:** `busline-usage-anomaly` ("Over- and under-used lines vs. their peers")
**Data:** data.gov.il datastore API (Resource `ef42a264-9da2-41ad-9120-822064fb5433` - ticketing validation records)

## What it answers

- **Which bus lines carry unusually many or few passengers compared to similar lines?** Rather than looking at absolute boarding numbers, this scores each line-hour against its regional geographic peers, identifying relative under-performance or overcrowding.

## Algorithm

1. **Fetch validations:** Pages through the data.gov.il hourly ticketing datastore, retrieving up to `sample_rows` (default 15,000 rows).
2. **Calculate Average Daily Boardings:**
   - The database contains validation columns `D1`..`D31` representing passenger counts per day of the month.
   - Calculates the mean daily validations for each row, ignoring null values.
   - Groups by `line` (`OfficeLineId`), `operator` (`operator_nm`), `cluster` (`cluster_nm`), and `hour` (`hour_a`, 0-23).
   - Filters out railway records (marked with line ID -1) and undefined clusters.
3. **Peer Grouping:** Groups line-hours by their regional ministry cluster ("אשכול", e.g., Netanya, Jerusalem, Sharon) and hour of day.
4. **Z-Score Calculation:**
   - Within each (cluster, hour) peer group, calculates the mean ($\mu$) and standard deviation ($\sigma$) of daily boardings.
   - Calculates the z-score of daily boardings for each individual line-hour:
     $$z = \frac{\text{boardings} - \mu}{\sigma}$$
   - Handles peer groups of size 1 by substituting a tiny standard deviation ($\epsilon = 10^{-5}$) to set their z-score to 0 (the honest value for "nothing to compare").
5. **Filter and Sort:** Drops line-hours with peer group sizes below `min_peers` (default 3) to prevent statistical noise. Sorts by absolute z-score and displays the most extreme over- and under-performing lines.

## Reasoning

**Why z-scores and regional clusters instead of raw counts.** You cannot compare a bus line in Tel Aviv directly to a bus line in a small Galilee village—their base demands are completely different. Comparing a line strictly to other lines operating in the same regional ministry cluster ("אשכול") at the exact same hour of day provides a realistic baseline of expected demand, turning "12 boardings" into a highly citable relative score.

**Why the "אשכול" (cluster_nm) is better than "metro score."** The original notebook attempted to derive a "metro score" by calculating exponential decay from geographic coordinates to major cities. However, the datastore resource used had no station coordinates, so the notebook ended up calculating identical scores across all lines. Using the ministry's official regional cluster field (`cluster_nm`) is structurally cleaner, requires no complex joins, and accurately reflects regional geographic peer networks.

## Findings

### 1. Relative ridership under-performance is concentrated on specific, identifiable line-hours — **confidence: High**
Calculating cluster-hour z-scores isolates specific routes that are severely under-utilized (z-scores below -1.5) compared to their own neighborhood peers operating in the same hour, revealing localized route design failures or scheduling mismatch rather than regional trends.

## Criticism

**Siloed data identifiers.** data.gov.il ticketing databases identify routes using "OfficeLineId" (the ministry's internal registration numbers). These identifiers do not correspond to the GTFS/SIRI `line_ref` or `route_short_name` keys used by the Stride API. As a result, this card operates in a disconnected silo, and changing the global line/operator filters on the dashboard has no effect on it.

**Incomplete sampling.** To prevent slow page loads, the datastore API is capped at 15,000 rows. This represents a tiny, arbitrary slice of the national ticketing database and may omit smaller operators or less frequent lines entirely, introducing sampling bias.
