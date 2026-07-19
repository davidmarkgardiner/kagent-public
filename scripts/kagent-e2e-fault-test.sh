#!/usr/bin/env bash
# kagent-e2e-fault-test.sh — safe end-to-end fault-injection test of the
# kagent triage pipeline.
#
# Encodes the order-critical sequence from
# agents/kagent-triage/SENSOR-SAFEGUARDS.md ("Deployment Sequence") verbatim:
#   1. Pre-check: no pre-existing fault pods in the target namespace and the
#      sensor idle for 30s (no new workflows appearing)
#   2. Inject the fault fixture
#   3. Watch for a new kagent-triage-* workflow and poll it to completion
#   4. ALWAYS delete the fixture — cleanup runs from an EXIT trap, so it
#      happens even on Ctrl-C or errors
#   5. Post-check: workflow count stable for 30s (no cascade)
#
# The 2026-03-16 sensor-cascade incident (SENSOR-SAFEGUARDS.md "Learned From")
# was a missed-cleanup + rate-limit gap; this script makes that failure mode
# structurally unrepeatable.
#
# Usage:
#   scripts/kagent-e2e-fault-test.sh --namespace NS [options]
#
# Options:
#   --namespace NS          Target namespace to inject into (required)
#   --fixture FILE          Fault manifest to apply (default: render
#                           agents/skills/kagent-namespace-agent/templates/test-error.yaml.tmpl)
#   --argo-ns NS            Namespace where triage workflows run (default: argo-events)
#   --workflow-timeout SECS Max seconds to wait for the workflow (default: 300)
#   --context CTX           kubectl context
#   --skip-precheck         Skip the pre-checks (refused unless --force)
#   --force                 Allow --skip-precheck
#   --keep                  Do NOT delete the fixture on exit (loud warning)
#   --json                  Print a JSON summary
#   -h, --help              Show this help
#
# Exit codes:
#   0  workflow triggered, succeeded, fixture cleaned, no cascade
#   2  pre-check failed (existing fault pods or sensor not idle)
#   3  no workflow fired within the timeout (sensor/filter problem)
#   4  workflow fired but failed (diagnosis problem — hand to the model)
#   5  cascade detected after cleanup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$REPO_ROOT/agents/skills/kagent-namespace-agent/templates/test-error.yaml.tmpl"

NAMESPACE=""
FIXTURE=""
ARGO_NS="argo-events"
WF_TIMEOUT="300"
CONTEXT=""
SKIP_PRECHECK=0
FORCE=0
KEEP=0
JSON_OUT=0

usage() {
  sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)        NAMESPACE="$2"; shift 2 ;;
    --fixture)          FIXTURE="$2"; shift 2 ;;
    --argo-ns)          ARGO_NS="$2"; shift 2 ;;
    --workflow-timeout) WF_TIMEOUT="$2"; shift 2 ;;
    --context)          CONTEXT="$2"; shift 2 ;;
    --skip-precheck)    SKIP_PRECHECK=1; shift ;;
    --force)            FORCE=1; shift ;;
    --keep)             KEEP=1; shift ;;
    --json)             JSON_OUT=1; shift ;;
    -h|--help)          usage 0 ;;
    *)                  echo "kagent-e2e-fault-test.sh: unknown option: $1" >&2; usage 1 >&2 ;;
  esac
done

if [[ -z "$NAMESPACE" ]]; then
  echo "kagent-e2e-fault-test.sh: --namespace is required" >&2
  exit 1
fi
if [[ "$SKIP_PRECHECK" -eq 1 && "$FORCE" -ne 1 ]]; then
  echo "kagent-e2e-fault-test.sh: --skip-precheck refused without --force." >&2
  echo "The pre-check exists because skipping it caused a real incident (SENSOR-SAFEGUARDS.md)." >&2
  exit 1
fi
if [[ -n "$FIXTURE" && ! -f "$FIXTURE" ]]; then
  echo "kagent-e2e-fault-test.sh: fixture not found: $FIXTURE" >&2
  exit 1
fi
command -v kubectl >/dev/null 2>&1 || { echo "kagent-e2e-fault-test.sh: kubectl is required" >&2; exit 1; }

KUBECTL=(kubectl)
[[ -n "$CONTEXT" ]] && KUBECTL=(kubectl --context "$CONTEXT")

WORK_DIR="$(mktemp -d)"
INJECTED=0
CLEANED=false

cleanup_fixture() {
  if [[ "$INJECTED" -eq 1 && "$KEEP" -ne 1 && "$CLEANED" != "true" ]]; then
    echo "CLEANUP deleting fault fixture from $NAMESPACE"
    "${KUBECTL[@]}" delete -f "$FIXTURE" --ignore-not-found=true --wait=false >/dev/null 2>&1 || true
    CLEANED=true
  fi
  rm -rf "$WORK_DIR"
}
trap cleanup_fixture EXIT

if [[ -z "$FIXTURE" ]]; then
  [[ -f "$TEMPLATE" ]] || { echo "kagent-e2e-fault-test.sh: default template missing: $TEMPLATE" >&2; exit 1; }
  FIXTURE="$WORK_DIR/${NAMESPACE}-test-error.yaml"
  sed -e "s|{{NAMESPACE}}|$NAMESPACE|g" "$TEMPLATE" > "$FIXTURE"
fi

workflow_names() {
  "${KUBECTL[@]}" get workflows -n "$ARGO_NS" -o name 2>/dev/null | sed 's|^workflow.argoproj.io/||' || true
}

workflow_count() {
  workflow_names | grep -c . || true
}

# ---- 1. Pre-check ----------------------------------------------------------
if [[ "$SKIP_PRECHECK" -ne 1 ]]; then
  EXISTING=$("${KUBECTL[@]}" get pods -n "$NAMESPACE" -l app=kagent-test --no-headers 2>/dev/null || true)
  if [[ -n "$EXISTING" ]]; then
    echo "PRECHECK fail — pre-existing fault pods in $NAMESPACE:" >&2
    echo "$EXISTING" >&2
    echo "Delete them first: kubectl delete pods,deployments -n $NAMESPACE -l app=kagent-test" >&2
    exit 2
  fi
  BEFORE_IDLE=$(workflow_count)
  echo "PRECHECK no fault pods; watching sensor for 30s (workflows: $BEFORE_IDLE)"
  sleep 30
  AFTER_IDLE=$(workflow_count)
  if [[ "$AFTER_IDLE" -gt "$BEFORE_IDLE" ]]; then
    echo "PRECHECK fail — sensor not idle ($BEFORE_IDLE -> $AFTER_IDLE workflows in 30s)" >&2
    exit 2
  fi
  echo "PRECHECK ok"
else
  echo "PRECHECK skipped (--skip-precheck --force)"
fi

# ---- 2. Inject -------------------------------------------------------------
BASELINE="$WORK_DIR/baseline.txt"
workflow_names > "$BASELINE"
"${KUBECTL[@]}" apply -f "$FIXTURE" >/dev/null
INJECTED=1
echo "INJECT applied $(basename "$FIXTURE") to $NAMESPACE"

# ---- 3. Watch for the workflow --------------------------------------------
WF_NAME=""
DEADLINE=$(( $(date +%s) + WF_TIMEOUT ))
while [[ $(date +%s) -lt $DEADLINE ]]; do
  WF_NAME=$(workflow_names | grep '^kagent-triage-' | grep -Fxv -f "$BASELINE" | head -1 || true)
  [[ -n "$WF_NAME" ]] && break
  sleep 5
done

if [[ -z "$WF_NAME" ]]; then
  echo "WORKFLOW none fired within ${WF_TIMEOUT}s — check the sensor and its filters" >&2
  cleanup_fixture
  exit 3
fi
echo "WORKFLOW $WF_NAME fired; waiting for completion"

PHASE=""
while [[ $(date +%s) -lt $DEADLINE ]]; do
  PHASE=$("${KUBECTL[@]}" get workflow "$WF_NAME" -n "$ARGO_NS" -o jsonpath='{.status.phase}' 2>/dev/null || true)
  case "$PHASE" in
    Succeeded|Failed|Error) break ;;
  esac
  sleep 5
done
echo "WORKFLOW $WF_NAME phase: ${PHASE:-timed-out}"

# ---- 4. Cleanup (always) ---------------------------------------------------
cleanup_fixture

# ---- 5. Post-check: no cascade --------------------------------------------
BEFORE_POST=$(workflow_count)
echo "POSTCHECK watching for cascade for 30s (workflows: $BEFORE_POST)"
sleep 30
AFTER_POST=$(workflow_count)
CASCADE=false
[[ "$AFTER_POST" -gt "$BEFORE_POST" ]] && CASCADE=true

echo "--- workflow log tail ---"
"${KUBECTL[@]}" logs -n "$ARGO_NS" -l "workflows.argoproj.io/workflow=$WF_NAME" --tail=20 2>/dev/null || echo "(no logs available)"
echo "-------------------------"

if [[ "$KEEP" -eq 1 ]]; then
  echo "⚠️  --keep set: fault fixture LEFT RUNNING in $NAMESPACE." >&2
  echo "⚠️  Delete it as soon as possible: kubectl delete -f $FIXTURE" >&2
fi

EXIT_CODE=0
if [[ "$CASCADE" == "true" ]]; then
  echo "POSTCHECK fail — workflow count still rising after cleanup ($BEFORE_POST -> $AFTER_POST): possible cascade" >&2
  EXIT_CODE=5
elif [[ "$PHASE" != "Succeeded" ]]; then
  EXIT_CODE=4
else
  echo "POSTCHECK ok — sensor idle"
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  command -v jq >/dev/null 2>&1 && jq -n \
    --arg ns "$NAMESPACE" --arg wf "$WF_NAME" --arg phase "${PHASE:-timed-out}" \
    --argjson cleaned "$( [[ "$KEEP" -eq 1 ]] && echo false || echo true )" \
    --argjson cascade "$CASCADE" --argjson code "$EXIT_CODE" \
    '{namespace:$ns, workflow:$wf, phase:$phase, cleaned:$cleaned, cascade:$cascade, exit_code:$code}'
fi

exit "$EXIT_CODE"
