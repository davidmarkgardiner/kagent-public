#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"
KB_DIR="${ROOT}/docs/platform-kb"
RENDERED="${POC_DIR}/evidence/rendered-platform-kb.yaml"

render_kustomize() {
  if command -v kustomize >/dev/null 2>&1; then
    kustomize build "$1"
  elif command -v kubectl >/dev/null 2>&1; then
    kubectl kustomize "$1"
  else
    echo "ERROR: kustomize or kubectl is required to render manifests" >&2
    return 1
  fi
}

safety_scan() {
  if command -v rg >/dev/null 2>&1; then
    rg -n "kind: (ManagedCluster|ResourceGroup|UserAssignedIdentity|VirtualNetwork|AKSCluster|UK8SCluster|DeploymentTemplate)" "$1"
  else
    grep -En "kind: (ManagedCluster|ResourceGroup|UserAssignedIdentity|VirtualNetwork|AKSCluster|UK8SCluster|DeploymentTemplate)" "$1"
  fi
}

print_rendered_resources() {
  if command -v yq >/dev/null 2>&1; then
    yq e '[.kind, .metadata.name] | @tsv' "${RENDERED}" | awk 'NF == 2 {print $1 "/" $2}' | sort
  else
    awk '/^kind: / {kind=$2} /^  name: / && kind {print kind "/" $2; kind=""}' "${RENDERED}" | sort
  fi
}

echo "== platform KB POC validation =="
echo "root: ${ROOT}"

echo
echo "== checking required files =="
required=(
  "${KB_DIR}/INDEX.md"
  "${KB_DIR}/aks/pod-security.md"
  "${KB_DIR}/aks/custom-domains.md"
  "${KB_DIR}/aks/pod-disruption-budgets.md"
  "${KB_DIR}/aks/shared-aks-resources.md"
  "${KB_DIR}/platform/kagent-docs-rag.md"
  "${POC_DIR}/config/doc2vec-platform-kb.yaml"
  "${POC_DIR}/k8s/kustomization.yaml"
)
for path in "${required[@]}"; do
  test -f "${path}"
  echo "ok: ${path#${ROOT}/}"
done

echo
echo "== checking shell scripts =="
for script in "${POC_DIR}"/scripts/*.sh; do
  bash -n "${script}"
  echo "ok: ${script#${ROOT}/}"
done

echo
echo "== checking doc2vec config intent =="
grep -q "product_name: 'platform-kb'" "${POC_DIR}/config/doc2vec-platform-kb.yaml"
grep -q "path: './platform-kb'" "${POC_DIR}/config/doc2vec-platform-kb.yaml"
grep -q "db_path: './vector-dbs/platform-kb.db'" "${POC_DIR}/config/doc2vec-platform-kb.yaml"
echo "ok: doc2vec config targets platform-kb local_directory and platform-kb.db"

echo
echo "== rendering kustomize =="
mkdir -p "${POC_DIR}/evidence"
render_kustomize "${POC_DIR}/k8s" > "${RENDERED}"
test -s "${RENDERED}"
echo "ok: rendered ${RENDERED#${ROOT}/}"

echo
echo "== safety scan =="
if safety_scan "${RENDERED}"; then
  echo "ERROR: rendered manifests include Azure/KRO provisioning kinds" >&2
  exit 1
fi
echo "ok: no Azure/KRO provisioning resource kinds found"

echo
echo "== rendered resources =="
print_rendered_resources

echo
echo "validation complete"
