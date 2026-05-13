#!/usr/bin/env bash
# Smoke test the kagent namespace-agent skill without requiring a live cluster.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$(mktemp -d "$SKILL_DIR/.smoke-test.XXXXXX")"
trap 'rm -rf "$OUT_DIR"' EXIT

NAMESPACE="payments-dev"
DESCRIPTION="Payment API diagnostics and rollout triage"

"$SKILL_DIR/scripts/create-agent.sh" \
  --namespace "$NAMESPACE" \
  --description "$DESCRIPTION" \
  --context smoke-test \
  --kagent-ns kagent \
  --model-config default-model-config \
  --output-dir "$OUT_DIR" >"$OUT_DIR/create-agent.log"

for file in \
  "$OUT_DIR/${NAMESPACE}-agent.yaml" \
  "$OUT_DIR/${NAMESPACE}-sensor.yaml" \
  "$OUT_DIR/${NAMESPACE}-test-error.yaml"; do
  test -s "$file"
  if grep -q '{{' "$file"; then
    echo "unreplaced template placeholder in $file" >&2
    exit 1
  fi
done

python3 - "$OUT_DIR" "$NAMESPACE" "$DESCRIPTION" <<'PY'
import pathlib
import sys

import yaml

out_dir = pathlib.Path(sys.argv[1])
namespace = sys.argv[2]
description = sys.argv[3]


def load_all(name):
    with (out_dir / name).open(encoding="utf-8") as handle:
        return list(yaml.safe_load_all(handle))


agent = load_all(f"{namespace}-agent.yaml")[0]
sensor = load_all(f"{namespace}-sensor.yaml")[0]
test_docs = load_all(f"{namespace}-test-error.yaml")

assert agent["apiVersion"] == "kagent.dev/v1alpha2"
assert agent["kind"] == "Agent"
assert agent["metadata"]["name"] == f"{namespace}-agent"
assert agent["metadata"]["namespace"] == "kagent"
assert agent["spec"]["declarative"]["modelConfig"] == "default-model-config"
assert description in agent["spec"]["description"]
assert description in agent["spec"]["declarative"]["systemMessage"]

skills = agent["spec"]["declarative"]["a2aConfig"]["skills"]
assert skills and skills[0]["id"] == f"{namespace}-diagnostics"

tools = agent["spec"]["declarative"]["tools"][0]["mcpServer"]["toolNames"]
for required_tool in (
    "k8s_get_resources",
    "k8s_describe_resource",
    "k8s_get_pod_logs",
    "k8s_get_events",
):
    assert required_tool in tools

assert sensor["apiVersion"] == "argoproj.io/v1alpha1"
assert sensor["kind"] == "Sensor"
assert sensor["metadata"]["name"] == f"kagent-triage-{namespace}"
assert sensor["spec"]["dependencies"][0]["filters"]["data"][0]["value"] == [namespace]

kinds = [doc["kind"] for doc in test_docs]
assert kinds == ["Deployment", "Pod", "Pod"], kinds
assert {doc["metadata"]["namespace"] for doc in test_docs} == {namespace}

print("kagent namespace-agent smoke test passed")
PY
