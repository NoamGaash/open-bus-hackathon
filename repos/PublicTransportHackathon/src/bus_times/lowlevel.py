"""Thin wrappers over the ``stride`` client.

These exist for one reason. ``stride.iterate(path, params, limit=N)`` looks like it fetches up to N
rows, but the ``limit`` kwarg is applied *client-side* while iterating the response — it never
reaches the server. Without ``limit`` in ``params`` the API applies its own default of 100 rows, so
the call silently truncates and no error is raised. Every request here passes the server-side limit
explicitly.
"""

from collections.abc import Iterator
from typing import Any

import stride

from .config import MAX_SERVER_LIMIT


def _with_limit(params: dict[str, Any] | None, limit: int) -> dict[str, Any]:
    if limit > MAX_SERVER_LIMIT:
        raise ValueError(f'limit={limit} exceeds the API maximum of {MAX_SERVER_LIMIT}')
    return {**(params or {}), 'limit': limit}


def get_rows(path: str, params: dict[str, Any] | None = None,
             limit: int = MAX_SERVER_LIMIT) -> list[dict[str, Any]]:
    """GET a list endpoint, returning at most ``limit`` rows."""
    return stride.get(path, _with_limit(params, limit))


def iter_rows(path: str, params: dict[str, Any] | None = None,
              limit: int = MAX_SERVER_LIMIT) -> Iterator[dict[str, Any]]:
    """Stream a list endpoint, returning at most ``limit`` rows.

    Preferred over :func:`get_rows` for large responses: it parses incrementally instead of holding
    the whole JSON body in memory.
    """
    return stride.iterate(path, _with_limit(params, limit), limit=limit)
