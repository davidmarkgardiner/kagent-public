#!/bin/bash
# create-agent.sh — Generate, deploy, and test a kagent namespace agent
# Part of the kagent-namespace-agent OpenClaw skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/../templates"

# Defaults
CONTEXT="{{CLUSTER_NAME}}"
KAGENT_NS="kagent"
MODEL_CONFIG="default-model-config"
DEPLOY=false
TEST=false
OUTPUT_DIR="."
NAMESPACE=""
DESCRIPTION=""

usage() {
  cat <<EOF
Usage: $(basename "$0") --namespace <ns> --description <desc> [options]

Create a kagent AI agent for a specific Kubernetes namespace.

Required:
  --namespace <ns>       Target namespace (e.g., cert-manager)
  --description <desc>   Domain description for the agent's system prompt

Options:
  --context <ctx>        kubectl context (default: {{CLUSTER_NAME}})
  --kagent-ns <ns>       kagent namespace (default: kagent)
  --model-config <name>  ModelConfig name (default: default-model-config)
  --deploy               Deploy to cluster after generation
  --test                 Run E2E test after deployment (implies --deploy)
  --output-dir <dir>     Output directory (default: current dir)
  -h, --help             Show this help

Examples:
  # Generate manifests only
  $(basename "$0") --namespace cert-manager --description "TLS certificate lifecycle management"

  # Generate, deploy, and test
  $(basename "$0") --namespace cert-manager --description "TLS cert management" --deploy --test

  # Custom output directory
  $(basename "$0") --namespace monitoring --description "Observability stack" --output-dir /tmp/kagent-manifests
EOF
  exit 0
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)    NAMESPACE="$2"; shift 2 ;;
    --description)  DESCRIPTION="$2"; shift 2 ;;
    --context)      CONTEXT="$2"; shift 2 ;;
    --kagent-ns)    KAGENT_NS="$2"; shift 2 ;;
    --model-config) MODEL_CONFIG="$2"; shift 2 ;;
    --deploy)       DEPLOY=true; shift ;;
    --test)         TEST=true; DEPLOY=true; shift ;;
    --output-dir)   OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help)      usage ;;
    *)              echo "Unknown arg: $1"; usage ;;
  esac
done

# Validate
if [[ -z "$NAMESPACE" ]]; then
  echo "❌ --namespace is required"
  exit 1
fi
if [[ -z "$DESCRIPTION" ]]; then
  echo "❌ --description is required"
  exit 1
fi

# Title case for display
NAMESPACE_TITLE="$(echo "$NAMESPACE" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')"

mkdir -p "$OUTPUT_DIR"

echo "🤖 Creating kagent agent for namespace: $NAMESPACE"
echo "   Description: $DESCRIPTION"
echo "   Context: $CONTEXT"
echo ""

# Generate Agent CR
AGENT_FILE="$OUTPUT_DIR/${NAMESPACE}-agent.yaml"
sed \
  -e "s|{{NAMESPACE}}|$NAMESPACE|g" \
  -e "s|{{NAMESPACE_TITLE}}|$NAMESPACE_TITLE|g" \
  -e "s|{{KAGENT_NS}}|$KAGENT_NS|g" \
  -e "s|{{MODEL_CONFIG}}|$MODEL_CONFIG|g" \
  -e "s|{{DESCRIPTION}}|$DESCRIPTION|g" \
  "$TEMPLATE_DIR/agent.yaml.tmpl" > "$AGENT_FILE"
echo "✅ Generated: $AGENT_FILE"

# Generate Sensor CR
SENSOR_FILE="$OUTPUT_DIR/${NAMESPACE}-sensor.yaml"
sed \
  -e "s|{{NAMESPACE}}|$NAMESPACE|g" \
  "$TEMPLATE_DIR/sensor.yaml.tmpl" > "$SENSOR_FILE"
echo "✅ Generated: $SENSOR_FILE"

# Generate test error injection
TEST_FILE="$OUTPUT_DIR/${NAMESPACE}-test-error.yaml"
sed \
  -e "s|{{NAMESPACE}}|$NAMESPACE|g" \
  "$TEMPLATE_DIR/test-error.yaml.tmpl" > "$TEST_FILE"
echo "✅ Generated: $TEST_FILE"

echo ""
echo "📁 Files created in: $OUTPUT_DIR"
echo "   - ${NAMESPACE}-agent.yaml     (kagent Agent CR)"
echo "   - ${NAMESPACE}-sensor.yaml    (Argo Sensor CR)"
echo "   - ${NAMESPACE}-test-error.yaml (Error injection for testing)"

# Deploy if requested
if [[ "$DEPLOY" == "true" ]]; then
  echo ""
  echo "🚀 Deploying to cluster ($CONTEXT)..."

  # Ensure namespace exists
  kubectl --context "$CONTEXT" create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f - 2>/dev/null
  echo "   ✅ Namespace $NAMESPACE exists"

  # Apply agent
  kubectl --context "$CONTEXT" apply -f "$AGENT_FILE"
  echo "   ✅ Agent ${NAMESPACE}-agent applied"

  # Apply sensor
  kubectl --context "$CONTEXT" apply -f "$SENSOR_FILE"
  echo "   ✅ Sensor kagent-triage-${NAMESPACE} applied"

  # Wait for agent to be ready
  echo "   ⏳ Waiting for agent to be ready..."
  for i in $(seq 1 30); do
    STATUS=$(kubectl --context "$CONTEXT" get agent "${NAMESPACE}-agent" -n "$KAGENT_NS" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
    if [[ "$STATUS" == "True" ]]; then
      echo "   ✅ Agent ${NAMESPACE}-agent is Ready"
      break
    fi
    if [[ $i -eq 30 ]]; then
      echo "   ⚠️  Agent not ready after 60s — check: kubectl --context $CONTEXT get agent ${NAMESPACE}-agent -n $KAGENT_NS -o yaml"
    fi
    sleep 2
  done
fi

# Test if requested
if [[ "$TEST" == "true" ]]; then
  echo ""
  echo "🧪 Running E2E test..."

  # Port-forward to kagent controller
  kubectl --context "$CONTEXT" port-forward svc/kagent-controller -n "$KAGENT_NS" 18083:8083 &>/dev/null &
  PF_PID=$!
  sleep 2

  # Test: send a diagnostic query via A2A. The session/chat API is broken on
  # kagent v0.8.0-beta4; the trailing slash and "kind":"text" are required.
  RESPONSE=$(curl -s --max-time 60 -X POST \
    "http://localhost:18083/api/a2a/${KAGENT_NS}/${NAMESPACE}-agent/" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":\"create-agent-test\",\"method\":\"message/send\",\"params\":{\"message\":{\"role\":\"user\",\"parts\":[{\"kind\":\"text\",\"text\":\"List all pods in the ${NAMESPACE} namespace and report their status.\"}]}}}" 2>/dev/null)

  REPLY=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
parts = [p.get('text', '') for a in d.get('result', {}).get('artifacts', [])
         for p in a.get('parts', [])]
print(' '.join(parts)[:200])
" 2>/dev/null)

  if [[ -n "$REPLY" ]]; then
    echo "   ✅ Agent responded to test query"
    echo "   Response preview: $REPLY"
  else
    echo "   ⚠️  No A2A reply from ${NAMESPACE}-agent"
    echo "   Check: kubectl --context $CONTEXT get agent ${NAMESPACE}-agent -n $KAGENT_NS -o yaml"
  fi

  kill $PF_PID 2>/dev/null

  echo ""
  echo "🧪 To inject test errors:"
  echo "   kubectl --context $CONTEXT apply -f $TEST_FILE"
  echo ""
  echo "👀 Then watch for workflows:"
  echo "   kubectl --context $CONTEXT get workflows -n argo-events -w"
fi

echo ""
echo "📖 To add more namespace agents, run this script again with different --namespace"
echo "🔗 For AKS lift-and-shift, update EventSource and secrets references in the sensor YAML"
