#!/bin/bash

# Script to install Argo Rollouts and Workflows

echo "Installing Argo Rollouts..."

# Install Argo Rollouts
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

echo "Installing Argo Workflows..."
# Install Argo Workflows
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/latest/download/install.yaml

echo "Waiting for Argo Rollouts to be ready..."
kubectl wait --for=condition=available deployment/argo-rollouts -n argo-rollouts --timeout=120s

echo "Waiting for Argo Workflows to be ready..."
kubectl wait --for=condition=available deployment/workflow-controller -n argo --timeout=120s

echo "Installing Argo CLI..."
# Install Argo CLI (if not already installed)
if ! command -v argo &> /dev/null
then
    echo "Installing Argo CLI..."
    curl -sLO https://github.com/argoproj/argo-workflows/releases/latest/download/argo-linux-amd64.gz
    gunzip argo-linux-amd64.gz
    chmod +x argo-linux-amd64
    sudo mv ./argo-linux-amd64 /usr/local/bin/argo
else
    echo "Argo CLI already installed"
fi

echo "Creating required RBAC roles..."
kubectl apply -f ../rbac.yaml

echo "Installation complete!"
echo "To access Argo Workflows UI, run:"
echo "kubectl -n argo port-forward deployment/argo-server 2746:2746"