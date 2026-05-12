#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-argo}"
DIRECT_URL="${DIRECT_URL:-http://127.0.0.1:12000/grafana/direct}"
REDPANDA_WEBHOOK_URL="${REDPANDA_WEBHOOK_URL:-http://127.0.0.1:8080/grafana/redpanda}"
REDPANDA_BROKERS="${REDPANDA_BROKERS:-redpanda.redpanda.svc.cluster.local:9092}"
REDPANDA_TOPIC="${REDPANDA_TOPIC:-grafana.alerts}"

log() {
  printf '\n==> %s\n' "$*"
}

require() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

case "${1:-dry-run}" in
  dry-run)
    require kubectl
    log "server dry-run for default Argo Events EventBus"
    kubectl apply --dry-run=server -f "$ROOT_DIR/argo/eventbus"
    log "server dry-run for Argo EventSources and Sensor"
    kubectl apply --dry-run=server -f "$ROOT_DIR/argo/eventsources" -f "$ROOT_DIR/argo/sensors"
    log "server dry-run for receiver and Sensor RBAC"
    kubectl apply --dry-run=server -f "$ROOT_DIR/k8s/alerting"
    if kubectl get namespace redpanda >/dev/null 2>&1; then
      log "server dry-run for optional single-node Redpanda"
      kubectl apply --dry-run=server -f "$ROOT_DIR/k8s/redpanda"
    else
      log "client dry-run for optional single-node Redpanda because namespace redpanda is not present"
      kubectl apply --dry-run=client -f "$ROOT_DIR/k8s/redpanda"
    fi
    ;;

  apply-redpanda)
    require kubectl
    log "apply optional single-node Redpanda"
    kubectl apply -f "$ROOT_DIR/k8s/redpanda"
    kubectl -n redpanda rollout status statefulset/redpanda --timeout=180s
    ;;

  apply)
    require kubectl
    log "apply receiver, RBAC, EventSources, and Sensor"
    kubectl apply -f "$ROOT_DIR/argo/eventbus"
    kubectl apply -f "$ROOT_DIR/k8s/alerting"
    kubectl apply -f "$ROOT_DIR/argo/eventsources"
    kubectl apply -f "$ROOT_DIR/argo/sensors"
    ;;

  send-direct)
    require curl
    payload="${2:-$ROOT_DIR/testdata/grafana-log-error-alert.json}"
    log "POST $payload to direct Argo EventSource webhook"
    curl -fsS -H 'Content-Type: application/json' --data-binary "@$payload" "$DIRECT_URL"
    ;;

  send-redpanda)
    require curl
    payload="${2:-$ROOT_DIR/testdata/grafana-metric-threshold-alert.json}"
    log "POST $payload to webhook receiver that publishes to Redpanda"
    curl -fsS -H 'Content-Type: application/json' --data-binary "@$payload" "$REDPANDA_WEBHOOK_URL"
    ;;

  port-forward-direct)
    require kubectl
    log "forward direct EventSource webhook to $DIRECT_URL"
    kubectl -n "$NAMESPACE" port-forward svc/grafana-alert-webhook-eventsource-svc 12000:12000
    ;;

  port-forward-redpanda-webhook)
    require kubectl
    log "forward Redpanda webhook receiver to $REDPANDA_WEBHOOK_URL"
    kubectl -n "$NAMESPACE" port-forward svc/grafana-redpanda-webhook 8080:8080
    ;;

  consume-redpanda)
    require rpk
    log "consume recent messages from $REDPANDA_TOPIC"
    rpk topic consume "$REDPANDA_TOPIC" --brokers "$REDPANDA_BROKERS" --num 3
    ;;

  logs)
    require kubectl
    log "EventSource logs"
    kubectl -n "$NAMESPACE" logs -l eventsource-name=grafana-alert-webhook --tail=100
    kubectl -n "$NAMESPACE" logs -l eventsource-name=grafana-alert-redpanda --tail=100
    log "Sensor logs"
    kubectl -n "$NAMESPACE" logs -l sensor-name=grafana-alert-router --tail=100
    log "Triggered workflows"
    kubectl -n "$NAMESPACE" get workflows -l app.kubernetes.io/name=grafana-alert-router
    ;;

  *)
    cat <<USAGE
Usage: $0 [dry-run|apply-redpanda|apply|send-direct|send-redpanda|port-forward-direct|port-forward-redpanda-webhook|consume-redpanda|logs]

Environment:
  NAMESPACE=$NAMESPACE
  DIRECT_URL=$DIRECT_URL
  REDPANDA_WEBHOOK_URL=$REDPANDA_WEBHOOK_URL
  REDPANDA_BROKERS=$REDPANDA_BROKERS
  REDPANDA_TOPIC=$REDPANDA_TOPIC
USAGE
    exit 2
    ;;
esac
