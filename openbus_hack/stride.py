"""A small, friendly client over the Open Bus Stride API.

Full API docs: https://open-bus-stride-api.hasadna.org.il/docs

Everything returns a pandas DataFrame. Every list endpoint is paged for you.
Responses are cached on disk for the session, because during a hackathon you
will run the same query fifty times and the API is a shared community resource
— be kind to it.

    from openbus_hack import stride

    ag = stride.agencies()                      # operator_ref <-> agency_name
    r  = stride.routes(lines=["480"], operators=["אגד"])
    s  = stride.siri_rides(lines=["480"], limit=5000)
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx
import pandas as pd

__all__ = [
    "BASE_URL",
    "get",
    "agencies",
    "operator_refs_for",
    "routes",
    "siri_rides",
    "siri_vehicle_locations",
    "gtfs_rides",
    "gtfs_rides_agg",
    "clear_cache",
    "default_window",
]

BASE_URL = os.environ.get("STRIDE_API_URL", "https://open-bus-stride-api.hasadna.org.il")

# Session cache. Lives under the repo so it's shared between the notebook and
# the dashboard server, and is gitignored.
CACHE_DIR = Path(os.environ.get("STRIDE_CACHE_DIR", Path(__file__).parent.parent / ".cache" / "stride"))

PAGE_SIZE = 1000
TIMEOUT = httpx.Timeout(120.0, connect=30.0)


def default_window(days: int = 7) -> tuple[date, date]:
    """A sane recent date window. Ends yesterday — today's data is still landing."""
    end = date.today() - timedelta(days=1)
    return end - timedelta(days=days - 1), end


def _fmt(v: Any) -> str:
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _csv(values: Iterable[Any] | None) -> str | None:
    """The API takes comma-separated strings for its *_refs / *_name filters."""
    if not values:
        return None
    if isinstance(values, str):
        return values
    return ",".join(_fmt(v) for v in values)


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {k: _fmt(v) for k, v in params.items() if v is not None and v != ""}


def _cache_path(path: str, params: dict[str, Any]) -> Path:
    key = hashlib.sha256(
        json.dumps([path, sorted(params.items())], ensure_ascii=False, default=str).encode()
    ).hexdigest()[:20]
    return CACHE_DIR / f"{path.strip('/').replace('/', '_')}__{key}.json"


def get(path: str, params: dict[str, Any] | None = None, *, use_cache: bool = True) -> Any:
    """One raw GET against the API, with on-disk caching. Returns parsed JSON."""
    params = _clean(params or {})
    cache_file = _cache_path(path, params)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = f"{BASE_URL}/{path.lstrip('/')}"
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if use_cache:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def _paged(path: str, params: dict[str, Any], limit: int | None,
           *, use_cache: bool = True) -> list[dict[str, Any]]:
    """Walk offset/limit pages until the API runs dry or we hit ``limit``."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page_size = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(rows))
        if page_size <= 0:
            break
        batch = get(path, {**params, "limit": page_size, "offset": offset}, use_cache=use_cache)
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += len(batch)
    return rows


def _df(rows: Sequence[dict[str, Any]], date_cols: Sequence[str] = ()) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed", utc=False)
    return df


# ── Endpoints ────────────────────────────────────────────────────────────────


def agencies(date_from: date | str | None = None, date_to: date | str | None = None) -> pd.DataFrame:
    """All operators (agencies) active in the window.

    Columns: ``date``, ``operator_ref``, ``agency_name``.
    """
    if date_from is None or date_to is None:
        d_from, d_to = default_window(2)
        date_from = date_from or d_from
        date_to = date_to or d_to
    rows = _paged("/gtfs_agencies/list", {"date_from": date_from, "date_to": date_to}, limit=5000)
    df = _df(rows)
    if df.empty:
        return df
    return df.drop_duplicates(subset=["operator_ref"]).sort_values("agency_name")


def operator_refs_for(names: Sequence[str], date_from: date | str | None = None,
                      date_to: date | str | None = None) -> list[int]:
    """Map agency names -> operator_ref ints. Matches on exact name, then substring."""
    if not names:
        return []
    ag = agencies(date_from, date_to)
    if ag.empty:
        return []
    refs: list[int] = []
    for n in names:
        exact = ag[ag["agency_name"] == n]
        hit = exact if not exact.empty else ag[ag["agency_name"].str.contains(str(n), na=False)]
        refs.extend(int(x) for x in hit["operator_ref"].tolist())
    return sorted(set(refs))


def routes(lines: Sequence[str] | None = None, operators: Sequence[str] | None = None,
           date_from: date | str | None = None, date_to: date | str | None = None,
           limit: int | None = 5000, **extra: Any) -> pd.DataFrame:
    """GTFS routes matching line short-names and/or operator names.

    Note a "line" is many routes: one per direction and alternative, per day.
    """
    if date_from is None or date_to is None:
        d_from, d_to = default_window()
        date_from = date_from or d_from
        date_to = date_to or d_to
    params = {
        "date_from": date_from,
        "date_to": date_to,
        "route_short_name": _csv(lines),
        "operator_refs": _csv(operator_refs_for(operators, date_from, date_to)) if operators else None,
        **extra,
    }
    return _df(_paged("/gtfs_routes/list", params, limit=limit))


def gtfs_rides(gtfs_route_id: int | None = None, start_time_from: Any = None,
               start_time_to: Any = None, limit: int | None = 5000, **extra: Any) -> pd.DataFrame:
    """Scheduled rides (from GTFS) — what was *supposed* to run."""
    params = {
        "gtfs_route_id": gtfs_route_id,
        "start_time_from": start_time_from,
        "start_time_to": start_time_to,
        **extra,
    }
    return _df(_paged("/gtfs_rides/list", params, limit=limit),
               date_cols=["start_time", "end_time"])


# The only field names /gtfs_rides_agg/group_by accepts. Anything else 500s.
AGG_GROUP_BY_FIELDS = ("gtfs_route_date", "gtfs_route_hour", "operator_ref",
                       "day_of_week", "line_ref")


def gtfs_rides_agg(date_from: date | str, date_to: date | str,
                   group_by: str = "operator_ref,gtfs_route_date") -> pd.DataFrame:
    """Pre-aggregated planned-vs-actual ride counts. Fast — prefer this for
    anything operator/day shaped instead of paging raw rides.

    ``group_by`` is a comma list drawn from :data:`AGG_GROUP_BY_FIELDS`:
    ``gtfs_route_date``, ``gtfs_route_hour``, ``operator_ref``, ``day_of_week``,
    ``line_ref``. Returns ``total_routes`` / ``total_planned_rides`` /
    ``total_actual_rides``.
    """
    fields = [f.strip() for f in group_by.split(",") if f.strip()]
    bad = [f for f in fields if f not in AGG_GROUP_BY_FIELDS]
    if bad:
        raise ValueError(
            f"Invalid group_by field(s) {bad}. Valid: {', '.join(AGG_GROUP_BY_FIELDS)}"
        )
    rows = get("/gtfs_rides_agg/group_by",
               {"date_from": date_from, "date_to": date_to, "group_by": ",".join(fields)})
    return _df(rows if isinstance(rows, list) else [], date_cols=["gtfs_route_date"])


def siri_rides(lines: Sequence[str] | None = None, operators: Sequence[str] | None = None,
               date_from: date | str | None = None, date_to: date | str | None = None,
               limit: int | None = 5000, **extra: Any) -> pd.DataFrame:
    """Actual observed rides (SIRI) joined against their GTFS route.

    This is where real-world behaviour lives: ``duration_minutes``,
    ``journey_ref``, ``vehicle_ref``, ``scheduled_start_time``.
    """
    if date_from is None or date_to is None:
        d_from, d_to = default_window()
        date_from = date_from or d_from
        date_to = date_to or d_to
    params = {
        "gtfs_route__date_from": date_from,
        "gtfs_route__date_to": date_to,
        "gtfs_route__route_short_name": _csv(lines),
        "gtfs_route__operator_refs": (
            _csv(operator_refs_for(operators, date_from, date_to)) if operators else None
        ),
        **extra,
    }
    return _df(_paged("/siri_rides/list", params, limit=limit),
               date_cols=["scheduled_start_time", "first_vehicle_location_recorded_at_time",
                          "last_vehicle_location_recorded_at_time"])


def siri_vehicle_locations(recorded_at_time_from: Any, recorded_at_time_to: Any,
                           lines: Sequence[str] | None = None,
                           operators: Sequence[str] | None = None,
                           limit: int | None = 20000, **extra: Any) -> pd.DataFrame:
    """Raw GPS pings. Big — always pass a tight time window.

    Useful columns: ``lon``, ``lat``, ``bearing``, ``velocity``,
    ``distance_from_journey_start``, ``recorded_at_time``.
    """
    params = {
        "recorded_at_time_from": recorded_at_time_from,
        "recorded_at_time_to": recorded_at_time_to,
        "siri_routes__line_refs": _csv(extra.pop("line_refs", None)),
        "siri_route__operator_refs": (
            _csv(operator_refs_for(operators)) if operators else None
        ),
        **extra,
    }
    if lines:
        params["gtfs_route__route_short_name"] = _csv(lines)
    return _df(_paged("/siri_vehicle_locations/list", params, limit=limit),
               date_cols=["recorded_at_time"])


def clear_cache() -> int:
    """Delete the on-disk response cache. Returns how many files were removed."""
    if not CACHE_DIR.exists():
        return 0
    files = list(CACHE_DIR.glob("*.json"))
    for f in files:
        f.unlink()
    return len(files)
