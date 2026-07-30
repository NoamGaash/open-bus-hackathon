# workspace/ — your personal scratch space

Each person gets a folder here. **Everything in it is meant to be committed.**

```
workspace/
  noam/
    notebooks/     draft notebooks, exploration, dead ends
    data/          intermediate results (CSV/Parquet you want to keep)
      raw/         ← the ONE gitignored spot: huge raw dumps
    out/           charts and images you exported
    NOTES.md       what you tried, what worked, what didn't
```

`./dev` creates your folder automatically on first run (named after your git
`user.name`). To make one by hand:

```bash
cp -r workspace/_template workspace/your-name
```

## Why commit drafts?

Because at 2am someone will ask "didn't you already compute the delay
distribution?" and the answer should be a git path, not a shrug. A messy
committed notebook beats a clean uncommitted one.

Save your work with:

```bash
./dev save "explored delay distribution for line 480"
```

That stages everything, commits, and pushes.

## What goes where

| Thing | Where |
|---|---|
| Exploration, trial and error | `workspace/<you>/notebooks/` |
| An intermediate CSV you'll reuse | `workspace/<you>/data/` |
| A 2GB raw API dump | `workspace/<you>/data/raw/` (gitignored) |
| **The finished function for the demo** | `analyses/<name>.py` |

Only `analyses/*.py` shows up on the dashboard. `workspace/` is yours to be
messy in.
