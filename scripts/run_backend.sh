#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "Creating venv..."
  python3.14 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev]"
else
  source .venv/bin/activate
fi

exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
