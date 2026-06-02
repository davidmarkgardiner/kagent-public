#!/usr/bin/env bash
set -euo pipefail

WORKFLOW="${1:-}"
NAMESPACE="${ARGO_NAMESPACE:-argo}"

if [[ -z "$WORKFLOW" ]]; then
  echo "usage: $0 <workflow-name>" >&2
  exit 2
fi

yq eval '.. | select(has("toolNames")) | .toolNames[]' a2a/smart-triage-fanout-demo/agents.yaml \
  | grep -Eiq '(apply|delete|exec|patch|admin|drop)' \
  && { echo "FAIL: mutating tool present" >&2; exit 1; } \
  || true

pod="$(kubectl get pods -n "$NAMESPACE" -l "workflows.argoproj.io/workflow=$WORKFLOW" -o name \
  | grep call-specialist | while read -r candidate; do
      if kubectl logs -n "$NAMESPACE" "$candidate" -c main 2>/dev/null | grep -q 'A2A phase: policy'; then
        echo "$candidate"
        break
      fi
    done)"

test -n "$pod"
kubectl logs -n "$NAMESPACE" "$pod" -c main | tee /tmp/smart-triage-policy-proof.txt
grep -Fq "SPECIALIST_POLICY: completed" /tmp/smart-triage-policy-proof.txt
grep -Fq "REMEDIATION_SAFETY: blocked" /tmp/smart-triage-policy-proof.txt
grep -Fq "BLOCKERS: require-reviewed-remediation" /tmp/smart-triage-policy-proof.txt
echo "PASS: policy summary proof"
