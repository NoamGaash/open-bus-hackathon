"""Generic on-disk memoization for slow external calls (REST API paging, SQL, ...).

Some analyses fetch through clients slower than ``stride.py`` (which has its own
disk cache under ``.cache/``) — e.g. the ``bus_times`` package pages a public
REST API and a single fetch can take over a minute. This persists results
across process restarts, keyed by whatever arguments identify the call, so a
rehearsal run or a dev-server reload doesn't repay that cost every time.

    from openbus_hack.diskcache import cached

    def _load(line, date_from, date_to):
        return cached("bus_arrival", (line, date_from, date_to),
                      lambda: _fetch_from_network(line, date_from, date_to))
"""

from __future__ import annotations

import hashlib
import os
import pickle
import threading
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path(os.environ.get("OPENBUS_CACHE_DIR", Path(__file__).parent.parent / "cache"))

# One lock per (namespace, key) so concurrent callers with the same key share
# the first caller's work instead of each repeating it — same problem as
# functools.lru_cache not deduplicating concurrent calls, solved on disk too.
_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def _path_for(namespace: str, key: tuple) -> Path:
    digest = hashlib.sha1(repr(key).encode("utf-8")).hexdigest()
    directory = CACHE_DIR / namespace
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{digest}.pkl"


def cached(namespace: str, key: tuple, compute: Callable[[], Any]) -> Any:
    """Return the cached result for ``(namespace, key)``, computing it once if needed.

    ``key`` must be a tuple of hashable, ``repr``-stable values (strings,
    numbers, dates). Results are pickled, so anything ``compute()`` returns
    must itself be picklable (DataFrames and plain dataclasses are fine).
    """
    path = _path_for(namespace, key)
    with _registry_lock:
        lock = _locks.setdefault(str(path), threading.Lock())
    with lock:
        if path.exists():
            with path.open("rb") as f:
                return pickle.load(f)
        result = compute()
        tmp = path.with_suffix(".tmp")
        with tmp.open("wb") as f:
            pickle.dump(result, f)
        tmp.replace(path)  # atomic within the same filesystem
        return result


def clear(namespace: str | None = None) -> int:
    """Delete cached entries (all of them, or just one namespace). Returns the count removed."""
    root = CACHE_DIR / namespace if namespace else CACHE_DIR
    if not root.exists():
        return 0
    files = list(root.rglob("*.pkl"))
    for f in files:
        f.unlink()
    return len(files)
