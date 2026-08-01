"""File the hackathon issues into hasadna/open-bus-map-search.

Reads the manifest written by gen_issues.py and creates one issue per entry, in
priority order, attached to the milestone. Idempotent: an issue whose exact
title already exists in the repo is skipped, so a partial run can be resumed.

    uv run python scripts/file_issues.py to_review <milestone-number> [--dry-run]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = "hasadna/open-bus-map-search"
PROVENANCE = ["ai-generated", "needs-validation"]

# 1,2 first (live wrong answers), then the cheap doc/DX wins, then the rest.
PRIORITY = [1, 2, 7, 8, 9, 3, 4, 5, 6, 10, 11, 12] + list(range(13, 30)) + list(range(30, 35))


def sh(*args: str) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}… failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def existing_titles() -> set[str]:
    raw = sh("gh", "issue", "list", "-R", REPO, "--state", "all",
             "--limit", "400", "--json", "title")
    return {i["title"] for i in json.loads(raw)}


def main() -> int:
    out = Path(sys.argv[1])
    milestone = sys.argv[2]
    dry = "--dry-run" in sys.argv

    manifest = {m["n"]: m for m in json.loads((out / "manifest.json").read_text())}
    have = existing_titles()
    created, skipped = [], []

    for n in PRIORITY:
        it = manifest[n]
        if it["title"] in have:
            skipped.append(n)
            print(f"  skip  {n:02d}  already exists — {it['title'][:64]}")
            continue

        labels = ",".join(it["labels"] + PROVENANCE)
        cmd = ["gh", "issue", "create", "-R", REPO,
               "--title", it["title"],
               "--body-file", it["file"],
               "--label", labels,
               "--milestone", milestone]
        if dry:
            print(f"  DRY   {n:02d}  [{labels}]  {it['title'][:64]}")
            continue

        url = sh(*cmd)
        created.append((n, url))
        print(f"  ok    {n:02d}  {url}")

    print(f"\ncreated {len(created)}, skipped {len(skipped)}")
    if created:
        (out / "created.json").write_text(
            json.dumps([{"n": n, "url": u} for n, u in created], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
