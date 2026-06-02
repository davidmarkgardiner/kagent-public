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
      if kubectl logs -n "$NAMESPACE" "$candidate" -c main 2>/dev/null | grep -q 'A2A phase: knowledge'; then
        echo "$candidate"
        break
      fi
    done)"

test -n "$pod"
kubectl logs -n "$NAMESPACE" "$pod" -c main | tee /tmp/smart-triage-knowledge-proof.txt
grep -Fq "SPECIALIST_KNOWLEDGE: completed" /tmp/smart-triage-knowledge-proof.txt
grep -Fq "CITATIONS: docs/platform-kb/runbooks/checkout-api-crashloop.md#chunk-1" /tmp/smart-triage-knowledge-proof.txt
grep -Fq "NO_RELEVANT_DOCS_CASE: validated" /tmp/smart-triage-knowledge-proof.txt
echo "PASS: knowledge citation proof"
