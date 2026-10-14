#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
: "${PROOF_KUBECONFIG:?Set the dedicated proof kubeconfig}"
: "${PROOF_TARGET:?Set a receipt label such as work}"
: "${PROOF_SUBSTRATE_VALUES:=$root/substrate-values.yaml}"
mkdir -p "$root/receipts/$PROOF_TARGET"
exec > >(tee "$root/receipts/$PROOF_TARGET/install-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
cd "$root/substrate-source"
kubectl --kubeconfig "$PROOF_KUBECONFIG" get --raw=/version
kubectl --kubeconfig "$PROOF_KUBECONFIG" api-resources --api-group=certificates.k8s.io
kubectl --kubeconfig "$PROOF_KUBECONFIG" create namespace ate-system --dry-run=client -o yaml | kubectl --kubeconfig "$PROOF_KUBECONFIG" apply -f -
helm upgrade --install substrate-crds "$root/artifacts/substrate-crds-0.4.0-alpha1.tgz" \
  --kubeconfig "$PROOF_KUBECONFIG" -n ate-system
for resource in jwt-authority-pool actor-id-ca-pool actor-id-ca-certs egress-mitm-ca-pool podcertificate-controller-cas api-authentication-config; do
  "$root/bin/ate-setup" --kubeconfig "$PROOF_KUBECONFIG" --no-dev-env create "$resource"
done
kubectl --kubeconfig "$PROOF_KUBECONFIG" label namespace podcertificate-controller-system app.kubernetes.io/managed-by=Helm --overwrite
kubectl --kubeconfig "$PROOF_KUBECONFIG" annotate namespace podcertificate-controller-system meta.helm.sh/release-name=substrate meta.helm.sh/release-namespace=ate-system --overwrite
helm upgrade --install substrate "$root/artifacts/substrate-0.4.0-alpha1.tgz" \
  --kubeconfig "$PROOF_KUBECONFIG" -n ate-system -f "$PROOF_SUBSTRATE_VALUES" --post-renderer "$root/pin-images.py" \
  --wait --timeout 10m
kubectl --kubeconfig "$PROOF_KUBECONFIG" -n ate-system get pods
kubectl --kubeconfig "$PROOF_KUBECONFIG" get nodes -o json > "$root/receipts/$PROOF_TARGET/nodes.json"
kubectl --kubeconfig "$PROOF_KUBECONFIG" get pods -A -o json > "$root/receipts/$PROOF_TARGET/pods-installed.json"
kubectl --kubeconfig "$PROOF_KUBECONFIG" get sandboxconfigs -o json > "$root/receipts/$PROOF_TARGET/sandboxconfigs.json"
echo "STOCK_SUBSTRATE_INSTALL=PASS"
