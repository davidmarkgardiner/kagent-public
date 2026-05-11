# UK8S Cluster Certification - Integration & Validation Guide

This guide covers two important topics:
1. **Modularizing certification resources** (separating from main RGD)
2. **Validating certification coverage** (ensuring new resources have tests)

---

## Part 1: Modularizing Certification Resources

Currently, certification resources are embedded directly in `uk8scluster.yaml`. You can modularize them for better organization.

### Option 1: Kustomize Components (Recommended)

**Structure:**
```
kro-stack/definitions/uk8scluster/
├── kustomization.yaml          # Main kustomization file
├── base.yaml                   # Core cluster resources
└── components/
    └── certification/
        ├── kustomization.yaml  # Component definition
        └── resources.yaml      # Certification resources
```

**Benefits:**
- ✅ Clean separation of concerns
- ✅ Optional certification (enable/disable per environment)
- ✅ Standard Kubernetes tooling (kustomize)
- ✅ Easy version control and updates

**Setup:**

1. **Create directory structure:**
```bash
mkdir -p kro-stack/definitions/uk8scluster/components/certification
```

2. **Split uk8scluster.yaml:**

**base.yaml** (core resources):
```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: uk8scluster.kro.run
spec:
  schema:
    # ... schema definition ...
  resources:
    - id: resourceGroup
      # ... resource definition ...
    - id: managedCluster
      # ... resource definition ...
    # ... other core resources (NO certification resources) ...
```

**components/certification/resources.yaml** (certification only):
```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: uk8scluster-certification
spec:
  resources:
    - id: certificationWorkflow
      template:
        # ... workflow template ...
    - id: certificationSchedule
      template:
        # ... cron workflow ...
    - id: certificationTrigger
      template:
        # ... trigger job ...
```

**components/certification/kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component
resources:
  - resources.yaml
```

**Main kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - base.yaml

components:
  - components/certification

# To disable certification, comment out:
# components:
#   - components/certification
```

3. **Apply with kustomize:**
```bash
kubectl apply -k kro-stack/definitions/uk8scluster
```

### Option 2: YAML Merge with yq (Build-time)

Use `yq` to merge certification resources at deployment time:

```bash
# Build script
yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' \
  kro-stack/definitions/uk8scluster-base.yaml \
  kro-stack/definitions/uk8scluster-certification.yaml \
  > uk8scluster-merged.yaml

kubectl apply -f uk8scluster-merged.yaml
```

**Pros:**
- Simple merge operation
- Clean source files
- Easy to version control components separately

**Cons:**
- Requires build step
- Generated file needs to be managed
- Not standard Kubernetes approach

### Option 3: Separate RGD with Dependencies (Not Recommended)

Create a separate ResourceGraphDefinition for certification:

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: uk8scluster-certification
spec:
  # Reference the main cluster RGD
  dependencies:
    - uk8scluster.kro.run
  resources:
    # Certification resources
```

**Why not recommended:**
- KRO doesn't natively support cross-RGD dependencies
- More complex lifecycle management
- Harder to ensure proper ordering

---

## Part 2: Certification Coverage Validation

As new resources are added to the RGD, we need to ensure they have corresponding certification tests.

### Validation System Architecture

```
┌────────────────────────────────────────────────────────┐
│ Developer adds new resource to uk8scluster.yaml        │
└──────────────────────┬─────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────┐
│ Git pre-commit hook runs validation                    │
│ ./scripts/validate-certification-coverage              │
└──────────────────────┬─────────────────────────────────┘
                       ▼
         ┌─────────────┴─────────────┐
         ▼                           ▼
    ✅ 100% Coverage            ❌ Missing Coverage
         │                           │
         ▼                           ▼
    Commit Allowed              Commit Blocked
         │                           │
         ▼                           ▼
    Push to Remote              Fix & Re-commit
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Pull Request Created                                    │
└──────────────────────┬─────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────┐
│ Azure DevOps Pipeline runs validation                  │
│ - Install yq                                            │
│ - Run validation script                                │
│ - Generate coverage report                             │
└──────────────────────┬─────────────────────────────────┘
                       ▼
         ┌─────────────┴─────────────┐
         ▼                           ▼
    ✅ Pass                       ❌ Fail
         │                           │
         ▼                           ▼
    PR Approved                 PR Blocked
```

### Validation Script

**Location:** `kro-stack/scripts/validate-certification-coverage`

**What it does:**
1. Parses `uk8scluster.yaml` to extract all resource IDs
2. Extracts validation steps from `certificationWorkflow`
3. Maps each resource to expected validation step
4. Reports coverage percentage
5. Exits with error if coverage < 100%

**Usage:**
```bash
# From repository root
./kro-stack/scripts/validate-certification-coverage

# Or specify RGD path
./kro-stack/scripts/validate-certification-coverage kro-stack/definitions/uk8scluster.yaml
```

**Example output:**
```
==========================================
Certification Coverage Validation
==========================================
RGD File: kro-stack/definitions/uk8scluster.yaml

Extracting resource IDs from RGD...
Found resources:
  - certificationSchedule
  - certificationTrigger
  - certificationWorkflow
  - fluxGitOps
  - jobs
  - managedCluster
  - resourceGroup

Extracting validation steps from certification workflow...
Found validation steps:
  - validate-aso-resources
  - validate-cluster-connectivity
  - validate-configuration
  - validate-flux-gitops
  - validate-kro-resources
  - validate-security-compliance

==========================================
Coverage Analysis
==========================================
⊘ certificationSchedule (infrastructure, skipped)
⊘ certificationTrigger (infrastructure, skipped)
⊘ certificationWorkflow (infrastructure, skipped)
✓ fluxGitOps → validate-flux-gitops
✓ jobs → validate-kro-resources
✓ managedCluster → validate-aso-resources
✓ resourceGroup → validate-aso-resources

==========================================
Summary
==========================================
Covered: 4 resources
Skipped: 3 resources (infrastructure)
Missing: 0 resources

Coverage: 100.0%

✅ VALIDATION PASSED: All resources have certification coverage
```

### Git Pre-Commit Hook

**Installation:**
```bash
# Copy hook to .git/hooks
cp kro-stack/scripts/pre-commit-hook-example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**How it works:**
1. Detects if `uk8scluster.yaml` was modified
2. Runs validation script
3. Blocks commit if coverage < 100%
4. Allows commit if coverage = 100%

**Bypass (not recommended):**
```bash
git commit --no-verify -m "bypassing validation"
```

### Azure DevOps Pipeline

**Location:** `kro-stack/pipelines/validate-certification-coverage.yaml`

**Setup:**
1. Add pipeline to Azure DevOps
2. Configure as required check for PRs
3. Set branch policy to require build

**Pipeline stages:**
1. Install yq
2. Run validation script
3. Publish validation report
4. Post PR comment on failure

**Branch policy:**
```
Repos → Branches → main → Branch Policies
✅ Require build verification
✅ Select "Validate Certification Coverage"
✅ Set as required for PR completion
```

---

## Adding New Resources with Validation

### Workflow

1. **Add resource to RGD:**
```yaml
- id: myNewResource
  template:
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: my-resource
```

2. **Add validation step:**
```yaml
- name: validate-my-resource
  script:
    image: bitnami/kubectl:latest
    command: [bash]
    source: |
      set -e
      echo "=== My Resource Validation ==="
      kubectl get configmap my-resource
      echo "✅ Validation complete"
```

3. **Add to DAG:**
```yaml
- name: validate-my-resource-step
  template: validate-my-resource
  dependencies: [validate-connectivity]
```

4. **Update validation script:**
```bash
# Edit kro-stack/scripts/validate-certification-coverage.sh
declare -A VALIDATION_MAPPING=(
    # ... existing mappings ...
    ["myNewResource"]="validate-my-resource"
)
```

5. **Test locally:**
```bash
./kro-stack/scripts/validate-certification-coverage
```

6. **Commit and push:**
```bash
git add kro-stack/definitions/uk8scluster.yaml
git add kro-stack/scripts/validate-certification-coverage.sh
git commit -m "feat: add myNewResource with certification"
git push
```

### Infrastructure Resources

Some resources don't need runtime validation (they're part of the deployment infrastructure):

```bash
# Edit validate-certification-coverage.sh
INFRASTRUCTURE_RESOURCES=(
    "certificationScripts"
    "certificationWorkflow"
    "certificationSchedule"
    "certificationTrigger"
    "certManagerIdentity"
    "certManagerFederatedCredential"
    # Add your infrastructure resource here
)
```

**When to mark as infrastructure:**
- Resource is part of certification system itself
- Resource is RBAC/auth related
- Resource is a deployment-time utility (Jobs, ConfigMaps)
- Resource doesn't represent cluster functionality

---

## Troubleshooting

### Validation Script: "bash 4+ required"

**Problem:** macOS ships with bash 3.2, script needs bash 4+

**Solution:**
```bash
# Option 1: Use devbox (already has bash 5.3)
devbox shell
./kro-stack/scripts/validate-certification-coverage

# Option 2: Install bash 5 via Homebrew
brew install bash
```

### Validation Script: "yq is not installed"

**Solution:**
```bash
# macOS
brew install yq

# Linux
sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
sudo chmod +x /usr/local/bin/yq
```

### Pre-commit Hook Not Running

**Check:**
```bash
# Verify hook exists and is executable
ls -la .git/hooks/pre-commit

# Make executable if needed
chmod +x .git/hooks/pre-commit
```

### Pipeline Failing in Azure DevOps

**Check:**
1. Verify yq installation step succeeds
2. Check script has correct path
3. Ensure bash 4+ available in pipeline agent
4. Review pipeline logs for errors

---

## Best Practices

### Resource Validation Mapping

**Map resources to appropriate validation categories:**

| Resource Type | Validation Step |
|---------------|-----------------|
| Azure resources (ResourceGroup, ManagedCluster) | validate-aso-resources |
| KRO instances (UK8SCluster, UK8SJobs) | validate-kro-resources |
| Flux resources (GitRepository, Kustomization) | validate-flux-gitops |
| Network resources (Nodes, API Server) | validate-cluster-connectivity |
| Security resources (ServiceAccounts, RBAC) | validate-security-compliance |
| Configuration (YAML, Schema) | validate-configuration |

### Testing Strategy

**Before committing:**
```bash
# 1. Make changes
vim kro-stack/definitions/uk8scluster.yaml

# 2. Update validation mapping if needed
vim kro-stack/scripts/validate-certification-coverage.sh

# 3. Test validation
./kro-stack/scripts/validate-certification-coverage

# 4. If 100%, commit
git add .
git commit -m "feat: add new resource with validation"
```

### Coverage Goals

- **Production:** 100% coverage required
- **Development:** 100% coverage recommended
- **Infrastructure resources:** Can be skipped with justification

---

## Summary

### Modularization Options

1. **Kustomize Components** (Recommended)
   - Standard Kubernetes approach
   - Optional certification per environment
   - Easy to maintain

2. **YAML Merge**
   - Simple merge operation
   - Requires build step
   - Clean source files

3. **Separate RGD**
   - Not recommended
   - Complex dependencies
   - Harder lifecycle management

### Validation System

1. **Validation Script**
   - Parses RGD and checks coverage
   - Maps resources to validation steps
   - Reports missing validations

2. **Git Pre-Commit Hook**
   - Blocks commits with incomplete coverage
   - Runs automatically on commit
   - Can be bypassed (not recommended)

3. **Azure DevOps Pipeline**
   - Validates PRs before merge
   - Required check for branch policy
   - Posts results to PR

### Coverage Enforcement

- ✅ 100% coverage for runtime resources
- ⊘ Infrastructure resources can be skipped
- 🔍 Automatic validation on commit and PR
- 🚫 Blocked commits/PRs if coverage incomplete

**Deploy with confidence using validated infrastructure.**
