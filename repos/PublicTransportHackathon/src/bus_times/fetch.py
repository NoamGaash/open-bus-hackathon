"""Every network call lives here. No statistics, no plotting.

The shape of this module is dictated by measured API limits rather than taste:

* A whole day of GPS pings for one line exceeds the server's 60 s statement timeout, so pings are
  requested in chunks of ride ids (about 0.7 s per ride).
* That per-ride cost makes "fetch everything" impractical — a busy line runs ~150 rides a day — so
  rides are **sampled**, stratified across date and departure hour so the heatmap's hour axis stays
  populated while a run stays bounded.
* Planned times come from ``/route_timetable/list``, which is the only endpoint that returns stop
  coordinates and Hebrew stop names alongside the schedule.
"""

import datetime
from collections.abc import Iterable

import pandas as pd

from .config import (
    DEFAULT_HOUR_RANGE,
    DEFAULT_MAX_RIDES,
    DEFAULT_MAX_RIDES_PER_HOUR,
    ISRAEL_TZ,
    MAX_SERVER_LIMIT,
    MAX_STOP_DISTANCE_M,
    RIDE_ID_CHUNK,
)
from .lines import LineSpec
from .lowlevel import get_rows, iter_rows
from .transform import build_ride_segments, build_stop_events, dominant_stop_pattern

PLANNED_COLUMNS = ['gtfs_ride_id', 'gtfs_line_start_time', 'name', 'city', 'lat', 'lon',
                   'planned_arrival_time']
PING_COLUMNS = ['siri_ride_id', 'recorded_at_time', 'lat', 'lon']


def _day_bounds(day: datetime.date, hour_range: tuple[int, int]) -> tuple[datetime.datetime, datetime.datetime]:
    start_hour, end_hour = hour_range
    midnight = datetime.datetime.combine(day, datetime.time(0, 0), tzinfo=ISRAEL_TZ)
    return (midnight + datetime.timedelta(hours=start_hour),
            midnight + datetime.timedelta(hours=end_hour))


def weekdays_between(date_from: datetime.date, date_to: datetime.date) -> list[datetime.date]:
    """Sunday-to-Thursday dates in the range — the Israeli working week."""
    days = []
    day = date_from
    while day <= date_to:
        if day.weekday() not in (4, 5):  # skip Friday and Saturday
            days.append(day)
        day += datetime.timedelta(days=1)
    return days


def fetch_planned_timetable(line: LineSpec, days: Iterable[datetime.date],
                            hour_range: tuple[int, int] = DEFAULT_HOUR_RANGE) -> pd.DataFrame:
    """Planned per-stop arrival times, with stop coordinates and Hebrew names, for whole days.

    One request per day; a full line-day is roughly 3500 rows and takes about 25 s.
    """
    frames = []
    for day in days:
        start, end = _day_bounds(day, hour_range)
        rows = list(iter_rows('/route_timetable/list', {
            'line_refs': str(line.line_ref),
            'planned_start_time_date_from': start,
            'planned_start_time_date_to': end,
            'order_by': 'gtfs_line_start_time, planned_arrival_time',
        }, limit=MAX_SERVER_LIMIT))
        if rows:
            frames.append(pd.DataFrame(rows)[PLANNED_COLUMNS])

    if not frames:
        return pd.DataFrame(columns=PLANNED_COLUMNS)

    planned = pd.concat(frames, ignore_index=True)
    for column in ('gtfs_line_start_time', 'planned_arrival_time'):
        planned[column] = pd.to_datetime(planned[column], utc=True)
    return planned


def fetch_rides(line: LineSpec, days: Iterable[datetime.date],
                hour_range: tuple[int, int] = DEFAULT_HOUR_RANGE) -> pd.DataFrame:
    """Real (SIRI) rides scheduled on the given days. Cheap — well under a second per day."""
    routes = get_rows('/siri_routes/list',
                      {'operator_refs': line.operator_ref, 'line_refs': line.line_ref}, limit=1000)
    if not routes:
        return pd.DataFrame(columns=['siri_ride_id', 'scheduled_start_time'])
    route_ids = ','.join(str(r['id']) for r in routes)

    frames = []
    for day in days:
        start, end = _day_bounds(day, hour_range)
        rows = get_rows('/siri_rides/list', {
            'siri_route_ids': route_ids,
            'scheduled_start_time_from': start,
            'scheduled_start_time_to': end,
            'order_by': 'scheduled_start_time asc',
        }, limit=MAX_SERVER_LIMIT)
        if rows:
            frames.append(pd.DataFrame(rows)[['id', 'scheduled_start_time']])

    if not frames:
        return pd.DataFrame(columns=['siri_ride_id', 'scheduled_start_time'])

    rides = pd.concat(frames, ignore_index=True).rename(columns={'id': 'siri_ride_id'})
    rides['scheduled_start_time'] = pd.to_datetime(rides['scheduled_start_time'], utc=True)
    return rides.drop_duplicates('siri_ride_id').reset_index(drop=True)


def sample_rides(rides: pd.DataFrame,
                 max_per_hour: int = DEFAULT_MAX_RIDES_PER_HOUR,
                 max_total: int = DEFAULT_MAX_RIDES,
                 seed: int = 0) -> pd.DataFrame:
    """Thin the ride list, spreading the sample evenly over date and departure hour.

    Fetching GPS costs ~0.7 s per ride, so the full ride list of a busy line is unaffordable. Even
    coverage matters more than volume here: the heatmap needs every hour represented, and the
    segment statistics converge long before a hundred rides.
    """
    if rides.empty:
        return rides

    local = rides['scheduled_start_time'].dt.tz_convert(ISRAEL_TZ)
    keyed = rides.assign(_date=local.dt.date, _hour=local.dt.hour)

    sampled = (keyed.groupby(['_date', '_hour'], group_keys=False)
               .apply(lambda g: g.sample(min(len(g), max_per_hour), random_state=seed),
                      include_groups=False))
    sampled = keyed.loc[sampled.index]

    if len(sampled) > max_total:
        # Spread the trim across the strata rather than truncating whole late hours away.
        sampled = sampled.sample(max_total, random_state=seed)

    return (sampled.drop(columns=['_date', '_hour'])
            .sort_values('scheduled_start_time')
            .reset_index(drop=True))


def fetch_pings(ride_ids: Iterable[int], chunk_size: int = RIDE_ID_CHUNK,
                progress: bool = True) -> pd.DataFrame:
    """GPS pings for the given rides, chunked to stay under the server's statement timeout."""
    ride_ids = list(ride_ids)
    frames = []
    for offset in range(0, len(ride_ids), chunk_size):
        chunk = ride_ids[offset:offset + chunk_size]
        rows = list(iter_rows('/siri_vehicle_locations/list', {
            'siri_rides__ids': ','.join(str(i) for i in chunk),
            'order_by': 'recorded_at_time asc',
        }, limit=MAX_SERVER_LIMIT))
        if rows:
            frames.append(pd.DataFrame(rows)[['siri_ride__id', 'recorded_at_time', 'lat', 'lon']])
        if progress:
            done = min(offset + chunk_size, len(ride_ids))
            print(f'  pings: {done}/{len(ride_ids)} rides', flush=True)

    if not frames:
        return pd.DataFrame(columns=PING_COLUMNS)

    pings = pd.concat(frames, ignore_index=True).rename(columns={'siri_ride__id': 'siri_ride_id'})
    pings['recorded_at_time'] = pd.to_datetime(pings['recorded_at_time'], utc=True)
    for column in ('lat', 'lon'):
        pings[column] = pd.to_numeric(pings[column], errors='coerce')
    return pings.dropna(subset=['lat', 'lon']).reset_index(drop=True)


def load_line_data(
    line: LineSpec,
    date_from: datetime.date,
    date_to: datetime.date,
    hour_range: tuple[int, int] = DEFAULT_HOUR_RANGE,
    max_rides_per_hour: int = DEFAULT_MAX_RIDES_PER_HOUR,
    max_rides: int = DEFAULT_MAX_RIDES,
    max_distance_m: float = MAX_STOP_DISTANCE_M,
    weekdays_only: bool = True,
    dominant_pattern_only: bool = True,
    verbose: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch and assemble everything the charts need: ``(stop_events, ride_segments)``.

    Coverage is printed rather than assumed — with derived arrival times and a sampled ride list,
    silently thin data is the main way to end up with a confident-looking but meaningless chart.

    ``dominant_pattern_only`` restricts the analysis to the line's most common stop pattern. One
    ``line_ref`` often serves several (short workings, detour variants); analysing them together
    interleaves two different routes into one chart, where the minority variant's segments look like a
    coverage problem instead of a different journey. Set it False to keep every variant.
    """
    days = weekdays_between(date_from, date_to) if weekdays_only else [
        date_from + datetime.timedelta(days=i) for i in range((date_to - date_from).days + 1)]
    if not days:
        raise ValueError(f'No days to analyse between {date_from} and {date_to}')

    def say(message: str) -> None:
        if verbose:
            print(message, flush=True)

    say(f'{line}')
    say(f'  planned timetable for {len(days)} day(s) {days[0]}..{days[-1]}')
    planned = fetch_planned_timetable(line, days, hour_range)
    if planned.empty:
        raise ValueError(
            f'No planned timetable for {line} between {date_from} and {date_to}. '
            f'Check the line_ref is active on those dates.')
    say(f'  planned: {len(planned)} stop rows across '
        f"{planned['gtfs_ride_id'].nunique()} scheduled rides")

    if dominant_pattern_only:
        selection = dominant_stop_pattern(planned)
        planned = selection.planned
        if selection.n_patterns > 1:
            # Worth stating plainly: this is a real narrowing of what the charts describe.
            say(f'  {selection.n_patterns} stop patterns on this line_ref; keeping the dominant one '
                f'({selection.kept_rides}/{selection.total_rides} scheduled rides, '
                f'{selection.n_stops} stops). Minority variants are different routes, not missing data.')

    rides = fetch_rides(line, days, hour_range)
    if rides.empty:
        raise ValueError(
            f'No real-time (SIRI) rides for {line} between {date_from} and {date_to}. '
            f'SIRI history is short — try a more recent date range.')
    sampled = sample_rides(rides, max_rides_per_hour, max_rides)
    say(f'  rides: sampled {len(sampled)} of {len(rides)} available')

    pings = fetch_pings(sampled['siri_ride_id'], progress=verbose)
    if pings.empty:
        raise ValueError(f'No GPS pings returned for any of the {len(sampled)} sampled rides')
    say(f'  pings: {len(pings)} across {pings["siri_ride_id"].nunique()} rides')

    stop_events = build_stop_events(sampled, planned, pings, max_distance_m=max_distance_m)
    if stop_events.empty:
        raise ValueError('No ride could be matched to a planned timetable and a GPS trail')
    ride_segments = build_ride_segments(stop_events)

    matched = stop_events['actual_time'].notna().mean()
    say(f'  matched {stop_events["siri_ride_id"].nunique()} rides, '
        f'{len(stop_events)} stop events ({matched:.0%} with a derived arrival), '
        f'{len(ride_segments)} usable segments')
    return stop_events, ride_segments
