#!/bin/bash
# Deploy Auto-Healer Pipeline
# Connects Kubernetes events -> Holmes analysis -> Auto-fix -> RocketChat notifications

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Deploying Auto-Healer Pipeline ==="

# 1. Apply RBAC
echo "1. Applying RBAC..."
kubectl apply -f "$SCRIPT_DIR/rbac.yaml"

# 2. Apply EventSource
echo "2. Applying EventSource..."
kubectl apply -f "$SCRIPT_DIR/eventsource.yaml"

# 3. Apply WorkflowTemplate
echo "3. Applying WorkflowTemplate..."
kubectl apply -f "$SCRIPT_DIR/workflowtemplate.yaml"

# 4. Apply Sensor
echo "4. Applying Sensor..."
kubectl apply -f "$SCRIPT_DIR/sensor.yaml"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Check status:"
echo "  kubectl get eventsource -n argo-events"
echo "  kubectl get sensor -n argo-events"
echo "  kubectl get workflowtemplates -n argo-events"
echo ""
echo "To test, deploy a broken app:"
echo "  kubectl apply -f $SCRIPT_DIR/test-broken-deployment.yaml"
echo ""
echo "Watch for workflows:"
echo "  kubectl get workflows -n argo-events -w"
