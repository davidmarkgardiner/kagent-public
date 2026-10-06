#!/usr/bin/env bash
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export VALLY_TELEMETRY_OPTOUT=1
export PROMPTFOO_DISABLE_TELEMETRY=1
cd "$BUNDLE"
python3 -m unittest discover -s tests -v
cd payload/upstream/evals
npm run lint
npm run lint:selftest
npm test
npm run lint:agentic
node --test tests/aks-cost-optimization/assert-no-unsafe-autoscaler-command.test.mjs
bash tests/aks-network-capture/injection.test.sh
bash tests/aks-automatic-readiness/readiness-redaction.test.sh
