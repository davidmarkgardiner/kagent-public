#!/usr/bin/env bash
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$BUNDLE"
mkdir -p .work/eval-skills
cp -R payload/upstream/skills/. .work/eval-skills/
cp -R payload/local-skills/. .work/eval-skills/
export PROMPTFOO_DISABLE_TELEMETRY=1
export SKILLS_BASE="$BUNDLE/.work/eval-skills"
CLI="$BUNDLE/payload/upstream/evals/node_modules/.bin/promptfoo"
case "${1:-quality}" in
  quality|routing)
    "$CLI" eval -c "evaluation/$1.yaml" -o ".work/$1-results.json" --no-cache --no-share
    python3 evaluation/check-results.py ".work/$1-results.json"
    ;;
  baseline)
    "$CLI" eval -c evaluation/baseline.yaml -o .work/baseline-results.json --no-cache --no-share
    ;;
  *) echo 'Usage: evaluate.sh quality|routing|baseline' >&2; exit 2 ;;
esac
