#!/usr/bin/env bash
# Install Container Network Insights Agent on an AKS cluster.
# Edit the variables below, then run: ./install.sh
#
# Prereqs:
#   - az CLI logged in (`az login`)
#   - Correct subscription selected (`az account set --subscription <sub>`)
#   - AKS cluster in a supported region (centralus, eastus, eastus2, uksouth, westus2)

set -euo pipefail

# ─── EDIT THESE ─────────────────────────────────────────────────────────────
AKS_NAME="<your-aks-cluster>"
RESOURCE_GROUP="<your-resource-group>"
# ────────────────────────────────────────────────────────────────────────────

EXTENSION_NAME="container-networking-agent"
EXTENSION_TYPE="microsoft.containernetworkingagent"

echo "==> Verifying AKS cluster is in a supported region..."
LOCATION=$(az aks show --name "$AKS_NAME" --resource-group "$RESOURCE_GROUP" \
  --query location -o tsv)
case "$LOCATION" in
  centralus|eastus|eastus2|uksouth|westus2)
    echo "    ✓ region $LOCATION is supported"
    ;;
  *)
    echo "    ✗ region $LOCATION is NOT supported (need centralus/eastus/eastus2/uksouth/westus2)"
    exit 1
    ;;
esac

echo
echo "==> Registering Microsoft.KubernetesConfiguration provider (one-off)..."
STATUS=$(az provider show --namespace Microsoft.KubernetesConfiguration \
  --query registrationState -o tsv)
if [[ "$STATUS" == "Registered" ]]; then
  echo "    ✓ already registered"
else
  az provider register --namespace Microsoft.KubernetesConfiguration
  echo "    ⏳ registration submitted (may take a few minutes to propagate)"
fi

echo
echo "==> Installing extension '$EXTENSION_NAME' on cluster $AKS_NAME..."
az k8s-extension create \
  --cluster-type managedClusters \
  --cluster-name "$AKS_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --name "$EXTENSION_NAME" \
  --extension-type "$EXTENSION_TYPE" \
  --scope cluster \
  --release-train preview

echo
echo "==> Fetching kubectl credentials..."
az aks get-credentials --name "$AKS_NAME" --resource-group "$RESOURCE_GROUP" --overwrite-existing

echo
echo "==> Waiting for the agent pod to be ready..."
kubectl wait --for=condition=ready pod \
  -l app=container-networking-agent \
  -n kube-system --timeout=180s

echo
echo "==> Done. To open the chat UI:"
echo "    kubectl port-forward -n kube-system svc/container-networking-agent 8080:80"
echo "    open http://localhost:8080"
