# Certification Coverage Validation

Automated validation to ensure all KRO resources have corresponding certification tests.

## Problem Statement

As the UK8S cluster RGD grows with new resources, we need to ensure every resource has appropriate certification/validation coverage. Without automated checks:

❌ New resources might be added without corresponding tests
❌ Deployments could succeed but resources remain unvalidated
❌ Issues might only be discovered in production

## Solution

This validation system automatically checks that:
✅ Every resource in the RGD has a corresponding validation step
✅ New PRs are validated before merge
✅ Local commits are checked before push

---

## How It Works

### 1. Validation Script

`validate-certification-coverage.sh` performs these checks:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Parse RGD YAML                                           │
│    Extract all resource IDs from spec.resources[]           │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Extract Certification Steps                              │
│    Find all validate-* steps in certificationWorkflow       │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Map Resources to Validations                             │
│    Check VALIDATION_MAPPING for each resource               │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Generate Coverage Report                                 │
│    ✓ Covered resources                                      │
│    ✗ Missing validations                                    │
│    ⊘ Infrastructure resources (skipped)                     │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Exit with Status                                         │
│    Exit 0: 100% coverage                                    │
│    Exit 1: Missing coverage                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2. Validation Mapping

Resources are mapped to validation steps in `VALIDATION_MAPPING`:

```bash
declare -A VALIDATION_MAPPING=(
    ["resourceGroup"]="validate-aso"
    ["aksCluster"]="validate-aso"
    ["systemNodePool"]="validate-connectivity"
    ["fluxGitOps"]="validate-flux"
    # ... add new mappings here
)
```

**Infrastructure resources** that don't need runtime validation:

```bash
INFRASTRUCTURE_RESOURCES=(
    "certificationScripts"
    "certificationWorkflow"
    "certificationSchedule"
    "certificationTrigger"
)
```

---

## Usage

### Manual Validation

Run the validation script manually:

```bash
# From repository root
./kro-stack/scripts/validate-certification-coverage.sh

# Or specify RGD path
./kro-stack/scripts/validate-certification-coverage.sh kro-stack/definitions/uk8scluster.yaml
```

**Example output:**

```
==========================================
Certification Coverage Validation
==========================================
RGD File: kro-stack/definitions/uk8scluster.yaml

Extracting resource IDs from RGD...
Found resources:
  - aksCluster
  - certificationSchedule
  - certificationTrigger
  - certificationWorkflow
  - fluxGitOps
  - resourceGroup
  - systemNodePool

Extracting validation steps from certification workflow...
Found validation steps:
  - validate-aso
  - validate-config
  - validate-connectivity
  - validate-flux
  - validate-kro
  - validate-security

==========================================
Coverage Analysis
==========================================
✓ resourceGroup → validate-aso
✓ aksCluster → validate-aso
✓ systemNodePool → validate-connectivity
✓ fluxGitOps → validate-flux
⊘ certificationWorkflow (infrastructure, skipped)
⊘ certificationSchedule (infrastructure, skipped)
⊘ certificationTrigger (infrastructure, skipped)

==========================================
Summary
==========================================
Covered: 4 resources
Skipped: 3 resources (infrastructure)
Missing: 0 resources

Coverage: 100.0%

✅ VALIDATION PASSED: All resources have certification coverage
```

---

## Git Hook Integration

### Installation

1. **Copy the pre-commit hook:**

```bash
cp kro-stack/scripts/pre-commit-hook-example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

2. **Test the hook:**

```bash
# Make a change to uk8scluster.yaml
vim kro-stack/definitions/uk8scluster.yaml

# Try to commit
git add kro-stack/definitions/uk8scluster.yaml
git commit -m "test: trigger pre-commit hook"
```

### Hook Behavior

The pre-commit hook will:

✅ **Allow commit** if:
- uk8scluster.yaml not modified
- All resources have 100% certification coverage

❌ **Block commit** if:
- Resources lack certification coverage
- Validation mapping is incomplete

⚠️ **Bypass hook** (not recommended):
```bash
git commit --no-verify -m "bypassing validation"
```

### Example Blocked Commit

```
🔍 Running certification coverage validation...

✓ Detected changes to uk8scluster.yaml

==========================================
Certification Coverage Validation
==========================================
...
✗ newResourceId → (no validation mapping defined)

Coverage: 87.5%

❌ VALIDATION FAILED: 1 resources lack certification coverage

Your commit has been blocked because certification coverage is incomplete.

Options:
  1. Add missing validation steps to the certification workflow
  2. Add resource to INFRASTRUCTURE_RESOURCES if it doesn't need validation
  3. Define validation mapping in VALIDATION_MAPPING
  4. Bypass this check with: git commit --no-verify (not recommended)
```

---

## Azure DevOps Pipeline Integration

### Setup

1. **Add pipeline to your repository:**

```bash
# Copy pipeline YAML
cp kro-stack/pipelines/validate-certification-coverage.yaml azure-pipelines-validation.yml
```

2. **Create pipeline in Azure DevOps:**

- Go to Pipelines → New Pipeline
- Select your repository
- Choose "Existing Azure Pipelines YAML file"
- Select `azure-pipelines-validation.yml`

3. **Configure branch policies:**

Go to Repos → Branches → main → Branch Policies:

✅ Enable "Require build verification"
✅ Select "Validate Certification Coverage" pipeline
✅ Set as required for PR completion

### Pipeline Behavior

The pipeline will:

1. **Trigger on PR** to main/develop that modifies:
   - `kro-stack/definitions/uk8scluster.yaml`
   - `kro-stack/scripts/validate-certification-coverage.sh`

2. **Run validation checks:**
   - Install `yq`
   - Execute validation script
   - Generate coverage report

3. **Block PR merge** if validation fails

4. **Post results** to PR (requires configuration)

### Example PR Check

When you create a PR, the pipeline will run:

```
✓ Install yq
✓ Validate Certification Coverage
  └─ Coverage: 100.0%
  └─ ✅ VALIDATION PASSED

✓ Publish Validation Report
```

If validation fails:

```
✓ Install yq
✗ Validate Certification Coverage
  └─ Coverage: 87.5%
  └─ ❌ VALIDATION FAILED: 1 resources lack certification coverage

! Publish Validation Report
! Post PR Comment on Failure
```

---

## Adding New Resources

When you add a new resource to the RGD, follow these steps:

### Step 1: Add the Resource

```yaml
# kro-stack/definitions/uk8scluster.yaml
spec:
  resources:
    - id: myNewResource
      template:
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: my-new-resource
```

### Step 2: Add Validation Step

```yaml
# In the same file, under certificationWorkflow
- name: validate-my-resource
  script:
    image: bitnami/kubectl:latest
    command: [bash]
    source: |
      set -e
      echo "=== My Resource Validation ==="

      # Validation logic here
      kubectl get configmap my-new-resource

      echo "✅ My resource validation complete"
```

### Step 3: Add to DAG

```yaml
# Add the validation step to the DAG
- name: validate-new
  template: validate-my-resource
  dependencies: [validate-connectivity]  # or appropriate dependency
```

### Step 4: Update Validation Mapping

```bash
# Edit kro-stack/scripts/validate-certification-coverage.sh
declare -A VALIDATION_MAPPING=(
    ["resourceGroup"]="validate-aso"
    ["aksCluster"]="validate-aso"
    # ... existing mappings ...
    ["myNewResource"]="validate-my-resource"  # Add this line
)
```

### Step 5: Test Locally

```bash
./kro-stack/scripts/validate-certification-coverage.sh
```

Expected output:
```
✓ myNewResource → validate-my-resource
Coverage: 100.0%
✅ VALIDATION PASSED
```

### Step 6: Commit and Push

```bash
git add kro-stack/definitions/uk8scluster.yaml
git add kro-stack/scripts/validate-certification-coverage.sh
git commit -m "feat: add myNewResource with certification"
git push
```

The pre-commit hook will validate before the commit, and the ADO pipeline will validate on PR.

---

## Infrastructure Resources

Some resources are **infrastructure** and don't need runtime validation:

```bash
INFRASTRUCTURE_RESOURCES=(
    "certificationScripts"       # ConfigMap for scripts
    "certificationWorkflow"      # WorkflowTemplate itself
    "certificationSchedule"      # CronWorkflow
    "certificationTrigger"       # Trigger Job
    "workloadIdentityServiceAccount"  # RBAC
    "workloadIdentityFederatedCreds"  # Azure credentials
)
```

These resources are **skipped** during validation and marked with `⊘`.

**When to add to INFRASTRUCTURE_RESOURCES:**
- Resource is part of the certification system itself
- Resource is RBAC/auth related
- Resource doesn't represent cluster functionality to be validated
- Resource is a deployment-time utility (Jobs, ConfigMaps for scripts)

---

## Troubleshooting

### Error: "yq is not installed"

**Fix:**
```bash
# macOS
brew install yq

# Linux
sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
sudo chmod +x /usr/local/bin/yq
```

### Error: "File not found"

**Fix:**
```bash
# Run from repository root
cd /path/to/argo-workflow
./kro-stack/scripts/validate-certification-coverage.sh
```

### Error: "No validation mapping defined"

This means a resource exists in the RGD but has no entry in `VALIDATION_MAPPING`.

**Fix:**
```bash
# Edit the validation script
vim kro-stack/scripts/validate-certification-coverage.sh

# Add mapping
declare -A VALIDATION_MAPPING=(
    # ... existing mappings ...
    ["yourResourceId"]="validate-your-step"
)
```

### Pre-commit Hook Not Running

**Fix:**
```bash
# Ensure hook is executable
chmod +x .git/hooks/pre-commit

# Verify hook exists
ls -la .git/hooks/pre-commit

# Test manually
.git/hooks/pre-commit
```

### Pipeline Not Triggering

**Fix:**
1. Check pipeline triggers in `azure-pipelines-validation.yml`
2. Verify paths match your modified files
3. Check branch policies in Azure DevOps

---

## Coverage Metrics

### Current Coverage

Run the validation script to see current coverage:

```bash
./kro-stack/scripts/validate-certification-coverage.sh
```

### Coverage Goals

- **Required:** 100% coverage for production resources
- **Infrastructure:** Can be skipped with proper justification
- **New Resources:** Must have validation before merge

### Coverage by Section

| Section | Resources | Coverage |
|---------|-----------|----------|
| ASO Resources | ResourceGroup, ManagedCluster | validate-aso |
| KRO Resources | UK8SCluster instance | validate-kro |
| Flux Resources | GitRepository, Kustomization | validate-flux |
| Network Resources | Nodes, API Server | validate-connectivity |
| Security Resources | ServiceAccounts, RBAC | validate-security |
| Config Resources | YAML, Schema | validate-config |

---

## Best Practices

### 1. Always Add Validation for New Resources

When adding a new resource:
- ✅ Create validation step in certification workflow
- ✅ Add to VALIDATION_MAPPING
- ✅ Test locally before committing
- ✅ Verify in PR pipeline

### 2. Use Appropriate Validation Categories

Map resources to logical validation steps:
- Azure resources → `validate-aso`
- Flux resources → `validate-flux`
- Network resources → `validate-connectivity`
- Security resources → `validate-security`

### 3. Infrastructure vs Runtime Resources

**Infrastructure resources** (skip validation):
- Part of certification system itself
- RBAC/authentication components
- Deployment-time utilities

**Runtime resources** (require validation):
- Cluster infrastructure (nodes, API)
- Azure resources (RG, AKS)
- Application resources (Flux, Istio)
- Security policies (Network Policies)

### 4. Test Coverage Locally

Before pushing:
```bash
# Make changes
vim kro-stack/definitions/uk8scluster.yaml

# Test validation
./kro-stack/scripts/validate-certification-coverage.sh

# If 100%, commit
git commit -m "feat: add new resource"
```

### 5. Document Custom Validations

When adding new validation steps, document:
- What is being validated
- Why it's important
- What success/failure looks like

---

## Integration Checklist

- [ ] Install git pre-commit hook
- [ ] Configure Azure DevOps pipeline
- [ ] Set branch policies to require validation
- [ ] Document validation requirements in team wiki
- [ ] Train team on adding new resources with validation
- [ ] Schedule periodic coverage audits

---

## Examples

### Example 1: Adding a New Storage Resource

```yaml
# 1. Add resource to RGD
- id: storageAccount
  template:
    apiVersion: storage.azure.com/v1api20230101
    kind: StorageAccount
    metadata:
      name: ${schema.spec.clusterName}storage

# 2. Add validation step
- name: validate-storage
  script:
    image: bitnami/kubectl:latest
    command: [bash]
    source: |
      set -e
      echo "=== Storage Validation ==="

      STORAGE=$(kubectl get storageaccount ${schema.spec.clusterName}storage -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

      if [[ "$STORAGE" == "True" ]]; then
        echo "✓ Storage account is ready"
      else
        echo "✗ Storage account not ready"
        exit 1
      fi

      echo "✅ Storage validation complete"

# 3. Add to DAG
- name: validate-storage-step
  template: validate-storage
  dependencies: [validate-aso]

# 4. Update validation script mapping
["storageAccount"]="validate-storage"
```

### Example 2: Marking Resource as Infrastructure

```yaml
# Resource doesn't need validation (it's a ConfigMap for scripts)
- id: deploymentScripts
  template:
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: deployment-scripts
    data:
      deploy.sh: |
        #!/bin/bash
        echo "Deploying..."

# Add to INFRASTRUCTURE_RESOURCES in validation script
INFRASTRUCTURE_RESOURCES=(
    "certificationScripts"
    "certificationWorkflow"
    "deploymentScripts"  # Add this
)
```

---

## Support

**Validation script issues:**
- Check script permissions: `chmod +x kro-stack/scripts/validate-certification-coverage.sh`
- Verify yq installation: `yq --version`
- Run with verbose output for debugging

**Pipeline issues:**
- Check Azure DevOps logs
- Verify branch policies
- Ensure yq installation step succeeds

**Coverage questions:**
- Review validation mapping in script
- Check infrastructure resources list
- Ensure validation steps exist in workflow

---

## Future Enhancements

Potential improvements:

1. **Automated mapping generation**: Parse workflow and auto-generate mapping
2. **Coverage badges**: Generate badge for README
3. **Historical tracking**: Track coverage over time
4. **Multi-RGD support**: Validate multiple RGDs
5. **IDE integration**: VS Code extension for real-time validation
6. **AI-assisted validation**: Suggest validation steps for new resources

---

## Summary

This validation system ensures:
- ✅ **100% certification coverage** for all resources
- ✅ **Automatic checks** via git hooks and pipelines
- ✅ **Early detection** of missing validations
- ✅ **Enforced standards** before merge
- ✅ **Clear guidance** for adding new resources

**Deploy confidence with validated infrastructure.**
