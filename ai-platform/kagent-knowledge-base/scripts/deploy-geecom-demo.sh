#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POC_DIR="${ROOT}/ai-platform/kagent-knowledge-base"
DB_PATH="${DB_PATH:-${POC_DIR}/dist/platform-kb.db}"
MANIFEST_PATH="${MANIFEST_PATH:-${POC_DIR}/dist/platform-kb-manifest.json}"
NAMESPACE="${NAMESPACE:-kagent}"
SEED_POD="${SEED_POD:-platform-kb-data-loader}"

if [ ! -s "${DB_PATH}" ]; then
  echo "ERROR: database not found or empty: ${DB_PATH}" >&2
  echo "Run ./scripts/build-platform-kb-db.sh first." >&2
  exit 1
fi

if [ ! -s "${MANIFEST_PATH}" ]; then
  echo "ERROR: manifest not found or empty: ${MANIFEST_PATH}" >&2
  exit 1
fi

echo "== validating rendered manifests =="
"${POC_DIR}/scripts/validate.sh"

echo
echo "== checking platform KB OpenAI secret =="
if ! kubectl -n "${NAMESPACE}" get secret platform-kb-openai >/dev/null 2>&1; then
  echo "ERROR: secret ${NAMESPACE}/platform-kb-openai is required" >&2
  echo "Create it with: kubectl -n ${NAMESPACE} create secret generic platform-kb-openai --from-literal=OPENAI_API_KEY=\"<key>\"" >&2
  exit 1
fi
kubectl -n "${NAMESPACE}" get secret platform-kb-openai -o jsonpath='{.metadata.name}{" present\n"}'

echo
echo "== applying platform KB resources =="
kubectl apply -k "${POC_DIR}/k8s"

echo
echo "== waiting for PVC =="
for _ in $(seq 1 60); do
  phase="$(kubectl -n "${NAMESPACE}" get pvc platform-kb-data -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  if [ "${phase}" = "Bound" ]; then
    kubectl -n "${NAMESPACE}" get pvc platform-kb-data
    break
  fi
  sleep 2
done

phase="$(kubectl -n "${NAMESPACE}" get pvc platform-kb-data -o jsonpath='{.status.phase}')"
if [ "${phase}" != "Bound" ]; then
  echo "ERROR: PVC platform-kb-data is ${phase}, expected Bound" >&2
  exit 1
fi

echo
echo "== seeding vector DB into PVC =="
kubectl -n "${NAMESPACE}" delete pod "${SEED_POD}" --ignore-not-found --wait=true
kubectl -n "${NAMESPACE}" run "${SEED_POD}" \
  --image=busybox:1.36 \
  --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"seed","image":"busybox:1.36","command":["sh","-c","sleep 3600"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"platform-kb-data"}}]}}'
kubectl -n "${NAMESPACE}" wait --for=condition=Ready "pod/${SEED_POD}" --timeout=120s
kubectl -n "${NAMESPACE}" cp "${DB_PATH}" "${SEED_POD}:/data/platform-kb.db"
kubectl -n "${NAMESPACE}" cp "${MANIFEST_PATH}" "${SEED_POD}:/data/platform-kb-manifest.json"
kubectl -n "${NAMESPACE}" exec "${SEED_POD}" -- ls -lh /data/platform-kb.db /data/platform-kb-manifest.json
kubectl -n "${NAMESPACE}" delete pod "${SEED_POD}" --wait=true

echo
echo "== rolling querydoc deployment =="
kubectl -n "${NAMESPACE}" rollout restart deployment/platform-kb-querydoc
kubectl -n "${NAMESPACE}" rollout status deployment/platform-kb-querydoc --timeout=180s

echo
echo "== deployed resources =="
kubectl -n "${NAMESPACE}" get deploy,svc,pvc,cronjob,remotemcpserver.kagent.dev,agent.kagent.dev \
  -l app.kubernetes.io/part-of=kagent

echo
echo "deployment complete"
