"""Tests for the pure helpers in the fetch layer. The network calls themselves are not tested here."""

import datetime

import pandas as pd

from bus_times.config import ISRAEL_TZ
from bus_times.fetch import sample_rides, weekdays_between


def test_weekdays_between_skips_the_israeli_weekend():
    # 2026-07-26 is a Sunday, so this range is Sun..Sat.
    days = weekdays_between(datetime.date(2026, 7, 26), datetime.date(2026, 8, 1))

    names = [d.strftime('%a') for d in days]
    assert names == ['Sun', 'Mon', 'Tue', 'Wed', 'Thu']


def test_weekdays_between_is_empty_for_a_weekend_only_range():
    friday, saturday = datetime.date(2026, 7, 31), datetime.date(2026, 8, 1)

    assert weekdays_between(friday, saturday) == []


def _rides(hours, day='2026-07-26', per_hour=6):
    """`per_hour` rides in each of the given local hours."""
    rows = []
    ride_id = 1
    for hour in hours:
        for minute in range(0, per_hour * 10, 10):
            local = pd.Timestamp(f'{day} {hour:02d}:{minute:02d}', tz=ISRAEL_TZ)
            rows.append({'siri_ride_id': ride_id, 'scheduled_start_time': local.tz_convert('UTC')})
            ride_id += 1
    return pd.DataFrame(rows)


def test_sample_rides_caps_each_hour():
    rides = _rides([7, 8, 9], per_hour=6)

    sampled = sample_rides(rides, max_per_hour=2, max_total=100)

    local_hours = sampled['scheduled_start_time'].dt.tz_convert(ISRAEL_TZ).dt.hour
    assert len(sampled) == 6
    assert sorted(local_hours.value_counts().tolist()) == [2, 2, 2]


def test_sample_rides_keeps_every_hour_represented_when_trimming_to_the_total():
    """The total cap must not lop off whole hours — the heatmap needs the hour axis populated."""
    rides = _rides(list(range(6, 22)), per_hour=6)

    sampled = sample_rides(rides, max_per_hour=4, max_total=24)

    assert len(sampled) == 24
    hours = sampled['scheduled_start_time'].dt.tz_convert(ISRAEL_TZ).dt.hour.nunique()
    assert hours >= 12  # spread over most of the day rather than the first few hours


def test_sample_rides_is_deterministic_and_sorted():
    rides = _rides([7, 8], per_hour=6)

    first = sample_rides(rides, max_per_hour=3, max_total=100)
    again = sample_rides(rides, max_per_hour=3, max_total=100)

    assert first['siri_ride_id'].tolist() == again['siri_ride_id'].tolist()
    assert first['scheduled_start_time'].is_monotonic_increasing


def test_sample_rides_passes_through_a_short_list():
    rides = _rides([7], per_hour=2)

    sampled = sample_rides(rides, max_per_hour=4, max_total=100)

    assert len(sampled) == 2


def test_sample_rides_handles_an_empty_frame():
    empty = pd.DataFrame(columns=['siri_ride_id', 'scheduled_start_time'])

    assert sample_rides(empty).empty
