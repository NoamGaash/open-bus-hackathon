"""FastAPI bridge: exposes every registered analysis to the React dashboard.

    ./dev api        # then http://localhost:8000/docs

Endpoints
    GET  /api/health
    GET  /api/analyses                  every registered analysis + its metadata
    POST /api/analyses/{name}/run       run one, returns an AnalysisResult
    GET  /api/agencies                  operator list, for the picker
    GET  /api/lines?q=                  line short-name suggestions, for the picker
    GET  /api/source-material?repo=&branch=&path=   one teammate's source file, parsed
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import source_material as source_material_module
from . import stride
from .contract import AnalysisRequest, AnalysisResult
from .registry import discover, registry, run

app = FastAPI(
    title="Open Bus Hackathon — Analyses API",
    description="Runs each team member's analysis and returns render-ready results.",
    version="0.1.0",
)

# The Vite dev server runs on a different origin; in Codespaces it's a different
# host entirely. This is a local hackathon tool, so allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import problems found at startup, surfaced to the dashboard so a teammate's
# broken file is visible instead of silently missing.
_IMPORT_PROBLEMS: list[str] = []


@app.on_event("startup")
def _load_analyses() -> None:
    global _IMPORT_PROBLEMS
    _IMPORT_PROBLEMS = discover()
    for p in _IMPORT_PROBLEMS:
        print(f"⚠ analysis failed to import — {p}")
    print(f"✔ {len(registry())} analyses registered")


# async def, deliberately: FastAPI runs sync `def` endpoints in a worker
# threadpool (40 slots by default). A dashboard full of slow analyses can occupy
# every slot, and a sync health check would then queue behind them — reporting
# the server as down exactly when you most want to know it's up. This one runs
# on the event loop and does no blocking work, so it always answers.
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "analyses": len(registry()),
        "import_problems": _IMPORT_PROBLEMS,
        "stride_api": stride.BASE_URL,
    }


@app.get("/api/analyses")
def list_analyses() -> dict[str, Any]:
    """Everything the dashboard needs to draw the cards and their controls."""
    specs = sorted(registry().values(), key=lambda s: (s.draft, s.author.lower(), s.name))
    return {
        "analyses": [s.to_json() for s in specs],
        "import_problems": _IMPORT_PROBLEMS,
    }


class RunBody(BaseModel):
    """Request body for running an analysis. All fields optional."""

    lines: list[str] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    options: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/analyses/{name}/run", response_model=AnalysisResult)
def run_analysis(name: str, body: RunBody | None = None) -> AnalysisResult:
    if name not in registry():
        raise HTTPException(status_code=404, detail=f"No analysis named {name!r}")
    body = body or RunBody()
    payload = body.model_dump(exclude_none=True)
    # AnalysisRequest supplies sensible date defaults when omitted.
    request = AnalysisRequest(**payload)
    # run() never raises — failures come back as kind="error".
    return run(name, request)


@app.get("/api/agencies")
def agencies() -> dict[str, Any]:
    """Operator names for the picker dropdown."""
    try:
        df = stride.agencies()
        if df.empty:
            return {"agencies": []}
        return {
            "agencies": [
                {"operator_ref": int(r.operator_ref), "name": str(r.agency_name)}
                for r in df.itertuples(index=False)
            ]
        }
    except Exception as exc:  # noqa: BLE001 — the picker must not break the page
        return {"agencies": [], "error": f"{type(exc).__name__}: {exc}"}


@app.get("/api/lines")
def lines(q: str = "", limit: int = 40) -> dict[str, Any]:
    """Line short-name suggestions, optionally filtered by prefix ``q``."""
    try:
        d_from, d_to = stride.default_window(2)
        df = stride.routes(lines=[q] if q else None, date_from=d_from, date_to=d_to, limit=2000)
        if df.empty or "route_short_name" not in df.columns:
            return {"lines": []}
        names = sorted(
            df["route_short_name"].dropna().astype(str).unique(),
            key=lambda s: (len(s), s),
        )
        return {"lines": names[:limit]}
    except Exception as exc:  # noqa: BLE001
        return {"lines": [], "error": f"{type(exc).__name__}: {exc}"}


@app.get("/api/source-material")
def source_material(repo: str, branch: str, path: str) -> dict[str, Any]:
    """One teammate's source file (script or notebook), for the dashboard's
    "Source material" reviewer appendix. See openbus_hack/source_material.py —
    both repos this currently serves are private, so this proxies through the
    `gh` CLI's auth rather than have the browser hit GitHub directly."""
    return source_material_module.fetch_source_file(repo, branch, path)


def main() -> None:
    """Entry point for ``openbus-serve``."""
    import uvicorn

    uvicorn.run(
        "openbus_hack.server:app",
        host="0.0.0.0",
        port=int(os.environ.get("API_PORT", 8000)),
        reload=bool(os.environ.get("RELOAD", "1") == "1"),
    )


if __name__ == "__main__":
    main()
