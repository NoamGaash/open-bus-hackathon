"""Finding a specific bus line.

An everyday line number is not a unique identifier: Egged runs a line "15" in Jerusalem, Haifa,
Eilat, Rehovot and several other cities, and each direction of each of those is a separate route.
Everything downstream keys off ``line_ref`` + ``operator_ref``, which do identify one physical
route in one direction, so this module exists to get from "line 15 in Jerusalem" to those numbers.
"""

import datetime
from dataclasses import dataclass

import pandas as pd

from .lowlevel import get_rows

_ROUTE_COLUMNS = ['line_ref', 'operator_ref', 'route_short_name', 'route_direction',
                  'route_alternative', 'agency_name', 'route_long_name']


@dataclass(frozen=True)
class LineSpec:
    """One physical route in one direction — the handle every fetch takes."""

    line_ref: int
    operator_ref: int
    label: str

    def __str__(self) -> str:
        return f'{self.label} (line_ref={self.line_ref})'


def find_lines(
    route_short_name: str | int,
    date_from: datetime.date,
    date_to: datetime.date,
    agency_name: str | None = None,
    name_contains: str | None = None,
) -> pd.DataFrame:
    """All GTFS routes matching a line number, one row per route and direction.

    ``name_contains`` filters on ``route_long_name``, which names the terminal stops and is the
    practical way to pick out a city (e.g. ``'ירושלים'``).
    """
    params: dict[str, object] = {
        'route_short_name': route_short_name,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
    }
    if agency_name:
        params['agency_name'] = agency_name
    if name_contains:
        params['route_long_name_contains'] = name_contains

    routes = get_rows('/gtfs_routes/list', params, limit=1000)
    if not routes:
        return pd.DataFrame(columns=_ROUTE_COLUMNS)

    df = pd.DataFrame(routes)
    # A route is repeated once per calendar date it is active; one row per route is what callers want.
    return (df[_ROUTE_COLUMNS]
            .drop_duplicates(subset=['line_ref', 'operator_ref'])
            .sort_values(['route_direction', 'line_ref'])
            .reset_index(drop=True))


def resolve_line(
    route_short_name: str | int,
    date_from: datetime.date,
    date_to: datetime.date,
    agency_name: str | None = None,
    name_contains: str | None = None,
    direction: str | int | None = None,
) -> LineSpec:
    """Pick exactly one line, raising if the description is ambiguous or matches nothing.

    Ambiguity is an error rather than a silent "first match" because picking the wrong direction
    produces charts that look perfectly plausible and are entirely wrong.
    """
    df = find_lines(route_short_name, date_from, date_to, agency_name, name_contains)
    if direction is not None:
        df = df[df['route_direction'].astype(str) == str(direction)]

    described = f'route_short_name={route_short_name!r}'
    if agency_name:
        described += f' agency_name={agency_name!r}'
    if name_contains:
        described += f' name_contains={name_contains!r}'
    if direction is not None:
        described += f' direction={direction!r}'

    if df.empty:
        raise ValueError(f'No route matches {described} between {date_from} and {date_to}')
    if len(df) > 1:
        options = '\n'.join(
            f"  line_ref={r.line_ref} direction={r.route_direction} {r.route_long_name}"
            for r in df.itertuples())
        raise ValueError(
            f'{len(df)} routes match {described}; narrow it with name_contains/direction:\n{options}')

    row = df.iloc[0]
    return LineSpec(
        line_ref=int(row['line_ref']),
        operator_ref=int(row['operator_ref']),
        label=f"{row['route_short_name']} {row['route_long_name']}",
    )
