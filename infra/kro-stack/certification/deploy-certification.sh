#!/bin/bash
# Deploy UK8S Cluster Certification Workflow
# This script sets up all prerequisites and deploys the certification workflow template

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}==>${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_info "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"

    # Check argo CLI (optional)
    if command -v argo &> /dev/null; then
        log_info "argo CLI found: $(argo version --short 2>/dev/null || echo 'version unknown')"
    else
        log_warn "argo CLI not found (optional, but recommended for workflow management)"
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_info "Connected to cluster: $(kubectl config current-context)"

    # Check if argo namespace exists
    if ! kubectl get namespace argo &> /dev/null; then
        log_error "Argo namespace not found. Please install Argo Workflows first."
        exit 1
    fi
    log_info "Argo namespace exists"

    echo ""
}

# Create ConfigMap with validation scripts
create_scripts_configmap() {
    log_step "Creating ConfigMap with validation scripts..."

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts"

    if [[ ! -d "$SCRIPT_DIR" ]]; then
        log_error "Scripts directory not found: $SCRIPT_DIR"
        exit 1
    fi

    # Create ConfigMap from scripts directory
    kubectl create configmap uk8s-certification-scripts \
        -n argo \
        --from-file="$SCRIPT_DIR" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_info "ConfigMap 'uk8s-certification-scripts' created/updated"
    echo ""
}

# Deploy RBAC for workflow
deploy_rbac() {
    log_step "Deploying RBAC for certification workflow..."

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argo-workflow-executor
  namespace: argo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: uk8s-certification-role
rules:
  # KRO resources
  - apiGroups: ["kro.run"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # ASO resources
  - apiGroups: ["resources.azure.com"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["containerservice.azure.com"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["managedidentity.azure.com"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # Flux resources
  - apiGroups: ["source.toolkit.fluxcd.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["kustomize.toolkit.fluxcd.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["helm.toolkit.fluxcd.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # Core Kubernetes resources
  - apiGroups: [""]
    resources: ["namespaces", "pods", "services", "endpoints", "configmaps", "secrets", "nodes", "serviceaccounts"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch"]
  # Networking
  - apiGroups: ["networking.k8s.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # Istio
  - apiGroups: ["networking.istio.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # Storage
  - apiGroups: ["storage.k8s.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
  # Metrics
  - apiGroups: ["metrics.k8s.io"]
    resources: ["*"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argo-workflow-executor-uk8s-cert
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: uk8s-certification-role
subjects:
  - kind: ServiceAccount
    name: argo-workflow-executor
    namespace: argo
EOF

    log_info "RBAC configured for certification workflow"
    echo ""
}

# Deploy workflow template
deploy_workflow_template() {
    log_step "Deploying UK8S certification workflow template..."

    WORKFLOW_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/workflows/uk8s-cluster-certification.yaml"

    if [[ ! -f "$WORKFLOW_FILE" ]]; then
        log_error "Workflow template not found: $WORKFLOW_FILE"
        exit 1
    fi

    kubectl apply -f "$WORKFLOW_FILE"

    log_info "WorkflowTemplate 'uk8s-cluster-certification' deployed"
    echo ""
}

# Display usage instructions
show_usage() {
    cat <<EOF
${GREEN}========================================
UK8S Certification Workflow Deployed!
========================================${NC}

${BLUE}To run a certification:${NC}

1. ${YELLOW}Submit the workflow:${NC}

   argo submit -n argo \\
     --from workflowtemplate/uk8s-cluster-certification \\
     -p clusterName=my-cluster \\
     -p resourceGroup=my-rg \\
     -p targetNamespace=azure-system \\
     -p instanceName=my-uk8s-cluster \\
     --watch

2. ${YELLOW}Monitor progress:${NC}

   argo watch <workflow-name> -n argo
   argo logs <workflow-name> -n argo

3. ${YELLOW}View results:${NC}

   argo get <workflow-name> -n argo
   kubectl logs <workflow-pod> -n argo

4. ${YELLOW}Optional parameters:${NC}

   -p subscriptionId=<azure-subscription-id>
   -p backstage-url=https://backstage.example.com
   -p component-name=my-service
   -p skip-azure-checks=false
   -p certification-timeout=1800

${GREEN}========================================${NC}

${BLUE}Example with all parameters:${NC}

argo submit -n argo \\
  --from workflowtemplate/uk8s-cluster-certification \\
  -p clusterName=prod-aks-001 \\
  -p resourceGroup=rg-aks-prod \\
  -p targetNamespace=azure-system \\
  -p instanceName=prod-cluster \\
  -p subscriptionId={{AZURE_SUBSCRIPTION_ID}} \\
  -p backstage-url=https://backstage.company.com \\
  -p component-name=prod-cluster \\
  --watch

${GREEN}========================================${NC}

For more information, see:
  - README.md in this directory
  - Certification checklist: CERTIFICATION_CHECKLIST.md

EOF
}

# Main deployment flow
main() {
    echo ""
    log_step "UK8S Cluster Certification Workflow Deployment"
    echo ""

    check_prerequisites
    create_scripts_configmap
    deploy_rbac
    deploy_workflow_template

    log_info "Deployment complete!"
    echo ""
    show_usage
}

main "$@"
