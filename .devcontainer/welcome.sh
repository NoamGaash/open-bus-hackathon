#!/usr/bin/env bash
# Printed every time you attach to the container. Short on purpose.
cat <<'BANNER'

  ┌─────────────────────────────────────────────────────────────────┐
  │  Open Bus hackathon                                             │
  ├─────────────────────────────────────────────────────────────────┤
  │  ./dev              start everything (dashboard + API + Jupyter)│
  │  ./dev dash         dashboard only        → http://localhost:5173│
  │  ./dev lab          JupyterLab only       → http://localhost:8888│
  │  ./dev new <name>   scaffold a new analysis from the template   │
  │  ./dev list         show all registered analyses                │
  │  ./dev save "msg"   commit + push everything you've done        │
  ├─────────────────────────────────────────────────────────────────┤
  │  Your scratch space:  workspace/<your-name>/                    │
  │  Your analysis goes in:  analyses/<something>.py                │
  │                                                                 │
  │  Commit early, commit often — drafts included. ./dev save       │
  └─────────────────────────────────────────────────────────────────┘

BANNER
