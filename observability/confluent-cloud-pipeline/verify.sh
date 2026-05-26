#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/confluent.io/.bootstrap.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing ${ENV_FILE}. Run 00-cluster-bootstrap.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

WORKLOAD_CONTEXT="${WORKLOAD_KUBE_CONTEXT:-{{WORKLOAD_KUBE_CONTEXT}}}"
MGMT_CONTEXT="${MGMT_KUBE_CONTEXT:-{{MGMT_KUBE_CONTEXT}}}"

echo "== Confluent topics =="
confluent kafka topic list --cluster "$CONFLUENT_CLUSTER_ID"

echo
echo "== Kubernetes contexts =="
kubectl config get-contexts "$WORKLOAD_CONTEXT" "$MGMT_CONTEXT"

echo
echo "== Argo Events pods =="
kubectl --context="$MGMT_CONTEXT" -n argo-events get pods

echo
echo "== EventSource logs =="
kubectl --context="$MGMT_CONTEXT" -n argo-events logs -l eventsource-name=confluent-kafka --tail=100 || true

echo
echo "== Alloy exporter metrics on ${WORKLOAD_CONTEXT} =="
kubectl --context="$WORKLOAD_CONTEXT" -n monitoring exec deploy/alloy -- wget -qO- localhost:12345/metrics | grep -E "otelcol_exporter.*(sent|failed).*log" || true

echo
echo "== Alertmanager bridge logs =="
kubectl --context="$MGMT_CONTEXT" -n monitoring logs deploy/alertmanager-confluent-bridge --tail=100 || true

echo
echo "== Recent workflows =="
kubectl --context="$MGMT_CONTEXT" -n argo-events get wf --sort-by=.metadata.creationTimestamp | tail -20 || true

cat <<EOF

Manual consume checks:
  confluent kafka topic consume "$CONFLUENT_K8S_TOPIC" --from-beginning --group "verify-$(date +%s)" --cluster "$CONFLUENT_CLUSTER_ID"
  confluent kafka topic consume "$CONFLUENT_ALERTS_TOPIC" --from-beginning --group "verify-alerts-$(date +%s)" --cluster "$CONFLUENT_CLUSTER_ID"

Capture redacted outputs in:
  observability/confluent-cloud-pipeline/EVIDENCE.md
EOF
