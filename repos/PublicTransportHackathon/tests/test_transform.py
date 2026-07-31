"""Unit tests for the pure analysis core.

Synthetic geometry throughout: stops and GPS pings are laid out along a straight west-to-east line
at 32°N, 1000 m apart, with the vehicle covering each 1000 m in 60 s. That makes the expected
arrival times exact and hand-checkable.
"""

import math

import numpy as np
import pandas as pd
import pytest

from bus_times.transform import (
    CONFIDENCE_COARSE_TIMING,
    CONFIDENCE_FEW_SAMPLES,
    CONFIDENCE_IMPLAUSIBLE,
    SEGMENT_COLUMNS,
    aggregate_segments,
    build_ride_segments,
    build_stop_events,
    dominant_stop_pattern,
    elapsed_profiles,
    estimate_arrival_seconds,
    match_rides_to_planned,
    quality_summary,
    segment_hour_matrix,
    stop_coverage,
)

LAT = 32.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT))
DEG_PER_KM = 1000.0 / M_PER_DEG_LON  # longitude delta covering 1000 m


def _straight_pings(count, start_lon=35.0, seconds_per_km=60.0, metres_per_step=1000.0):
    """A vehicle travelling due east, covering ``metres_per_step`` between consecutive pings."""
    step_deg = metres_per_step / M_PER_DEG_LON
    lon = start_lon + step_deg * np.arange(count)
    lat = np.full(count, LAT)
    t = seconds_per_km * (metres_per_step / 1000.0) * np.arange(count)
    return lat, lon, t


# --------------------------------------------------------------------------- arrival estimation

def test_stop_on_a_ping_position_gets_that_pings_time():
    plat, plon, pt = _straight_pings(5)
    estimate = estimate_arrival_seconds(
        np.array([LAT, LAT]), np.array([plon[0], plon[2]]),
        plat, plon, pt, origin_departure=False)

    assert estimate.seconds == pytest.approx([0.0, 120.0], abs=1.0)
    assert estimate.distance_m == pytest.approx([0.0, 0.0], abs=1.0)
    # Resolution is the ping spacing the arrival was interpolated within.
    assert estimate.resolution_s == pytest.approx([60.0, 60.0], abs=1.0)


def test_stop_midway_between_pings_is_time_interpolated():
    # 200 m between pings, so a stop between two of them is well inside the match threshold and the
    # result has to come from interpolation rather than from snapping to a ping.
    plat, plon, pt = _straight_pings(5, metres_per_step=200.0)
    midway = (plon[1] + plon[2]) / 2

    estimate = estimate_arrival_seconds(
        np.array([LAT]), np.array([midway]), plat, plon, pt, origin_departure=False)

    # Halfway along the leg between the 12 s and 24 s pings.
    assert estimate.seconds[0] == pytest.approx(18.0, abs=0.5)
    assert estimate.distance_m[0] == pytest.approx(100.0, abs=1.0)
    assert estimate.resolution_s[0] == pytest.approx(12.0, abs=0.5)


def test_stop_beyond_max_distance_is_not_matched():
    plat, plon, pt = _straight_pings(5)
    far_lat = LAT + 5000.0 / 111_320.0  # 5 km north of the route

    estimate = estimate_arrival_seconds(
        np.array([far_lat]), np.array([plon[2]]), plat, plon, pt,
        max_distance_m=300.0, origin_departure=False)

    assert np.isnan(estimate.seconds[0])
    # The distance is still reported — it is the evidence for calling the stop unmatched.
    assert estimate.distance_m[0] == pytest.approx(5000.0, rel=0.01)
    assert np.isnan(estimate.resolution_s[0])


def test_coincident_stops_never_produce_going_back_in_time():
    """Junctions carry several stop records metres apart; arrival times must stay ordered."""
    plat, plon, pt = _straight_pings(6)
    jitter = 20.0 / M_PER_DEG_LON
    stop_lon = np.array([plon[1], plon[3] - jitter, plon[3] + jitter, plon[3], plon[4]])

    arrivals = estimate_arrival_seconds(
        np.array([LAT] * 5), stop_lon, plat, plon, pt, origin_departure=False).seconds

    assert np.all(np.diff(arrivals) >= 0), arrivals


def test_origin_departure_uses_the_last_ping_before_the_bus_leaves():
    """Buses idle at the terminal emitting pings from one spot; closest approach lands mid-idle."""
    idle_lat = np.full(3, LAT)
    idle_lon = np.full(3, 35.0)
    idle_t = np.array([0.0, 60.0, 120.0])
    move_lat, move_lon, move_t = _straight_pings(4, start_lon=35.0 + DEG_PER_KM)
    plat = np.concatenate([idle_lat, move_lat])
    plon = np.concatenate([idle_lon, move_lon])
    pt = np.concatenate([idle_t, move_t + 180.0])

    stop_lat, stop_lon = np.array([LAT]), np.array([35.0])

    departure = estimate_arrival_seconds(stop_lat, stop_lon, plat, plon, pt,
                                         origin_departure=True).seconds
    closest = estimate_arrival_seconds(stop_lat, stop_lon, plat, plon, pt,
                                       origin_departure=False).seconds

    assert departure[0] == pytest.approx(120.0, abs=1.0)  # last ping still at the terminal
    assert closest[0] == pytest.approx(0.0, abs=1.0)      # first ping, mid-idle


def test_origin_departure_falls_back_when_the_trail_starts_away_from_the_terminal():
    """A vehicle picked up mid-route has a first timestamp that says nothing about its departure."""
    # Pings begin 3 km east of the origin stop and pass close to it only later, on the way back.
    plat, plon, pt = _straight_pings(4, start_lon=35.0 + 3 * DEG_PER_KM)
    back_lat, back_lon, back_t = _straight_pings(3, start_lon=35.0)
    plat = np.concatenate([plat, back_lat])
    plon = np.concatenate([plon, back_lon])
    pt = np.concatenate([pt, back_t + 300.0])

    arrivals = estimate_arrival_seconds(
        np.array([LAT]), np.array([35.0]), plat, plon, pt, origin_departure=True).seconds

    # The closest approach happens at 300 s, not at the first ping's 0 s.
    assert arrivals[0] == pytest.approx(300.0, abs=1.0)


def test_no_pings_yields_no_arrivals():
    empty = np.array([])
    estimate = estimate_arrival_seconds(np.array([LAT]), np.array([35.0]), empty, empty, empty)

    assert np.isnan(estimate.seconds[0])
    assert np.isnan(estimate.distance_m[0])
    assert np.isnan(estimate.resolution_s[0])


def test_resolution_reports_the_ping_gap_the_arrival_sits_in():
    """A wide gap between pings means the arrival time is barely constrained; say so."""
    plat = np.array([LAT, LAT, LAT])
    plon = np.array([35.0, 35.0 + DEG_PER_KM * 0.1, 35.0 + DEG_PER_KM * 0.2])
    sparse_t = np.array([0.0, 600.0, 1200.0])  # ten minutes between pings

    estimate = estimate_arrival_seconds(np.array([LAT]), np.array([plon[1]]),
                                        plat, plon, sparse_t, origin_departure=False)

    assert estimate.resolution_s[0] == pytest.approx(600.0, abs=1.0)


# --------------------------------------------------------------------------- ride/plan matching

def _planned_frame(*, gtfs_ride_id, start, names, gaps_s):
    """Planned stops for one GTFS ride: ``gaps_s`` are seconds after ``start`` per stop."""
    return pd.DataFrame({
        'gtfs_ride_id': gtfs_ride_id,
        'gtfs_line_start_time': pd.Timestamp(start, tz='UTC'),
        'name': names,
        'city': 'ירושלים',
        'lat': LAT,
        'lon': [35.0 + DEG_PER_KM * i for i in range(len(names))],
        'planned_arrival_time': [pd.Timestamp(start, tz='UTC') + pd.Timedelta(seconds=g)
                                 for g in gaps_s],
    })


def test_ride_ids_keep_the_api_string_type():
    """The API returns gtfs_ride_id as a string; coercing it breaks every lookup downstream."""
    planned = _planned_frame(gtfs_ride_id='151817932', start='2026-07-26 04:00',
                             names=['א', 'ב'], gaps_s=[0, 60])
    rides = pd.DataFrame({'siri_ride_id': [1],
                          'scheduled_start_time': pd.to_datetime(['2026-07-26 04:00'], utc=True)})

    matched = match_rides_to_planned(rides, planned)

    assert matched[1] == '151817932'
    # And the whole pipeline still resolves the plan for that ride.
    events = build_stop_events(rides, planned, _pings_frame(1, 2, start='2026-07-26 04:00'))
    assert list(events['stop_name']) == ['א', 'ב']


def test_dominant_stop_pattern_keeps_the_majority_route_shape():
    """One line_ref often serves several stop patterns; mixing them interleaves two routes."""
    main = pd.concat([
        _planned_frame(gtfs_ride_id=str(i), start=f'2026-07-20 0{i}:00',
                       names=['א', 'ב', 'ג'], gaps_s=[0, 60, 120])
        for i in (1, 2, 3)
    ])
    variant = _planned_frame(gtfs_ride_id='9', start='2026-07-20 09:00',
                             names=['א', 'שונה', 'ג'], gaps_s=[0, 60, 120])

    selection = dominant_stop_pattern(pd.concat([main, variant]))

    assert selection.n_patterns == 2
    assert selection.kept_rides == 3
    assert selection.total_rides == 4
    assert selection.n_stops == 3
    assert set(selection.planned['gtfs_ride_id']) == {'1', '2', '3'}
    assert 'שונה' not in set(selection.planned['name'])


def test_dominant_stop_pattern_is_a_no_op_for_a_single_pattern():
    planned = pd.concat([
        _planned_frame(gtfs_ride_id=str(i), start=f'2026-07-20 0{i}:00',
                       names=['א', 'ב'], gaps_s=[0, 60])
        for i in (1, 2)
    ])

    selection = dominant_stop_pattern(planned)

    assert selection.n_patterns == 1
    assert len(selection.planned) == len(planned)


def test_dominant_pattern_stops_one_route_pair_appearing_twice():
    """The visible symptom: the same stop pair charted at two positions with wildly different n."""
    main = pd.concat([
        _planned_frame(gtfs_ride_id=str(i), start=f'2026-07-20 0{i}:00',
                       names=['א', 'ב', 'ג'], gaps_s=[0, 60, 120])
        for i in (1, 2, 3)
    ])
    # A detour variant that reaches ב one position later, so ב->ג lands at a different index.
    variant = _planned_frame(gtfs_ride_id='9', start='2026-07-20 09:00',
                             names=['א', 'עוקף', 'ב', 'ג'], gaps_s=[0, 30, 60, 120])
    everything = pd.concat([main, variant])

    kept = dominant_stop_pattern(everything).planned
    positions = (kept.sort_values(['gtfs_ride_id', 'planned_arrival_time'])
                 .groupby('gtfs_ride_id')['name'].apply(tuple).unique())

    assert len(positions) == 1  # one route shape, so each pair has one segment_index


def test_rides_match_the_nearest_planned_departure():
    planned = pd.concat([
        _planned_frame(gtfs_ride_id=10, start='2026-07-20 05:00', names=['א', 'ב'], gaps_s=[0, 60]),
        _planned_frame(gtfs_ride_id=11, start='2026-07-20 06:00', names=['א', 'ב'], gaps_s=[0, 60]),
    ])
    rides = pd.DataFrame({
        'siri_ride_id': [1, 2, 3],
        'scheduled_start_time': pd.to_datetime(
            ['2026-07-20 05:02', '2026-07-20 05:58', '2026-07-20 12:00'], utc=True),
    })

    matched = match_rides_to_planned(rides, planned, tolerance_minutes=20)

    assert matched[1] == 10
    assert matched[2] == 11
    assert 3 not in matched  # more than 20 minutes from any planned departure


# --------------------------------------------------------------------------- stop events

def _pings_frame(ride_id, count, start='2026-07-20 05:00', seconds_per_km=60.0, start_lon=35.0):
    lat, lon, t = _straight_pings(count, start_lon=start_lon, seconds_per_km=seconds_per_km)
    return pd.DataFrame({
        'siri_ride_id': ride_id,
        'recorded_at_time': pd.Timestamp(start, tz='UTC') + pd.to_timedelta(t, unit='s'),
        'lat': lat,
        'lon': lon,
    })


def test_build_stop_events_pairs_planned_stops_with_derived_arrivals():
    planned = _planned_frame(gtfs_ride_id=10, start='2026-07-20 05:00',
                             names=['א', 'ב', 'ג'], gaps_s=[0, 60, 120])
    rides = pd.DataFrame({'siri_ride_id': [1],
                          'scheduled_start_time': pd.to_datetime(['2026-07-20 05:00'], utc=True)})
    # Vehicle runs slow: 90 s per km instead of the planned 60 s.
    pings = _pings_frame(1, 3, seconds_per_km=90.0)

    events = build_stop_events(rides, planned, pings)

    assert list(events['stop_name']) == ['א', 'ב', 'ג']
    assert list(events['stop_sequence']) == [0, 1, 2]
    # 05:00 UTC is 08:00 in Israel; the hour is local because rush hour is a local-clock idea.
    assert events['departure_hour'].unique().tolist() == [8]
    actual_gaps = events['actual_time'].diff().dt.total_seconds().dropna()
    assert actual_gaps.tolist() == pytest.approx([90.0, 90.0], abs=2.0)


def test_build_stop_events_skips_rides_with_no_planned_match():
    planned = _planned_frame(gtfs_ride_id=10, start='2026-07-20 05:00',
                             names=['א', 'ב'], gaps_s=[0, 60])
    rides = pd.DataFrame({'siri_ride_id': [1, 2],
                          'scheduled_start_time': pd.to_datetime(
                              ['2026-07-20 05:00', '2026-07-20 22:00'], utc=True)})
    pings = pd.concat([_pings_frame(1, 2), _pings_frame(2, 2, start='2026-07-20 22:00')])

    events = build_stop_events(rides, planned, pings)

    assert set(events['siri_ride_id']) == {1}


# --------------------------------------------------------------------------- segments

def _events(ride_id, names, planned_s, actual_s, hour=8, base='2026-07-20 05:00',
            match_distance_m=30.0, resolution_s=30.0):
    base_ts = pd.Timestamp(base, tz='UTC')
    return pd.DataFrame({
        'siri_ride_id': ride_id,
        'scheduled_start_time': base_ts,
        'departure_hour': hour,
        'stop_sequence': range(len(names)),
        'stop_name': names,
        'planned_time': [base_ts + pd.Timedelta(seconds=s) if s is not None else pd.NaT
                         for s in planned_s],
        'actual_time': [base_ts + pd.Timedelta(seconds=s) if s is not None else pd.NaT
                        for s in actual_s],
        'match_distance_m': match_distance_m,
        'resolution_s': resolution_s,
    })


def test_build_ride_segments_pairs_consecutive_stops():
    events = _events(1, ['א', 'ב', 'ג'], [0, 60, 180], [0, 90, 300])

    segments = build_ride_segments(events)

    assert list(segments['from_name']) == ['א', 'ב']
    assert list(segments['to_name']) == ['ב', 'ג']
    assert list(segments['planned_duration_s']) == [60, 120]
    assert list(segments['actual_duration_s']) == [90, 210]
    assert list(segments['segment_index']) == [0, 1]


def test_build_ride_segments_drops_only_the_segments_touching_a_missing_stop():
    events = _events(1, ['א', 'ב', 'ג', 'ד'], [0, 60, 120, 180], [0, None, 200, 260])

    segments = build_ride_segments(events)

    # א->ב and ב->ג are unusable; ג->ד survives.
    assert list(zip(segments['from_name'], segments['to_name'])) == [('ג', 'ד')]


def test_build_ride_segments_drops_non_positive_durations():
    """Coincident junction stops can resolve to the same instant; a zero-length segment is noise."""
    events = _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 90, 90])

    segments = build_ride_segments(events)

    assert list(segments['from_name']) == ['א']


def test_build_ride_segments_drops_segments_the_timetable_allots_no_time():
    """Junction stops share a planned arrival time; that pair is not a measurable segment."""
    events = _events(1, ['א', 'ב', 'ג'], [0, 60, 60], [0, 90, 150])

    segments = build_ride_segments(events)

    assert list(segments['from_name']) == ['א']


def test_segments_keep_their_place_in_the_route_across_rides():
    """Segment identity must be the stop pair, not the row position within a ride."""
    full = _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 70, 150])
    gappy = _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, None, 160])

    segments = build_ride_segments(pd.concat([full, gappy]))
    bc = segments[segments['from_name'] == 'ב']

    assert list(bc['segment_index']) == [1]


# --------------------------------------------------------------------------- aggregation

def test_aggregate_segments_reports_mean_spread_and_counts():
    rides = pd.concat([
        _events(1, ['א', 'ב'], [0, 60], [0, 60]),
        _events(2, ['א', 'ב'], [0, 60], [0, 90]),
        _events(3, ['א', 'ב'], [0, 60], [0, 120]),
    ])
    segments = build_ride_segments(rides)

    agg = aggregate_segments(segments, min_samples=3)

    row = agg.iloc[0]
    assert row['sample_count'] == 3
    assert row['actual_mean_s'] == pytest.approx(90.0)
    assert row['actual_std_s'] == pytest.approx(pd.Series([60.0, 90.0, 120.0]).std())
    assert row['actual_median_s'] == pytest.approx(90.0)
    assert row['actual_p25_s'] == pytest.approx(75.0)
    assert row['actual_p75_s'] == pytest.approx(105.0)
    assert row['planned_duration_s'] == pytest.approx(60.0)


def test_median_resists_a_single_broken_arrival_estimate():
    """A GPS trail starting late makes one ride wildly long; the charted statistic must survive it."""
    rides = pd.concat([
        _events(1, ['א', 'ב'], [0, 60], [0, 60]),
        _events(2, ['א', 'ב'], [0, 60], [0, 66]),
        _events(3, ['א', 'ב'], [0, 60], [0, 72]),
        _events(4, ['א', 'ב'], [0, 60], [0, 2400]),  # 40 minutes: an artifact, not traffic
    ])

    row = aggregate_segments(build_ride_segments(rides), min_samples=3).iloc[0]

    assert row['actual_median_s'] == pytest.approx(69.0)
    assert row['actual_mean_s'] > 600  # the mean is wrecked by the outlier


def test_under_sampled_segments_are_flagged_not_hidden():
    """A segment silently absent from a chart reads as a segment that does not exist."""
    rides = pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 130]),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 70, None]),
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, 80, None]),
    ])
    segments = build_ride_segments(rides)

    agg = aggregate_segments(segments, min_samples=3)

    assert list(agg['from_name']) == ['א', 'ב']  # both kept
    by_name = agg.set_index('from_name')
    assert by_name.loc['א', 'is_reliable']
    assert not by_name.loc['ב', 'is_reliable']
    assert by_name.loc['ב', 'confidence'] == CONFIDENCE_FEW_SAMPLES


def test_aggregate_segments_can_still_filter_on_request():
    rides = pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 130]),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 70, None]),
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, 80, None]),
    ])

    agg = aggregate_segments(build_ride_segments(rides), min_samples=3, drop_insufficient=True)

    assert list(agg['from_name']) == ['א']


def test_coverage_records_how_many_rides_backed_each_segment():
    rides = pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 130]),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 70, 140]),
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, 80, None]),
        _events(4, ['א', 'ב', 'ג'], [0, 60, 120], [0, 90, None]),
    ])

    agg = aggregate_segments(build_ride_segments(rides), min_samples=2).set_index('from_name')

    assert agg.loc['א', 'coverage'] == pytest.approx(1.0)
    assert agg.loc['ב', 'coverage'] == pytest.approx(0.5)


def test_a_coarse_gps_gap_makes_a_segment_unreliable():
    """Plenty of rides, but each arrival known only to five minutes — the number is not usable."""
    rides = pd.concat([
        _events(i, ['א', 'ב'], [0, 60], [0, 60 + i], resolution_s=300.0)
        for i in range(1, 6)
    ])

    row = aggregate_segments(build_ride_segments(rides), min_samples=3).iloc[0]

    assert row['sample_count'] == 5
    assert not row['is_reliable']
    assert row['confidence'] == CONFIDENCE_COARSE_TIMING


def test_an_implausible_ratio_outranks_other_caveats():
    rides = pd.concat([
        _events(i, ['א', 'ב'], [0, 60], [0, 3000]) for i in range(1, 6)
    ])

    row = aggregate_segments(build_ride_segments(rides), min_samples=3).iloc[0]

    assert row['confidence'] == CONFIDENCE_IMPLAUSIBLE


def test_aggregate_segments_raises_when_there_is_nothing_at_all():
    empty = pd.DataFrame(columns=SEGMENT_COLUMNS)

    with pytest.raises(ValueError, match='No usable segments'):
        aggregate_segments(empty, min_samples=3)


def test_quality_summary_names_the_problems():
    rides = pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 130]),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 70, None]),
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, 80, None]),
    ])

    summary = quality_summary(aggregate_segments(build_ride_segments(rides), min_samples=3))

    assert '1/2 segments reliable' in summary
    assert CONFIDENCE_FEW_SAMPLES in summary


# --------------------------------------------------------------------------- heatmap matrix

def test_segment_hour_matrix_buckets_by_departure_hour():
    morning = pd.concat([_events(i, ['א', 'ב'], [0, 60], [0, 120], hour=8) for i in (1, 2)])
    midday = pd.concat([_events(i, ['א', 'ב'], [0, 60], [0, 60], hour=13) for i in (3, 4)])
    segments = build_ride_segments(pd.concat([morning, midday]))

    matrix = segment_hour_matrix(segments)

    assert list(matrix.ratio.columns) == [8, 13]
    assert matrix.ratio.iloc[0][8] == pytest.approx(2.0)  # twice the planned duration
    assert matrix.ratio.iloc[0][13] == pytest.approx(1.0)  # exactly on schedule


def test_segment_hour_matrix_reports_counts_so_thin_cells_can_be_marked():
    """A one-ride cell keeps its value and is distinguishable from a cell with no data at all."""
    segments = build_ride_segments(pd.concat([
        _events(1, ['א', 'ב'], [0, 60], [0, 120], hour=8),
        _events(2, ['א', 'ב'], [0, 60], [0, 120], hour=8),
        _events(3, ['א', 'ב'], [0, 60], [0, 60], hour=13),
    ]))

    matrix = segment_hour_matrix(segments)

    assert matrix.ratio.iloc[0][8] == pytest.approx(2.0)
    assert matrix.count.iloc[0][8] == 2
    # The single-ride cell still carries its value, flagged by a count below any threshold.
    assert matrix.ratio.iloc[0][13] == pytest.approx(1.0)
    assert matrix.count.iloc[0][13] == 1


def test_segment_hour_matrix_counts_are_zero_where_no_ride_ran():
    segments = build_ride_segments(pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 120, 200], hour=8),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 120, 200], hour=8),
        # Only the first segment is measurable at 13:00.
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, None], hour=13),
        _events(4, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, None], hour=13),
    ]))

    matrix = segment_hour_matrix(segments)

    bc = matrix.count.xs('ב', level='from_name')
    assert bc[13].iloc[0] == 0  # no data, as opposed to a thin average
    assert bc[8].iloc[0] == 2


def test_stop_coverage_reports_the_match_rate_per_stop():
    events = pd.concat([
        _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 120]),
        _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, None, 120]),
        _events(3, ['א', 'ב', 'ג'], [0, 60, 120], [0, None, 120]),
        _events(4, ['א', 'ב', 'ג'], [0, 60, 120], [0, None, 120]),
    ])

    coverage = stop_coverage(events).set_index('stop_name')

    assert coverage.loc['א', 'coverage'] == pytest.approx(1.0)
    assert coverage.loc['ב', 'coverage'] == pytest.approx(0.25)
    assert coverage.loc['ג', 'coverage'] == pytest.approx(1.0)


def test_stop_coverage_gives_one_row_per_route_position():
    """Route alternatives name different stops at one position; coverage must stay indexable."""
    common = _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 120])
    variant = _events(2, ['א', 'ב', 'שונה'], [0, 60, 120], [0, 60, None])

    coverage = stop_coverage(pd.concat([common, variant]))

    assert list(coverage['stop_sequence']) == [0, 1, 2]
    assert coverage['stop_sequence'].is_unique
    # Position 2 was resolved on one of the two rides, regardless of which stop sat there.
    assert coverage.iloc[2]['coverage'] == pytest.approx(0.5)


# --------------------------------------------------------------------------- marey profiles

def test_elapsed_profiles_measure_from_each_rides_own_first_stop():
    early = _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 90, 200], base='2026-07-20 05:00')
    late = _events(2, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 120], base='2026-07-20 09:00')

    actual, planned = elapsed_profiles(pd.concat([early, late]))

    first_ride = actual[actual['siri_ride_id'] == 1].sort_values('stop_sequence')
    assert list(first_ride['elapsed_min']) == pytest.approx([0.0, 1.5, 200 / 60])
    second_ride = actual[actual['siri_ride_id'] == 2].sort_values('stop_sequence')
    assert list(second_ride['elapsed_min']) == pytest.approx([0.0, 1.0, 2.0])
    # The planned reference is a single profile shared by all rides.
    assert list(planned['elapsed_min']) == pytest.approx([0.0, 1.0, 2.0])
    assert list(planned['stop_name']) == ['א', 'ב', 'ג']


def test_elapsed_profiles_gives_one_planned_row_per_stop_position():
    """Route alternatives can name different stops at one position; the reference must not duplicate."""
    common = _events(1, ['א', 'ב', 'ג'], [0, 60, 120], [0, 60, 120])
    variant = _events(2, ['א', 'ב', 'שונה'], [0, 60, 120], [0, 60, 120])

    _, planned = elapsed_profiles(pd.concat([common, variant]))

    assert list(planned['stop_sequence']) == [0, 1, 2]
    assert planned['stop_sequence'].is_unique
