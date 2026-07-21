#!/usr/bin/env bash
# select-clusters.sh — deterministic, auditable fleet selection.
#
# Implements the fleet-selector rules (../SKILL.md) as code so a selection is
# reproducible from its recorded seed instead of being re-derived as prose:
#   - reject production
#   - cap the requested count
#   - select only clusters labelled reliability.platform/chaos-optin="true"
#   - exclude clusters in blackout/incident/release/quiet windows
#   - emit the exact output contract block, dry-run unless approved
#
# Usage:
#   select-clusters.sh --tier dev|test|staging --count N --inventory FILE
#                      [--seed S] [--labels k=v[,k=v...]] [--blackout-file F]
#                      [--max N] [--approval REF]
#
#   --inventory FILE  JSON list of clusters:
#                     [{"name":"c1","tier":"dev","labels":{"reliability.platform/chaos-optin":"true"},
#                       "windows":[]}, ...]
#   --blackout-file F Optional file with one cluster name per line currently in
#                     a blackout window (merged with each cluster's "windows")
#   --max N           Selection cap (default: $MAX_SELECTED_CLUSTERS or 5)
#   --approval REF    Approved GitOps/HITL reference; without it the output is
#                     a dry-run plan
#
# Exit codes: 0 selection recorded; 2 selection refused (contract STOP block
# printed); 1 usage error.
set -euo pipefail

TIER=""
COUNT=""
INVENTORY=""
SEED=""
LABELS=""
BLACKOUT_FILE=""
MAX="${MAX_SELECTED_CLUSTERS:-5}"
APPROVAL=""

usage() {
  sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier)          TIER="$2"; shift 2 ;;
    --count)         COUNT="$2"; shift 2 ;;
    --inventory)     INVENTORY="$2"; shift 2 ;;
    --seed)          SEED="$2"; shift 2 ;;
    --labels)        LABELS="$2"; shift 2 ;;
    --blackout-file) BLACKOUT_FILE="$2"; shift 2 ;;
    --max)           MAX="$2"; shift 2 ;;
    --approval)      APPROVAL="$2"; shift 2 ;;
    -h|--help)       usage 0 ;;
    *)               echo "select-clusters.sh: unknown option: $1" >&2; usage 1 >&2 ;;
  esac
done

if [[ -z "$TIER" || -z "$COUNT" || -z "$INVENTORY" ]]; then
  echo "select-clusters.sh: --tier, --count, and --inventory are required" >&2
  exit 1
fi
[[ -f "$INVENTORY" ]] || { echo "select-clusters.sh: inventory not found: $INVENTORY" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "select-clusters.sh: python3 is required" >&2; exit 1; }

BLACKOUT_ARG="${BLACKOUT_FILE:-/dev/null}"

python3 - "$TIER" "$COUNT" "$INVENTORY" "$SEED" "$LABELS" "$BLACKOUT_ARG" "$MAX" "$APPROVAL" <<'PY'
import json
import random
import sys

tier, count_s, inventory, seed, labels_s, blackout_file, max_s, approval = sys.argv[1:9]

def stop(reason):
    print("CLUSTER_SELECTION_RECORDED: no")
    print(f"STOP_REASON: {reason}")
    print("OUTPUT_SANITIZED: yes")
    sys.exit(2)

if tier not in ("dev", "test", "staging"):
    stop(f"tier '{tier}' refused — production and unknown tiers are rejected for v1")

try:
    count = int(count_s)
    cap = int(max_s)
except ValueError:
    stop("count and max must be integers")
if count < 1:
    stop("requested count must be >= 1")
if count > cap:
    stop(f"requested count {count} exceeds cap {cap}")

with open(inventory, encoding="utf-8") as handle:
    clusters = json.load(handle)
if not isinstance(clusters, list):
    stop("inventory must be a JSON list of cluster objects")

blackout = set()
with open(blackout_file, encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if line and not line.startswith("#"):
            blackout.add(line)

extra_labels = {}
if labels_s:
    for pair in labels_s.split(","):
        k, _, v = pair.partition("=")
        extra_labels[k.strip()] = v.strip()

pool = []
excluded = 0
window_kinds = {"blackout", "incident", "release", "quiet", "quiet-period"}
for cluster in clusters:
    name = cluster.get("name", "")
    labels = cluster.get("labels") or {}
    windows = {str(w).lower() for w in (cluster.get("windows") or [])}
    if cluster.get("tier") != tier:
        continue  # different tier — not part of the candidate pool
    if labels.get("reliability.platform/chaos-optin") != "true":
        excluded += 1
        continue
    if windows & window_kinds or name in blackout:
        excluded += 1
        continue
    if any(labels.get(k) != v for k, v in extra_labels.items()):
        excluded += 1
        continue
    pool.append(name)

if len(pool) < count:
    stop(f"candidate pool ({len(pool)}) smaller than requested count ({count})")

if seed:
    mode = "random"
    rng = random.Random(seed)
    selected = sorted(rng.sample(pool, count))
    reason = f"seed={seed}"
else:
    mode = "label-selector"
    selected = sorted(pool)[:count]
    reason = "deterministic first-N over sorted opt-in pool (pass --seed for a shuffled draw)"

print("CLUSTER_SELECTION_RECORDED: yes")
print(f"SELECTION_MODE: {mode}")
print(f"CANDIDATE_POOL: {len(pool)}")
print(f"EXCLUDED_CLUSTERS: {excluded}")
print(f"SELECTED_CLUSTERS: {', '.join(selected)}")
print(f"SELECTION_REASON: {reason}")
if approval:
    print(f"APPROVAL_REFERENCE: {approval}")
else:
    print("PLAN_ONLY: yes  # dry-run — supply --approval <GitOps/HITL ref> to record an approved selection")
print("OUTPUT_SANITIZED: yes")
PY
