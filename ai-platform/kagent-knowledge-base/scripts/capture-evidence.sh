#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"
OUT="${POC_DIR}/evidence/EVIDENCE.md"
RENDERED="${POC_DIR}/evidence/rendered-platform-kb.yaml"
PREFLIGHT_LOG="${POC_DIR}/evidence/doc2vec-preflight.log"

sanitize() {
  sed -E $'s/\x1b\\[[0-9;]*[A-Za-z]//g; s/sk-[A-Za-z0-9_*.-]{6,}/sk-***/g; s/(OPENAI_API_KEY=)[^[:space:]]+/\\1***/g; s/(AZURE_OPENAI_KEY=)[^[:space:]]+/\\1***/g; s/(Bearer )[A-Za-z0-9._~+\\/-]+=*/\\1***/g; s/\\b[[:xdigit:]]{32}\\b/{{AZURE_OPENAI_KEY}}/g'
}

mkdir -p "${POC_DIR}/evidence"

{
  echo "# Platform KB POC Evidence"
  echo
  echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Workspace: ${ROOT}"
  echo
  echo "## Local Validation"
  echo
  echo '```text'
  "${POC_DIR}/scripts/validate.sh" 2>&1
  echo '```'
  echo
  echo "## Homelab Host Environment"
  echo
  echo "Expected host: homelab server"
  echo
  echo '```text'
  hostname
  uname -a
  command -v docker || true
  command -v kubectl || true
  command -v node || true
  command -v npm || true
  command -v git || true
  command -v kustomize || true
  echo '```'
  echo
  echo "## Kubernetes Client Dry Run"
  echo
  echo '```text'
  kubectl apply --dry-run=client --validate=false -f "${RENDERED}" 2>&1
  echo '```'
  echo
  echo "## Homelab Cluster Readiness"
  echo
  echo '```text'
  kubectl config current-context 2>&1 || true
  kubectl get namespace kagent --ignore-not-found 2>&1 || true
  kubectl get crd agents.kagent.dev remotemcpservers.kagent.dev 2>&1 || true
  if kubectl -n kagent get secret platform-kb-openai >/dev/null 2>&1; then
    echo "secret/platform-kb-openai present"
    kubectl -n kagent get secret platform-kb-openai -o jsonpath='{.data.OPENAI_API_KEY}' 2>/dev/null | wc -c | awk '{print "OPENAI_API_KEY data bytes: " $1}'
  else
    echo "secret/platform-kb-openai missing"
  fi
  echo '```'
  echo
  echo "## Kubernetes Server Dry Run"
  echo
  echo '```text'
  kubectl apply --dry-run=server --validate=false -f "${RENDERED}" 2>&1 || true
  echo '```'
  echo
  echo "## Notes"
  echo
  echo "- No mutating Kubernetes apply command was run by this evidence script; Kubernetes validation used dry-run only."
  echo "- No Azure or ASO resources were created, modified, or deleted."
  echo "- The indexer CronJob is rendered as \`suspend: true\`; it will not run nightly until intentionally enabled."
  echo "- A real querydoc smoke test requires a valid embedding credential because querydoc embeds user queries at runtime."
  echo
  echo "## Embedding Credential Preflight"
  echo
  echo '```text'
  raw_log="${PREFLIGHT_LOG}.raw"
  set +e
  if kubectl -n kagent get secret platform-kb-openai >/dev/null 2>&1; then
    OPENAI_API_KEY="$(kubectl -n kagent get secret platform-kb-openai -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)" \
      "${POC_DIR}/scripts/build-platform-kb-db.sh" > "${raw_log}" 2>&1
    preflight_rc=$?
  else
    "${POC_DIR}/scripts/build-platform-kb-db.sh" > "${raw_log}" 2>&1
    preflight_rc=$?
  fi
  set -e
  sanitize < "${raw_log}" > "${PREFLIGHT_LOG}"
  rm -f "${raw_log}"
  echo "exit_code=${preflight_rc}"
  echo "full_log=${PREFLIGHT_LOG}"
  grep -m 1 "Using local KB repo" "${PREFLIGHT_LOG}" || true
  grep -m 1 "Cloning doc2vec" "${PREFLIGHT_LOG}" || true
  grep -m 1 "Running doc2vec" "${PREFLIGHT_LOG}" || true
  grep -m 1 "Incorrect API key" "${PREFLIGHT_LOG}" || true
  grep -m 1 -E "refusing to publish|ERROR:" "${PREFLIGHT_LOG}" || true
  echo '```'
} > "${OUT}"

echo "Wrote ${OUT}"
