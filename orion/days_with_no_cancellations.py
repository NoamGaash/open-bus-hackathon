# motivation - for a given bus line we want to provide a quality score based on how many days all buses operated as expected.
# i.e. a day with at least 1 cancellation is counter as 0, a day with full operations counted as 1
# we measure ratio of good days relative to to total days
# we average over past 15 days.

# method 1 : days_wo_cancellation_score()
# input: line args
# output: score

# method 2: script that runs on all buses for one bus company and provide score per bus line, and provide a visualization
# method 3: script that compares average score per bus company, and provide a visualization

""""Days without cancellations" quality score — methods 1 and 2.

Data source is ``/rides_execution/list`` (Option A in days_with_no_cancellations.md):
one row per planned ride, where ``actual_start_time is None`` means the ride did
not run. Everything below exists to work around the five live caveats documented
there — see the ``# caveat N`` comments.

    days_wo_cancellation_score("480")      # method 1: one line          -> 0.53
    daily_report("480")                    #   its per-day breakdown     -> DataFrame
    operator_line_scores("סופרבוס")        # method 2: every line of one company
    plot_operator_scores(scores, 35)       #   ...as a bar chart

    $ python days_with_no_cancellations.py --line 480
    $ python days_with_no_cancellations.py --operator "בית שמש אקספרס"

Method 2 costs one paged request per line_ref: ~80 for a small company (minutes),
~1,240 for אגד. Responses are disk-cached by stride, so a rerun is instant.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openbus_hack import stride  # noqa: E402

ISRAEL = ZoneInfo("Asia/Jerusalem")  # caveat 5: never a fixed UTC+3 — winter is +2
DEFAULT_DAYS = 15


# ── window ───────────────────────────────────────────────────────────────────


def score_window(days: int = DEFAULT_DAYS, end: date | str | None = None) -> tuple[date, date]:
    """The ``days``-long service-date window ending at ``end`` (default: yesterday).

    Today is excluded by default — its actuals are still landing, so a live day
    looks like a wall of cancellations.
    """
    if end is None:
        end = datetime.now(ISRAEL).date() - timedelta(days=1)
    elif isinstance(end, str):
        end = date.fromisoformat(end)
    return end - timedelta(days=days - 1), end


def _service_date(iso: str) -> date:
    """UTC timestamp string -> the Israel service date it belongs to."""
    return datetime.fromisoformat(iso).astimezone(ISRAEL).date()


# ── fetching ─────────────────────────────────────────────────────────────────


def line_variants(line: str, date_from: date, date_to: date,
                  operators: Sequence[str] | None = None) -> set[tuple[int, int]]:
    """Resolve a line short-name to its ``(line_ref, operator_ref)`` pairs.

    caveat 1: a "line" is many refs — one per direction × route alternative, and
    the set changes over time (480 was 2 refs in Nov 2025, 8 in Jul 2026). Always
    resolve for the window being scored; never cache one mapping and reuse it.
    """
    routes = stride.routes(lines=[line], operators=operators,
                           date_from=date_from, date_to=date_to)
    if routes.empty:
        return set()
    return {
        (int(r.line_ref), int(r.operator_ref))
        for r in routes.itertuples()
        if pd.notna(r.line_ref) and pd.notna(r.operator_ref)
    }


def rides_execution(line_ref: int, operator_ref: int,
                    date_from: date, date_to: date) -> Iterator[dict[str, Any]]:
    """Page through ``/rides_execution/list``. All four filters are required."""
    offset = 0
    while True:
        batch = stride.get("/rides_execution/list", {
            "line_ref": line_ref,
            "operator_ref": operator_ref,
            "date_from": date_from,
            "date_to": date_to,
            "limit": stride.PAGE_SIZE,
            "offset": offset,
        })
        if not isinstance(batch, list) or not batch:
            return
        yield from batch
        if len(batch) < stride.PAGE_SIZE:
            return
        offset += len(batch)


# ── the score ────────────────────────────────────────────────────────────────


def daily_report(line: str, days: int = DEFAULT_DAYS, end: date | str | None = None,
                 operators: Sequence[str] | None = None,
                 variants: Iterable[tuple[int, int]] | None = None) -> pd.DataFrame:
    """Per-day planned/cancelled counts for one line.

    Columns: ``date``, ``planned``, ``cancelled``, ``good`` (bool).
    Days on which the line had no planned rides at all are simply absent — they
    are neither good nor bad, and must not land in the denominator.
    """
    date_from, date_to = score_window(days, end)
    if variants is None:
        variants = line_variants(line, date_from, date_to, operators)

    # caveat 3: one departure can surface under several gtfs_ride_ids. Key on the
    # planned departure itself, and let *any* observed actual mark it as operated,
    # so a duplicated row with a null actual can't invent a cancellation.
    operated: dict[tuple[int, int, str], bool] = {}
    for line_ref, operator_ref in variants:
        for row in rides_execution(line_ref, operator_ref, date_from, date_to):
            planned = row.get("planned_start_time")
            if not planned:
                continue  # caveat 2: unplanned ride (~3-6%) — the opposite of a cancellation
            key = (line_ref, operator_ref, planned)
            operated[key] = operated.get(key, False) or bool(row.get("actual_start_time"))

    per_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])  # planned, cancelled
    for (_, _, planned), ran in operated.items():
        day = _service_date(planned)
        if not (date_from <= day <= date_to):
            continue  # the API's service-date filter is fuzzy at the window edges
        per_day[day][0] += 1
        per_day[day][1] += 0 if ran else 1

    rows = [
        {"date": day, "planned": planned, "cancelled": cancelled, "good": cancelled == 0}
        for day, (planned, cancelled) in sorted(per_day.items())
    ]
    return pd.DataFrame(rows, columns=["date", "planned", "cancelled", "good"])


def days_wo_cancellation_score(line: str, days: int = DEFAULT_DAYS,
                               end: date | str | None = None,
                               operators: Sequence[str] | None = None) -> float | None:
    """Fraction of the last ``days`` service days on which *no* ride was cancelled.

    Returns ``None`` when the line had no planned rides in the window at all —
    that is "unknown", not "perfect", and callers must not average it in as 1.0.
    """
    report = daily_report(line, days, end, operators)
    if report.empty:
        return None
    return float(report["good"].mean())


# ── method 2: score every line of one operator ───────────────────────────────


def operator_ref_of(operator: str | int) -> int:
    """Accept an operator_ref (``5``, ``"5"``) or an agency name (``"אגד"``)."""
    if isinstance(operator, int) or str(operator).isdigit():
        return int(operator)
    refs = stride.operator_refs_for([str(operator)])
    if not refs:
        raise ValueError(f"no operator matched {operator!r} — see stride.agencies()")
    return refs[0]


def operator_name(operator: str | int, date_from: date | None = None,
                  date_to: date | None = None) -> str:
    """Agency name for display. Passes non-numeric input straight through."""
    if not (isinstance(operator, int) or str(operator).isdigit()):
        return str(operator)
    ag = stride.agencies(date_from, date_to)
    hit = ag[ag["operator_ref"] == int(operator)] if not ag.empty else ag
    return str(hit.iloc[0]["agency_name"]) if len(hit) else f"operator {operator}"


def operator_variants(operator: str | int, date_from: date,
                      date_to: date) -> dict[str, set[tuple[int, int]]]:
    """``route_short_name -> {(line_ref, operator_ref)}`` for one operator.

    One request set for the whole company, instead of a /gtfs_routes lookup per
    line. This is where method 2's real cost lives: אגד is ~1,240 line_refs over
    15 days, i.e. ~1,240 ride pulls downstream.
    """
    ref = operator_ref_of(operator)
    routes = stride.routes(date_from=date_from, date_to=date_to,
                           operator_refs=str(ref), limit=None)
    by_line: dict[str, set[tuple[int, int]]] = defaultdict(set)
    if routes.empty:
        return by_line
    for r in routes.itertuples():
        if pd.notna(r.line_ref) and pd.notna(r.route_short_name):
            by_line[str(r.route_short_name)].add((int(r.line_ref), int(r.operator_ref)))
    return by_line


def operator_line_scores(operator: str | int, days: int = DEFAULT_DAYS,
                         end: date | str | None = None, max_lines: int | None = None,
                         progress: bool = True) -> pd.DataFrame:
    """Method 2 — one row per line of one bus company, worst score first.

    Columns: ``line``, ``score``, ``good_days``, ``days_scored``, ``planned``,
    ``cancelled``, ``variants``. Lines with no planned rides in the window are
    dropped (score would be undefined, not zero).
    """
    date_from, date_to = score_window(days, end)
    by_line = operator_variants(operator, date_from, date_to)
    lines = sorted(by_line, key=lambda s: (len(s), s))
    if max_lines:
        lines = lines[:max_lines]

    rows = []
    for i, line in enumerate(lines, 1):
        if progress:
            print(f"  [{i}/{len(lines)}] line {line} "
                  f"({len(by_line[line])} variants)", file=sys.stderr, flush=True)
        report = daily_report(line, days, end, variants=by_line[line])
        if report.empty:
            continue
        planned, cancelled = int(report["planned"].sum()), int(report["cancelled"].sum())
        rows.append({
            "line": line,
            "score": float(report["good"].mean()),
            "good_days": int(report["good"].sum()),
            "days_scored": len(report),
            "planned": planned,
            "cancelled": cancelled,
            # Not one actual in 15 days is an ingestion gap, not a company that
            # cancelled every bus it ever scheduled. Score is meaningless here.
            "no_actuals": cancelled == planned,
            "variants": len(by_line[line]),
        })

    df = pd.DataFrame(rows, columns=["line", "score", "good_days", "days_scored",
                                     "planned", "cancelled", "no_actuals", "variants"])
    return df.sort_values(["no_actuals", "score", "cancelled"],
                          ascending=[True, True, False], ignore_index=True)


# ── visualization ────────────────────────────────────────────────────────────


NO_DATA_GREY = "#898781"  # theme.py _CHROME["light"]["muted"] — never a series color


_RUN = re.compile(r"[0-9A-Za-z]+|[^0-9A-Za-z]+")


def _rtl(text: str) -> str:
    """Since modern matplotlib (>= 3.11) has native bidi and HarfBuzz support,
    we do not reorder or reverse the text, as doing so would garble the characters."""
    return text


def _score_color(score: float) -> str:
    from openbus_hack.theme import STATUS
    if score >= 0.9:
        return STATUS["good"]
    if score >= 0.7:
        return STATUS["warning"]
    if score >= 0.4:
        return STATUS["serious"]
    return STATUS["critical"]


def plot_operator_scores(scores: pd.DataFrame, operator: str | int,
                         days: int = DEFAULT_DAYS, out: str | Path | None = None) -> Path:
    """Horizontal bar chart, worst line at the top. Returns the written path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from openbus_hack.theme import use_openbus_style
    use_openbus_style()

    df = scores.iloc[::-1]  # barh draws bottom-up; we want worst on top
    blind = df["no_actuals"] if "no_actuals" in df else pd.Series(False, index=df.index)
    height = max(3.0, 0.28 * len(df) + 1.6)
    fig, ax = plt.subplots(figsize=(9, height))

    labels = [_rtl(s) for s in df["line"].astype(str)]  # line names like "4א" are RTL too
    bars = ax.barh(labels, df["score"].where(~blind, 1.0), height=0.72,
                   color=[NO_DATA_GREY if b else _score_color(s)
                          for s, b in zip(df["score"], blind)])
    for bar, b in zip(bars, blind):
        if b:  # a bar you must not read as a score
            bar.set_hatch("///")
            bar.set_alpha(0.35)
    for line, score, cancelled, b in zip(labels, df["score"], df["cancelled"], blind):
        label = "no actuals reported" if b else (
            f"{score:.2f}" + (f"  ({cancelled} cx)" if cancelled else ""))
        ax.text((1.0 if b else score) + 0.015, line, label, va="center", fontsize=8.5,
                color=NO_DATA_GREY if b else None)

    ax.set_xlim(0, 1.18)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("days with zero cancellations / days scored")
    ax.set_ylabel("line")
    ax.set_title(f"{_rtl(operator_name(operator))} — "
                 f"days-without-cancellations score, last {days} days")
    ax.margins(y=0.01)
    fig.tight_layout()

    # ref first so the name sorts and stays unambiguous, then the agency name so
    # the file is identifiable without looking the ref up.
    slug = re.sub(r"[^\w()'-]+", "_", operator_name(operator)).strip("_")
    out = (Path(out) if out else Path(__file__).parent / "out"
           / f"operator_{operator_ref_of(operator)}_{slug}_scores.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--line", help="method 1: score one line (e.g. 480)")
    p.add_argument("--operator", help="method 2: score every line of one company "
                                      "(agency name or operator_ref)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--end", help="last service date to score (default: yesterday)")
    p.add_argument("--max-lines", type=int, help="method 2: stop after N lines")
    p.add_argument("--out", help="method 2: chart path")
    args = p.parse_args(argv)

    if args.operator:
        scores = operator_line_scores(args.operator, args.days, args.end, args.max_lines)
        if scores.empty:
            print(f"operator {args.operator}: no lines with planned rides in the window")
            return 0
        print(scores.to_string(index=False))
        scored = scores[~scores["no_actuals"]]
        blind = int(scores["no_actuals"].sum())
        if scored.empty:
            print(f"\n⚠ all {len(scores)} lines report zero actuals for the whole window — "
                  "this is an ingestion gap, not a 0.00 score. Nothing scoreable here.")
        else:
            print(f"\n{len(scored)} lines scored, mean score {scored['score'].mean():.2f}, "
                  f"{int((scored['score'] == 1.0).sum())} perfect, "
                  f"{int((scored['score'] == 0.0).sum())} never clean"
                  + (f"; {blind} excluded (zero actuals all window)" if blind else ""))
        print(f"chart: {plot_operator_scores(scores, args.operator, args.days, args.out)}")
        return 0

    line = args.line or "480"
    report = daily_report(line, args.days, args.end)
    if report.empty:
        print(f"line {line}: no planned rides in the window")
        return 0
    print(report.to_string(index=False))
    good, scored = int(report["good"].sum()), len(report)
    print(f"\nline {line}: score = {good / scored:.2f}  ({good}/{scored} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
