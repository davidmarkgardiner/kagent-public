#!/bin/bash
# =============================================================================
# Test: Agent Routing Logic for k8s-triage-critical workflow
#
# Extracts the jq routing logic from parse-otlp and validates it against
# test OTLP payloads with various namespace/reason combinations.
#
# Usage: ./test-routing-logic.sh
# No cluster access needed — runs entirely locally.
# =============================================================================
set -e

PASS=0
FAIL=0

check() {
  local label="$1" actual="$2" expected="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  PASS: $label → $actual"
    PASS=$((PASS+1))
  else
    echo "  FAIL: $label → $actual (expected $expected)"
    FAIL=$((FAIL+1))
  fi
}

# ---- Routing tables ----
NS_ROUTES='{"kube-system":"kube-system-agent","flux-system":"flux-system-agent","gatekeeper-system":"gatekeeper-system-agent","aks-istio-system":"aks-istio-system-agent","aks-istio-ingress":"aks-istio-ingress-agent"}'
REASON_ROUTES='{}'
DEFAULT_TRIAGE="sre-triage-agent"
DEFAULT_REMEDIATION="sre-remediation-agent"

echo "$NS_ROUTES" > /tmp/ns_routes.json
echo "$REASON_ROUTES" > /tmp/reason_routes.json

# ---- Test OTLP payload ----
# 5 events across different namespaces:
#   1. CrashLoopBackOff in kube-system (critical, namespace match)
#   2. OOMKilled in flux-system (critical, namespace match)
#   3. FailedMount in payments (critical, no match → default)
#   4. Unhealthy in kube-system (NOT critical → should be filtered)
#   5. CrashLoopBackOff in aks-istio-system (critical, namespace match)
cat > /tmp/otlp_test.json << 'EOF'
{
  "resourceLogs": [{
    "resource": {
      "attributes": [
        {"key": "cluster", "value": {"stringValue": "aks-test-cluster"}},
        {"key": "environment", "value": {"stringValue": "dev"}}
      ]
    },
    "scopeLogs": [{
      "logRecords": [
        {
          "attributes": [
            {"key": "event_reason", "value": {"stringValue": "CrashLoopBackOff"}},
            {"key": "event_type", "value": {"stringValue": "Warning"}},
            {"key": "obj_namespace", "value": {"stringValue": "kube-system"}},
            {"key": "obj_kind", "value": {"stringValue": "Pod"}}
          ],
          "body": {"stringValue": "{\"reason\":\"CrashLoopBackOff\",\"type\":\"Warning\",\"message\":\"Back-off restarting failed container\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"coredns-abc123\",\"namespace\":\"kube-system\"},\"count\":5,\"lastTimestamp\":\"2026-03-18T10:00:00Z\"}"}
        },
        {
          "attributes": [
            {"key": "event_reason", "value": {"stringValue": "OOMKilled"}},
            {"key": "event_type", "value": {"stringValue": "Warning"}},
            {"key": "obj_namespace", "value": {"stringValue": "flux-system"}},
            {"key": "obj_kind", "value": {"stringValue": "Pod"}}
          ],
          "body": {"stringValue": "{\"reason\":\"OOMKilled\",\"type\":\"Warning\",\"message\":\"Container killed due to OOM\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"source-controller-xyz\",\"namespace\":\"flux-system\"},\"count\":1,\"lastTimestamp\":\"2026-03-18T10:01:00Z\"}"}
        },
        {
          "attributes": [
            {"key": "event_reason", "value": {"stringValue": "FailedMount"}},
            {"key": "event_type", "value": {"stringValue": "Warning"}},
            {"key": "obj_namespace", "value": {"stringValue": "payments"}},
            {"key": "obj_kind", "value": {"stringValue": "Pod"}}
          ],
          "body": {"stringValue": "{\"reason\":\"FailedMount\",\"type\":\"Warning\",\"message\":\"Unable to attach volume\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"payments-api-def456\",\"namespace\":\"payments\"},\"count\":3,\"lastTimestamp\":\"2026-03-18T10:02:00Z\"}"}
        },
        {
          "attributes": [
            {"key": "event_reason", "value": {"stringValue": "Unhealthy"}},
            {"key": "event_type", "value": {"stringValue": "Warning"}},
            {"key": "obj_namespace", "value": {"stringValue": "kube-system"}},
            {"key": "obj_kind", "value": {"stringValue": "Pod"}}
          ],
          "body": {"stringValue": "{\"reason\":\"Unhealthy\",\"type\":\"Warning\",\"message\":\"Readiness probe failed\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"metrics-server-ghi789\",\"namespace\":\"kube-system\"},\"count\":10}"}
        },
        {
          "attributes": [
            {"key": "event_reason", "value": {"stringValue": "CrashLoopBackOff"}},
            {"key": "event_type", "value": {"stringValue": "Warning"}},
            {"key": "obj_namespace", "value": {"stringValue": "aks-istio-system"}},
            {"key": "obj_kind", "value": {"stringValue": "Pod"}}
          ],
          "body": {"stringValue": "{\"reason\":\"CrashLoopBackOff\",\"type\":\"Warning\",\"message\":\"Back-off restarting istiod\",\"involvedObject\":{\"kind\":\"Pod\",\"name\":\"istiod-abc\",\"namespace\":\"aks-istio-system\"},\"count\":2}"}
        }
      ]
    }]
  }]
}
EOF

# ---- The jq filter (exact copy from workflow template) ----
JQ_FILTER='
def attrs: [.[]? | {(.key): (.value.stringValue // (.value.intValue // .value.boolValue // "" | tostring))}] | add // {};
def is_critical: . as $r | ["CrashLoopBackOff","OOMKilled","OOMKilling","FailedScheduling","NodeNotReady","NodeNotSchedulable","FailedMount","FailedAttachVolume"] | any(. == $r);
[
  .resourceLogs[]? |
  (.resource.attributes // [] | attrs) as $res |
  .scopeLogs[]?.logRecords[]? |
  (.attributes // [] | attrs) as $a |
  (.body.stringValue // "" | if . != "" then (fromjson? // {}) else {} end) as $ev |
  ($a.event_reason // $ev.reason // "") as $reason |
  ($a.event_type // $ev.type // "") as $type |
  ($a.obj_namespace // $ev.involvedObject.namespace // "") as $ns |
  select($type == "Warning" and ($reason | is_critical)) |
  ($ns_routes[0][$ns] // null) as $ns_agent |
  ($reason_routes[0][$reason] // null) as $reason_agent |
  (if $remediate == "true" then $default_remediation else $default_triage end) as $default_agent |
  {
    event_reason:     $reason,
    object_namespace: $ns,
    object_name:      ($ev.involvedObject.name // ""),
    target_agent:     ($ns_agent // $reason_agent // $default_agent)
  }
]
'

run_filter() {
  local remediate="$1"
  jq \
    --arg default_triage "$DEFAULT_TRIAGE" \
    --arg default_remediation "$DEFAULT_REMEDIATION" \
    --arg remediate "$remediate" \
    --slurpfile ns_routes /tmp/ns_routes.json \
    --slurpfile reason_routes /tmp/reason_routes.json \
    "$JQ_FILTER" /tmp/otlp_test.json
}

# ==========================================================================
echo "=== Test 1: Namespace routing (triage mode) ==="
RESULT=$(run_filter "false")
echo "$RESULT" | jq -r '.[] | "  \(.event_reason) in \(.object_namespace) → \(.target_agent)"'
echo ""

check "kube-system/CrashLoopBackOff" \
  "$(echo "$RESULT" | jq -r '[.[] | select(.object_namespace == "kube-system")][0].target_agent')" \
  "kube-system-agent"

check "flux-system/OOMKilled" \
  "$(echo "$RESULT" | jq -r '[.[] | select(.object_namespace == "flux-system")][0].target_agent')" \
  "flux-system-agent"

check "payments/FailedMount (no ns match → default)" \
  "$(echo "$RESULT" | jq -r '[.[] | select(.object_namespace == "payments")][0].target_agent')" \
  "sre-triage-agent"

check "aks-istio-system/CrashLoopBackOff" \
  "$(echo "$RESULT" | jq -r '[.[] | select(.object_namespace == "aks-istio-system")][0].target_agent')" \
  "aks-istio-system-agent"

check "Unhealthy filtered out (not critical)" \
  "$(echo "$RESULT" | jq '[.[] | select(.event_reason == "Unhealthy")] | length')" \
  "0"

check "Total events = 4" \
  "$(echo "$RESULT" | jq 'length')" \
  "4"

# ==========================================================================
echo ""
echo "=== Test 2: Reason routing (FailedMount → storage-specialist) ==="
echo '{"FailedMount":"storage-specialist-agent","FailedAttachVolume":"storage-specialist-agent"}' > /tmp/reason_routes.json

RESULT2=$(run_filter "false")
echo "$RESULT2" | jq -r '.[] | "  \(.event_reason) in \(.object_namespace) → \(.target_agent)"'
echo ""

check "payments/FailedMount → storage-specialist (reason route)" \
  "$(echo "$RESULT2" | jq -r '[.[] | select(.object_namespace == "payments")][0].target_agent')" \
  "storage-specialist-agent"

check "kube-system still namespace-routed (not reason)" \
  "$(echo "$RESULT2" | jq -r '[.[] | select(.object_namespace == "kube-system")][0].target_agent')" \
  "kube-system-agent"

# ==========================================================================
echo ""
echo "=== Test 3: Remediation mode ==="
RESULT3=$(run_filter "true")

check "kube-system still ns-routed in remediate mode" \
  "$(echo "$RESULT3" | jq -r '[.[] | select(.object_namespace == "kube-system")][0].target_agent')" \
  "kube-system-agent"

# Reset reason routes to empty for this test
echo '{}' > /tmp/reason_routes.json
RESULT4=$(run_filter "true")

check "payments default → sre-remediation-agent in remediate mode" \
  "$(echo "$RESULT4" | jq -r '[.[] | select(.object_namespace == "payments")][0].target_agent')" \
  "sre-remediation-agent"

# ==========================================================================
echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
