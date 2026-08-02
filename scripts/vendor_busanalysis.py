"""Vendor the MIT-licensed BusAnalysis material the upstream tickets cite.

lihay7/BusAnalysis is private but MIT-licensed, so redistribution with attribution
is permitted. This copies only what the hasadna tickets need to be verifiable:

  handoff/   — the five defect write-ups, authored explicitly "for the maintainer"
  docs/      — architecture / data / reproduce, needed to re-derive the numbers
  figures/   — the four evidence figures the defect issues reference
  metrics/   — the per-metric summaries backing the M1/M2/M3 tickets
  LICENSE    — the basis on which any of this may be republished

Deliberately NOT copied: src/, tests/, assistant/, plans/, the 11 MB dashboard,
the interactive HTML bundles and the parquet aggregates. None are needed to
verify a ticket, and this is someone else's project.

    uv run python scripts/vendor_busanalysis.py
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

REPO = "lihay7/BusAnalysis"
DEST = Path("source-material/busanalysis")

FILES = [
    *[f"handoff/issues/{n}.md" for n in (
        "F1-stored-linkage", "F6-duplicate-rides", "F7-enrichment-flag",
        "F8-stale-gtfs-release", "F9-coverage-holes")],
    "handoff/README.md",
    "handoff/QUESTIONS_FOR_HASADNA.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA.md",
    "docs/REPRODUCE.md",
    "report/figures/findings/f6_duplication_trend.png",
    "report/figures/findings/f7_enrichment_gap.png",
    "report/figures/findings/f8_divergence_curve.png",
    "report/figures/findings/f9_coverage_holes.png",
    "report/figures/tolerance_curve.png",
    "report/figures/density_bands.png",
    "report/metrics/departure_fidelity/summary.md",
    "report/metrics/enforcement_gap/summary.md",
    "report/metrics/gap_series/summary.md",
    "report/metrics/record_integrity/summary.md",
    "report/metrics/city_profiles/summary.md",
    "LICENSE",
    "README.md",
]


def fetch(path: str) -> bytes | None:
    r = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{path}", "--jq", ".content"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return base64.b64decode(r.stdout)


def main() -> int:
    ok, missing = [], []
    for path in FILES:
        data = fetch(path)
        if data is None:
            missing.append(path)
            print(f"  MISS  {path}")
            continue
        # Flatten report/figures/... and report/metrics/<m>/summary.md into
        # readable destinations; keep handoff/ and docs/ structure as-is.
        if path.startswith("report/figures/"):
            out = DEST / "figures" / Path(path).name
        elif path.startswith("report/metrics/"):
            out = DEST / "metrics" / f"{Path(path).parent.name}.md"
        else:
            out = DEST / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        ok.append(str(out))
        print(f"  ok    {len(data)//1024:>6} KB  {out}")

    print(f"\ncopied {len(ok)}, missing {len(missing)}")
    if missing:
        print("missing:", json.dumps(missing, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
