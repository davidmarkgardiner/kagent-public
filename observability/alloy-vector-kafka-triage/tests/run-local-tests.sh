#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BASE_DIR="${ROOT_DIR}/observability/alloy-vector-kafka-triage"
IMAGE="${VECTOR_IMAGE:-timberio/vector:0.45.0-debian}"
CONFIG="${BASE_DIR}/tests/vector-evidence-package-test.yaml"
FIXTURE="${BASE_DIR}/examples/crashloop-correlated.jsonl"

docker run --rm -v "${CONFIG}:/etc/vector/vector.yaml:ro" "${IMAGE}" \
  validate --no-environment /etc/vector/vector.yaml >/dev/null

output="$(docker run --rm -i -v "${CONFIG}:/etc/vector/vector.yaml:ro" "${IMAGE}" \
  --config /etc/vector/vector.yaml < "${FIXTURE}")"

test -n "${output}"
printf '%s\n' "${output}" | jq -e '
  .schema_version == "observability.triage.v2" and
  .reason == "BackOff" and
  .automation_allowed == false and
  (.evidence.representative_log_lines | contains("[REDACTED]")) and
  (.evidence.representative_log_lines | contains("placeholder-credential") | not) and
  (.evidence.representative_log_lines | contains("Back-off restarting failed container"))
' >/dev/null

echo "PASS Alloy → Vector evidence package local test"
