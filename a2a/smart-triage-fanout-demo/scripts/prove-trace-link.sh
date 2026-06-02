#!/usr/bin/env bash
set -euo pipefail

WORKFLOW="${1:-}"
NAMESPACE="${ARGO_NAMESPACE:-argo}"

if [[ -z "$WORKFLOW" ]]; then
  echo "usage: $0 <workflow-name>" >&2
  exit 2
fi

pod="$(kubectl get pods -n "$NAMESPACE" -l "workflows.argoproj.io/workflow=$WORKFLOW" -o name \
  | grep call-specialist | while read -r candidate; do
      if kubectl logs -n "$NAMESPACE" "$candidate" -c main 2>/dev/null | grep -q 'A2A phase: trace'; then
        echo "$candidate"
        break
      fi
    done)"

test -n "$pod"
kubectl logs -n "$NAMESPACE" "$pod" -c main | tee /tmp/smart-triage-trace-proof.txt
grep -Fq "SPECIALIST_TRACE: completed" /tmp/smart-triage-trace-proof.txt
grep -Fq "FALLBACK: NO_TRACE" /tmp/smart-triage-trace-proof.txt
grep -Fq "TRACE_QUERY:" /tmp/smart-triage-trace-proof.txt
echo "PASS: trace fallback proof"
