"""The registry: how your function gets found and shown on the dashboard.

Add a file under ``analyses/``, decorate one function, and you're on the
dashboard. No wiring, no imports to edit anywhere else.

    from openbus_hack import analysis, AnalysisRequest, line_chart

    @analysis(name="rides-per-day", title="Rides per day", author="dana")
    def run(req: AnalysisRequest):
        df = ...
        return line_chart(df, x="date", y="rides")
"""

from __future__ import annotations

import importlib
import pkgutil
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .contract import AnalysisRequest, AnalysisResult, error

__all__ = ["analysis", "AnalysisSpec", "discover", "registry", "get", "run", "OptionSpec"]

# Which pickers the dashboard should show for this analysis.
InputName = Literal["lines", "operators", "dates"]


@dataclass
class OptionSpec:
    """An extra knob rendered as a control on the analysis card."""

    key: str
    label: str
    type: Literal["number", "text", "select", "bool"] = "number"
    default: Any = None
    choices: list[Any] = field(default_factory=list)
    help: str | None = None


@dataclass
class AnalysisSpec:
    name: str
    title: str
    func: Callable[[AnalysisRequest], Any]
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    inputs: list[InputName] = field(default_factory=lambda: ["lines", "operators", "dates"])
    options: list[OptionSpec] = field(default_factory=list)
    # Draft analyses still show up, but flagged — so nobody demos a WIP by accident.
    draft: bool = False
    module: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "inputs": self.inputs,
            "draft": self.draft,
            "module": self.module,
            "options": [
                {
                    "key": o.key, "label": o.label, "type": o.type,
                    "default": o.default, "choices": o.choices, "help": o.help,
                }
                for o in self.options
            ],
        }


_REGISTRY: dict[str, AnalysisSpec] = {}


def analysis(
    *,
    name: str,
    title: str | None = None,
    description: str = "",
    author: str = "",
    tags: list[str] | None = None,
    inputs: list[InputName] | None = None,
    options: list[OptionSpec] | None = None,
    draft: bool = False,
) -> Callable[[Callable[[AnalysisRequest], Any]], Callable[[AnalysisRequest], Any]]:
    """Register a function as a dashboard analysis.

    Args:
        name: URL-safe unique id, e.g. ``"delay-by-hour"``.
        title: Human-facing card title. Defaults to ``name``.
        description: One or two sentences — shown on the card.
        author: Your name, so the presentation can credit you.
        inputs: Which pickers you actually use. Defaults to all three; trim it so
            the UI doesn't offer knobs you ignore.
        options: Extra per-analysis controls (see :class:`OptionSpec`).
        draft: ``True`` while you're still hacking. Still visible, but badged.
    """

    def deco(func: Callable[[AnalysisRequest], Any]) -> Callable[[AnalysisRequest], Any]:
        if name in _REGISTRY and _REGISTRY[name].func is not func:
            raise ValueError(
                f"Duplicate analysis name {name!r} "
                f"(already registered by {_REGISTRY[name].module}). Pick another name."
            )
        _REGISTRY[name] = AnalysisSpec(
            name=name,
            title=title or name,
            func=func,
            description=description.strip(),
            author=author,
            tags=list(tags or []),
            inputs=list(inputs or ["lines", "operators", "dates"]),
            options=list(options or []),
            draft=draft,
            module=getattr(func, "__module__", ""),
        )
        return func

    return deco


def discover(package: str = "analyses") -> list[str]:
    """Import every module under ``analyses/`` so their decorators run.

    A module that fails to import is reported but does not stop the others —
    one person's syntax error must not break the demo.
    """
    problems: list[str] = []
    try:
        pkg = importlib.import_module(package)
    except ImportError as exc:
        return [f"could not import package {package!r}: {exc}"]

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_"):
            continue
        full = f"{package}.{mod.name}"
        try:
            importlib.import_module(full)
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            problems.append(f"{full}: {type(exc).__name__}: {exc}")
    return problems


def registry() -> dict[str, AnalysisSpec]:
    return dict(_REGISTRY)


def get(name: str) -> AnalysisSpec | None:
    return _REGISTRY.get(name)


def _coerce(value: Any) -> AnalysisResult:
    """Let authors return whatever is natural and turn it into an AnalysisResult."""
    from .contract import image as _image
    from .contract import metrics as _metrics
    from .contract import table as _table

    if isinstance(value, AnalysisResult):
        return value
    if value is None:
        return error("Analysis returned None. Did you forget a `return`?")
    # matplotlib Figure
    if hasattr(value, "savefig"):
        return _image(value)
    # pandas DataFrame
    if hasattr(value, "columns") and hasattr(value, "itertuples"):
        return _table(value)
    # pandas Series -> single-series bar chart
    if hasattr(value, "index") and hasattr(value, "to_dict"):
        from .contract import bar_chart as _bar

        return _bar({str(getattr(value, "name", None) or "value"): value.to_dict()})
    if isinstance(value, dict):
        return _metrics(*[{"label": str(k), "value": v} for k, v in value.items()])
    return error(f"Don't know how to render a {type(value).__name__}. "
                 "Return an AnalysisResult (see openbus_hack.contract helpers).")


def run(name: str, request: AnalysisRequest) -> AnalysisResult:
    """Run one analysis, never raising.

    Any exception becomes an ``error`` result so the dashboard renders a broken
    card instead of a 500 page mid-presentation.
    """
    spec = get(name)
    if spec is None:
        return error(f"No analysis named {name!r}.")
    try:
        result = _coerce(spec.func(request))
    except Exception as exc:  # noqa: BLE001 - deliberately broad
        return error(f"{type(exc).__name__}: {exc}", traceback.format_exc())
    if result.title is None:
        result.title = spec.title
    return result.ensure_table()
