#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-}"
ARGO_EVENTS_NAMESPACE="${ARGO_EVENTS_NAMESPACE:-argo-events}"
EVENTSOURCE_SERVICE="${EVENTSOURCE_SERVICE:-smart-triage-alertmanager-eventsource-svc}"
LOCAL_PORT="${LOCAL_PORT:-12000}"
ALERT_FINGERPRINT="${ALERT_FINGERPRINT:-smart-triage-alert-replay-checkout-api}"
ALERT_STARTS_AT="${ALERT_STARTS_AT:-2026-06-01T00:00:00Z}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need kubectl
need curl

KUBECTL=(kubectl)
if [[ -n "$KUBE_CONTEXT" ]]; then
  KUBECTL+=(--context "$KUBE_CONTEXT")
fi

payload_file="$(mktemp)"
pf_log="$(mktemp)"
cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then
    kill "$PF_PID" >/dev/null 2>&1 || true
    wait "$PF_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$payload_file" "$pf_log"
}
trap cleanup EXIT

cat > "$payload_file" <<JSON
{
  "receiver": "smart-triage-demo",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "KubePodCrashLooping",
        "severity": "warning",
        "cluster": "demo-cluster",
        "environment": "nonprod",
        "namespace": "demo-payments",
        "workload": "checkout-api",
        "deployment": "checkout-api",
        "pod": "checkout-api-abc123",
        "container": "checkout-api",
        "service": "checkout-api"
      },
      "annotations": {
        "summary": "checkout-api pod is crash looping after a config rollout",
        "description": "Synthetic Alertmanager replay for the smart-triage fan-out demo.",
        "runbook_url": "https://runbooks.example.invalid/checkout-api-crashloop"
      },
      "startsAt": "$ALERT_STARTS_AT",
      "endsAt": "0001-01-01T00:00:00Z",
      "fingerprint": "$ALERT_FINGERPRINT"
    }
  ],
  "groupLabels": {
    "alertname": "KubePodCrashLooping",
    "namespace": "demo-payments"
  },
  "commonLabels": {
    "alertname": "KubePodCrashLooping",
    "severity": "warning"
  },
  "commonAnnotations": {
    "summary": "checkout-api pod is crash looping after a config rollout"
  }
}
JSON

echo "== Smart triage Alertmanager replay =="
echo "namespace: $ARGO_EVENTS_NAMESPACE"
echo "service: $EVENTSOURCE_SERVICE"

"${KUBECTL[@]}" -n "$ARGO_EVENTS_NAMESPACE" get svc "$EVENTSOURCE_SERVICE" >/dev/null
"${KUBECTL[@]}" -n "$ARGO_EVENTS_NAMESPACE" port-forward "svc/$EVENTSOURCE_SERVICE" "$LOCAL_PORT:12000" >"$pf_log" 2>&1 &
PF_PID="$!"

for _ in $(seq 1 30); do
  if grep -q "Forwarding from" "$pf_log"; then
    break
  fi
  if ! kill -0 "$PF_PID" >/dev/null 2>&1; then
    cat "$pf_log" >&2
    exit 1
  fi
  sleep 1
done

if ! grep -q "Forwarding from" "$pf_log"; then
  echo "port-forward did not become ready" >&2
  cat "$pf_log" >&2
  exit 1
fi

echo "-- posting replay payload"
curl -sS -X POST "http://127.0.0.1:$LOCAL_PORT/alerts" \
  -H "Content-Type: application/json" \
  --data-binary @"$payload_file"
echo
echo "ALERT_REPLAYED: yes"
echo "ALERT_SOURCE: alertmanager"
echo "FINGERPRINT: $ALERT_FINGERPRINT"
