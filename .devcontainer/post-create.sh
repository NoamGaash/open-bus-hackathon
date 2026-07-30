#!/usr/bin/env bash
# Runs ONCE when the container is created. Keep it idempotent anyway.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "▸ Installing Python dependencies (uv)…"
# --frozen if a lockfile exists, otherwise resolve and write one.
if [ -f uv.lock ]; then
  uv sync --frozen
else
  uv sync
fi

echo "▸ Installing frontend dependencies (npm)…"
if [ -d frontend ]; then
  cd frontend
  if [ -f package-lock.json ]; then
    npm ci --no-audit --no-fund
  else
    npm install --no-audit --no-fund
  fi
  cd ..
fi

echo "▸ Wiring git for notebook-friendly diffs…"
# nbdime makes .ipynb diffs and merges readable, which is what makes
# "commit your notebooks" actually workable.
if command -v nbdime >/dev/null 2>&1; then
  nbdime config-git --enable --system 2>/dev/null || nbdime config-git --enable || true
fi
# Long hackathon days + many small commits: make pulls linear by default.
git config --local pull.rebase true
git config --local push.autoSetupRemote true

echo "▸ Registering the Jupyter kernel…"
python -m ipykernel install --user --name openbus --display-name "Open Bus (py3.12)" 2>/dev/null || true

echo "▸ Creating your personal workspace folder…"
# Each member gets a scratch area, named after their git user or OS user.
WHO="$(git config --get user.name 2>/dev/null || echo "${USER:-me}")"
SLUG="$(echo "$WHO" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')"
[ -z "$SLUG" ] && SLUG="me"
if [ ! -d "workspace/$SLUG" ]; then
  cp -r workspace/_template "workspace/$SLUG" 2>/dev/null || mkdir -p "workspace/$SLUG"
  echo "  → workspace/$SLUG"
fi

echo ""
echo "✅ Setup complete. Run:  ./dev"
