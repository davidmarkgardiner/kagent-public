#!/usr/bin/env bash
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-}"
NAMESPACE="${KAGENT_NAMESPACE:-kagent}"
SERVICE="${KAGENT_SERVICE:-kagent-controller}"
SERVICE_PORT="${KAGENT_SERVICE_PORT:-8083}"
LOCAL_PORT="${LOCAL_PORT:-18083}"
AGENT_NAME="${AGENT_NAME:-k8s-agent}"
TOTAL="${TOTAL:-10}"
CONCURRENCY="${CONCURRENCY:-2}"
PROMPT="${PROMPT:-reply with exactly: ok}"
OUT_DIR="$(mktemp -d)"

kc() {
  if [[ -n "${CONTEXT}" ]]; then
    kubectl --context "${CONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}

cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then
    kill "${PF_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

kc port-forward -n "${NAMESPACE}" "svc/${SERVICE}" "${LOCAL_PORT}:${SERVICE_PORT}" >/tmp/work-kagent-a2a-bench-portforward.log 2>&1 &
PF_PID=$!
sleep 2

run_one() {
  local i="$1"
  local body="${OUT_DIR}/${i}.body"
  local meta="${OUT_DIR}/${i}.meta"
  local payload
  payload="$(printf '{"jsonrpc":"2.0","id":"bench-%s","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"%s"}]}}}' "${i}" "${PROMPT}")"

  curl -sS -o "${body}" \
    -w "${i} %{http_code} %{time_total}\n" \
    -X POST "http://127.0.0.1:${LOCAL_PORT}/api/a2a/kagent/${AGENT_NAME}/" \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    >"${meta}" || echo "${i} 000 0" >"${meta}"
}
export -f run_one
export OUT_DIR LOCAL_PORT AGENT_NAME PROMPT

seq 1 "${TOTAL}" | xargs -n1 -P "${CONCURRENCY}" bash -c 'run_one "$0"'

cat "${OUT_DIR}"/*.meta | sort -n >"${OUT_DIR}/summary.tsv"
cat "${OUT_DIR}/summary.tsv"

python3 - "${OUT_DIR}/summary.tsv" <<'PY'
import statistics
import sys
from collections import Counter

rows = []
for line in open(sys.argv[1], encoding="utf-8"):
    idx, status, elapsed = line.split()
    rows.append((int(idx), status, float(elapsed)))

counts = Counter(status for _, status, _ in rows)
times = sorted(t for _, status, t in rows if status != "000")

def pct(values, p):
    if not values:
        return 0.0
    k = max(0, min(len(values) - 1, round((p / 100) * (len(values) - 1))))
    return values[k]

print("\nsummary")
print(f"total={len(rows)}")
print("status_counts=" + ",".join(f"{k}:{v}" for k, v in sorted(counts.items())))
if times:
    print(f"min={min(times):.3f}s p50={statistics.median(times):.3f}s p95={pct(times,95):.3f}s max={max(times):.3f}s")
print(f"output_dir={sys.argv[1].rsplit('/', 1)[0]}")
PY
