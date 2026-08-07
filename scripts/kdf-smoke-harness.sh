#!/usr/bin/env bash
# Disposable Kubernetes Delivery Factory smoke harness.
# Public-safe: emits local evidence only, avoids Secret data, and hard-refuses
# any target other than context kind-homelab / namespace kdf-smoke.
set -euo pipefail

readonly ALLOWED_CONTEXT="kind-homelab"
readonly ALLOWED_NAMESPACE="kdf-smoke"
readonly APP_LABEL="kdf-smoke-harness"
readonly DEFAULT_IMAGE="registry.k8s.io/e2e-test-images/agnhost:2.45"

MODE="plan"
CONTEXT="${ALLOWED_CONTEXT}"
NAMESPACE="${ALLOWED_NAMESPACE}"
KUBECONFIG_PATH="${KUBECONFIG:-}"
RUN_ID="$(date -u +%Y%m%d%H%M%S)"
EVIDENCE_DIR=""
TIMEOUT="120s"
IMAGE="${DEFAULT_IMAGE}"

usage() {
  cat <<'USAGE'
Usage: KUBECONFIG=/path/to/kubeconfig scripts/kdf-smoke-harness.sh [options]

Modes:
  --plan              Print the manifest and perform fail-closed target checks only (default)
  --run               Create, observe, and clean up labelled smoke resources

Safety target (hard-coded allowlist):
  --context NAME      Must be kind-homelab
  --namespace NAME    Must be kdf-smoke

Other options:
  --evidence-dir DIR  Directory for evidence files (default: mktemp under /tmp)
  --run-id ID         DNS-label-safe suffix for resource names (default: UTC timestamp)
  --timeout DURATION  kubectl wait timeout (default: 120s)
  --image IMAGE       Public test image (default: registry.k8s.io/e2e-test-images/agnhost:2.45)
  -h, --help          Show this help

The harness never reads Secret data. It gathers node capacity/allocatable, namespace-scoped
non-Secret resources, events, pod status, and test pod logs; then it deletes only resources
with app.kubernetes.io/part-of=kdf-smoke-harness and this run-id label.
USAGE
}

log() { printf '[kdf-smoke] %s\n' "$*"; }
fatal() { printf '[kdf-smoke] ERROR: %s\n' "$*" >&2; exit 1; }

require_arg() {
  local opt="$1"
  local val="${2:-}"
  [[ -n "${val}" ]] || fatal "${opt} requires a value"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan) MODE="plan"; shift ;;
    --run) MODE="run"; shift ;;
    --context) require_arg "$1" "${2:-}"; CONTEXT="$2"; shift 2 ;;
    --namespace|-n) require_arg "$1" "${2:-}"; NAMESPACE="$2"; shift 2 ;;
    --kubeconfig) require_arg "$1" "${2:-}"; KUBECONFIG_PATH="$2"; shift 2 ;;
    --evidence-dir) require_arg "$1" "${2:-}"; EVIDENCE_DIR="$2"; shift 2 ;;
    --run-id) require_arg "$1" "${2:-}"; RUN_ID="$2"; shift 2 ;;
    --timeout) require_arg "$1" "${2:-}"; TIMEOUT="$2"; shift 2 ;;
    --image) require_arg "$1" "${2:-}"; IMAGE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fatal "unknown argument: $1" ;;
  esac
done

[[ "${MODE}" == "plan" || "${MODE}" == "run" ]] || fatal "mode must be plan or run"
[[ "${CONTEXT}" == "${ALLOWED_CONTEXT}" ]] || fatal "refusing context '${CONTEXT}'; allowed context is '${ALLOWED_CONTEXT}'"
[[ "${NAMESPACE}" == "${ALLOWED_NAMESPACE}" ]] || fatal "refusing namespace '${NAMESPACE}'; allowed namespace is '${ALLOWED_NAMESPACE}'"
[[ "${RUN_ID}" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || fatal "run-id must be a Kubernetes DNS label suffix"
[[ "${#RUN_ID}" -le 40 ]] || fatal "run-id must be <= 40 characters"
[[ -n "${KUBECONFIG_PATH}" ]] || fatal "KUBECONFIG is required; pass --kubeconfig or set KUBECONFIG"
[[ -f "${KUBECONFIG_PATH}" ]] || fatal "kubeconfig does not exist: ${KUBECONFIG_PATH}"
command -v kubectl >/dev/null 2>&1 || fatal "kubectl not found in PATH"

export KUBECONFIG="${KUBECONFIG_PATH}"
readonly KUBECTL=(kubectl --kubeconfig "${KUBECONFIG_PATH}" --context "${CONTEXT}")
readonly KUBECTL_NS=(kubectl --kubeconfig "${KUBECONFIG_PATH}" --context "${CONTEXT}" --namespace "${NAMESPACE}")
readonly NAME="kdf-smoke-${RUN_ID}"
readonly SELECTOR="app.kubernetes.io/part-of=${APP_LABEL},kdf.delivery/run-id=${RUN_ID}"

current_context="$(${KUBECTL[0]} --kubeconfig "${KUBECONFIG_PATH}" config current-context 2>/dev/null || true)"
[[ "${current_context}" == "${ALLOWED_CONTEXT}" ]] || fatal "current kube context is '${current_context:-<unset>}'; switch to '${ALLOWED_CONTEXT}' before running"

api_host="$(${KUBECTL[@]} config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
[[ -n "${api_host}" ]] || fatal "could not resolve API server for context '${CONTEXT}'"
if [[ "${api_host}" != https://127.0.0.1:* && "${api_host}" != https://localhost:* ]]; then
  fatal "refusing non-local API server for local Kind smoke context (server must be localhost/127.0.0.1)"
fi

"${KUBECTL[@]}" get namespace "${NAMESPACE}" >/dev/null

if [[ -z "${EVIDENCE_DIR}" ]]; then
  EVIDENCE_DIR="$(mktemp -d "/tmp/kdf-smoke-${RUN_ID}.XXXXXX")"
else
  mkdir -p "${EVIDENCE_DIR}"
fi

manifest() {
  cat <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: kdf-smoke
    app.kubernetes.io/part-of: ${APP_LABEL}
    app.kubernetes.io/managed-by: kdf-smoke-harness
    kdf.delivery/run-id: "${RUN_ID}"
data:
  message: "kdf-smoke-harness-public-safe-probe"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: kdf-smoke
    app.kubernetes.io/part-of: ${APP_LABEL}
    app.kubernetes.io/managed-by: kdf-smoke-harness
    kdf.delivery/run-id: "${RUN_ID}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: kdf-smoke
      app.kubernetes.io/part-of: ${APP_LABEL}
      kdf.delivery/run-id: "${RUN_ID}"
  template:
    metadata:
      labels:
        app.kubernetes.io/name: kdf-smoke
        app.kubernetes.io/part-of: ${APP_LABEL}
        app.kubernetes.io/managed-by: kdf-smoke-harness
        kdf.delivery/run-id: "${RUN_ID}"
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 5
      containers:
        - name: web
          image: ${IMAGE}
          imagePullPolicy: IfNotPresent
          args: ["netexec", "--http-port=8080"]
          ports:
            - containerPort: 8080
              name: http
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 2
            failureThreshold: 15
          livenessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
            failureThreshold: 3
          resources:
            requests:
              cpu: 10m
              memory: 32Mi
            limits:
              cpu: 100m
              memory: 64Mi
---
apiVersion: v1
kind: Service
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: kdf-smoke
    app.kubernetes.io/part-of: ${APP_LABEL}
    app.kubernetes.io/managed-by: kdf-smoke-harness
    kdf.delivery/run-id: "${RUN_ID}"
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: kdf-smoke
    app.kubernetes.io/part-of: ${APP_LABEL}
    kdf.delivery/run-id: "${RUN_ID}"
  ports:
    - name: http
      port: 80
      targetPort: http
YAML
}

capture() {
  local phase="$1"
  log "capturing ${phase} evidence in ${EVIDENCE_DIR}"
  "${KUBECTL[@]}" get nodes -o custom-columns=NAME:.metadata.name,CPU_CAPACITY:.status.capacity.cpu,MEM_CAPACITY:.status.capacity.memory,CPU_ALLOCATABLE:.status.allocatable.cpu,MEM_ALLOCATABLE:.status.allocatable.memory >"${EVIDENCE_DIR}/${phase}-nodes.txt"
  "${KUBECTL_NS[@]}" get deploy,po,svc,cm,pvc,sa --show-labels >"${EVIDENCE_DIR}/${phase}-namespace-resources.txt" 2>&1 || true
  "${KUBECTL_NS[@]}" get events --sort-by=.lastTimestamp >"${EVIDENCE_DIR}/${phase}-events.txt" 2>&1 || true
}

printf 'mode=%s\ncontext=%s\nnamespace=%s\nrun_id=%s\nevidence_dir=%s\n' "${MODE}" "${CONTEXT}" "${NAMESPACE}" "${RUN_ID}" "${EVIDENCE_DIR}" >"${EVIDENCE_DIR}/run-metadata.txt"
manifest >"${EVIDENCE_DIR}/manifest.yaml"

if [[ "${MODE}" == "plan" ]]; then
  log "plan mode: target checks passed; manifest written to ${EVIDENCE_DIR}/manifest.yaml"
  printf '%s\n' '--- planned manifest ---'
  manifest
  exit 0
fi

cleanup() {
  local status=$?
  log "cleaning up labelled resources for run ${RUN_ID}"
  manifest | "${KUBECTL_NS[@]}" delete -f - --ignore-not-found=true --wait=true --timeout=60s >"${EVIDENCE_DIR}/cleanup-delete.txt" 2>&1 || true
  "${KUBECTL_NS[@]}" get deploy,po,svc,cm -l "${SELECTOR}" >"${EVIDENCE_DIR}/cleanup-proof.txt" 2>&1 || true
  if grep -q "No resources found" "${EVIDENCE_DIR}/cleanup-proof.txt"; then
    log "cleanup verified: no labelled resources remain"
  else
    log "cleanup proof needs review: ${EVIDENCE_DIR}/cleanup-proof.txt"
  fi
  exit "${status}"
}
trap cleanup EXIT

capture before
log "applying resource-limited smoke manifest"
manifest | "${KUBECTL_NS[@]}" apply -f - >"${EVIDENCE_DIR}/apply.txt"
log "waiting for deployment/${NAME} to become available"
"${KUBECTL_NS[@]}" rollout status "deployment/${NAME}" --timeout="${TIMEOUT}" >"${EVIDENCE_DIR}/rollout-status.txt"
"${KUBECTL_NS[@]}" wait --for=condition=Available "deployment/${NAME}" --timeout="${TIMEOUT}" >"${EVIDENCE_DIR}/wait-available.txt"
"${KUBECTL_NS[@]}" get deploy,po,svc,cm -l "${SELECTOR}" -o wide >"${EVIDENCE_DIR}/smoke-status.txt"
"${KUBECTL_NS[@]}" describe deployment "${NAME}" >"${EVIDENCE_DIR}/deployment-describe.txt"
"${KUBECTL_NS[@]}" logs -l "${SELECTOR}" --all-containers=true --tail=100 >"${EVIDENCE_DIR}/pod-logs.txt" 2>&1 || true
capture after
log "run complete; evidence in ${EVIDENCE_DIR}"
