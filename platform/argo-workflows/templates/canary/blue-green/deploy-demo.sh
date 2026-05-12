#!/bin/bash

# Script to deploy the Blue-Green demo

echo "Deploying Blue-Green demo application..."

# Apply the services first
echo "Creating services..."
kubectl apply -f services.yaml

# Apply the rollout
echo "Creating rollout..."
kubectl apply -f rollout.yaml

# Apply the analysis templates
echo "Creating analysis templates..."
kubectl apply -f analysis-templates.yaml

# Apply the workflow template
echo "Creating workflow template..."
kubectl apply -f deployment-workflow.yaml

echo "Deployment complete!"
echo "To start a test deployment, run:"
echo "kubectl create -f test-workflow.yaml"