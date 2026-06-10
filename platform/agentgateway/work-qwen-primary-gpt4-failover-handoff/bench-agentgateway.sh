#!/usr/bin/env bash
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-}"
NAMESPACE="${AGENTGATEWAY_NAMESPACE:-agentgateway-system}"
SERVICE="${AGENTGATEWAY_SERVICE:-ai-gateway}"
SERVICE_PORT="${AGENTGATEWAY_SERVICE_PORT:-80}"
LOCAL_PORT="${LOCAL_PORT:-18080}"
AGENTGATEWAY_BASE_URL="${AGENTGATEWAY_BASE_URL:-}"
POLICY="${FAILOVER_POLICY:-work-llm-failover-policy}"
TOTAL="${TOTAL:-25}"
CONCURRENCY="${CONCURRENCY:-5}"
MODEL="${MODEL:-qwen-bench}"
PROMPT="${PROMPT:-reply with exactly: ok}"
MAX_TOKENS="${MAX_TOKENS:-20}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
mkdir -p "${OUT_DIR}"

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

if [[ -z "${AGENTGATEWAY_BASE_URL}" ]]; then
  kc port-forward -n "${NAMESPACE}" "svc/${SERVICE}" "${LOCAL_PORT}:${SERVICE_PORT}" >/tmp/work-llm-bench-portforward.log 2>&1 &
  PF_PID=$!
  sleep 2
  AGENTGATEWAY_BASE_URL="http://127.0.0.1:${LOCAL_PORT}"
fi
CHAT_COMPLETIONS_URL="${AGENTGATEWAY_BASE_URL%/}/llm/v1/chat/completions"

if [[ -z "${AGENTGATEWAY_BASE_URL:-}" || "${AGENTGATEWAY_BASE_URL}" == http://127.0.0.1:* ]] && command -v jq >/dev/null 2>&1; then
  LIMITS="$(kc get agentgatewaypolicy "${POLICY}" -n "${NAMESPACE}" -o json 2>/dev/null | jq -c '.spec.traffic.rateLimit.local // []' || true)"
  if [[ -n "${LIMITS}" && "${LIMITS}" != "[]" ]]; then
    echo "gateway_local_rate_limit=${LIMITS}"
    echo "note: HTTP 429s during this bench may be gateway-local, not only upstream model quota."
  fi
fi

run_one() {
  local i="$1"
  local body="${OUT_DIR}/${i}.body"
  local meta="${OUT_DIR}/${i}.meta"
  curl -sS -o "${body}" \
    -w "${i} %{http_code} %{time_total}\n" \
    -X POST "${CHAT_COMPLETIONS_URL}" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"${PROMPT}\"}],\"max_tokens\":${MAX_TOKENS}}" \
    >"${meta}" || echo "${i} 000 0" >"${meta}"
}
export -f run_one
export OUT_DIR CHAT_COMPLETIONS_URL MODEL PROMPT MAX_TOKENS

seq 1 "${TOTAL}" | xargs -n1 -P "${CONCURRENCY}" bash -c 'run_one "$0"'

cat "${OUT_DIR}"/*.meta | sort -n >"${OUT_DIR}/summary.tsv"
cat "${OUT_DIR}/summary.tsv"

python3 - "${OUT_DIR}/summary.tsv" <<'PY'
import json
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
summary = {
    "total": len(rows),
    "status_counts": dict(sorted(counts.items())),
    "success_count": counts.get("200", 0),
    "success_rate": counts.get("200", 0) / len(rows) if rows else 0,
}
if times:
    summary.update({
        "min_seconds": min(times),
        "p50_seconds": statistics.median(times),
        "p95_seconds": pct(times, 95),
        "max_seconds": max(times),
    })
    print(f"min={summary['min_seconds']:.3f}s p50={summary['p50_seconds']:.3f}s p95={summary['p95_seconds']:.3f}s max={summary['max_seconds']:.3f}s")
out_dir = sys.argv[1].rsplit("/", 1)[0]
with open(f"{out_dir}/summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, sort_keys=True)
print(f"output_dir={out_dir}")
print(f"summary_json={out_dir}/summary.json")
PY
