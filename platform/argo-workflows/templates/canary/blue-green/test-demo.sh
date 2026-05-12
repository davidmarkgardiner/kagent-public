#!/bin/bash

# Test script to demonstrate the complete Blue-Green deployment workflow
# This script should be run from the blue-green directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Blue-Green Deployment Demo ==="

echo "1. Installing Argo Rollouts and Workflows..."
./install-argo.sh

echo "2. Deploying Blue-Green demo components..."
./deploy-demo.sh

echo "3. Starting test deployment workflow..."
kubectl create -f test-workflow.yaml

echo "4. Monitoring workflow progress..."
echo "Run 'argo watch' to monitor the workflow execution"
echo "Run 'kubectl get rollout blue-green-demo' to check rollout status"

echo "5. To promote the deployment manually:"
echo "   kubectl argo rollouts promote blue-green-demo"

echo "6. To rollback the deployment:"
echo "   kubectl argo rollouts undo blue-green-demo"

echo ""
echo "=== Demo Setup Complete ==="
echo "Check the README.md for more detailed instructions"