#!/usr/bin/env sh
set -eu

root="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
repo="$(CDPATH='' cd -- "$root/../../.." && pwd)"
output_dir="$(mktemp -d)"

python3 -m unittest discover -s "$root/tests" -v
python3 "$root/orchestrator.py" run \
  --alert-file "$root/fixtures/crashloop-alert.json" \
  --registry "$root/fixtures/approved-targets.json" \
  --lifecycle-module "$root/../finding-lifecycle/lifecycle.py" \
  --run-id offline-selective-smoke \
  --mode fixture \
  --output-dir "$output_dir"
test "$(cat "$output_dir/status.txt")" = "VALIDATED_REPORT"
kubectl kustomize "$root" | grep -Fq 'kind: WorkflowTemplate'
if kubectl kustomize "$root" | grep -Fq 'kind: Deployment'; then
  echo "selective orchestrator must not add an always-on Deployment" >&2
  exit 1
fi
sensor_ref="$(kubectl create --dry-run=client \
  -f "$root/../sensors/alertmanager-to-fanout-sensor.yaml" \
  -o jsonpath='{.spec.triggers[0].template.k8s.source.resource.spec.workflowTemplateRef.name}')"
test "$sensor_ref" = "smart-triage-selective-orchestrator"
"$repo/scripts/public-safe-scan.sh" "$root"

echo "SMART_TRIAGE_SELECTIVE_ORCHESTRATOR_VERIFY_OK"
