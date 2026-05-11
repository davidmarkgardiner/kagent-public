#!/usr/bin/env bash
# Validation script to ensure all KRO resources have corresponding certification tests
# Usage: ./validate-certification-coverage.sh [path-to-rgd-yaml]
# Requires: bash 4+ (for associative arrays), yq

set -e

# Check bash version (require 4.0+)
if ((BASH_VERSINFO[0] < 4)); then
    echo "ERROR: This script requires bash 4.0 or higher"
    echo "Current version: $BASH_VERSION"
    echo ""
    echo "To install bash 4+ on macOS:"
    echo "  brew install bash"
    echo ""
    echo "Or use devbox shell (which includes bash 5+)"
    exit 1
fi

RGD_FILE="${1:-kro-stack/definitions/uk8scluster.yaml}"
CERTIFICATION_FILE="$RGD_FILE"  # Certification is in same file

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Certification Coverage Validation"
echo "=========================================="
echo "RGD File: $RGD_FILE"
echo ""

# Check if yq is installed
if ! command -v yq &> /dev/null; then
    echo -e "${RED}ERROR: yq is not installed${NC}"
    echo "Install with: brew install yq"
    exit 1
fi

# Check if file exists
if [[ ! -f "$RGD_FILE" ]]; then
    echo -e "${RED}ERROR: File not found: $RGD_FILE${NC}"
    exit 1
fi

# Extract all resource IDs from the RGD
echo "Extracting resource IDs from RGD..."
RESOURCE_IDS=$(yq eval '.spec.resources[].id' "$RGD_FILE" | sort | uniq)

if [[ -z "$RESOURCE_IDS" ]]; then
    echo -e "${RED}ERROR: No resources found in RGD${NC}"
    exit 1
fi

echo "Found resources:"
echo "$RESOURCE_IDS" | sed 's/^/  - /'
echo ""

# Define resources that should have certification
# Resources that are infrastructure (not needing runtime validation)
INFRASTRUCTURE_RESOURCES=(
    "certificationScripts"
    "certificationWorkflow"
    "certificationSchedule"
    "certificationTrigger"
    "certManagerIdentity"
    "certManagerFederatedCredential"
    "externalDnsIdentity"
    "externalDnsFederatedCredential"
    "externalDnsBcmFederatedCredential"
    "externalSecretsIdentity"
    "externalSecretsFederatedCredential"
    "fluxSourceFederatedCredential"
    "fluxImageFederatedCredential"
)

# Define which resources need validation and map them to validation steps
# Format: "resourceId:validationStep"
declare -A VALIDATION_MAPPING=(
    ["resourceGroup"]="validate-aso-resources"
    ["managedCluster"]="validate-aso-resources"
    ["systemNodePool"]="validate-cluster-connectivity"
    ["userNodePool"]="validate-cluster-connectivity"
    ["fluxGitOps"]="validate-flux-gitops"
    ["jobs"]="validate-kro-resources"
    ["gitRepository"]="validate-flux-gitops"
    ["kustomization"]="validate-flux-gitops"
    ["istioGateway"]="validate-cluster-connectivity"
    ["istioVirtualService"]="validate-cluster-connectivity"
)

# Extract validation steps from the certification workflow
echo "Extracting validation steps from certification workflow..."
VALIDATION_STEPS=$(yq eval '.spec.resources[] | select(.id == "certificationWorkflow") | .template.spec.templates[].name | select(. == "validate-*")' "$RGD_FILE" | sort | uniq)

if [[ -z "$VALIDATION_STEPS" ]]; then
    echo -e "${YELLOW}WARNING: No validation steps found in certification workflow${NC}"
    echo ""
fi

echo "Found validation steps:"
echo "$VALIDATION_STEPS" | sed 's/^/  - /'
echo ""

# Check coverage
echo "=========================================="
echo "Coverage Analysis"
echo "=========================================="

MISSING_COUNT=0
COVERED_COUNT=0
SKIPPED_COUNT=0

while IFS= read -r resource_id; do
    # Skip if empty
    [[ -z "$resource_id" ]] && continue

    # Check if resource is in infrastructure list (skip validation check)
    skip_resource=false
    for infra in "${INFRASTRUCTURE_RESOURCES[@]}"; do
        if [[ "$resource_id" == "$infra" ]]; then
            echo -e "${YELLOW}⊘ $resource_id${NC} (infrastructure, skipped)"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            skip_resource=true
            break
        fi
    done

    [[ "$skip_resource" == true ]] && continue

    # Check if resource should have validation
    if [[ -n "${VALIDATION_MAPPING[$resource_id]}" ]]; then
        expected_validation="${VALIDATION_MAPPING[$resource_id]}"

        # Check if the validation step exists
        if echo "$VALIDATION_STEPS" | grep -q "^$expected_validation$"; then
            echo -e "${GREEN}✓ $resource_id${NC} → $expected_validation"
            COVERED_COUNT=$((COVERED_COUNT + 1))
        else
            echo -e "${RED}✗ $resource_id${NC} → $expected_validation (MISSING)"
            MISSING_COUNT=$((MISSING_COUNT + 1))
        fi
    else
        echo -e "${YELLOW}? $resource_id${NC} (no validation mapping defined)"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done <<< "$RESOURCE_IDS"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Covered:${NC} $COVERED_COUNT resources"
echo -e "${YELLOW}Skipped:${NC} $SKIPPED_COUNT resources (infrastructure)"
echo -e "${RED}Missing:${NC} $MISSING_COUNT resources"
echo ""

TOTAL_RESOURCES=$(echo "$RESOURCE_IDS" | wc -l | tr -d ' ')
COVERAGE_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($COVERED_COUNT / ($TOTAL_RESOURCES - $SKIPPED_COUNT)) * 100}")

echo "Coverage: $COVERAGE_PERCENT%"
echo ""

# Exit with error if coverage is not 100%
if [[ $MISSING_COUNT -gt 0 ]]; then
    echo -e "${RED}VALIDATION FAILED: $MISSING_COUNT resources lack certification coverage${NC}"
    echo ""
    echo "To fix:"
    echo "1. Add validation mapping to VALIDATION_MAPPING in this script"
    echo "2. Create corresponding validation step in certificationWorkflow"
    echo "3. Add resource to INFRASTRUCTURE_RESOURCES if it doesn't need validation"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ VALIDATION PASSED: All resources have certification coverage${NC}"
    exit 0
fi
