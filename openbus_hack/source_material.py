"""Fetches source files (scripts/notebooks) from teammates' private GitHub repos,
for the dashboard's "Source material" reviewer appendix.

Both source repos this currently points at are **private** — raw.githubusercontent.com
404s on them for an unauthenticated request, so the browser can't fetch them directly
(and embedding a personal token in frontend JS would leak it to every viewer). This
shells out to the `gh` CLI instead, which is authenticated in this devcontainer, and
serves the parsed result to the frontend over our own API. That means this feature only
works where `gh auth login` has been done — which is true here, but would need a real
GitHub App / server-side token for a deployment outside this devcontainer.
"""

from __future__ import annotations

import base64
import json
import subprocess
from urllib.parse import quote

from .diskcache import cached


def _api_path(repo: str, branch: str, path: str) -> str:
    encoded = "/".join(quote(seg, safe="") for seg in path.split("/"))
    # ?ref= directly in the path, not `-f ref=`: `gh api` switches to POST as
    # soon as any -f/-F flag is given (unless -X is also passed), which 404s
    # against this GET-only endpoint.
    return f"repos/{repo}/contents/{encoded}?ref={quote(branch, safe='')}"


def _parse_ipynb(text: str) -> list[dict]:
    """Extract code/markdown cell text, dropping outputs (the embedded-image blobs
    are most of a notebook's size and irrelevant to comparing source code)."""
    try:
        nb = json.loads(text)
    except json.JSONDecodeError as exc:
        return [{"kind": "text", "source": f"(couldn't parse notebook JSON: {exc})"}]
    cells = []
    for c in nb.get("cells", []):
        kind = "code" if c.get("cell_type") == "code" else (
            "markdown" if c.get("cell_type") == "markdown" else "text"
        )
        source = c.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        if source.strip():
            cells.append({"kind": kind, "source": source})
    return cells


def fetch_source_file(repo: str, branch: str, path: str) -> dict:
    """Returns ``{"cells": [...]}`` or ``{"error": "..."}``. Disk-cached — this is a
    subprocess call per file, not something to repeat on every page load."""

    def compute():
        try:
            proc = subprocess.run(
                ["gh", "api", _api_path(repo, branch, path), "--jq", ".content"],
                capture_output=True, text=True, timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        if proc.returncode != 0:
            return {"error": (proc.stderr or "gh api failed").strip()[:300]}
        try:
            content = base64.b64decode(proc.stdout).decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 — surface as a card-level error, not a 500
            return {"error": f"{type(exc).__name__}: {exc}"}
        cells = _parse_ipynb(content) if path.endswith(".ipynb") else [{"kind": "code", "source": content}]
        return {"cells": cells}

    return cached("source_material", (repo, branch, path), compute)
