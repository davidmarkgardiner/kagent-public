#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULT_ROOT="${RESULT_ROOT:-$(mktemp -d)}"
CONCURRENCY_LEVELS="${CONCURRENCY_LEVELS:-1 2 4 8 12 16 20}"
REQUESTS_PER_LEVEL="${REQUESTS_PER_LEVEL:-40}"
STOP_ON_FAILURE="${STOP_ON_FAILURE:-true}"
AGENT_NAME="${AGENT_NAME:-k8s-agent}"
PROMPT="${PROMPT:-reply with exactly: ok}"
CURL_TIMEOUT="${CURL_TIMEOUT:-300}"
MIN_COMPLETED_RATE="${MIN_COMPLETED_RATE:-0.99}"
MAX_P95_SECONDS="${MAX_P95_SECONDS:-180}"

mkdir -p "${RESULT_ROOT}"
CSV="${RESULT_ROOT}/kagent-capacity-sweep.csv"
printf 'concurrency,total,completed_rate,p95_seconds,status_counts,state_counts,output_dir\n' >"${CSV}"

echo "result_root=${RESULT_ROOT}"
echo "agent=${AGENT_NAME}"
echo "levels=${CONCURRENCY_LEVELS}"
echo "requests_per_level=${REQUESTS_PER_LEVEL}"
echo "pass_thresholds=min_completed_rate:${MIN_COMPLETED_RATE},max_p95_seconds:${MAX_P95_SECONDS}"

for concurrency in ${CONCURRENCY_LEVELS}; do
  run_dir="${RESULT_ROOT}/c${concurrency}"
  mkdir -p "${run_dir}"
  echo
  echo "== kagent concurrency=${concurrency} =="
  TOTAL="${REQUESTS_PER_LEVEL}" \
    CONCURRENCY="${concurrency}" \
    AGENT_NAME="${AGENT_NAME}" \
    PROMPT="${PROMPT}" \
    CURL_TIMEOUT="${CURL_TIMEOUT}" \
    OUT_DIR="${run_dir}" \
    "${DIR}/bench-kagent-a2a.sh" | tee "${run_dir}/bench.log"

  if ! python3 - "${run_dir}/summary.json" "${CSV}" "${concurrency}" "${MIN_COMPLETED_RATE}" "${MAX_P95_SECONDS}" <<'PY'
import csv
import json
import sys

summary_path, csv_path, concurrency, min_completed_rate, max_p95 = sys.argv[1:]
summary = json.load(open(summary_path, encoding="utf-8"))
status_counts = ",".join(f"{k}:{v}" for k, v in sorted(summary["status_counts"].items()))
state_counts = ",".join(f"{k}:{v}" for k, v in sorted(summary["state_counts"].items()))
row = {
    "concurrency": concurrency,
    "total": summary["total"],
    "completed_rate": f"{summary['completed_rate']:.4f}",
    "p95_seconds": f"{summary.get('p95_seconds', 0):.3f}",
    "status_counts": status_counts,
    "state_counts": state_counts,
    "output_dir": summary_path.rsplit("/", 1)[0],
}
with open(csv_path, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=row.keys())
    writer.writerow(row)

passed = (
    summary["completed_rate"] >= float(min_completed_rate)
    and summary.get("p95_seconds", 0) <= float(max_p95)
    and not any(k in summary["status_counts"] for k in ("000", "429", "500", "502", "503", "504"))
    and not any(k in summary["state_counts"] for k in ("failed", "input-required", "missing", "parse_error", "transport_error"))
)
print("level_result=" + ("pass" if passed else "fail"))
if not passed:
    raise SystemExit(3)
PY
  then
    echo "kagent concurrency ${concurrency} crossed the configured capacity threshold"
    if [[ "${STOP_ON_FAILURE}" == "true" ]]; then
      break
    fi
  fi
done

echo
echo "kagent_capacity_sweep_csv=${CSV}"
cat "${CSV}"
