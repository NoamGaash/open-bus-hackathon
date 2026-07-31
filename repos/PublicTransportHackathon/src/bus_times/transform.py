"""The analysis core: pure functions, no network and no plotting.

All the correctness risk in this project lives here, which is why it is kept free of I/O and
covered by unit tests.

The central problem is that the API exposes no actual arrival times — only raw GPS pings and the
planned GTFS timetable (see the design doc for the probing that established this). So an arrival is
*derived*: the time of the vehicle's closest approach to a stop's coordinates, interpolated between
the two nearest pings. Pings arrive roughly once a minute, so a single ride's arrival time is
accurate to about ±30 s; that is fine for the aggregate views the charts show and too coarse to
read a single ride's short segment from.
"""

import math
from typing import NamedTuple

import numpy as np
import pandas as pd

from .config import (
    ISRAEL_TZ,
    MAX_STOP_DISTANCE_M,
    PLAUSIBLE_RATIO_RANGE,
    TRUSTED_COVERAGE,
    TRUSTED_MATCH_DISTANCE_M,
    TRUSTED_RESOLUTION_S,
)

M_PER_DEG_LAT = 111_320.0

_EPOCH = pd.Timestamp(0, tz='UTC')

STOP_EVENT_COLUMNS = ['siri_ride_id', 'ride_date', 'scheduled_start_time', 'departure_hour',
                      'stop_sequence', 'stop_name', 'city', 'planned_time', 'actual_time',
                      'match_distance_m', 'resolution_s']

SEGMENT_COLUMNS = ['siri_ride_id', 'scheduled_start_time', 'departure_hour', 'segment_index',
                   'from_name', 'to_name', 'planned_duration_s', 'actual_duration_s',
                   'match_distance_m', 'resolution_s']

# Verdicts on how much a segment's number can be trusted, worst first. Anything other than 'ok' is
# marked in the charts rather than hidden.
CONFIDENCE_OK = 'ok'
CONFIDENCE_FEW_SAMPLES = 'few samples'
CONFIDENCE_LOW_COVERAGE = 'patchy coverage'
CONFIDENCE_COARSE_TIMING = 'coarse GPS timing'
CONFIDENCE_LOOSE_MATCH = 'loose stop match'
CONFIDENCE_IMPLAUSIBLE = 'implausible value'


class ArrivalEstimate(NamedTuple):
    """Derived arrival times plus the two things that say how much to trust each one.

    ``distance_m`` is how close the vehicle actually got to the stop, and ``resolution_s`` is the gap
    between the two pings the time was interpolated from — i.e. the estimate's own precision. Both are
    NaN where no arrival could be derived.
    """

    seconds: np.ndarray
    distance_m: np.ndarray
    resolution_s: np.ndarray


def _epoch_seconds(times: pd.Series) -> np.ndarray:
    """Seconds since the epoch, independent of the frame's datetime resolution.

    Avoids ``astype('int64')``, whose scale depends on whether pandas chose microsecond or
    nanosecond precision — a silent factor-of-1000 error.
    """
    return (pd.to_datetime(times, utc=True) - _EPOCH).dt.total_seconds().to_numpy(dtype=float)


def estimate_arrival_seconds(
    stop_lat: np.ndarray,
    stop_lon: np.ndarray,
    ping_lat: np.ndarray,
    ping_lon: np.ndarray,
    ping_seconds: np.ndarray,
    max_distance_m: float = MAX_STOP_DISTANCE_M,
    origin_departure: bool = True,
) -> ArrivalEstimate:
    """Estimate when a vehicle reached each stop, from its GPS trail.

    Stops must be given in route order and pings in chronological order. Returns an
    :class:`ArrivalEstimate`: the derived times plus, for each one, how close the vehicle got and how
    coarse the timing was. All three are NaN for stops the vehicle never came within
    ``max_distance_m`` of.

    Three properties matter, and each exists because real data violates the naive version:

    * The search is **forward-constrained** — stop *k* may only match a ping at or after the one
      matched for stop *k-1*. Without this, a route that doubles back past an earlier stop matches
      the wrong pass.
    * Results are **clamped monotonic**. Junctions carry several stop records a few metres apart,
      which otherwise resolve to slightly decreasing times and negative segment durations.
    * With ``origin_departure``, the first stop resolves to the moment the vehicle *left* it rather
      than its closest approach. Buses idle at the terminal emitting pings from one position, so
      closest approach lands somewhere mid-idle and inflates the first segment by minutes.
    """
    n_stops = len(stop_lat)
    arrivals = np.full(n_stops, np.nan)
    distances = np.full(n_stops, np.nan)
    resolutions = np.full(n_stops, np.nan)
    if n_stops == 0 or len(ping_seconds) == 0:
        return ArrivalEstimate(arrivals, distances, resolutions)

    # Equirectangular projection to metres. Over a single bus route the distortion is negligible
    # and it keeps the per-stop distance computation a plain vectorised hypot.
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(float(np.mean(ping_lat))))
    px = np.asarray(ping_lon, dtype=float) * m_per_deg_lon
    py = np.asarray(ping_lat, dtype=float) * M_PER_DEG_LAT
    pt = np.asarray(ping_seconds, dtype=float)
    n_pings = len(pt)

    search_from = 0
    last_arrival = -np.inf
    for k in range(n_stops):
        sx = float(stop_lon[k]) * m_per_deg_lon
        sy = float(stop_lat[k]) * M_PER_DEG_LAT
        dist = np.hypot(px[search_from:] - sx, py[search_from:] - sy)
        nearest = search_from + int(np.argmin(dist))
        distances[k] = float(dist.min())

        if distances[k] > max_distance_m:
            continue  # unvisited: leave the window open so later stops can still match

        # The departure rule only applies when the trail actually begins at the terminal. If the
        # first ping is already away from the origin, the vehicle was picked up mid-route and its
        # first timestamp says nothing about when it left, so fall back to closest approach.
        starts_at_origin = (k == 0 and origin_departure
                            and math.hypot(px[0] - sx, py[0] - sy) <= max_distance_m)
        if starts_at_origin:
            nearest = _last_ping_in_origin_vicinity(px, py, pt, sx, sy, max_distance_m)
            arrival = pt[nearest]
        else:
            arrival = _interpolate_closest_approach(px, py, pt, sx, sy, nearest,
                                                    search_from, n_pings)

        arrivals[k] = last_arrival = max(arrival, last_arrival)
        resolutions[k] = _local_ping_gap(pt, nearest)
        search_from = nearest

    return ArrivalEstimate(arrivals, distances, resolutions)


def _local_ping_gap(pt: np.ndarray, index: int) -> float:
    """Spacing between the pings around ``index`` — the precision of an arrival derived there.

    Interpolation places the arrival somewhere inside this interval, so the interval's width is how
    precisely the moment is known. A 20-second gap gives a usable arrival time; a five-minute gap
    means the bus could have passed the stop anywhere in those five minutes.
    """
    gaps = [pt[j + 1] - pt[j] for j in (index - 1, index) if 0 <= j < len(pt) - 1]
    return float(min(gaps)) if gaps else float('nan')


def _last_ping_in_origin_vicinity(px, py, pt, sx, sy, max_distance_m) -> int:
    """Index of the last ping of the opening run within range of the origin — i.e. departure."""
    i = 0
    while i + 1 < len(pt) and math.hypot(px[i + 1] - sx, py[i + 1] - sy) <= max_distance_m:
        i += 1
    return i


def _interpolate_closest_approach(px, py, pt, sx, sy, nearest, search_from, n_pings) -> float:
    """Project the stop onto the leg beside the nearest ping and interpolate its timestamp.

    Raises the effective resolution well below the ~60 s ping cadence: instead of snapping to the
    nearest ping, it estimates when the vehicle was actually abreast of the stop.
    """
    neighbours = [j for j in (nearest - 1, nearest + 1) if search_from <= j < n_pings]
    if not neighbours:
        return float(pt[nearest])

    other = min(neighbours, key=lambda j: math.hypot(px[j] - sx, py[j] - sy))
    vx, vy = px[other] - px[nearest], py[other] - py[nearest]
    span = vx * vx + vy * vy
    if span == 0:
        return float(pt[nearest])

    fraction = np.clip(((sx - px[nearest]) * vx + (sy - py[nearest]) * vy) / span, 0.0, 1.0)
    return float(pt[nearest] + fraction * (pt[other] - pt[nearest]))


class PatternSelection(NamedTuple):
    """The planned rides sharing the line's most common stop pattern, and what was set aside."""

    planned: pd.DataFrame
    n_patterns: int
    kept_rides: int
    total_rides: int
    n_stops: int


def dominant_stop_pattern(planned: pd.DataFrame) -> PatternSelection:
    """Keep only the planned rides whose stop sequence is the line's most common one.

    A single ``line_ref`` frequently serves more than one stop pattern — short workings, variants that
    detour past a station, occasional extended runs. Analysed together they produce a chart with two
    interleaved routes: the same stop pair appears twice at different positions, and every segment
    belonging to the minority variant looks like a coverage problem rather than a different route.

    Keeping the dominant pattern answers the question actually being asked — how long this line takes
    between its stops — instead of averaging two different journeys. The caller reports what was
    dropped, so the choice is visible rather than silent.
    """
    if planned.empty:
        raise ValueError('No planned timetable to pick a stop pattern from')

    ordered = planned.sort_values(['gtfs_ride_id', 'planned_arrival_time'])
    signatures = ordered.groupby('gtfs_ride_id')['name'].apply(tuple)
    counts = signatures.value_counts()
    dominant = counts.index[0]

    keep_ids = signatures[signatures.map(lambda sig: sig == dominant)].index
    return PatternSelection(
        planned=planned[planned['gtfs_ride_id'].isin(keep_ids)].copy(),
        n_patterns=len(counts),
        kept_rides=len(keep_ids),
        total_rides=len(signatures),
        n_stops=len(dominant),
    )


def match_rides_to_planned(rides: pd.DataFrame, planned: pd.DataFrame,
                           tolerance_minutes: int = 20) -> pd.Series:
    """Map each real (SIRI) ride to the planned (GTFS) ride it was meant to be.

    Real and planned records come from separate systems with no shared ride key, so they are matched
    on scheduled departure time. Rides with no planned departure within ``tolerance_minutes`` are
    left out — usually extra unscheduled services.
    """
    planned_starts = (planned.groupby('gtfs_ride_id')['gtfs_line_start_time']
                      .first()
                      .sort_values())
    if planned_starts.empty or rides.empty:
        return pd.Series(dtype='object')

    start_values = pd.to_datetime(planned_starts, utc=True)
    tolerance = pd.Timedelta(minutes=tolerance_minutes)

    matches = {}
    for ride in rides.itertuples():
        scheduled = pd.Timestamp(ride.scheduled_start_time).tz_convert('UTC')
        offsets = (start_values - scheduled).abs()
        best = offsets.idxmin()
        if offsets[best] <= tolerance:
            matches[ride.siri_ride_id] = best

    # The ride id keeps whatever type the API gave it — the API returns gtfs_ride_id as a *string*,
    # and coercing it to an integer here silently breaks every downstream lookup by key.
    return pd.Series(matches) if matches else pd.Series(dtype='object')


def build_stop_events(
    rides: pd.DataFrame,
    planned: pd.DataFrame,
    pings: pd.DataFrame,
    max_distance_m: float = MAX_STOP_DISTANCE_M,
) -> pd.DataFrame:
    """One row per (ride, stop), pairing each planned stop with its derived actual arrival.

    ``rides`` needs ``siri_ride_id`` and ``scheduled_start_time``; ``planned`` comes from
    ``/route_timetable/list``; ``pings`` needs ``siri_ride_id``, ``recorded_at_time``, ``lat`` and
    ``lon``. Rides with no planned counterpart or no GPS trail are dropped.
    """
    matched = match_rides_to_planned(rides, planned)
    if matched.empty or pings.empty:
        return pd.DataFrame(columns=STOP_EVENT_COLUMNS)

    planned = planned.copy()
    planned['planned_arrival_time'] = pd.to_datetime(planned['planned_arrival_time'], utc=True)
    plans = {gid: g.sort_values('planned_arrival_time').reset_index(drop=True)
             for gid, g in planned.groupby('gtfs_ride_id')}

    pings = pings.copy()
    pings['recorded_at_time'] = pd.to_datetime(pings['recorded_at_time'], utc=True)
    trails = {rid: g.sort_values('recorded_at_time')
              for rid, g in pings.groupby('siri_ride_id')}

    frames = []
    for ride in rides.itertuples():
        ride_id = ride.siri_ride_id
        plan = plans.get(matched.get(ride_id))
        trail = trails.get(ride_id)
        if plan is None or trail is None or trail.empty:
            continue

        estimate = estimate_arrival_seconds(
            plan['lat'].to_numpy(dtype=float), plan['lon'].to_numpy(dtype=float),
            trail['lat'].to_numpy(dtype=float), trail['lon'].to_numpy(dtype=float),
            _epoch_seconds(trail['recorded_at_time']),
            max_distance_m=max_distance_m,
        )

        scheduled = pd.Timestamp(ride.scheduled_start_time).tz_convert('UTC')
        local = scheduled.tz_convert(ISRAEL_TZ)
        frames.append(pd.DataFrame({
            'siri_ride_id': ride_id,
            'ride_date': local.date(),
            'scheduled_start_time': scheduled,
            'departure_hour': local.hour,
            'stop_sequence': np.arange(len(plan)),
            'stop_name': plan['name'].to_numpy(),
            'city': plan['city'].to_numpy(),
            'planned_time': plan['planned_arrival_time'].to_numpy(),
            'actual_time': pd.to_datetime(estimate.seconds, unit='s', utc=True),
            'match_distance_m': estimate.distance_m,
            'resolution_s': estimate.resolution_s,
        }))

    if not frames:
        return pd.DataFrame(columns=STOP_EVENT_COLUMNS)
    return pd.concat(frames, ignore_index=True)[STOP_EVENT_COLUMNS]


def build_ride_segments(stop_events: pd.DataFrame) -> pd.DataFrame:
    """One row per (ride, consecutive stop pair), with planned and actual durations.

    ``segment_index`` is the position of the segment in the route, taken from the planned stop
    sequence rather than from surviving rows, so the same segment lines up across rides even when
    one ride is missing a stop in between.
    """
    if stop_events.empty:
        return pd.DataFrame(columns=SEGMENT_COLUMNS)

    events = stop_events.sort_values(['siri_ride_id', 'stop_sequence'])
    grouped = events.groupby('siri_ride_id', sort=False)

    segments = pd.DataFrame({
        'siri_ride_id': events['siri_ride_id'],
        'scheduled_start_time': events['scheduled_start_time'],
        'departure_hour': events['departure_hour'],
        'segment_index': events['stop_sequence'],
        'from_name': events['stop_name'],
        'to_name': grouped['stop_name'].shift(-1),
        'planned_duration_s': grouped['planned_time'].shift(-1).sub(
            events['planned_time']).dt.total_seconds(),
        'actual_duration_s': grouped['actual_time'].shift(-1).sub(
            events['actual_time']).dt.total_seconds(),
        # A duration is only as good as its worse endpoint, so both quality measures take the
        # worst of the two stops bounding the segment.
        'match_distance_m': np.fmax(events['match_distance_m'],
                                    grouped['match_distance_m'].shift(-1)),
        'resolution_s': np.fmax(events['resolution_s'], grouped['resolution_s'].shift(-1)),
        # A gap in the stop sequence means the intermediate stop was dropped upstream, so the pair
        # of rows either side of it is not really a segment.
        '_step': grouped['stop_sequence'].shift(-1).sub(events['stop_sequence']),
    })

    usable = (segments['to_name'].notna()
              & (segments['_step'] == 1)
              & segments['actual_duration_s'].gt(0)
              # Junctions carry duplicate stop records sharing one planned arrival time. A segment
              # the timetable allots zero seconds has nothing to compare against, and its
              # actual/planned ratio is infinite.
              & segments['planned_duration_s'].gt(0))
    return segments[usable].drop(columns='_step').reset_index(drop=True)[SEGMENT_COLUMNS]


def _classify_confidence(row, min_samples: int) -> str:
    """One verdict per segment, naming the *worst* problem found.

    Ordered by how badly each issue undermines the number, so the label tells the reader which
    caveat actually applies rather than just "uncertain".
    """
    ratio = row['actual_median_s'] / row['planned_duration_s'] if row['planned_duration_s'] else None
    if ratio is not None and not (PLAUSIBLE_RATIO_RANGE[0] <= ratio <= PLAUSIBLE_RATIO_RANGE[1]):
        return CONFIDENCE_IMPLAUSIBLE
    if row['sample_count'] < min_samples:
        return CONFIDENCE_FEW_SAMPLES
    if row['coverage'] < TRUSTED_COVERAGE:
        return CONFIDENCE_LOW_COVERAGE
    if row['resolution_s'] > TRUSTED_RESOLUTION_S:
        return CONFIDENCE_COARSE_TIMING
    if row['match_distance_m'] > TRUSTED_MATCH_DISTANCE_M:
        return CONFIDENCE_LOOSE_MATCH
    return CONFIDENCE_OK


def aggregate_segments(ride_segments: pd.DataFrame, min_samples: int,
                       drop_insufficient: bool = False) -> pd.DataFrame:
    """Collapse per-ride segments into one row per segment: median, quartiles, mean, spread, count.

    Both a median with quartiles and a mean with standard deviation are returned. The **median** is
    what the charts plot: travel-time distributions are right-skewed, and a single ride whose GPS
    trail starts late produces an arrival estimate minutes out, which drags a mean far enough to
    flatten every other segment on the axis. The mean is kept because it is what a schedule planner
    budgeting total run time actually needs.

    Every segment is returned, each carrying a ``confidence`` verdict and the measurements behind it
    (``sample_count``, ``coverage``, ``resolution_s``, ``match_distance_m``). Under-sampled segments
    are **kept and flagged**, not dropped: a segment silently missing from a chart looks like a
    segment that does not exist, which is the most misleading failure available here. Pass
    ``drop_insufficient=True`` for the old filtering behaviour.
    """
    if ride_segments.empty:
        raise ValueError('No usable segments: every ride was missing planned or GPS data')

    total_rides = ride_segments['siri_ride_id'].nunique()
    agg = (ride_segments
           .groupby(['segment_index', 'from_name', 'to_name'], as_index=False)
           .agg(actual_median_s=('actual_duration_s', 'median'),
                actual_p25_s=('actual_duration_s', lambda s: s.quantile(0.25)),
                actual_p75_s=('actual_duration_s', lambda s: s.quantile(0.75)),
                actual_mean_s=('actual_duration_s', 'mean'),
                actual_std_s=('actual_duration_s', 'std'),
                sample_count=('actual_duration_s', 'size'),
                planned_duration_s=('planned_duration_s', 'mean'),
                resolution_s=('resolution_s', 'median'),
                match_distance_m=('match_distance_m', 'median'))
           .sort_values('segment_index')
           .reset_index(drop=True))
    # std is undefined for a single sample; zero spread is the honest reading of one observation.
    agg['actual_std_s'] = agg['actual_std_s'].fillna(0.0)
    # How many of the rides that ran this route produced a usable value here. A segment measured on 4
    # of 200 rides deserves a different reading than one measured on 190, even though both clear
    # min_samples.
    agg['coverage'] = agg['sample_count'] / max(total_rides, 1)
    agg['confidence'] = agg.apply(_classify_confidence, axis=1, min_samples=min_samples)
    agg['is_reliable'] = agg['confidence'] == CONFIDENCE_OK

    if drop_insufficient:
        agg = agg[agg['sample_count'] >= min_samples].reset_index(drop=True)

    if agg.empty or agg['sample_count'].max() < 1:
        raise ValueError(
            f'No segment had any usable data (min_samples={min_samples}); '
            f'widen the date range or lower min_samples')
    return agg


def stop_coverage(stop_events: pd.DataFrame) -> pd.DataFrame:
    """Per stop: how often an arrival could be derived there, and how good those matches were.

    A stop the GPS rarely resolves drags down both segments beside it, so the Marey chart marks these
    on its axis instead of letting the reader assume every stop is equally well measured.
    """
    if stop_events.empty:
        raise ValueError('No stop events to measure coverage on')

    # Grouped by route *position*, one row per stop_sequence. Grouping by (sequence, name) instead
    # duplicates a position whenever route alternatives put different stops there, and anything that
    # then indexes coverage by sequence blows up on the duplicate label.
    coverage = (stop_events
                .groupby('stop_sequence', as_index=False)
                .agg(stop_name=('stop_name', lambda s: s.mode().iat[0]),
                     rides=('actual_time', 'size'),
                     matched=('actual_time', 'count'),
                     match_distance_m=('match_distance_m', 'median'),
                     resolution_s=('resolution_s', 'median'))
                .assign(coverage=lambda d: d['matched'] / d['rides'].where(d['rides'] > 0))
                .sort_values('stop_sequence')
                .reset_index(drop=True))
    assert coverage['stop_sequence'].is_unique  # the invariant callers index on
    return coverage


def quality_summary(aggregated: pd.DataFrame) -> str:
    """One-line, human-readable verdict on how much of a route is well measured."""
    total = len(aggregated)
    reliable = int(aggregated['is_reliable'].sum())
    parts = [f'{reliable}/{total} segments reliable']
    flagged = aggregated.loc[~aggregated['is_reliable'], 'confidence'].value_counts()
    parts += [f'{count} {reason}' for reason, count in flagged.items()]
    return ' · '.join(parts)


class HourMatrix(NamedTuple):
    """Paired segment × hour grids: the values, and how many rides each one rests on."""

    ratio: pd.DataFrame
    count: pd.DataFrame


def segment_hour_matrix(ride_segments: pd.DataFrame, min_samples: int = 1) -> HourMatrix:
    """Segments × departure hour, valued by median actual/planned duration ratio, plus ride counts.

    A ratio rather than a duration so that segments of very different lengths stay comparable in one
    colour scale, with 1.0 meaning "exactly as scheduled". The median rather than the mean so a single
    broken arrival estimate cannot define a cell.

    The count grid is returned alongside so the chart can distinguish a cell with **no** data from one
    resting on a single ride — collapsing those two into one blank cell hides exactly the thing worth
    knowing. ``min_samples`` only filters out segments that nowhere reach it.
    """
    if ride_segments.empty:
        raise ValueError('No usable segments to build an hour matrix from')

    df = ride_segments.copy()
    df['ratio'] = df['actual_duration_s'] / df['planned_duration_s']
    df = df[np.isfinite(df['ratio'])]
    if df.empty:
        raise ValueError('No segment had a finite actual/planned ratio')

    keys = ['segment_index', 'from_name', 'to_name']
    cells = df.groupby(keys + ['departure_hour'], as_index=False).agg(
        ratio=('ratio', 'median'), count=('ratio', 'size'))

    ratio = (cells.pivot_table(index=keys, columns='departure_hour', values='ratio', dropna=False)
             .sort_index(level='segment_index'))
    count = (cells.pivot_table(index=keys, columns='departure_hour', values='count', dropna=False)
             .reindex(index=ratio.index, columns=ratio.columns)
             .fillna(0)
             .astype(int))

    # Keep a segment if it clears min_samples in at least one hour; a row that never does is noise.
    keep = count.max(axis=1) >= min_samples
    if not keep.any():
        raise ValueError(
            f'No segment reached min_samples={min_samples} in any hour; '
            f'widen the date range or lower min_samples')
    return HourMatrix(ratio[keep], count[keep])


def elapsed_profiles(stop_events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-ride and planned progress along the route, in minutes since the first stop.

    Returns ``(actual, planned)``. Measuring elapsed rather than wall-clock time is what lets rides
    from different hours and days overlay on one axis in the Marey diagram.
    """
    if stop_events.empty:
        raise ValueError('No stop events to build trajectories from')

    actual = stop_events.dropna(subset=['actual_time']).copy()
    if actual.empty:
        raise ValueError('No stop had a derived arrival time; GPS coverage was too sparse')
    actual = actual.sort_values(['siri_ride_id', 'stop_sequence'])
    first = actual.groupby('siri_ride_id')['actual_time'].transform('first')
    actual['elapsed_min'] = (actual['actual_time'] - first).dt.total_seconds() / 60

    # The planned profile is identical for every ride of the line up to schedule padding, so one
    # median profile is the right reference to draw behind the trajectories.
    plan = stop_events.dropna(subset=['planned_time']).copy()
    plan = plan.sort_values(['siri_ride_id', 'stop_sequence'])
    plan_first = plan.groupby('siri_ride_id')['planned_time'].transform('first')
    plan['elapsed_min'] = (plan['planned_time'] - plan_first).dt.total_seconds() / 60
    # Exactly one row per stop_sequence. Route alternatives can put different stops at the same
    # position, and a duplicated sequence would give the Marey chart two ticks at one y value.
    planned = (plan.groupby('stop_sequence', as_index=False)
               .agg(elapsed_min=('elapsed_min', 'median'),
                    stop_name=('stop_name', lambda s: s.mode().iat[0]))
               .sort_values('stop_sequence')
               .reset_index(drop=True))

    return actual, planned[['stop_sequence', 'stop_name', 'elapsed_min']]
