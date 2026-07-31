"""Generate all three charts for a few real bus lines.

    uv run python examples/generate_charts.py
    uv run python examples/generate_charts.py --line jerusalem-15 --days 5
    uv run python examples/generate_charts.py --mode dark --out /tmp/charts

Each line costs a few minutes of API time: the planned timetable is one request per day and GPS
pings run about 0.7 s per sampled ride. Expect roughly 2-4 minutes per line with the defaults.
"""

import argparse
import datetime
import pathlib
import sys
import traceback
from dataclasses import dataclass

import matplotlib

matplotlib.use('Agg')  # writing files, never opening a window

import matplotlib.pyplot as plt  # noqa: E402  - must follow the backend selection

from bus_times import (  # noqa: E402
    aggregate_segments,
    elapsed_profiles,
    load_line_data,
    plot_marey,
    plot_segment_hour_heatmap,
    plot_segment_times,
    quality_summary,
    resolve_line,
    save_figure,
    segment_hour_matrix,
    stop_coverage,
)
from bus_times.config import (  # noqa: E402
    DEFAULT_HOUR_RANGE,
    DEFAULT_LAG_DAYS,
    DEFAULT_MAX_RIDES,
    DEFAULT_MAX_RIDES_PER_HOUR,
    DEFAULT_MIN_SAMPLES,
    OUTPUT_DIR,
)


@dataclass(frozen=True)
class Example:
    """A line described the way a person would, resolved to identifiers at run time.

    ``line_ref`` values are deliberately not hardcoded: they are tied to a GTFS version and change
    when the timetable is republished, so a hardcoded id quietly starts pointing at a different route.
    """

    key: str
    route_short_name: int
    agency_name: str
    name_contains: str
    direction: int
    note: str


EXAMPLES = (
    # Example('jerusalem-15', 15, 'אגד', 'ירושלים', 1,
    #         'Jerusalem line 15 — a long cross-city route through congested corridors'),
    # Example('haifa-15', 15, 'אגד', 'חיפה', 1,
    #         'Haifa line 15 — Haifa to the Krayot, one of two mirrored directions'),
    # Example('rehovot-15', 15, 'אגד', 'רחובות', 1,
    #         'Rehovot line 15 — a shorter suburban route, for contrast'),
    Example('tel-aviv-23', 23, 'דן', 'תל אביב', 1,
            'Tel Aviv line 23 (Dan) — Carmelit terminal to Korazin, Givatayim'),
    Example('tel-aviv-82', 82, 'דן', 'תל אביב', 1,
            'Tel Aviv line 82 (Dan) — Petah Tikva to Carmelit terminal'),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--line', action='append', choices=[e.key for e in EXAMPLES],
                        help='only this line; repeatable (default: all of them)')
    parser.add_argument('--days', type=int, default=4,
                        help='how many working days back to analyse (default: 4)')
    parser.add_argument('--lag-days', type=int, default=DEFAULT_LAG_DAYS,
                        help='end the window this many days before today, since the most recent '
                             f'days are still being ingested (default: {DEFAULT_LAG_DAYS})')
    parser.add_argument('--hours', type=int, nargs=2, metavar=('FROM', 'TO'),
                        default=list(DEFAULT_HOUR_RANGE),
                        help=f'departure hour range (default: {DEFAULT_HOUR_RANGE[0]} '
                             f'{DEFAULT_HOUR_RANGE[1]})')
    parser.add_argument('--max-rides-per-hour', type=int, default=DEFAULT_MAX_RIDES_PER_HOUR)
    parser.add_argument('--max-rides', type=int, default=DEFAULT_MAX_RIDES)
    parser.add_argument('--min-samples', type=int, default=DEFAULT_MIN_SAMPLES)
    parser.add_argument('--mode', choices=('light', 'dark'), default='light')
    parser.add_argument('--orientation', choices=('stops-y', 'stops-x', 'both'), default='both',
                        help="which axis carries the stops. 'stops-y' keeps them on the vertical "
                             "axis (labels read flat); 'stops-x' puts them along the bottom "
                             "(rotated 45°); 'both' writes each chart twice, the stops-x copy "
                             "suffixed '_stopsx' (default: both)")
    parser.add_argument('--out', default=str(OUTPUT_DIR), help='output directory for the PNGs')
    return parser.parse_args(argv)


def date_window(days: int, lag_days: int) -> tuple[datetime.date, datetime.date]:
    """A recent window, ending a few days back because SIRI ingestion lags."""
    date_to = datetime.date.today() - datetime.timedelta(days=lag_days)
    # Over-reach on the calendar span so that `days` *working* days actually land in the window.
    return date_to - datetime.timedelta(days=int(days * 1.6) + 2), date_to


def render_line(example: Example, args: argparse.Namespace, out_dir) -> list[str]:
    """Fetch one line and write its three charts. Returns the paths written."""
    date_from, date_to = date_window(args.days, args.lag_days)
    line = resolve_line(example.route_short_name, date_from, date_to,
                        agency_name=example.agency_name,
                        name_contains=example.name_contains,
                        direction=example.direction)

    stop_events, ride_segments = load_line_data(
        line, date_from, date_to,
        hour_range=tuple(args.hours),
        max_rides_per_hour=args.max_rides_per_hour,
        max_rides=args.max_rides,
    )

    rides = stop_events['siri_ride_id'].nunique()
    days = stop_events['ride_date'].nunique()
    subtitle = (f'{date_from.isoformat()}..{date_to.isoformat()} · '
                f'{rides} rides over {days} days · '
                f'arrival times derived from GPS, ±30s')
    label = f'{example.route_short_name} {example.name_contains}'

    aggregated = aggregate_segments(ride_segments, args.min_samples)
    print(f'  quality: {quality_summary(aggregated)}')
    coverage = stop_coverage(stop_events)

    orientations = {'stops-y': False, 'stops-x': True}
    if args.orientation != 'both':
        orientations = {args.orientation: orientations[args.orientation]}

    written = []
    for orientation, stops_on_x in orientations.items():
        suffix = '_stopsx' if stops_on_x else ''
        charts = {
            'segments': lambda sx=stops_on_x: plot_segment_times(
                aggregated, label, subtitle, mode=args.mode, stops_on_x=sx),
            'marey': lambda sx=stops_on_x: plot_marey(
                *elapsed_profiles(stop_events), label, subtitle,
                mode=args.mode, coverage=coverage, stops_on_x=sx),
            'heatmap': lambda sx=stops_on_x: plot_segment_hour_heatmap(
                segment_hour_matrix(ride_segments), label, subtitle,
                min_samples=args.min_samples, mode=args.mode, stops_on_x=sx),
        }
        for name, build in charts.items():
            try:
                fig = build()
            except ValueError as exc:
                # One chart having too little data is not a reason to lose the others.
                print(f'  skipped {name} ({orientation}): {exc}')
                continue
            path = out_dir / f'{example.key}_{name}{suffix}.png'
            save_figure(fig, path)
            plt.close(fig)
            written.append(str(path))
            print(f'  wrote {path}')
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = [e for e in EXAMPLES if not args.line or e.key in args.line]
    written, failed = [], []
    for example in selected:
        print(f'\n=== {example.key}: {example.note}')
        try:
            written += render_line(example, args, out_dir)
        except Exception as exc:  # noqa: BLE001 - a dead line must not kill the whole run
            failed.append((example.key, exc))
            print(f'  FAILED: {exc}')
            traceback.print_exc(limit=1, file=sys.stdout)

    print(f'\n{len(written)} chart(s) written to {out_dir}')
    for key, exc in failed:
        print(f'  {key} failed: {type(exc).__name__}: {exc}')
    return 0 if written else 1


if __name__ == '__main__':
    raise SystemExit(main())
