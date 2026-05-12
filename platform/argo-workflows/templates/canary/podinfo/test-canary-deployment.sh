#!/bin/bash

set -e

echo "=== Podinfo Canary Deployment Test Script ==="

# Configuration
NAMESPACE="podinfo"
NEW_IMAGE_TAG="6.5.0"
WORKFLOW_TEMPLATE="podinfo-canary-deployment-template"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi

    # Check if argo CLI is available (optional)
    if ! command -v argo &> /dev/null; then
        print_warning "argo CLI is not installed - using kubectl instead"
    fi

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot access Kubernetes cluster"
        exit 1
    fi

    # Check if Argo Workflows is running
    if ! kubectl get pods -n argo | grep -q "workflow-controller.*Running"; then
        print_error "Argo Workflows is not running"
        exit 1
    fi

    # Check if Argo Rollouts is running
    if ! kubectl get pods -n argo-rollouts | grep -q "argo-rollouts.*Running"; then
        print_warning "Argo Rollouts is not running - will try to start it"
    fi

    print_success "Prerequisites check completed"
}

# Deploy workflow templates
deploy_templates() {
    print_status "Deploying workflow templates..."

    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    kubectl apply -f "${SCRIPT_DIR}/podinfo-canary-deployment-template.yaml"
    kubectl apply -f "${SCRIPT_DIR}/podinfo-canary-analysis-template.yaml"

    print_success "Workflow templates deployed"
}

# Create namespace if not exists
create_namespace() {
    print_status "Creating namespace if not exists..."

    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        kubectl create namespace $NAMESPACE
        print_success "Namespace $NAMESPACE created"
    else
        print_status "Namespace $NAMESPACE already exists"
    fi
}

# Submit canary deployment workflow
submit_workflow() {
    print_status "Submitting canary deployment workflow..."

    WORKFLOW_NAME="podinfo-canary-$(date +%s)"

    cat <<EOF | kubectl create -f -
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: podinfo-canary-deployment-
  namespace: argo
spec:
  workflowTemplateRef:
    name: $WORKFLOW_TEMPLATE
  arguments:
    parameters:
    - name: newImageTag
      value: "$NEW_IMAGE_TAG"
    - name: applicationName
      value: "podinfo"
    - name: namespace
      value: "$NAMESPACE"
    - name: autoPromote
      value: "false"
EOF

    # Get the actual workflow name
    sleep 2
    ACTUAL_WORKFLOW_NAME=$(kubectl get workflows -n argo --sort-by=.metadata.creationTimestamp | tail -1 | awk '{print $1}')

    print_success "Workflow submitted: $ACTUAL_WORKFLOW_NAME"
    echo "WORKFLOW_NAME=$ACTUAL_WORKFLOW_NAME" > /tmp/workflow-info
}

# Monitor workflow progress
monitor_workflow() {
    if [ -f /tmp/workflow-info ]; then
        source /tmp/workflow-info
    else
        print_error "Workflow name not found"
        return 1
    fi

    print_status "Monitoring workflow: $WORKFLOW_NAME"

    # Wait for workflow to complete
    timeout=600  # 10 minutes
    while [ $timeout -gt 0 ]; do
        status=$(kubectl get workflow $WORKFLOW_NAME -n argo -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

        print_status "Workflow status: $status"

        case $status in
            "Succeeded")
                print_success "Workflow completed successfully!"
                return 0
                ;;
            "Failed")
                print_error "Workflow failed!"
                kubectl get workflow $WORKFLOW_NAME -n argo -o yaml
                return 1
                ;;
            "Error")
                print_error "Workflow encountered an error!"
                kubectl get workflow $WORKFLOW_NAME -n argo -o yaml
                return 1
                ;;
            "Running"|"Pending")
                print_status "Workflow is still running..."
                ;;
        esac

        sleep 10
        timeout=$((timeout - 10))
    done

    print_error "Timeout waiting for workflow to complete"
    return 1
}

# Check rollout status
check_rollout() {
    print_status "Checking rollout status..."

    if kubectl get rollout podinfo -n $NAMESPACE &> /dev/null; then
        kubectl get rollout podinfo -n $NAMESPACE
        kubectl describe rollout podinfo -n $NAMESPACE | tail -20
    else
        print_warning "No rollout found in namespace $NAMESPACE"
    fi
}

# Test services
test_services() {
    print_status "Testing services..."

    # Port-forward to stable service
    print_status "Testing stable service..."
    kubectl port-forward -n $NAMESPACE service/podinfo-stable 19898:80 &
    PF_PID1=$!
    sleep 3

    if curl -s http://localhost:19898/healthz > /dev/null; then
        print_success "Stable service is healthy"
    else
        print_warning "Stable service health check failed"
    fi

    kill $PF_PID1 2>/dev/null || true

    # Port-forward to canary service
    print_status "Testing canary service..."
    kubectl port-forward -n $NAMESPACE service/podinfo-canary 19899:80 &
    PF_PID2=$!
    sleep 3

    if curl -s http://localhost:19899/healthz > /dev/null; then
        print_success "Canary service is healthy"
    else
        print_warning "Canary service health check failed"
    fi

    kill $PF_PID2 2>/dev/null || true
}

# Cleanup function
cleanup() {
    print_status "Cleaning up port-forwards..."
    pkill -f "kubectl port-forward" 2>/dev/null || true
    rm -f /tmp/workflow-info
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    print_status "Starting podinfo canary deployment test..."

    check_prerequisites
    create_namespace
    deploy_templates
    submit_workflow

    print_status "Waiting a moment for workflow to initialize..."
    sleep 5

    monitor_workflow

    print_status "Checking final state..."
    check_rollout
    test_services

    print_success "Test script completed!"

    print_status "To manually promote the canary deployment, run:"
    echo "kubectl argo rollouts promote podinfo -n $NAMESPACE"

    print_status "To check the Argo Workflows UI, run:"
    echo "kubectl port-forward -n argo service/argo-server 2746:2746"
    echo "Then visit: http://localhost:2746"
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --image-tag TAG    Set the new image tag (default: 6.5.0)"
    echo "  --namespace NS     Set the namespace (default: podinfo)"
    echo "  --auto-promote     Enable auto-promotion"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Use default settings"
    echo "  $0 --image-tag 6.6.0                # Use specific image tag"
    echo "  $0 --auto-promote                   # Auto-promote on success"
    echo "  $0 --namespace my-app --image-tag latest"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image-tag)
            NEW_IMAGE_TAG="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --auto-promote)
            AUTO_PROMOTE="true"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main