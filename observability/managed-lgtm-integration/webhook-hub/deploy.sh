#!/bin/bash
# Deploy the Webhook Hub in dependency order with prereq checks.
#
# Usage:
#   ./deploy.sh --context <kube-context>
#   ./deploy.sh --context <kube-context> --skip-istio   # if not on AKS / no Istio
#
# Idempotent — safe to re-run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUBE_CONTEXT=""
SKIP_ISTIO="false"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
  cat <<EOF
Usage: $0 --context <kube-context> [--skip-istio]

Deploys the Webhook Hub:
  - Namespace label
  - Bearer token Secret (validates the Secret exists; does not create one with placeholder)
  - RBAC (ServiceAccount + ClusterRole + Role)
  - Argo Events EventSource (webhook-hub)
  - Istio VirtualService + AuthorizationPolicy (skip with --skip-istio)
  - WorkflowTemplate (webhook-hub-ai-triage)
  - Sensors (ai-triage + team-x slack example)

Prereqs:
  - Argo Events controller + EventBus in argo-events namespace
  - Argo Workflows controller in argo namespace
  - For Istio: shared wildcard Gateway already provisioned

EOF
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --context)      KUBE_CONTEXT="$2"; shift 2 ;;
    --skip-istio)   SKIP_ISTIO="true"; shift ;;
    -h|--help)      usage ;;
    *)              log_error "Unknown arg: $1"; usage ;;
  esac
done

if [ -z "$KUBE_CONTEXT" ]; then
  log_error "--context is required"
  usage
fi

KCTL="kubectl --context ${KUBE_CONTEXT}"

# ─── Prereq checks ────────────────────────────────────────────────────────
log_info "Checking prereqs in context: ${KUBE_CONTEXT}"

if ! ${KCTL} get ns argo-events >/dev/null 2>&1; then
  log_error "namespace argo-events does not exist — install Argo Events first"
  exit 1
fi

if ! ${KCTL} get eventbus default -n argo-events >/dev/null 2>&1; then
  log_error "EventBus 'default' missing in argo-events — install Argo Events first"
  exit 1
fi

if ! ${KCTL} get secret webhook-hub-token -n argo-events >/dev/null 2>&1; then
  log_warn "Secret webhook-hub-token not found — generating one now"
  TOKEN=$(openssl rand -hex 32)
  ${KCTL} create secret generic webhook-hub-token \
    --namespace argo-events \
    --from-literal=token="${TOKEN}"
  log_info "Token created. SAVE THIS — give it to the upstream webhook sender:"
  echo ""
  echo "    ${TOKEN}"
  echo ""
fi

# ─── Apply manifests in order ─────────────────────────────────────────────
log_info "Applying namespace label"
${KCTL} apply -f "${SCRIPT_DIR}/00-namespace.yaml"

log_info "Applying RBAC"
${KCTL} apply -f "${SCRIPT_DIR}/02-rbac.yaml"

log_info "Applying EventSource"
${KCTL} apply -f "${SCRIPT_DIR}/03-eventsource.yaml"

log_info "Waiting for EventSource pod to be Ready"
${KCTL} wait --for=condition=ready pod \
  -l eventsource-name=webhook-hub \
  -n argo-events --timeout=120s

if [ "$SKIP_ISTIO" = "false" ]; then
  log_info "Applying Istio VirtualService + AuthorizationPolicy"
  log_warn "Verify placeholders are replaced in 04-* and 05-*.yaml before applying!"
  ${KCTL} apply -f "${SCRIPT_DIR}/04-istio-virtualservice.yaml"
  ${KCTL} apply -f "${SCRIPT_DIR}/05-istio-authorization-policy.yaml"
else
  log_warn "--skip-istio set, skipping VirtualService + AuthorizationPolicy"
  log_warn "You'll need an alternative ingress (nginx Ingress, LoadBalancer, etc.)"
fi

log_info "Applying WorkflowTemplate (AI triage)"
${KCTL} apply -f "${SCRIPT_DIR}/06-workflow-template-triage.yaml"

log_info "Applying Sensors"
${KCTL} apply -f "${SCRIPT_DIR}/07-sensor-ai-triage.yaml"
${KCTL} apply -f "${SCRIPT_DIR}/08-sensor-slack-example.yaml"

log_info "Waiting for Sensor pods to be Ready"
${KCTL} wait --for=condition=ready pod \
  -l sensor-name=webhook-hub-ai-triage-sensor \
  -n argo-events --timeout=120s
${KCTL} wait --for=condition=ready pod \
  -l sensor-name=webhook-hub-team-x-slack-sensor \
  -n argo-events --timeout=120s

log_info "Hub deployed. Smoke test:"
echo ""
echo "  TOKEN=\$(${KCTL} get secret webhook-hub-token -n argo-events -o jsonpath='{.data.token}' | base64 -d)"
echo ""
echo "  # In-cluster (port-forward):"
echo "  ${KCTL} port-forward -n argo-events svc/webhook-hub-eventsource-svc 12000:12000 &"
echo "  curl -X POST http://localhost:12000/inbound \\"
echo "    -H \"Authorization: Bearer \${TOKEN}\" \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"version\":\"4\",\"status\":\"firing\",\"receiver\":\"hub\",\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"HubSmokeTest\",\"severity\":\"warning\",\"namespace\":\"default\",\"team\":\"team-x\"},\"annotations\":{\"summary\":\"smoke test\",\"description\":\"smoke\"},\"startsAt\":\"$(date -u +%FT%TZ)\"}],\"commonLabels\":{\"team\":\"team-x\"}}'"
echo ""
echo "  # External (after Istio is wired):"
echo "  curl -X POST https://webhook-hub.<your-domain>/inbound -H \"Authorization: Bearer \${TOKEN}\" ..."
echo ""
echo "  ${KCTL} get workflows -n argo-events -l app.kubernetes.io/part-of=webhook-hub --sort-by=.metadata.creationTimestamp | tail -5"
