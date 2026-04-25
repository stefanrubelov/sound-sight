#!/usr/bin/env bash
# Run Promptfoo test suites for SoundSight prompt evaluation.
#
# Usage:
#   scripts/run_promptfoo.sh              # run all suites
#   scripts/run_promptfoo.sh rule_parser  # run one suite
#
# Suites: rule_parser | event_interpretation | anomaly_narration | onboarding_profiler

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROMPTFOO_DIR="$REPO_ROOT/prompts/promptfoo"
RESULTS_DIR="$PROMPTFOO_DIR/results"

if ! command -v promptfoo &>/dev/null; then
  echo "promptfoo not found. Install with: npm i -g promptfoo" >&2
  exit 1
fi

SUITE="${1:-all}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FAILED=0

run_suite() {
  local name="$1"
  local config="$PROMPTFOO_DIR/${name}.yaml"
  local output="$RESULTS_DIR/${name}_${TIMESTAMP}.json"

  echo ""
  echo "=== Running suite: $name ==="
  if promptfoo eval --config "$config" --output "$output" --no-cache; then
    echo "--- PASSED: $name ---"
  else
    echo "--- FAILED: $name ---" >&2
    FAILED=$((FAILED + 1))
  fi
}

mkdir -p "$RESULTS_DIR"

case "$SUITE" in
  rule_parser | event_interpretation | anomaly_narration | onboarding_profiler)
    run_suite "$SUITE"
    ;;
  all)
    run_suite "rule_parser"
    run_suite "event_interpretation"
    run_suite "anomaly_narration"
    run_suite "onboarding_profiler"
    ;;
  *)
    echo "Unknown suite: $SUITE" >&2
    echo "Valid suites: rule_parser | event_interpretation | anomaly_narration | onboarding_profiler | all" >&2
    exit 1
    ;;
esac

echo ""
if [ "$FAILED" -gt 0 ]; then
  echo "RESULT: $FAILED suite(s) failed. Check output above." >&2
  exit 1
else
  echo "RESULT: All suites passed."
fi
