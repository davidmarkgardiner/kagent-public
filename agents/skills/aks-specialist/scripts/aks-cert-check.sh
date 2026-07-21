#!/usr/bin/env bash
# aks-cert-check.sh — full cluster certification health check.
#
# The runnable version of the "Full Cluster Certification" block that was
# previously narrated inline in ../SKILL.md (and had to be retyped each run).
#
# Usage: aks-cert-check.sh [--context CTX] [--json]
#
# Exit codes: 0 all sections ran and no problems detected; 1 problems detected
# (problem pods, unbound PVCs); 3 cluster unreachable; 2 usage error.
set -euo pipefail

CONTEXT=""
JSON_OUT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="$2"; shift 2 ;;
    --json)    JSON_OUT=1; shift ;;
    -h|--help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "aks-cert-check.sh: unknown option: $1" >&2; exit 2 ;;
  esac
done

command -v kubectl >/dev/null 2>&1 || { echo "aks-cert-check.sh: kubectl is required" >&2; exit 2; }
KUBECTL=(kubectl)
[[ -n "$CONTEXT" ]] && KUBECTL=(kubectl --context "$CONTEXT")

section() { [[ "$JSON_OUT" -eq 0 ]] && echo "=== $1 ===" || true; }
run() { [[ "$JSON_OUT" -eq 0 ]] && { "$@" || true; } || { "$@" >/dev/null 2>&1 || true; } }

if ! "${KUBECTL[@]}" cluster-info >/dev/null 2>&1; then
  echo "aks-cert-check.sh: API server unreachable${CONTEXT:+ (context $CONTEXT)}" >&2
  exit 3
fi

section "API Server"
run "${KUBECTL[@]}" cluster-info

section "Nodes"
run "${KUBECTL[@]}" get nodes
run "${KUBECTL[@]}" top nodes

section "System Pods (not Running)"
SYSTEM_NOT_RUNNING=$("${KUBECTL[@]}" get pods -n kube-system --no-headers 2>/dev/null | grep -cv 'Running\|Completed' || true)
[[ "$JSON_OUT" -eq 0 ]] && { "${KUBECTL[@]}" get pods -n kube-system | grep -v 'Running\|Completed' || echo "(none)"; }

section "Problem Pods"
PROBLEM_PODS=$("${KUBECTL[@]}" get pods -A --no-headers 2>/dev/null | grep -cE 'CrashLoop|Error|Pending|ImagePull' || true)
[[ "$JSON_OUT" -eq 0 ]] && { "${KUBECTL[@]}" get pods -A | grep -E 'CrashLoop|Error|Pending|ImagePull' || echo "(none)"; }

section "Recent Events"
[[ "$JSON_OUT" -eq 0 ]] && { "${KUBECTL[@]}" get events -A --sort-by='.lastTimestamp' 2>/dev/null | tail -20 || true; }

section "PVC Status (not Bound)"
UNBOUND_PVCS=$("${KUBECTL[@]}" get pvc -A --no-headers 2>/dev/null | grep -cv Bound || true)
[[ "$JSON_OUT" -eq 0 ]] && { "${KUBECTL[@]}" get pvc -A | grep -v Bound || echo "(none)"; }

section "Resource Quotas"
[[ "$JSON_OUT" -eq 0 ]] && { "${KUBECTL[@]}" describe resourcequotas -A 2>/dev/null | grep -A5 "Used" || echo "(none)"; }

TOTAL_PROBLEMS=$((SYSTEM_NOT_RUNNING + PROBLEM_PODS + UNBOUND_PVCS))
if [[ "$JSON_OUT" -eq 1 ]]; then
  printf '{"reachable":true,"system_pods_not_running":%d,"problem_pods":%d,"unbound_pvcs":%d,"problems":%d}\n' \
    "$SYSTEM_NOT_RUNNING" "$PROBLEM_PODS" "$UNBOUND_PVCS" "$TOTAL_PROBLEMS"
else
  echo "=== Summary ==="
  echo "system pods not running: $SYSTEM_NOT_RUNNING, problem pods: $PROBLEM_PODS, unbound PVCs: $UNBOUND_PVCS"
fi

[[ "$TOTAL_PROBLEMS" -eq 0 ]] && exit 0 || exit 1
