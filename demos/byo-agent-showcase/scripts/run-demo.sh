#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="${ROOT}/demos/byo-agent-showcase"
MODE="${1:---dry-run}"
KUBECTL_CONTEXT="${KUBECTL_CONTEXT:-}"

render() {
  if command -v kubectl >/dev/null 2>&1; then
    kubectl kustomize "${DEMO_DIR}/expected"
  elif command -v kustomize >/dev/null 2>&1; then
    kustomize build "${DEMO_DIR}/expected"
  else
    echo "ERROR: kubectl or kustomize is required" >&2
    return 1
  fi
}

case "${MODE}" in
  --dry-run)
    bash "${DEMO_DIR}/scripts/verify-demo.sh"
    render >/tmp/byo-agent-showcase.rendered.yaml
    echo "BYO_DEMO_MODE: dry-run"
    echo "BYO_AGENT_RENDERED: yes"
    echo "Rendered manifest: /tmp/byo-agent-showcase.rendered.yaml"
    echo "Next apply command:"
    echo "KUBECTL_CONTEXT={{KUBE_CONTEXT}} bash demos/byo-agent-showcase/scripts/run-demo.sh --apply"
    ;;
  --apply)
    : "${KUBECTL_CONTEXT:?KUBECTL_CONTEXT is required for --apply}"
    bash "${DEMO_DIR}/scripts/verify-demo.sh"
    render | kubectl --context "${KUBECTL_CONTEXT}" apply -f -
    echo "BYO_DEMO_MODE: apply"
    echo "BYO_AGENT_RENDERED: yes"
    echo "TOOLGRANT_CREATED: yes"
    echo "OUTPUT_SANITIZED: yes"
    ;;
  *)
    echo "Usage: $0 [--dry-run|--apply]" >&2
    exit 2
    ;;
esac
