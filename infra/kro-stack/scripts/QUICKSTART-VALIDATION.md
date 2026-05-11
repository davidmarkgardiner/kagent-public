# Certification Coverage Validation - Quick Start

> **Goal:** Ensure all resources in the UK8S cluster RGD have corresponding certification tests.

---

## 🚀 Quick Setup (5 minutes)

### 1. Install Git Hook

```bash
# Copy pre-commit hook
cp kro-stack/scripts/pre-commit-hook-example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Test it
./kro-stack/scripts/validate-certification-coverage
```

Expected output:
```
✅ VALIDATION PASSED: All resources have certification coverage
Coverage: 100.0%
```

### 2. Configure Azure DevOps Pipeline (Optional)

```bash
# Copy pipeline YAML
cp kro-stack/pipelines/validate-certification-coverage.yaml azure-pipelines-validation.yml

# Push to repository
git add azure-pipelines-validation.yml
git commit -m "ci: add certification coverage validation pipeline"
git push
```

Then in Azure DevOps:
1. Go to Pipelines → New Pipeline
2. Select your repository
3. Choose "Existing Azure Pipelines YAML file"
4. Select `azure-pipelines-validation.yml`
5. Save and run

### 3. Set Branch Policy (Optional)

In Azure DevOps:
```
Repos → Branches → main → Branch Policies
✅ Require build verification
✅ Select "Validate Certification Coverage"
✅ Set as required for PR completion
```

Done! 🎉

---

## 📖 Daily Workflow

### Adding a New Resource

```bash
# 1. Add resource to RGD
vim kro-stack/definitions/uk8scluster.yaml

# Add:
# - id: myNewResource
#   template:
#     apiVersion: v1
#     kind: ConfigMap
#     ...

# 2. Add validation step (in same file)
# - name: validate-my-resource
#   script:
#     image: bitnami/kubectl:latest
#     command: [bash]
#     source: |
#       kubectl get configmap my-resource
#       echo "✅ Validated"

# 3. Add to DAG
# - name: validate-my-resource-step
#   template: validate-my-resource
#   dependencies: [validate-connectivity]

# 4. Update validation mapping
vim kro-stack/scripts/validate-certification-coverage.sh

# Add to VALIDATION_MAPPING:
# ["myNewResource"]="validate-my-resource"

# 5. Test locally
./kro-stack/scripts/validate-certification-coverage

# 6. Commit (pre-commit hook will validate)
git add .
git commit -m "feat: add myNewResource with certification"
```

### If Validation Fails

```
❌ VALIDATION FAILED: 1 resources lack certification coverage

✗ myNewResource → (no validation mapping defined)

To fix:
1. Add validation mapping to VALIDATION_MAPPING
2. Create corresponding validation step in certificationWorkflow
3. Add resource to INFRASTRUCTURE_RESOURCES if it doesn't need validation
```

**Fix:**
```bash
# Option 1: Add validation mapping
vim kro-stack/scripts/validate-certification-coverage.sh
# Add: ["myNewResource"]="validate-my-resource"

# Option 2: Mark as infrastructure (if it doesn't need validation)
vim kro-stack/scripts/validate-certification-coverage.sh
# Add to INFRASTRUCTURE_RESOURCES: "myNewResource"

# Re-test
./kro-stack/scripts/validate-certification-coverage
```

---

## 🛠️ Troubleshooting

### "bash 4+ required"

```bash
# You're on macOS with bash 3.2
# Solution: Use the wrapper script (already handles this)
./kro-stack/scripts/validate-certification-coverage

# Or install bash 5 via brew
brew install bash
```

### "yq is not installed"

```bash
# macOS
brew install yq

# Linux
sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
sudo chmod +x /usr/local/bin/yq
```

### Pre-commit hook not running

```bash
# Make sure it's executable
chmod +x .git/hooks/pre-commit

# Test manually
.git/hooks/pre-commit
```

### Bypass hook temporarily (NOT RECOMMENDED)

```bash
git commit --no-verify -m "emergency fix"
```

---

## 📊 Validation Mapping Reference

### Current Resources

| Resource ID | Validation Step | Status |
|-------------|----------------|--------|
| resourceGroup | validate-aso-resources | ✅ |
| managedCluster | validate-aso-resources | ✅ |
| fluxGitOps | validate-flux-gitops | ✅ |
| jobs | validate-kro-resources | ✅ |

### Infrastructure Resources (Skipped)

| Resource ID | Reason |
|-------------|--------|
| certificationWorkflow | Part of certification system |
| certificationSchedule | Part of certification system |
| certificationTrigger | Part of certification system |
| certManagerIdentity | RBAC/Auth |
| externalDnsIdentity | RBAC/Auth |
| *FederatedCredential | RBAC/Auth |

### Available Validation Steps

| Step Name | What It Validates |
|-----------|-------------------|
| validate-configuration | YAML schema, UK8SCluster CRD |
| validate-kro-resources | KRO RGDs, instance state |
| validate-aso-resources | Azure resources (RG, AKS) |
| validate-flux-gitops | Flux controllers, GitRepository |
| validate-cluster-connectivity | Nodes, API server, network |
| validate-security-compliance | ServiceAccounts, RBAC, policies |

---

## 🎯 Best Practices

### ✅ DO

- Run validation locally before committing
- Add validation for all runtime resources
- Map resources to appropriate validation steps
- Keep validation scripts simple and fast
- Document why infrastructure resources are skipped

### ❌ DON'T

- Commit without 100% coverage (unless infrastructure resource)
- Bypass pre-commit hook without good reason
- Add resources without corresponding tests
- Mix runtime and infrastructure resources
- Skip validation mapping updates

---

## 📚 Full Documentation

- **Detailed Guide:** [README-VALIDATION.md](./README-VALIDATION.md)
- **Integration Guide:** [../certification/INTEGRATION-GUIDE.md](../certification/INTEGRATION-GUIDE.md)
- **Certification README:** [../certification/README.md](../certification/README.md)

---

## 🔗 Quick Links

```bash
# Test validation
./kro-stack/scripts/validate-certification-coverage

# Edit RGD
vim kro-stack/definitions/uk8scluster.yaml

# Edit validation mapping
vim kro-stack/scripts/validate-certification-coverage.sh

# View pre-commit hook
cat .git/hooks/pre-commit

# View pipeline config
cat kro-stack/pipelines/validate-certification-coverage.yaml
```

---

## ✨ Summary

**What you get:**
- ✅ Automatic validation on every commit
- ✅ PR checks in Azure DevOps
- ✅ 100% certification coverage enforcement
- ✅ Clear error messages when coverage incomplete
- ✅ Easy workflow for adding new resources

**Time investment:**
- Initial setup: 5 minutes
- Per new resource: 2 minutes (add validation mapping)
- Ongoing: Zero (automated)

**Deploy with confidence! 🚀**
