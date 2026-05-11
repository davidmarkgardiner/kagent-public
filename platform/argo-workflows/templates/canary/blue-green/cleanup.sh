#!/bin/bash

# Script to clean up the Blue-Green demo deployment

echo "Cleaning up Blue-Green demo deployment..."

# Delete the test workflow if it exists
echo "Deleting test workflow..."
kubectl delete -f k8s/argo-workflows/blue-green/test-workflow.yaml --ignore-not-found

# Delete the workflow template
echo "Deleting workflow template..."
kubectl delete -f k8s/argo-workflows/blue-green/deployment-workflow.yaml --ignore-not-found

# Delete the analysis templates
echo "Deleting analysis templates..."
kubectl delete -f k8s/argo-workflows/blue-green/analysis-templates.yaml --ignore-not-found

# Delete the rollout
echo "Deleting rollout..."
kubectl delete -f k8s/argo-workflows/blue-green/rollout.yaml --ignore-not-found

# Delete the services
echo "Deleting services..."
kubectl delete -f k8s/argo-workflows/blue-green/services.yaml --ignore-not-found

# Delete the demo app
echo "Deleting demo application..."
kubectl delete -f k8s/argo-workflows/blue-green/demo-app.yaml --ignore-not-found

echo "Cleanup complete!"