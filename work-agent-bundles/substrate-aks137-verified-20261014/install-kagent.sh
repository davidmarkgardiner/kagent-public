#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
: "${PROOF_KUBECONFIG:?Set dedicated kubeconfig}"
: "${PROOF_TARGET:?Set home or aks}"
exec > >(tee "$root/receipts/$PROOF_TARGET/kagent-install-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
helm upgrade --install kagent-crds "$root/artifacts/kagent-crds-1.0.0-alpha8.tgz" \
  --kubeconfig "$PROOF_KUBECONFIG" -n kagent --create-namespace
helm upgrade --install kagent "$root/artifacts/kagent-1.0.0-alpha8.tgz" \
  --kubeconfig "$PROOF_KUBECONFIG" -n kagent -f "$root/kagent-values.yaml" \
  --post-renderer "$root/pin-images.py" --wait --timeout 10m
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n kagent get workerpools -o yaml > "$root/receipts/$PROOF_TARGET/workerpools.yaml"
echo "STOCK_KAGENT_INSTALL=PASS"
