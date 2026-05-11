#!/bin/bash
# Example: Run UK8S Cluster Certification
# This example certifies the simple test cluster from instances/dev/simple-cluster-example.yaml

set -e

echo "========================================"
echo "UK8S Cluster Certification Example"
echo "========================================"
echo ""

# Configuration from simple-cluster-example.yaml
CLUSTER_NAME="my-test-cluster"
RESOURCE_GROUP="rg-my-test-cluster"
TARGET_NAMESPACE="azure-system"
INSTANCE_NAME="my-test-cluster"

echo "Cluster Configuration:"
echo "  Cluster Name:     $CLUSTER_NAME"
echo "  Resource Group:   $RESOURCE_GROUP"
echo "  Namespace:        $TARGET_NAMESPACE"
echo "  Instance Name:    $INSTANCE_NAME"
echo ""

# Check if workflow template exists
echo "Checking if workflow template is deployed..."
if ! kubectl get workflowtemplate uk8s-cluster-certification -n argo &>/dev/null; then
    echo "ERROR: Workflow template not found!"
    echo "Please run: ./deploy-certification.sh"
    exit 1
fi
echo "✓ Workflow template found"
echo ""

# Check if argo CLI is available
if ! command -v argo &> /dev/null; then
    echo "WARNING: argo CLI not found. Using kubectl instead..."
    USE_KUBECTL=true
else
    USE_KUBECTL=false
fi

# Submit workflow
echo "Submitting certification workflow..."
echo ""

if [[ "$USE_KUBECTL" == "true" ]]; then
    # Using kubectl to submit (more complex)
    cat <<EOF | kubectl create -f -
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: uk8s-cert-
  namespace: argo
spec:
  workflowTemplateRef:
    name: uk8s-cluster-certification
  arguments:
    parameters:
      - name: clusterName
        value: "$CLUSTER_NAME"
      - name: resourceGroup
        value: "$RESOURCE_GROUP"
      - name: targetNamespace
        value: "$TARGET_NAMESPACE"
      - name: instanceName
        value: "$INSTANCE_NAME"
EOF

    echo ""
    echo "Workflow submitted via kubectl"
    echo ""
    echo "To monitor the workflow:"
    echo "  kubectl get workflows -n argo"
    echo "  kubectl logs <workflow-pod> -n argo -f"

else
    # Using argo CLI (recommended)
    WORKFLOW_NAME=$(argo submit -n argo \
        --from workflowtemplate/uk8s-cluster-certification \
        -p clusterName="$CLUSTER_NAME" \
        -p resourceGroup="$RESOURCE_GROUP" \
        -p targetNamespace="$TARGET_NAMESPACE" \
        -p instanceName="$INSTANCE_NAME" \
        --output name)

    echo "Workflow submitted: $WORKFLOW_NAME"
    echo ""

    # Watch the workflow
    echo "Watching workflow progress..."
    echo "Press Ctrl+C to stop watching (workflow will continue running)"
    echo ""
    sleep 2

    argo watch "$WORKFLOW_NAME" -n argo

    echo ""
    echo "========================================"
    echo "Workflow Completed"
    echo "========================================"
    echo ""

    # Get workflow status
    STATUS=$(argo get "$WORKFLOW_NAME" -n argo | grep "Status:" | awk '{print $2}')

    echo "Final Status: $STATUS"
    echo ""

    # Show logs with certification report
    echo "Certification Report:"
    echo "--------------------"
    argo logs "$WORKFLOW_NAME" -n argo | grep -A 50 "CERTIFICATION REPORT" || echo "Report not found in logs"

    echo ""
    echo "To view full logs:"
    echo "  argo logs $WORKFLOW_NAME -n argo"
    echo ""
    echo "To view in Argo UI:"
    echo "  kubectl port-forward -n argo svc/argo-server 2746:2746"
    echo "  Then visit: https://localhost:2746"
fi

echo ""
echo "========================================"
echo "Example Complete"
echo "========================================"
