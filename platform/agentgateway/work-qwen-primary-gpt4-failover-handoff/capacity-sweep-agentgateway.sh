#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULT_ROOT="${RESULT_ROOT:-$(mktemp -d)}"
CONCURRENCY_LEVELS="${CONCURRENCY_LEVELS:-1 2 4 8 12 16 24 32}"
REQUESTS_PER_LEVEL="${REQUESTS_PER_LEVEL:-40}"
STOP_ON_FAILURE="${STOP_ON_FAILURE:-true}"
MODEL="${MODEL:-qwen-capacity-sweep}"
MAX_TOKENS="${MAX_TOKENS:-20}"
PROMPT="${PROMPT:-reply with exactly: ok}"
MIN_SUCCESS_RATE="${MIN_SUCCESS_RATE:-0.99}"
MAX_P95_SECONDS="${MAX_P95_SECONDS:-90}"

mkdir -p "${RESULT_ROOT}"
CSV="${RESULT_ROOT}/capacity-sweep.csv"
printf 'concurrency,total,success_rate,p95_seconds,status_counts,output_dir\n' >"${CSV}"

echo "result_root=${RESULT_ROOT}"
echo "levels=${CONCURRENCY_LEVELS}"
echo "requests_per_level=${REQUESTS_PER_LEVEL}"
echo "pass_thresholds=min_success_rate:${MIN_SUCCESS_RATE},max_p95_seconds:${MAX_P95_SECONDS}"

for concurrency in ${CONCURRENCY_LEVELS}; do
  run_dir="${RESULT_ROOT}/c${concurrency}"
  mkdir -p "${run_dir}"
  echo
  echo "== concurrency=${concurrency} =="
  TOTAL="${REQUESTS_PER_LEVEL}" \
    CONCURRENCY="${concurrency}" \
    MODEL="${MODEL}" \
    MAX_TOKENS="${MAX_TOKENS}" \
    PROMPT="${PROMPT}" \
    OUT_DIR="${run_dir}" \
    "${DIR}/bench-agentgateway.sh" | tee "${run_dir}/bench.log"

  if ! python3 - "${run_dir}/summary.json" "${CSV}" "${concurrency}" "${MIN_SUCCESS_RATE}" "${MAX_P95_SECONDS}" <<'PY'
import csv
import json
import sys

summary_path, csv_path, concurrency, min_success_rate, max_p95 = sys.argv[1:]
summary = json.load(open(summary_path, encoding="utf-8"))
status_counts = ",".join(f"{k}:{v}" for k, v in sorted(summary["status_counts"].items()))
row = {
    "concurrency": concurrency,
    "total": summary["total"],
    "success_rate": f"{summary['success_rate']:.4f}",
    "p95_seconds": f"{summary.get('p95_seconds', 0):.3f}",
    "status_counts": status_counts,
    "output_dir": summary_path.rsplit("/", 1)[0],
}
with open(csv_path, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=row.keys())
    writer.writerow(row)

passed = (
    summary["success_rate"] >= float(min_success_rate)
    and summary.get("p95_seconds", 0) <= float(max_p95)
    and not any(k in summary["status_counts"] for k in ("000", "429", "500", "502", "503", "504"))
)
print("level_result=" + ("pass" if passed else "fail"))
if not passed:
    raise SystemExit(3)
PY
  then
    echo "concurrency ${concurrency} crossed the configured capacity threshold"
    if [[ "${STOP_ON_FAILURE}" == "true" ]]; then
      break
    fi
  fi
done

echo
echo "capacity_sweep_csv=${CSV}"
cat "${CSV}"
