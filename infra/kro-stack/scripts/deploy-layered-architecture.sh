#!/bin/bash
set -e

# ============================================
# UK8S Layered Architecture Deployment Script
# ============================================
# This script deploys the three-layer KRO architecture:
# 1. Platform Foundation (UAMIs, shared resources)
# 2. Management Cluster (platform controllers)
# 3. Worker Clusters (application workloads)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFINITIONS_DIR="${SCRIPT_DIR}/../definitions"
INSTANCES_DIR="${SCRIPT_DIR}/../instances"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to wait for resource to be ready
wait_for_resource() {
  local resource_type=$1
  local resource_name=$2
  local namespace=$3
  local timeout=${4:-600}

  log_info "Waiting for $resource_type/$resource_name in namespace $namespace to be ready..."

  kubectl wait --for=condition=Ready \
    "$resource_type/$resource_name" \
    -n "$namespace" \
    --timeout="${timeout}s" || {
    log_error "Timeout waiting for $resource_type/$resource_name"
    return 1
  }

  log_success "$resource_type/$resource_name is ready"
}

# Function to extract identity information from foundation
extract_foundation_identities() {
  local foundation_name=$1
  local namespace=$2

  log_info "Extracting identity information from platform foundation..."

  # Extract client IDs and resource IDs
  ESO_CLIENT_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.externalSecretsClientId}')
  ESO_RESOURCE_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.externalSecretsResourceId}')

  EXTDNS_CLIENT_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.externalDnsClientId}')
  EXTDNS_RESOURCE_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.externalDnsResourceId}')

  CERTMGR_CLIENT_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.certManagerClientId}')
  CERTMGR_RESOURCE_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.certManagerResourceId}')

  GRAFANA_CLIENT_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.grafanaClientId}')
  GRAFANA_RESOURCE_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.grafanaResourceId}')

  FLUX_CLIENT_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.fluxClientId}')
  FLUX_RESOURCE_ID=$(kubectl get uk8splatformfoundation "$foundation_name" -n "$namespace" \
    -o jsonpath='{.status.fluxResourceId}')

  # Verify all values are extracted
  if [[ -z "$ESO_CLIENT_ID" || -z "$EXTDNS_CLIENT_ID" || -z "$CERTMGR_CLIENT_ID" || \
        -z "$GRAFANA_CLIENT_ID" || -z "$FLUX_CLIENT_ID" ]]; then
    log_error "Failed to extract all identity information from foundation"
    return 1
  fi

  log_success "Identity information extracted successfully"

  # Display extracted values
  echo ""
  log_info "Extracted Identity Information:"
  echo "  External Secrets Client ID: $ESO_CLIENT_ID"
  echo "  External DNS Client ID: $EXTDNS_CLIENT_ID"
  echo "  Cert Manager Client ID: $CERTMGR_CLIENT_ID"
  echo "  Grafana Client ID: $GRAFANA_CLIENT_ID"
  echo "  Flux Client ID: $FLUX_CLIENT_ID"
  echo ""
}

# Function to deploy platform foundation
deploy_platform_foundation() {
  local instance_file=$1

  echo ""
  log_info "============================================"
  log_info "LAYER 1: Deploying Platform Foundation"
  log_info "============================================"
  echo ""

  # Apply RGD
  log_info "Applying Platform Foundation ResourceGraphDefinition..."
  kubectl apply -f "${DEFINITIONS_DIR}/uk8s-platform-foundation.yaml"
  sleep 2

  # Apply instance
  log_info "Applying Platform Foundation instance..."
  kubectl apply -f "$instance_file"

  # Extract foundation name and namespace from instance file
  FOUNDATION_NAME=$(yq eval '.metadata.name' "$instance_file")
  FOUNDATION_NAMESPACE=$(yq eval '.metadata.namespace' "$instance_file")

  # Wait for foundation to be ready
  wait_for_resource uk8splatformfoundation "$FOUNDATION_NAME" "$FOUNDATION_NAMESPACE" 900

  # Extract identity information
  extract_foundation_identities "$FOUNDATION_NAME" "$FOUNDATION_NAMESPACE"

  log_success "Platform Foundation deployed successfully"
  echo ""
}

# Function to create cluster instance with identity injection
deploy_cluster_with_identities() {
  local layer_name=$1
  local rgd_file=$2
  local instance_template=$3
  local output_file=$4

  log_info "============================================"
  log_info "LAYER $layer_name: Deploying Cluster"
  log_info "============================================"
  echo ""

  # Apply RGD
  log_info "Applying $layer_name ResourceGraphDefinition..."
  kubectl apply -f "$rgd_file"
  sleep 2

  # Create instance file with injected identities
  log_info "Creating instance file with platform identities..."

  sed -e "s|REPLACE_FROM_FOUNDATION|${ESO_CLIENT_ID}|g" \
      -e "s|/subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-myplatform-externalsecrets|${ESO_RESOURCE_ID}|g" \
      -e "s|/subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-myplatform-externaldns|${EXTDNS_RESOURCE_ID}|g" \
      -e "s|/subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-myplatform-certmanager|${CERTMGR_RESOURCE_ID}|g" \
      -e "s|/subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-myplatform-grafana|${GRAFANA_RESOURCE_ID}|g" \
      -e "s|/subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-myplatform-flux|${FLUX_RESOURCE_ID}|g" \
      "$instance_template" > "$output_file"

  # Now replace the remaining client IDs
  sed -i.bak \
      -e "s/externalDnsClientId: \"REPLACE_FROM_FOUNDATION\"/externalDnsClientId: \"${EXTDNS_CLIENT_ID}\"/g" \
      -e "s/certManagerClientId: \"REPLACE_FROM_FOUNDATION\"/certManagerClientId: \"${CERTMGR_CLIENT_ID}\"/g" \
      -e "s/grafanaClientId: \"REPLACE_FROM_FOUNDATION\"/grafanaClientId: \"${GRAFANA_CLIENT_ID}\"/g" \
      -e "s/fluxClientId: \"REPLACE_FROM_FOUNDATION\"/fluxClientId: \"${FLUX_CLIENT_ID}\"/g" \
      "$output_file"

  rm -f "${output_file}.bak"

  log_success "Instance file created: $output_file"

  # Apply instance
  log_info "Applying cluster instance..."
  kubectl apply -f "$output_file"

  log_success "$layer_name deployed successfully"
  echo ""
}

# Main execution
main() {
  echo ""
  log_info "============================================"
  log_info "UK8S Layered Architecture Deployment"
  log_info "============================================"
  echo ""

  # Check prerequisites
  log_info "Checking prerequisites..."
  command -v kubectl &> /dev/null || { log_error "kubectl not found"; exit 1; }
  command -v yq &> /dev/null || { log_warning "yq not found - some features may not work"; }

  # Parse arguments
  DEPLOY_FOUNDATION=${1:-yes}
  DEPLOY_MGMT=${2:-yes}
  DEPLOY_WORKER=${3:-yes}

  # Step 1: Deploy Platform Foundation
  if [[ "$DEPLOY_FOUNDATION" == "yes" ]]; then
    deploy_platform_foundation "${INSTANCES_DIR}/01-platform-foundation-example.yaml"
  else
    log_warning "Skipping Platform Foundation deployment"
    # Still need to extract identities if foundation exists
    FOUNDATION_NAME="myplatform-foundation"
    FOUNDATION_NAMESPACE="uk8s-platform"
    extract_foundation_identities "$FOUNDATION_NAME" "$FOUNDATION_NAMESPACE"
  fi

  # Step 2: Deploy Management Cluster
  if [[ "$DEPLOY_MGMT" == "yes" ]]; then
    deploy_cluster_with_identities \
      "2 (Management Cluster)" \
      "${DEFINITIONS_DIR}/uk8s-management-cluster.yaml" \
      "${INSTANCES_DIR}/02-management-cluster-example.yaml" \
      "/tmp/management-cluster-instance.yaml"
  else
    log_warning "Skipping Management Cluster deployment"
  fi

  # Step 3: Deploy Worker Cluster
  if [[ "$DEPLOY_WORKER" == "yes" ]]; then
    deploy_cluster_with_identities \
      "3 (Worker Cluster)" \
      "${DEFINITIONS_DIR}/uk8s-worker-cluster.yaml" \
      "${INSTANCES_DIR}/03-worker-cluster-dev-example.yaml" \
      "/tmp/worker-cluster-dev-instance.yaml"
  else
    log_warning "Skipping Worker Cluster deployment"
  fi

  echo ""
  log_success "============================================"
  log_success "Deployment Complete!"
  log_success "============================================"
  echo ""
  log_info "Architecture Summary:"
  echo "  Layer 1: Platform Foundation (shared UAMIs)"
  echo "  Layer 2: Management Cluster (platform controllers)"
  echo "  Layer 3: Worker Clusters (application workloads)"
  echo ""
  log_info "To deploy additional worker clusters:"
  echo "  1. Copy 03-worker-cluster-dev-example.yaml"
  echo "  2. Update cluster name and configuration"
  echo "  3. Run: kubectl apply -f <new-worker-cluster>.yaml"
  echo ""
}

# Show usage
usage() {
  echo "Usage: $0 [deploy_foundation] [deploy_mgmt] [deploy_worker]"
  echo ""
  echo "Arguments:"
  echo "  deploy_foundation  - Deploy platform foundation (yes/no, default: yes)"
  echo "  deploy_mgmt        - Deploy management cluster (yes/no, default: yes)"
  echo "  deploy_worker      - Deploy worker cluster (yes/no, default: yes)"
  echo ""
  echo "Examples:"
  echo "  $0                    # Deploy all layers"
  echo "  $0 no yes yes         # Skip foundation, deploy clusters"
  echo "  $0 yes no no          # Only deploy foundation"
  exit 1
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
fi

# Run main
main "$@"
