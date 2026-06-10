#!/usr/bin/env bash
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-}"
NAMESPACE="${KAGENT_NAMESPACE:-kagent}"
SERVICE="${KAGENT_SERVICE:-kagent-controller}"
SERVICE_PORT="${KAGENT_SERVICE_PORT:-8083}"
LOCAL_PORT="${LOCAL_PORT:-18083}"
KAGENT_BASE_URL="${KAGENT_BASE_URL:-}"
AGENT_NAME="${AGENT_NAME:-k8s-agent}"
AGENT_NAMESPACE="${AGENT_NAMESPACE:-${NAMESPACE}}"
TOTAL="${TOTAL:-20}"
CONCURRENCY="${CONCURRENCY:-20}"
PROMPT="${PROMPT:-reply with exactly: ok}"
CURL_TIMEOUT="${CURL_TIMEOUT:-300}"
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

if [[ -z "${KAGENT_BASE_URL}" ]]; then
  kc port-forward -n "${NAMESPACE}" "svc/${SERVICE}" "${LOCAL_PORT}:${SERVICE_PORT}" >/tmp/work-kagent-a2a-bench-portforward.log 2>&1 &
  PF_PID=$!
  sleep 2
  KAGENT_BASE_URL="http://127.0.0.1:${LOCAL_PORT}"
fi
A2A_URL="${KAGENT_BASE_URL%/}/api/a2a/${AGENT_NAMESPACE}/${AGENT_NAME}/"

run_one() {
  local i="$1"
  local body="${OUT_DIR}/${i}.body"
  local meta="${OUT_DIR}/${i}.meta"
  local state_file="${OUT_DIR}/${i}.state"
  local text_file="${OUT_DIR}/${i}.text"
  local payload
  payload="$(
    jq -nc \
      --arg id "bench-${i}" \
      --arg message_id "bench-msg-${i}" \
      --arg text "${PROMPT}" \
      '{
        jsonrpc:"2.0",
        id:$id,
        method:"message/send",
        params:{
          message:{
            messageId:$message_id,
            role:"user",
            parts:[{kind:"text",text:$text}]
          }
        }
      }'
  )"

  if curl -sS -m "${CURL_TIMEOUT}" -o "${body}" \
    -w "${i} %{http_code} %{time_total}\n" \
    -X POST "${A2A_URL}" \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    >"${meta}"; then
    jq -r '.result.status.state // "missing"' "${body}" >"${state_file}" 2>/dev/null || echo "parse_error" >"${state_file}"
    jq -r 'if (.result.artifacts // [] | length) > 0 then [.result.artifacts[]?.parts[]?.text] | join("\n") elif (.result.status.message.parts // [] | length) > 0 then [.result.status.message.parts[]?.text] | join("\n") else "" end' "${body}" >"${text_file}" 2>/dev/null || true
  else
    echo "${i} 000 0" >"${meta}"
    echo "transport_error" >"${state_file}"
    : >"${text_file}"
  fi
}
export -f run_one
export OUT_DIR A2A_URL PROMPT CURL_TIMEOUT

seq 1 "${TOTAL}" | xargs -n1 -P "${CONCURRENCY}" bash -c 'run_one "$0"'

cat "${OUT_DIR}"/*.meta | sort -n >"${OUT_DIR}/summary.tsv"
cat "${OUT_DIR}/summary.tsv"

python3 - "${OUT_DIR}/summary.tsv" "${OUT_DIR}" <<'PY'
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

rows = []
for line in open(sys.argv[1], encoding="utf-8"):
    idx, status, elapsed = line.split()
    rows.append((int(idx), status, float(elapsed)))

out_dir = Path(sys.argv[2])
counts = Counter(status for _, status, _ in rows)
states = Counter()
for idx, _, _ in rows:
    state_path = out_dir / f"{idx}.state"
    state = state_path.read_text(encoding="utf-8").strip() if state_path.exists() else "missing"
    states[state or "empty"] += 1

times = sorted(t for _, status, t in rows if status != "000")

def pct(values, p):
    if not values:
        return 0.0
    k = max(0, min(len(values) - 1, round((p / 100) * (len(values) - 1))))
    return values[k]

print("\nsummary")
print(f"total={len(rows)}")
print("status_counts=" + ",".join(f"{k}:{v}" for k, v in sorted(counts.items())))
print("state_counts=" + ",".join(f"{k}:{v}" for k, v in sorted(states.items())))
summary = {
    "total": len(rows),
    "status_counts": dict(sorted(counts.items())),
    "state_counts": dict(sorted(states.items())),
    "http_success_count": counts.get("200", 0),
    "completed_count": states.get("completed", 0),
    "completed_rate": states.get("completed", 0) / len(rows) if rows else 0,
}
if times:
    summary.update({
        "min_seconds": min(times),
        "p50_seconds": statistics.median(times),
        "p95_seconds": pct(times, 95),
        "max_seconds": max(times),
    })
    print(f"min={summary['min_seconds']:.3f}s p50={summary['p50_seconds']:.3f}s p95={summary['p95_seconds']:.3f}s max={summary['max_seconds']:.3f}s")
with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, sort_keys=True)
print(f"output_dir={out_dir}")
print(f"summary_json={out_dir}/summary.json")
PY
