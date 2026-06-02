#!/usr/bin/env bash
set -euo pipefail

WORKFLOW="${1:-}"
NAMESPACE="${ARGO_NAMESPACE:-argo}"

if [[ -z "$WORKFLOW" ]]; then
  echo "usage: $0 <workflow-name>" >&2
  exit 2
fi

yq eval '.. | select(has("toolNames")) | .toolNames[]' a2a/smart-triage-fanout-demo/agents.yaml \
  | grep -Eiq '(apply|delete|exec|patch|restart|sync|rollback)' \
  && { echo "FAIL: mutating tool present" >&2; exit 1; } \
  || true

pod="$(kubectl get pods -n "$NAMESPACE" -l "workflows.argoproj.io/workflow=$WORKFLOW" -o name \
  | grep call-specialist | while read -r candidate; do
      if kubectl logs -n "$NAMESPACE" "$candidate" -c main 2>/dev/null | grep -q 'A2A phase: deployment'; then
        echo "$candidate"
        break
      fi
    done)"

test -n "$pod"
kubectl logs -n "$NAMESPACE" "$pod" -c main | tee /tmp/smart-triage-deployment-proof.txt
grep -Fq "SPECIALIST_DEPLOYMENT: completed" /tmp/smart-triage-deployment-proof.txt
grep -Fq "VERDICT: bad_deploy" /tmp/smart-triage-deployment-proof.txt
grep -Fq "DRIFT: no" /tmp/smart-triage-deployment-proof.txt
echo "PASS: deployment read-only proof"
