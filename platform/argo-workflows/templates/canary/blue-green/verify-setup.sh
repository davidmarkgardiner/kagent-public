#!/bin/bash

# Verification script to check that all Blue-Green deployment components are correctly configured

echo "=== Verifying Blue-Green Deployment Components ==="

# Check if required tools are installed
echo "1. Checking required tools..."
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
else
    echo "✅ kubectl is installed"
fi

if ! command -v argo &> /dev/null; then
    echo "⚠️  argo CLI is not installed (optional but recommended)"
else
    echo "✅ argo CLI is installed"
fi

# Check if Kubernetes cluster is accessible
echo "2. Checking Kubernetes cluster connectivity..."
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes cluster is accessible"
else
    echo "❌ Kubernetes cluster is not accessible"
    exit 1
fi

# Check for required CRDs
echo "3. Checking for required CRDs..."
rollout_crd=$(kubectl get crds | grep rollouts.argoproj.io | wc -l)
workflow_crd=$(kubectl get crds | grep workflows.argoproj.io | wc -l)

if [ "$rollout_crd" -gt 0 ]; then
    echo "✅ Argo Rollouts CRD found"
else
    echo "⚠️  Argo Rollouts CRD not found (will be installed during deployment)"
fi

if [ "$workflow_crd" -gt 0 ]; then
    echo "✅ Argo Workflows CRD found"
else
    echo "⚠️  Argo Workflows CRD not found (will be installed during deployment)"
fi

# Check YAML files
echo "4. Validating YAML files..."
for file in blue-green/*.yaml; do
    if [ -f "$file" ]; then
        if yq eval "$file" &> /dev/null; then
            echo "✅ $file is valid"
        else
            echo "❌ $file is invalid"
            exit 1
        fi
    fi
done

# Check script files
echo "5. Checking script files..."
scripts=("blue-green/install-argo.sh" "blue-green/deploy-demo.sh" "blue-green/cleanup.sh" "blue-green/test-demo.sh")
for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✅ $script is executable"
        else
            echo "❌ $script is not executable"
            exit 1
        fi
    else
        echo "❌ $script not found"
        exit 1
    fi
done

echo ""
echo "=== Verification Complete ==="
echo "All components are correctly configured."
echo "To deploy the Blue-Green demo, run: ./blue-green/test-demo.sh"