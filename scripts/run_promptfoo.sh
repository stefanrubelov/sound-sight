#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/prompts/promptfoo"

if ! command -v promptfoo &>/dev/null; then
  echo "promptfoo not found. Install with: npm i -g promptfoo"
  exit 1
fi

exec promptfoo eval --config promptfooconfig.yaml "$@"
